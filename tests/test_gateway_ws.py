# -*- coding: utf-8 -*-
"""WebSocket 网关集成测试：用本地伪造网关验证完整握手协议。

协议流程（对齐最新文档）：
  client 连接 → server 下发 Hello(op=10, 含 heartbeat_interval)
  → client 发送 Identify(op=2, token="QQBot x", intents, shard)
  → server 下发 Ready(op=0, d 含 session_id/user/shard)
  → client 按 heartbeat_interval 定时发送心跳(op=1, d=最新 s)
  → server 下发业务事件 → client 解析并分发到 on_xx 回调
"""

import asyncio
import json
import time

import pytest
from aiohttp import WSMsgType, web
from aiohttp.test_utils import TestServer

from botpy import logging
from botpy.connection import ConnectionSession
from botpy.gateway import BotWebSocket
from botpy.robot import Token

_log = logging.get_logger()


class FakeGateway:
    """伪造的 QQ 网关 WebSocket 服务。"""

    def __init__(self):
        self.identify_payload = None
        self.resumed_payload = None
        self.heartbeats = []
        self.session_id = "sess-1"
        self.seq = 0
        self._ws = None

    async def handler(self, request):
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        self._ws = ws

        # 1. Hello
        await ws.send_json({"op": 10, "d": {"heartbeat_interval": 100}})

        async for msg in ws:
            if msg.type != WSMsgType.TEXT:
                break
            payload = json.loads(msg.data)
            op = payload.get("op")

            if op == 2:  # Identify
                self.identify_payload = payload
                self.seq += 1
                await ws.send_json({
                    "op": 0, "s": self.seq, "t": "READY",
                    "d": {
                        "version": 1,
                        "session_id": self.session_id,
                        "user": {"id": "10000", "username": "测试机器人", "bot": True},
                        "shard": [0, 1],
                    },
                })
            elif op == 6:  # Resume
                self.resumed_payload = payload
                self.seq += 1
                await ws.send_json({"op": 0, "s": self.seq, "t": "RESUMED", "d": None})
            elif op == 1:  # Heartbeat
                self.heartbeats.append(payload.get("d"))

        return ws


@pytest.fixture
async def gateway():
    app = web.Application()
    gw = FakeGateway()
    app.router.add_get("/websocket", gw.handler)
    server = TestServer(app)
    await server.start_server()
    gw.url = f"ws://{server.host}:{server.port}/websocket"
    yield gw
    await server.close()


def make_session_and_connection(gateway, dispatched):
    token = Token("appid", "secret")
    token.access_token = "preset-token"
    token.expires_in = int(time.time()) + 3600  # 避免测试中发起真实 token 请求

    async def connect(session):
        pass

    def dispatch(name, *args):
        dispatched.append((name, args))

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
async def test_gateway_full_handshake(gateway):
    dispatched = []
    conn, session = make_session_and_connection(gateway, dispatched)

    ws_client = BotWebSocket(session, conn)
    task = asyncio.get_running_loop().create_task(ws_client.ws_connect())

    # 等待握手与若干次心跳
    for _ in range(100):
        if gateway.identify_payload and len(gateway.heartbeats) >= 2:
            break
        await asyncio.sleep(0.02)

    # 1. Identify 格式符合最新文档
    assert gateway.identify_payload is not None
    assert gateway.identify_payload["op"] == 2
    d = gateway.identify_payload["d"]
    assert d["token"] == "QQBot preset-token"
    assert d["intents"] == 1 << 25
    assert d["shard"] == [0, 1]

    # 2. Ready 事件被解析，session_id 已保存
    assert session["session_id"] == "sess-1"

    # 3. 心跳按 Hello 下发的 100ms 间隔发送（而非固定 30s）
    assert len(gateway.heartbeats) >= 2

    # 4. 派发 ready 事件
    assert ("ready", ()) in dispatched or any(n == "ready" for n, _ in dispatched)

    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


@pytest.mark.asyncio
async def test_gateway_dispatch_event_to_parser(gateway):
    """网关下发业务事件后应解析为模型并分发到回调。"""
    dispatched = []
    conn, session = make_session_and_connection(gateway, dispatched)

    ws_client = BotWebSocket(session, conn)
    task = asyncio.get_running_loop().create_task(ws_client.ws_connect())

    # 等待连接就绪
    for _ in range(100):
        if session["session_id"]:
            break
        await asyncio.sleep(0.02)

    # 下发一条群消息事件
    gateway.seq += 1
    await gateway._ws.send_json({
        "op": 0, "id": "EVT-G1", "s": gateway.seq,
        "t": "GROUP_AT_MESSAGE_CREATE",
        "d": {
            "id": "M-G1",
            "author": {"member_openid": "MEM1"},
            "content": "ping",
            "group_openid": "G1",
            "timestamp": "2026-07-21T10:00:00+08:00",
            "message_type": 0,
        },
    })

    for _ in range(100):
        if any(n == "group_at_message_create" for n, _ in dispatched):
            break
        await asyncio.sleep(0.02)

    names = [n for n, _ in dispatched]
    assert "group_at_message_create" in names
    name, args = next((n, a) for n, a in dispatched if n == "group_at_message_create")
    msg = args[0]
    assert msg.id == "M-G1"
    assert msg.content == "ping"
    assert msg.group_openid == "G1"

    # 事件序号应被记录，下一次心跳 d 应携带最新 s
    assert session["last_seq"] == gateway.seq
    for _ in range(100):
        if gateway.heartbeats and gateway.heartbeats[-1] == gateway.seq:
            break
        await asyncio.sleep(0.02)
    assert gateway.heartbeats[-1] == gateway.seq

    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
