# -*- coding: utf-8 -*-
"""Webhook（HTTP 回调）接入支持。

按照最新官方文档：
  - 平台通过 HTTP POST 将事件推送到开发者配置的回调地址（端口仅允许 80/443/8080/8443）
  - 推送请求头携带 ``X-Signature-Ed25519``（hex 签名）与 ``X-Signature-Timestamp``（签名时间戳）
  - 签名内容为 ``timestamp + body``，使用 Ed25519 算法；
    私钥 seed 由 AppSecret 循环填充至 32 字节生成
  - 回调地址验证（op=13）：请求 d 中携带 ``plain_token`` 与 ``event_ts``，
    服务端需返回 ``{"plain_token": ..., "signature": ...}``，
    signature 为对 ``event_ts + plain_token`` 的 Ed25519 签名（hex）
  - 事件推送处理成功后需返回 ``{"op": 12}``（HTTP Callback ACK）

本模块依赖 ``PyNaCl``（可选依赖，安装: ``pip install pynacl``）。
"""

import asyncio
import json
from typing import TYPE_CHECKING, Callable, Optional

from aiohttp import web

from . import logging

if TYPE_CHECKING:  # pragma: no cover
    from .client import Client

try:
    from nacl.signing import SigningKey

    _HAS_NACL = True
except ImportError:  # pragma: no cover
    _HAS_NACL = False

_log = logging.get_logger()

WEBHOOK_OP_DISPATCH = 0
WEBHOOK_OP_HTTP_CALLBACK_ACK = 12
WEBHOOK_OP_CALLBACK_VALIDATE = 13

# 平台回调请求的 User-Agent 标识（仅用于日志判断）
QQBOT_CALLBACK_UA = "QQBot-Callback"


def _generate_seed(secret: str) -> bytes:
    """以 secret 为种子循环填充至 32 字节（ed25519.SeedSize）。

    与官方文档算法一致：长度不足 32 字节时重复填充后截断。
    """
    seed = bytes(secret, "utf-8")
    if len(seed) == 0:
        raise ValueError("secret 不能为空")
    while len(seed) < 32:
        seed += seed
    return seed[:32]


def _require_nacl():
    if not _HAS_NACL:
        raise RuntimeError(
            "Webhook 模式需要 PyNaCl 库支持，请先安装: pip install pynacl"
        )


def generate_signature(event_ts: str, plain_token: str, secret: str) -> str:
    """生成回调地址验证所需的签名。

    对 ``event_ts + plain_token`` 进行 Ed25519 签名并做 hex 编码，
    用于响应平台的 op=13 验证请求。

    Args:
      event_ts (str): 验证请求中的时间戳。
      plain_token (str): 验证请求中的待签名字符串。
      secret (str): 机器人 AppSecret。

    Returns:
      str: hex 编码的签名字符串。
    """
    _require_nacl()
    sign_key = SigningKey(_generate_seed(secret))
    msg = event_ts + plain_token
    return sign_key.sign(msg.encode("utf-8")).signature.hex()


def check_signature(event_ts: str, signature: str, body: str, secret: str) -> bool:
    """校验事件推送请求的签名。

    按照官方文档，签名内容为 ``timestamp + body``，签名字段在请求头
    ``X-Signature-Ed25519`` 中。

    Args:
      event_ts (str): 请求头 ``X-Signature-Timestamp`` 中的时间戳。
      signature (str): 请求头 ``X-Signature-Ed25519`` 中的 hex 签名。
      body (str): 原始请求体文本。
      secret (str): 机器人 AppSecret。

    Returns:
      bool: 验证通过返回 True，否则 False。
    """
    _require_nacl()
    if not event_ts or not signature:
        return False
    sign_key = SigningKey(_generate_seed(secret))
    msg = event_ts + body
    try:
        # PyNaCl 的 verify 签名为 verify(smessage, signature)
        sign_key.verify_key.verify(msg.encode("utf-8"), bytes.fromhex(signature))
    except Exception:
        return False
    return True


class WebhookServer:
    """Webhook HTTP 回调服务器。

    将平台推送的事件转换后交给 :class:`botpy.Client` 的事件回调处理，
    用法与 WebSocket 模式完全一致（on_at_message_create / on_group_at_message_create 等）。

    用法::

        client = MyClient(intents=botpy.Intents(public_messages=True))
        server = botpy.webhook.WebhookServer(client, secret="your secret")
        # 配合 asyncio 直接运行:
        await server.start(host="0.0.0.0", port=8080)
        # 或直接使用 client.webhook_run(appid, secret, port=8080)
    """

    def __init__(
        self,
        client: "Client",
        secret: str,
        path: str = "/bot/webhook",
        request_handler: Optional[Callable[[dict], None]] = None,
    ):
        """
        Args:
          client (Client): 机器人客户端实例，事件将分发到其 on_xx 回调。
          secret (str): 机器人 AppSecret，用于签名校验。
          path (str): 回调路径。Defaults to "/bot/webhook"
          request_handler (Callable): 自定义原始 payload 处理函数（可选），
            传入后事件在分发到 client 之外还会调用该函数。
        """
        self.client = client
        self.secret = secret
        self.path = path
        self.request_handler = request_handler
        self._runner: Optional[web.AppRunner] = None

    def make_app(self) -> web.Application:
        """构建 aiohttp Application。"""
        app = web.Application()
        app.router.add_post(self.path, self._handle)
        return app

    async def _handle(self, request: web.Request) -> web.Response:
        body = await request.text()
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            return web.json_response({"code": -3}, status=400)

        op = payload.get("op")

        # 回调地址验证（op=13）
        if op == WEBHOOK_OP_CALLBACK_VALIDATE:
            d = payload.get("d") or {}
            plain_token = d.get("plain_token", "")
            event_ts = d.get("event_ts", "")
            signature = generate_signature(event_ts, plain_token, self.secret)
            _log.info("[botpy] webhook 回调地址验证通过")
            return web.json_response({"plain_token": plain_token, "signature": signature})

        # 事件推送：先验签
        signature = request.headers.get("X-Signature-Ed25519", "")
        event_ts = request.headers.get("X-Signature-Timestamp", "")
        if not check_signature(event_ts, signature, body, self.secret):
            _log.warning("[botpy] webhook 签名校验失败，拒绝处理")
            return web.json_response({"code": -1}, status=403)

        # 分发事件（复用 WebSocket 的事件解析器与 on_xx 回调）
        if op == WEBHOOK_OP_DISPATCH:
            if self.request_handler:
                self.request_handler(payload)
            if not self.client.dispatch_event_payload(payload):
                _log.warning("[botpy] webhook 收到未知事件: %s", payload.get("t"))

        # 校验成功，返回 HTTP Callback ACK（op=12）
        return web.json_response({"op": WEBHOOK_OP_HTTP_CALLBACK_ACK})

    async def start(self, host: str = "0.0.0.0", port: int = 8080) -> None:
        """启动 HTTP 服务（阻塞直到 cancel）。

        注意: 平台仅允许回调端口 80、443、8080、8443。
        """
        self._runner = web.AppRunner(self.make_app())
        await self._runner.setup()
        site = web.TCPSite(self._runner, host, port)
        await site.start()
        _log.info(f"[botpy] webhook 服务已启动: http://{host}:{port}{self.path}")
        try:
            # 保持运行直到被取消
            while True:
                await asyncio.Event().wait()
        finally:
            await self.stop()

    async def stop(self) -> None:
        """停止 HTTP 服务。"""
        if self._runner:
            await self._runner.cleanup()
            self._runner = None
            _log.info("[botpy] webhook 服务已停止")
