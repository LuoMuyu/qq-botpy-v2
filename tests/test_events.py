# -*- coding: utf-8 -*-
"""事件解析与事件模型测试（含最新新增事件）。"""

import pytest

from botpy.api import BotAPI
from botpy.connection import ConnectionState
from botpy.http import BotHttp
from botpy.manage import GroupJoinRequest, GroupMemberEvent
from botpy.message import C2CMessage, GroupMessage


def make_state(dispatch):
    return ConnectionState(dispatch, BotAPI(BotHttp(timeout=5)))


def collect(events):
    def dispatch(name, *args):
        events.append((name, args))

    return dispatch


GROUP_MSG_PAYLOAD = {
    "id": "EVT1",
    "op": 0,
    "t": "GROUP_AT_MESSAGE_CREATE",
    "s": 1,
    "d": {
        "id": "ROBOT1.0_xxx",
        "author": {"id": "A1", "member_openid": "MEM1", "username": "nick", "member_role": "member"},
        "content": "hello bot",
        "group_openid": "GROUP1",
        "timestamp": "2026-07-21T10:00:00+08:00",
        "message_type": 0,
        "message_scene": {"source": "default", "ext": ["msg_idx=REFIDX_abc==", "auth_token=t"]},
        "attachments": [
            {"content_type": "voice", "url": "https://e.com/a.silk", "voice_wav_url": "https://e.com/a.wav",
             "asr_refer_text": "语音内容"}
        ],
        "mentions": [{"id": "A1", "member_openid": "MEM1"}],
    },
}


@pytest.mark.asyncio
async def test_parse_group_at_message_create():
    events = []
    state = make_state(collect(events))
    state.parse_group_at_message_create(GROUP_MSG_PAYLOAD)

    name, args = events[0]
    assert name == "group_at_message_create"
    msg: GroupMessage = args[0]
    assert msg.id == "ROBOT1.0_xxx"
    assert msg.content == "hello bot"
    assert msg.group_openid == "GROUP1"
    assert msg.author.member_openid == "MEM1"
    assert msg.author.member_role == "member"
    # 新增字段
    assert msg.message_type == 0
    assert msg.get_scene_ext()["msg_idx"] == "REFIDX_abc=="
    assert msg.attachments[0].voice_wav_url == "https://e.com/a.wav"
    assert msg.attachments[0].asr_refer_text == "语音内容"
    assert msg.event_id == "EVT1"


@pytest.mark.asyncio
async def test_parse_group_message_create_full_mode():
    events = []
    state = make_state(collect(events))
    payload = dict(
        GROUP_MSG_PAYLOAD,
        t="GROUP_MESSAGE_CREATE",
        d=dict(
            GROUP_MSG_PAYLOAD["d"],
            message_type=103,
            msg_elements=[
                {"msg_idx": "REFIDX_ref==", "message_type": 0, "content": "被引用的内容"}
            ],
        ),
    )
    state.parse_group_message_create(payload)

    name, args = events[0]
    assert name == "group_message_create"
    msg: GroupMessage = args[0]
    assert msg.message_type == 103
    assert msg.msg_elements is not None


@pytest.mark.asyncio
async def test_parse_c2c_message_create():
    events = []
    state = make_state(collect(events))
    payload = {
        "id": "EVT2",
        "op": 0,
        "t": "C2C_MESSAGE_CREATE",
        "s": 2,
        "d": {
            "id": "ROBOT1.0_yyy",
            "author": {"id": "U1", "user_openid": "U1", "username": "", "bot": False},
            "content": "hi",
            "timestamp": "2026-07-21T10:00:00+08:00",
            "message_type": 3,
            "ark_data": {"ark_type": "miniapp", "ark_name": "小程序", "fields": {"title": "t"}},
            "message_scene": {"source": "default", "ext": ["msg_idx=REFIDX_x=="]},
        },
    }
    state.parse_c2c_message_create(payload)

    name, args = events[0]
    assert name == "c2c_message_create"
    msg: C2CMessage = args[0]
    assert msg.author.user_openid == "U1"
    assert msg.openid == "U1"
    assert msg.message_type == 3
    assert msg.ark_data["ark_type"] == "miniapp"


@pytest.mark.asyncio
async def test_parse_group_join_request():
    events = []
    state = make_state(collect(events))
    payload = {
        "id": "EVT3",
        "op": 0,
        "t": "GROUP_JOIN_REQUEST",
        "s": 3,
        "d": {
            "group_openid": "GROUP1",
            "join_request_id": "JR1",
            "member_openid": "MEM9",
            "username": "张三",
            "apply_at": "2026-08-05T16:21:40+08:00",
            "apply_source": "invited",
            "invited_by": "MEM1",
            "bot": False,
            "verify_info": {"method": "verify_message", "verify_message": "就快乐了"},
        },
    }
    state.parse_group_join_request(payload)

    name, args = events[0]
    assert name == "group_join_request"
    req: GroupJoinRequest = args[0]
    assert req.join_request_id == "JR1"
    assert req.member_openid == "MEM9"
    assert req.username == "张三"
    assert req.apply_source == "invited"
    assert req.invited_by == "MEM1"
    assert req.verify_info["method"] == "verify_message"


@pytest.mark.asyncio
async def test_group_join_request_approve_decline():
    class FakeHttp:
        def __init__(self):
            self.calls = []

        async def request(self, route, **kwargs):
            self.calls.append((route, kwargs))
            return {}

    api = BotAPI(FakeHttp())
    req = GroupJoinRequest(api, "EVT3", {
        "group_openid": "GROUP1",
        "join_request_id": "JR1",
        "member_openid": "MEM9",
    })
    await req.approve()
    route, kwargs = api._http.calls[-1]
    assert route.url.endswith("/v2/groups/GROUP1/approval_join_request/MEM9")
    assert kwargs["json"]["op"] == "approve"

    await req.decline(reject_reason="不满", add_to_member_blacklist=True)
    route, kwargs = api._http.calls[-1]
    assert kwargs["json"]["op"] == "decline"
    assert kwargs["json"]["reject_reason"] == "不满"
    assert kwargs["json"]["add_to_member_blacklist"] is True


@pytest.mark.asyncio
async def test_parse_group_member_add_quit():
    events = []
    state = make_state(collect(events))
    d = {
        "timestamp": 1784276757,
        "group_openid": "GROUP1",
        "member_openid": "MEM2",
        "user_openid": "U2",
    }
    state.parse_group_member_add({"id": "EVT4", "op": 0, "t": "GROUP_MEMBER_ADD", "s": 4, "d": d})
    state.parse_group_member_quit({"id": "EVT5", "op": 0, "t": "GROUP_MEMBER_QUIT", "s": 5, "d": d})

    assert events[0][0] == "group_member_add"
    ev: GroupMemberEvent = events[0][1][0]
    assert ev.member_openid == "MEM2"
    assert ev.group_openid == "GROUP1"

    assert events[1][0] == "group_member_quit"


@pytest.mark.asyncio
async def test_parse_guild_at_message_compat():
    """原版频道事件保持不变。"""
    events = []
    state = make_state(collect(events))
    payload = {
        "id": "EVT6",
        "op": 0,
        "t": "AT_MESSAGE_CREATE",
        "s": 6,
        "d": {
            "id": "M1",
            "author": {"id": "U1", "username": "n"},
            "content": "hello",
            "channel_id": "C1",
            "guild_id": "G1",
            "timestamp": "2026-07-21T10:00:00+08:00",
        },
    }
    state.parse_at_message_create(payload)
    name, args = events[0]
    assert name == "at_message_create"
    msg = args[0]
    assert msg.channel_id == "C1"
    assert msg.guild_id == "G1"


@pytest.mark.asyncio
async def test_parser_registry_contains_all_events():
    events = []
    state = make_state(collect(events))
    expected = {
        # 原版事件
        "ready", "resumed", "guild_create", "guild_update", "guild_delete",
        "channel_create", "channel_update", "channel_delete",
        "guild_member_add", "guild_member_update", "guild_member_remove",
        "message_create", "message_delete", "message_reaction_add", "message_reaction_remove",
        "direct_message_create", "direct_message_delete", "interaction_create",
        "message_audit_pass", "message_audit_reject",
        "audio_start", "audio_finish", "on_mic", "off_mic",
        "at_message_create", "public_message_delete",
        "group_at_message_create", "c2c_message_create",
        "group_add_robot", "group_del_robot", "group_msg_reject", "group_msg_receive",
        "friend_add", "friend_del", "c2c_msg_reject", "c2c_msg_receive",
        "forum_thread_create", "forum_thread_update", "forum_thread_delete",
        "forum_post_create", "forum_post_delete", "forum_reply_create", "forum_reply_delete",
        "forum_publish_audit_result", "audio_or_live_channel_member_enter",
        "audio_or_live_channel_member_exit", "open_forum_thread_create", "open_forum_thread_update",
        "open_forum_thread_delete", "open_forum_post_create", "open_forum_post_delete",
        "open_forum_reply_create", "open_forum_reply_delete",
        # 新增事件
        "group_message_create", "group_join_request", "group_member_add", "group_member_quit",
    }
    missing = expected - set(state.parsers.keys())
    assert not missing, f"缺少事件解析器: {missing}"


# ============== 事件模型 reply() ==============
@pytest.mark.asyncio
async def test_group_message_reply():
    class FakeHttp:
        def __init__(self):
            self.calls = []

        async def request(self, route, **kwargs):
            self.calls.append((route, kwargs))
            return {}

    api = BotAPI(FakeHttp())
    msg = GroupMessage(api, "EVT1", GROUP_MSG_PAYLOAD["d"])
    await msg.reply(content="world")
    route, kwargs = api._http.calls[-1]
    assert route.url == "https://api.bot.qq.com/v2/groups/GROUP1/messages"
    assert kwargs["json"]["msg_id"] == "ROBOT1.0_xxx"
    assert kwargs["json"]["content"] == "world"


@pytest.mark.asyncio
async def test_c2c_message_reply():
    class FakeHttp:
        def __init__(self):
            self.calls = []

        async def request(self, route, **kwargs):
            self.calls.append((route, kwargs))
            return {}

    api = BotAPI(FakeHttp())
    payload = {
        "id": "M2",
        "author": {"id": "U1", "user_openid": "U1"},
        "content": "hi",
    }
    msg = C2CMessage(api, "EVT2", payload)
    await msg.reply(content="yo")
    route, kwargs = api._http.calls[-1]
    assert route.url == "https://api.bot.qq.com/v2/users/U1/messages"
    assert kwargs["json"]["msg_id"] == "M2"
