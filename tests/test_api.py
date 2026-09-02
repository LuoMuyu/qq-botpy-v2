# -*- coding: utf-8 -*-
"""核心单元测试：路由、鉴权、intents、消息负载构建。"""

import pytest

from botpy.api import BotAPI
from botpy.errors import ApiError
from botpy.flags import Intents, Permission
from botpy.http import Route, _clean_payload
from botpy.robot import Token


class FakeHttp:
    """捕获 request 调用的假 HTTP 客户端，用于断言路由与负载。

    与真实 BotHttp 一致，会对 json 负载做 None 字段清理。
    """

    def __init__(self):
        self.calls = []

    async def request(self, route, **kwargs):
        if "json" in kwargs and isinstance(kwargs["json"], dict):
            kwargs["json"] = _clean_payload(kwargs["json"])
        self.calls.append((route, kwargs))
        return {}

    @property
    def last(self):
        return self.calls[-1]


# ============== Route ==============
def test_route_url_official_domain():
    route = Route("GET", "/users/@me")
    assert route.url == "https://api.bot.qq.com/users/@me"


def test_route_url_sandbox_domain():
    route = Route("GET", "/users/@me", is_sandbox=True)
    assert route.url == "https://sandbox.api.bot.qq.com/users/@me"


def test_route_url_with_params():
    route = Route("POST", "/v2/groups/{group_openid}/messages", group_openid="G123")
    assert route.url == "https://api.bot.qq.com/v2/groups/G123/messages"


# ============== Token ==============
def test_token_get_string():
    token = Token("app", "sec")
    token.access_token = "abc"
    assert token.get_string() == "QQBot abc"
    assert token.bot_token() is token


def test_token_type():
    token = Token("app", "sec")
    assert token.get_type() == "QQBot"


# ============== Intents ==============
def test_intents_bits():
    assert Intents.public_messages.flag == 1 << 25
    assert Intents.public_guild_messages.flag == 1 << 30
    assert Intents.guild_messages.flag == 1 << 9
    assert Intents.direct_message.flag == 1 << 12
    assert Intents.interaction.flag == 1 << 26
    assert Intents.group_member_event.flag == 1 << 24


def test_intents_combine():
    intents = Intents(public_messages=True, group_member_event=True)
    assert intents.value == (1 << 25) | (1 << 24)


def test_intents_all_contains_group_member():
    intents = Intents.all()
    assert intents.group_member_event
    assert intents.public_messages


def test_intents_default_excludes_private():
    intents = Intents.default()
    assert not intents.guild_messages
    assert not intents.forums
    assert intents.public_messages


def test_intents_invalid_flag_name():
    with pytest.raises(TypeError):
        Intents(not_a_flag=True)


# ============== Permission ==============
def test_permission_bits():
    p = Permission(view_permission=True)
    assert p.value == 1
    p2 = Permission(view_permission=True, speak_permission=True)
    assert p2.value == 0b101


# ============== BotAPI：兼容原版的方法与路由 ==============
@pytest.mark.asyncio
async def test_get_guild_route():
    api = BotAPI(FakeHttp())
    await api.get_guild("G1")
    route, kwargs = api._http.last
    assert route.method == "GET"
    assert route.url == "https://api.bot.qq.com/guilds/G1"


@pytest.mark.asyncio
async def test_post_message_payload():
    api = BotAPI(FakeHttp())
    await api.post_message("C1", content="hello", msg_id="M1", msg_seq=2)
    route, kwargs = api._http.last
    assert route.method == "POST"
    assert route.path == "/channels/{channel_id}/messages"
    body = kwargs["json"]
    assert body["content"] == "hello"
    assert body["msg_id"] == "M1"
    assert body["msg_seq"] == 2


@pytest.mark.asyncio
async def test_post_message_file_image_from_path(tmp_path):
    p = tmp_path / "img.png"
    p.write_bytes(b"png-bytes")
    api = BotAPI(FakeHttp())
    await api.post_message("C1", file_image=str(p))
    _, kwargs = api._http.last
    assert kwargs["json"]["file_image"] == b"png-bytes"


@pytest.mark.asyncio
async def test_create_dms_route():
    api = BotAPI(FakeHttp())
    await api.create_dms("G1", "U1")
    route, kwargs = api._http.last
    assert route.path == "/users/@me/dms"
    assert kwargs["json"] == {"recipient_id": "U1", "source_guild_id": "G1"}


@pytest.mark.asyncio
async def test_post_dms_route():
    api = BotAPI(FakeHttp())
    await api.post_dms("G1", content="hi", msg_id="M1")
    route, _ = api._http.last
    assert route.url == "https://api.bot.qq.com/dms/G1/messages"


@pytest.mark.asyncio
async def test_get_ws_url_route():
    api = BotAPI(FakeHttp())
    await api.get_ws_url()
    route, _ = api._http.last
    assert route.path == "/gateway/bot"


@pytest.mark.asyncio
async def test_get_gateway_route():
    api = BotAPI(FakeHttp())
    await api.get_gateway()
    route, _ = api._http.last
    assert route.path == "/gateway"


@pytest.mark.asyncio
async def test_recall_message_params():
    api = BotAPI(FakeHttp())
    await api.recall_message("C1", "M1", hidetip=True)
    route, kwargs = api._http.last
    assert route.method == "DELETE"
    assert kwargs["params"] == {"hidetip": "true"}


# ============== BotAPI：群聊/单聊消息（最新文档） ==============
@pytest.mark.asyncio
async def test_post_group_message_payload():
    api = BotAPI(FakeHttp())
    await api.post_group_message(
        "GROUP1", content="hello", msg_id="M1", msg_seq=2, markdown={"content": "# t"}
    )
    route, kwargs = api._http.last
    assert route.url == "https://api.bot.qq.com/v2/groups/GROUP1/messages"
    body = kwargs["json"]
    assert body["msg_type"] == 0
    assert body["content"] == "hello"
    assert body["msg_id"] == "M1"
    assert body["msg_seq"] == 2
    assert body["markdown"] == {"content": "# t"}
    # None 字段应被清除（http 层 _clean_payload）
    assert "embed" not in body
    assert "event_id" not in body


@pytest.mark.asyncio
async def test_post_group_message_media_and_wakeup():
    api = BotAPI(FakeHttp())
    await api.post_group_message(
        "GROUP1", msg_type=7, media={"file_info": "FI"}, msg_id="M1", is_wakeup=False
    )
    _, kwargs = api._http.last
    body = kwargs["json"]
    assert body["msg_type"] == 7
    assert body["media"] == {"file_info": "FI"}
    assert body["is_wakeup"] is False


@pytest.mark.asyncio
async def test_post_c2c_message_payload():
    api = BotAPI(FakeHttp())
    await api.post_c2c_message("U1", content="hi", msg_id="M1")
    route, kwargs = api._http.last
    assert route.url == "https://api.bot.qq.com/v2/users/U1/messages"
    assert kwargs["json"]["content"] == "hi"


@pytest.mark.asyncio
async def test_post_c2c_message_input_notify():
    api = BotAPI(FakeHttp())
    await api.post_c2c_message(
        "U1", msg_type=6, input_notify={"input_type": 1, "input_second": 30}, msg_id="M1"
    )
    _, kwargs = api._http.last
    body = kwargs["json"]
    assert body["msg_type"] == 6
    assert body["input_notify"] == {"input_type": 1, "input_second": 30}


@pytest.mark.asyncio
async def test_post_stream_message_payload():
    api = BotAPI(FakeHttp())
    await api.post_stream_message(
        "U1",
        input_mode="replace",
        input_state=10,
        index=2,
        content_type="markdown",
        content_raw="# done",
        stream_msg_id="S1",
        msg_id="M1",
    )
    route, kwargs = api._http.last
    assert route.url == "https://api.bot.qq.com/v2/users/U1/stream_messages"
    body = kwargs["json"]
    assert body["input_mode"] == "replace"
    assert body["input_state"] == 10
    assert body["index"] == 2
    assert body["stream_msg_id"] == "S1"
    assert body["content_raw"] == "# done"


@pytest.mark.asyncio
async def test_recall_group_and_c2c_message():
    api = BotAPI(FakeHttp())
    await api.recall_group_message("GROUP1", "M1")
    route, _ = api._http.last
    assert route.method == "DELETE"
    assert route.url == "https://api.bot.qq.com/v2/groups/GROUP1/messages/M1"

    await api.recall_c2c_message("U1", "M2")
    route, _ = api._http.last
    assert route.url == "https://api.bot.qq.com/v2/users/U1/messages/M2"


@pytest.mark.asyncio
async def test_post_group_file_payload():
    api = BotAPI(FakeHttp())
    await api.post_group_file("GROUP1", file_type=1, url="https://e.com/a.png")
    route, kwargs = api._http.last
    assert route.url == "https://api.bot.qq.com/v2/groups/GROUP1/files"
    body = kwargs["json"]
    assert body["file_type"] == 1
    assert body["url"] == "https://e.com/a.png"
    assert body["srv_send_msg"] is False


@pytest.mark.asyncio
async def test_post_c2c_file_chunked_merge():
    api = BotAPI(FakeHttp())
    await api.post_c2c_file("U1", file_type=2, upload_id="UP1", file_name="v.mp4")
    _, kwargs = api._http.last
    body = kwargs["json"]
    assert body["upload_id"] == "UP1"
    assert body["file_name"] == "v.mp4"


@pytest.mark.asyncio
async def test_upload_prepare_and_part_finish():
    api = BotAPI(FakeHttp())
    await api.post_group_upload_prepare(
        "GROUP1", file_type=2, file_size="100", file_name="v.mp4",
        md5="m", sha1="s", md5_10m="m10",
    )
    route, kwargs = api._http.last
    assert route.url == "https://api.bot.qq.com/v2/groups/GROUP1/upload_prepare"
    assert kwargs["json"]["md5_10m"] == "m10"

    await api.post_group_upload_part_finish("GROUP1", upload_id="UP1", part_index=0, block_size="100", md5="m")
    route, kwargs = api._http.last
    assert route.url == "https://api.bot.qq.com/v2/groups/GROUP1/upload_part_finish"
    assert kwargs["json"] == {
        "upload_id": "UP1", "part_index": 0, "block_size": "100", "md5": "m",
    }

    await api.post_c2c_upload_prepare(
        "U1", file_type=1, file_size="10", file_name="a.png",
        md5="m", sha1="s", md5_10m="m10",
    )
    route, _ = api._http.last
    assert route.url == "https://api.bot.qq.com/v2/users/U1/upload_prepare"


# ============== BotAPI：群管理（2026.08 新增） ==============
@pytest.mark.asyncio
async def test_get_group_info_and_bot_state():
    api = BotAPI(FakeHttp())
    await api.get_group_info("GROUP1")
    route, _ = api._http.last
    assert route.url == "https://api.bot.qq.com/v2/groups/GROUP1/info"

    await api.get_group_bot_state("GROUP1")
    route, _ = api._http.last
    assert route.url == "https://api.bot.qq.com/v2/groups/GROUP1/bot_state"


@pytest.mark.asyncio
async def test_group_mute_setting():
    api = BotAPI(FakeHttp())
    await api.get_group_mute_setting("GROUP1")
    route, _ = api._http.last
    assert route.method == "GET"
    assert route.url == "https://api.bot.qq.com/v2/groups/GROUP1/restrict_chat_setting"

    members = [{"op": "add", "member_openid": "M1", "mute_expire_at": "2026-08-05T11:23:05+08:00"}]
    await api.set_group_mute_setting("GROUP1", members)
    route, kwargs = api._http.last
    assert route.method == "POST"
    assert kwargs["json"]["members"] == members


@pytest.mark.asyncio
async def test_join_request_apis():
    api = BotAPI(FakeHttp())
    await api.get_group_join_requests("GROUP1", cursor="c1", limit=20)
    route, kwargs = api._http.last
    assert route.url == "https://api.bot.qq.com/v2/groups/GROUP1/join_request_list"
    assert kwargs["params"] == {"cursor": "c1", "limit": 20}

    await api.approve_group_join_request("GROUP1", "MEM1", op="approve", join_request_id="JR1")
    route, kwargs = api._http.last
    assert route.url == "https://api.bot.qq.com/v2/groups/GROUP1/approval_join_request/MEM1"
    assert kwargs["json"]["op"] == "approve"
    assert kwargs["json"]["join_request_id"] == "JR1"

    await api.approve_group_join_request(
        "GROUP1", "MEM1", op="decline", join_request_id="JR1",
        reject_reason="no", add_to_member_blacklist=True,
    )
    _, kwargs = api._http.last
    assert kwargs["json"]["reject_reason"] == "no"
    assert kwargs["json"]["add_to_member_blacklist"] is True


@pytest.mark.asyncio
async def test_join_approval_strategy_apis():
    api = BotAPI(FakeHttp())
    await api.create_join_approval_strategy(group_openids=["G1"], is_enable="on")
    route, kwargs = api._http.last
    assert route.url == "https://api.bot.qq.com/v2/groups/join_approval_strategy"
    assert kwargs["json"]["group_openids"] == ["G1"]

    await api.get_join_approval_strategies()
    route, _ = api._http.last
    assert route.method == "GET"

    await api.update_join_approval_strategy("ST1", is_enable="off")
    route, kwargs = api._http.last
    assert route.method == "PATCH"
    assert route.url.endswith("/v2/groups/join_approval_strategy/ST1")
    assert kwargs["json"]["is_enable"] == "off"

    await api.delete_join_approval_strategy("ST1")
    route, _ = api._http.last
    assert route.method == "DELETE"

    await api.execute_join_approval_strategy("ST1")
    route, _ = api._http.last
    assert route.url.endswith("/v2/groups/join_approval_strategy/ST1/execute")


# ============== BotAPI：菜单与指令面板（2026.08 新增） ==============
@pytest.mark.asyncio
async def test_menu_apis():
    api = BotAPI(FakeHttp())
    await api.get_menu()
    route, _ = api._http.last
    assert route.method == "GET"
    assert route.url == "https://api.bot.qq.com/v2/menu"

    await api.update_menu({"items": [{"type": "send_message", "name": "帮助", "send_message": "/help"}]})
    route, kwargs = api._http.last
    assert route.method == "PUT"
    assert kwargs["json"]["menu"]["items"][0]["name"] == "帮助"


@pytest.mark.asyncio
async def test_panel_apis():
    api = BotAPI(FakeHttp())
    panel_cfg = {"items": [{"name": "签到", "type": "command", "desc": "每日签到"}]}
    await api.create_panel("group", panel_cfg)
    route, kwargs = api._http.last
    assert route.url == "https://api.bot.qq.com/v2/panels"
    assert kwargs["json"]["scope"] == "group"
    assert kwargs["json"]["target_type"] == "all"
    assert kwargs["json"]["panel"] == panel_cfg

    await api.get_panels("c2c", limit=10)
    route, kwargs = api._http.last
    assert kwargs["params"]["scope"] == "c2c"

    await api.get_panel("P1")
    route, _ = api._http.last
    assert route.url == "https://api.bot.qq.com/v2/panels/P1"

    await api.update_panel("P1", panel_cfg)
    route, _ = api._http.last
    assert route.method == "PUT"

    await api.update_panel_target("P1", add_user_openids=["U1"])
    route, kwargs = api._http.last
    assert route.url == "https://api.bot.qq.com/v2/panels/P1/target"
    assert kwargs["json"]["add_user_openids"] == ["U1"]

    await api.delete_panel("P1")
    route, _ = api._http.last
    assert route.method == "DELETE"
    assert route.url == "https://api.bot.qq.com/v2/panels/P1"


# ============== 错误处理 ==============
def test_api_error_with_code():
    err = ApiError("msg expired", 40034005)
    assert err.code == 40034005
    assert "40034005" in str(err)
