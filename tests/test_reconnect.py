# -*- coding: utf-8 -*-
"""断线重连回归测试：模拟服务端多种断开方式，验证客户端自动重连。"""

import asyncio
import json

import pytest
from aiohttp import WSMsgType, web
from aiohttp.test_utils import TestServer

from botpy import logging
from botpy.connection import ConnectionSession
from botpy.gateway import BotWebSocket
from botpy.robot import Token

_log = logging.get_logger()


class ReconnectGateway:
    """伪造网关：可配置第 N 次连接时的断开方式，统计握手次数。

    支持完整协议：Hello / Identify→Ready / Resume→RESUMED / Heartbeat ACK。
    """

    def __init__(self, break_mode: str, mute_ack: bool = False):
        self.break_mode = break_mode  # "tcp" 硬断开 / "close_frame" 带关闭帧 / "none" 不断开
        self.mute_ack = mute_ack  # True 时不回复心跳 ACK（模拟僵尸连接）
        self.connections = 0
        self.identifies = 0
        self.resumes = 0
        self._ws = None
        self._request = None
        self.break_at = 1  # 在第几次连接上断开

    async def handler(self, request):
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        self.connections += 1
        self._ws = ws
        self._request = request

        await ws.send_json({"op": 10, "d": {"heartbeat_interval": 100}})

        async for msg in ws:
            if msg.type != WSMsgType.TEXT:
                break
            payload = json.loads(msg.data)
            if payload.get("op") == 2:  # Identify
                self.identifies += 1
                await ws.send_json({
                    "op": 0, "s": 1, "t": "READY",
                    "d": {"version": 1, "session_id": f"sess-{self.connections}",
                          "user": {"id": "1", "username": "bot", "bot": True},
                          "shard": [0, 1]},
                })
                await self._maybe_break(ws, request)
            elif payload.get("op") == 6:  # Resume
                self.resumes += 1
                await ws.send_json({"op": 0, "s": 2, "t": "RESUMED", "d": None})
                await self._maybe_break(ws, request)
            elif payload.get("op") == 1:  # Heartbeat
                if not self.mute_ack:
                    await ws.send_json({"op": 11})
        return ws

    async def _maybe_break(self, ws, request):
        if self.connections != self.break_at:
            return
        if self.break_mode == "tcp":
            # 模拟网关/NAT 硬断开：不发关闭帧直接断 TCP
            await asyncio.sleep(0.05)
            request.transport.close()
        elif self.break_mode == "close_frame":
            await asyncio.sleep(0.05)
            await ws.close(code=1000, message=b"server restart")


async def wait_until(predicate, timeout=8.0, step=0.05):
    deadline = asyncio.get_running_loop().time() + timeout
    while asyncio.get_running_loop().time() < deadline:
        if predicate():
            return True
        await asyncio.sleep(step)
    return False


def make_client(gateway, dispatched):
    token = Token("appid", "secret")
    token.access_token = "preset"
    token.expires_in = 2 ** 31  # 避免测试中请求真实 token 接口

    async def connect(session):
        # 与 client.bot_connect 完全一致的包装方式
        ws_client = BotWebSocket(session, conn)
        try:
            await ws_client.ws_connect()
        except Exception as e:
            await ws_client.on_error(e)

    def dispatch(name, *args):
        dispatched.append(name)

    conn = ConnectionSession(max_async=1, connect=connect, dispatch=dispatch)
    session = {
        "session_id": "",
        "last_seq": 0,
        "intent": 1 << 25,
        "token": token,
        "url": gateway.url,
        "shards": {"shard_id": 0, "shard_count": 1},
    }
    return conn, session


@pytest.mark.asyncio
@pytest.mark.parametrize("break_mode", ["tcp", "close_frame"])
async def test_reconnect_after_disconnect(break_mode):
    gw = ReconnectGateway(break_mode)
    app = web.Application()
    app.router.add_get("/websocket", gw.handler)
    server = TestServer(app)
    await server.start_server()
    gw.url = f"ws://{server.host}:{server.port}/websocket"

    dispatched = []
    conn, session = make_client(gw, dispatched)

    # 模拟 _pool_init 的重连循环
    async def pool_loop():
        while True:
            await conn.multi_run(0)
            await asyncio.sleep(0.05)  # 列表为空时 multi_run 立即返回，避免忙等

    loop_task = asyncio.get_running_loop().create_task(pool_loop())
    conn.add(session)

    # 第一次连接成功
    ok1 = await wait_until(lambda: gw.connections >= 1 and gw.identifies >= 1)
    assert ok1, "首次连接/鉴权失败"

    # 网关断开后，客户端应自动重连并完成 Resume/重新鉴权
    ok2 = await wait_until(
        lambda: gw.connections >= 2 and (gw.identifies + gw.resumes) >= 2, timeout=10
    )
    assert ok2, (
        f"[{break_mode}] 断开后未重连! connections={gw.connections}, "
        f"identifies={gw.identifies}, resumes={gw.resumes}"
    )

    await teardown(gw, loop_task, server)


@pytest.mark.asyncio
async def test_reconnect_on_heartbeat_ack_timeout():
    """心跳连续无 ACK（僵尸连接）时，看门狗应强制断开并自动重连。"""
    gw = ReconnectGateway(break_mode="none", mute_ack=True)
    app = web.Application()
    app.router.add_get("/websocket", gw.handler)
    server = TestServer(app)
    await server.start_server()
    gw.url = f"ws://{server.host}:{server.port}/websocket"

    dispatched = []
    conn, session = make_client(gw, dispatched)

    async def pool_loop():
        while True:
            await conn.multi_run(0)
            await asyncio.sleep(0.05)

    loop_task = asyncio.get_running_loop().create_task(pool_loop())
    conn.add(session)

    ok1 = await wait_until(lambda: gw.connections >= 1 and gw.identifies >= 1)
    assert ok1, "首次连接/鉴权失败"

    # 心跳间隔 100ms，连续 2 次无 ACK 后应在 1 秒内强制重连；
    # 重连后仍无 ACK，会持续重连，这里验证至少发生了 3 次连接
    ok2 = await wait_until(lambda: gw.connections >= 3, timeout=10)
    assert ok2, f"心跳看门狗未触发重连! connections={gw.connections}"

    await teardown(gw, loop_task, server)


async def teardown(gw, loop_task, server):
    """结束客户端连接与服务端，避免 aiohttp 关闭时长时间等待。"""
    loop_task.cancel()
    try:
        await loop_task
    except asyncio.CancelledError:
        pass
    if gw._request and gw._request.transport:
        gw._request.transport.close()  # 断开所有存活连接，让服务端 handler 结束
    await asyncio.sleep(0.1)
    await server.close()
