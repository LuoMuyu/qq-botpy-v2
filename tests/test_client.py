# -*- coding: utf-8 -*-
"""Client 兼容性测试：不依赖网络，验证与原版 botpy 一致的构造与分发行为。"""

import asyncio

import pytest

from botpy import Client, Intents
from botpy.api import BotAPI
from botpy.http import BotHttp


class MyClient(Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.received = []

    async def on_group_at_message_create(self, message):
        self.received.append(("group_at_message_create", message))

    async def on_c2c_message_create(self, message):
        self.received.append(("c2c_message_create", message))

    async def on_group_join_request(self, request):
        self.received.append(("group_join_request", request))


@pytest.fixture
def intents():
    return Intents(public_messages=True)


def test_client_construct_compat(intents):
    """与原版 botpy 相同的构造参数。"""
    client = MyClient(
        intents=intents,
        timeout=10,
        is_sandbox=True,
        bot_log=False,
        ext_handlers=False,
    )
    assert client.intents == intents.value
    assert isinstance(client.http, BotHttp)
    assert isinstance(client.api, BotAPI)
    assert client.http.is_sandbox is True
    assert client.ret_coro is False
    assert client.is_closed() is False
    assert client.robot is None


def test_client_ws_dispatch(intents):
    client = MyClient(intents=intents, bot_log=False, ext_handlers=False)

    payload = {
        "id": "EVT1",
        "op": 0,
        "t": "GROUP_AT_MESSAGE_CREATE",
        "s": 1,
        "d": {
            "id": "M1",
            "author": {"member_openid": "MEM1"},
            "content": "hi",
            "group_openid": "G1",
        },
    }

    async def scenario():
        # 事件任务在 client.loop 上调度，需绑定到当前运行的循环
        client.loop = asyncio.get_running_loop()
        client.dispatch_event_payload(payload)
        await asyncio.sleep(0.05)
        pending = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
        await asyncio.gather(*pending, return_exceptions=True)

    asyncio.run(scenario())

    assert len(client.received) == 1
    name, msg = client.received[0]
    assert name == "group_at_message_create"
    assert msg.content == "hi"
    assert msg.group_openid == "G1"


def test_client_dispatch_unknown_event(intents):
    client = MyClient(intents=intents, bot_log=False, ext_handlers=False)
    assert client.dispatch_event_payload({"op": 0, "t": "NOT_A_EVENT", "d": {}}) is False
    assert client.dispatch_event_payload({"op": 1, "t": "GROUP_AT_MESSAGE_CREATE", "d": {}}) is False
