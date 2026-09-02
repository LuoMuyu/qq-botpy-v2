# -*- coding: utf-8 -*-
"""优雅关闭验收测试（v1.0.2）。

场景：调用方取消 Client.start() 任务（如收到 stop 信号）后，不应出现：
  1. aiohttp "Unclosed client session"
  2. WARNING "[botpy] 会话未正常回队，强制放回重连队列"
  3. ERROR "websocket连接 ... CancelledError" 回溯
  4. "Task exception was never retrieved"

同时验证非关闭期的断线重连语义不受影响（见 test_reconnect.py）。
"""

import asyncio
import json
import logging

import pytest
from aiohttp import WSMsgType, web
from aiohttp.test_utils import TestServer

import botpy
from botpy import logging as botpy_logging
from botpy.api import BotAPI
from botpy.http import BotHttp
from botpy.robot import Token

_log = botpy_logging.get_logger()


class ShutdownGateway:
    """伪造网关：完整协议握手 + 心跳 ACK，统计连接与鉴权次数。"""

    def __init__(self):
        self.connections = 0
        self.identifies = 0
        self.closed_cleanly = False

    async def handler(self, request):
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        self.connections += 1
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
                          "user": {"id": "10000", "username": "测试机器人", "bot": True},
                          "shard": [0, 1]},
                })
            elif payload.get("op") == 1:  # Heartbeat
                await ws.send_json({"op": 11})
        self.closed_cleanly = True
        return ws


async def wait_until(predicate, timeout=8.0, step=0.02):
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout
    while loop.time() < deadline:
        if predicate():
            return True
        await asyncio.sleep(step)
    return False


@pytest.mark.asyncio
async def test_graceful_shutdown_by_cancel_start(monkeypatch, caplog):
    """取消 start() 任务优雅关闭：无 error 日志、无回队告警、无未取回异常。"""
    gw = ShutdownGateway()
    app = web.Application()
    app.router.add_get("/websocket", gw.handler)
    server = TestServer(app)
    await server.start_server()
    gw.url = f"ws://{server.host}:{server.port}/websocket"

    # 桩掉登录与网关地址获取（不访问真实平台）
    async def fake_login(self, token):
        return {"id": "10000", "username": "测试机器人", "avatar": ""}

    async def fake_get_ws_url(self):
        return {
            "url": gw.url,
            "shards": 1,
            "session_start_limit": {"total": 1, "remaining": 1, "reset_after": 1, "max_concurrency": 1},
        }

    async def fake_check_token(self):
        # 避免访问真实 token 接口
        if self.access_token is None:
            self.access_token = "fake-token"
            self.expires_in = 2**31

    monkeypatch.setattr(BotHttp, "login", fake_login)
    monkeypatch.setattr(BotAPI, "get_ws_url", fake_get_ws_url)
    monkeypatch.setattr(Token, "check_token", fake_check_token)

    class MyClient(botpy.Client):
        pass

    with caplog.at_level(logging.DEBUG):
        client = MyClient(intents=botpy.Intents(public_messages=True), bot_log=False, ext_handlers=False)
        start_task = asyncio.get_running_loop().create_task(client.start("appid", "secret"))

        # 等待 READY（网关侧收到 Identify 即视为就绪）
        assert await wait_until(lambda: gw.identifies >= 1), "客户端未完成鉴权"
        await asyncio.sleep(0.3)  # 让心跳与事件循环稳定运行片刻

        # 模拟 stop 信号：取消 start 任务
        start_task.cancel()
        try:
            await start_task
        except asyncio.CancelledError:
            pass

        # 关闭是异步收尾，再给事件循环一点时间暴露任何遗留问题
        await asyncio.sleep(0.5)

    # 验收断言
    errors = [r for r in caplog.records if r.levelno >= logging.ERROR]
    assert not errors, f"关闭过程出现 error 级日志: {[r.getMessage() for r in errors]}"

    requeue_warnings = [
        r for r in caplog.records
        if r.levelno == logging.WARNING and "会话未正常回队" in r.getMessage()
    ]
    assert not requeue_warnings, "关闭过程出现回队告警"

    noise = [
        r for r in caplog.records
        if "Unclosed client session" in r.getMessage()
        or "Unclosed connector" in r.getMessage()
        or "never retrieved" in r.getMessage()
    ]
    assert not noise, f"出现资源泄漏/未取回异常日志: {[r.getMessage() for r in noise]}"

    # 会话任务应已全部退出
    assert client._connection is not None
    assert all(t.done() for t in client._connection._tasks), "存在未退出的 ws 会话任务"

    await server.close()


@pytest.mark.asyncio
async def test_graceful_shutdown_by_close_call(monkeypatch, caplog):
    """直接调用 await client.close() 优雅关闭，同样无噪音。"""
    gw = ShutdownGateway()
    app = web.Application()
    app.router.add_get("/websocket", gw.handler)
    server = TestServer(app)
    await server.start_server()
    gw.url = f"ws://{server.host}:{server.port}/websocket"

    async def fake_login(self, token):
        return {"id": "10000", "username": "测试机器人", "avatar": ""}

    async def fake_get_ws_url(self):
        return {
            "url": gw.url,
            "shards": 1,
            "session_start_limit": {"total": 1, "remaining": 1, "reset_after": 1, "max_concurrency": 1},
        }

    async def fake_check_token(self):
        # 避免访问真实 token 接口
        if self.access_token is None:
            self.access_token = "fake-token"
            self.expires_in = 2**31

    monkeypatch.setattr(BotHttp, "login", fake_login)
    monkeypatch.setattr(BotAPI, "get_ws_url", fake_get_ws_url)
    monkeypatch.setattr(Token, "check_token", fake_check_token)

    class MyClient(botpy.Client):
        pass

    with caplog.at_level(logging.DEBUG):
        client = MyClient(intents=botpy.Intents(public_messages=True), bot_log=False, ext_handlers=False)
        start_task = asyncio.get_running_loop().create_task(client.start("appid", "secret"))
        assert await wait_until(lambda: gw.identifies >= 1), "客户端未完成鉴权"
        await asyncio.sleep(0.3)

        # 模拟直接调用 close()（不取消 start 任务）
        await client.close()
        await wait_until(lambda: start_task.done(), timeout=5)
        await asyncio.sleep(0.3)

    errors = [r for r in caplog.records if r.levelno >= logging.ERROR]
    assert not errors, f"关闭过程出现 error 级日志: {[r.getMessage() for r in errors]}"

    requeue_warnings = [
        r for r in caplog.records
        if r.levelno == logging.WARNING and "会话未正常回队" in r.getMessage()
    ]
    assert not requeue_warnings, "关闭过程出现回队告警"

    noise = [
        r for r in caplog.records
        if "Unclosed client session" in r.getMessage()
        or "Unclosed connector" in r.getMessage()
        or "never retrieved" in r.getMessage()
    ]
    assert not noise, f"出现资源泄漏/未取回异常日志: {[r.getMessage() for r in noise]}"

    await server.close()
