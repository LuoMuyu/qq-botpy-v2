# -*- coding: utf-8 -*-
"""事件回调字段覆盖审计测试。

将最新官方文档中每个事件体字段表固化为用例：
模型必须暴露文档中的全部字段（含嵌套对象），并提供原始载荷 raw。
"""

from botpy.api import BotAPI
from botpy.http import BotHttp
from botpy.channel import Channel
from botpy.forum import OpenThread, Thread
from botpy.guild import Guild
from botpy.interaction import Interaction
from botpy.manage import (
    C2CManageEvent,
    GroupJoinRequest,
    GroupManageEvent,
    GroupMemberEvent,
)
from botpy.message import C2CMessage, DirectMessage, GroupMessage, Message, MessageAudit
from botpy.reaction import Reaction
from botpy.user import Member

api = BotAPI(BotHttp(timeout=5))

DOC_USER_FIELDS = ["id", "username", "bot", "union_openid", "union_user_account",
                   "user_openid", "member_openid", "member_role"]


def slots_of(obj):
    slots = set()
    for klass in type(obj).__mro__:
        slots.update(getattr(klass, "__slots__", ()))
    return slots


def assert_fields(cls, fields, data, label):
    obj = cls(api, "EVT", data)
    missing = [f for f in fields if f not in slots_of(obj)]
    assert not missing, f"{label} 缺少字段: {missing}"
    # raw 原始载荷
    assert obj.raw == data, f"{label} 缺少 raw 原始载荷"
    return obj


# ============== 频道（GUILDS 1<<0） ==============
def test_guild_create_update_delete_fields():
    # 文档字段表：id/name/icon/owner_id/member_count/max_members/description/joined_at/op_user_id
    g = assert_fields(Guild,
        ["id", "name", "icon", "owner_id", "member_count", "max_members",
         "description", "joined_at", "op_user_id"],
        {"id": "G1", "op_user_id": "U9"}, "GUILD_CREATE/UPDATE/DELETE")
    assert g.op_user_id == "U9"


def test_channel_create_update_delete_fields():
    # 文档字段表：id/guild_id/name/type/sub_type/owner_id/op_user_id（示例另含 position）
    c = assert_fields(Channel,
        ["id", "guild_id", "name", "type", "sub_type", "position", "owner_id", "op_user_id"],
        {"id": "C1", "op_user_id": "U9"}, "CHANNEL_CREATE/UPDATE/DELETE")
    assert c.op_user_id == "U9"


# ============== 频道成员（GUILD_MEMBERS 1<<1） ==============
def test_guild_member_events_fields():
    # 文档字段表：guild_id/joined_at/nick/op_user_id/roles/user{id,avatar,bot,username}
    m = assert_fields(Member,
        ["guild_id", "joined_at", "nick", "roles", "op_user_id"],
        {"guild_id": "G1", "op_user_id": "U9",
         "user": {"id": "U1", "username": "n", "avatar": "a", "bot": False,
                  "union_openid": "UN", "union_user_account": "UA"}},
        "GUILD_MEMBER_ADD/UPDATE/REMOVE")
    assert m.op_user_id == "U9"
    # user 嵌套对象全字段
    for f in ["id", "username", "avatar", "bot", "union_openid", "union_user_account"]:
        assert hasattr(m.user, f), f"Member.user 缺少 {f}"


# ============== 频道消息（GUILD_MESSAGES / PUBLIC_GUILD_MESSAGES） ==============
def test_guild_message_fields():
    # 老版 v2 文档的频道消息事件体（稳定，未被 autogen 重构）
    assert_fields(Message,
        ["id", "channel_id", "guild_id", "content", "timestamp", "author", "member",
         "message_reference", "mentions", "attachments", "seq", "seq_in_channel"],
        {"id": "M1", "channel_id": "C1", "guild_id": "G1",
         "author": {"id": "U1"}, "member": {"nick": "n", "roles": ["1"], "joined_at": "t"},
         "mentions": [{}], "attachments": [{}]},
        "MESSAGE_CREATE / AT_MESSAGE_CREATE / MESSAGE_DELETE")


def test_direct_message_fields():
    # 老版 v2 文档的私信事件体（无 mentions 字段，与频道消息不同）
    assert_fields(DirectMessage,
        ["id", "channel_id", "guild_id", "content", "timestamp", "author", "member",
         "message_reference", "attachments", "seq", "seq_in_channel",
         "direct_message", "src_guild_id"],
        {"id": "M1", "src_guild_id": "SG1", "author": {"id": "U1"}, "member": {}},
        "DIRECT_MESSAGE_CREATE/DELETE")


def test_message_audit_fields():
    assert_fields(MessageAudit,
        ["audit_id", "message_id", "channel_id", "guild_id"],
        {"audit_id": "A1", "message_id": "M1", "channel_id": "C1", "guild_id": "G1"},
        "MESSAGE_AUDIT_PASS/REJECT")


# ============== 表情表态 / 音频 / 论坛（稳定遗留事件） ==============
def test_reaction_fields():
    r = assert_fields(Reaction,
        ["user_id", "channel_id", "guild_id", "emoji", "target"],
        {"user_id": "U1", "emoji": {"id": "4", "type": 1}, "target": {"id": "M1", "type": 0}},
        "MESSAGE_REACTION_ADD/REMOVE")
    for f in ("id", "type"):
        assert hasattr(r.emoji, f) and hasattr(r.target, f)


def test_audio_and_forum_fields():
    from botpy.audio import Audio, PublicAudio
    assert_fields(Audio, ["channel_id", "guild_id", "audio_url", "text"],
                  {}, "AUDIO_START/FINISH/ON_MIC/OFF_MIC")
    # PublicAudio 构造无 event_id 参数
    pa = PublicAudio(api, {"guild_id": "G1", "channel_id": "C1",
                           "channel_type": "2", "user_id": "U1"})
    assert pa.raw["user_id"] == "U1"
    t = Thread(api, "EVT", {"guild_id": "G1", "channel_id": "C1", "author_id": "U1",
                            "thread_info": {"thread_id": "T1", "title": "{\"paragraphs\":[]}",
                                            "content": "{\"paragraphs\":[]}", "date_time": "d"}})
    assert t.raw["thread_info"]["thread_id"] == "T1"
    assert t.thread_info.thread_id == "T1"
    o = OpenThread(api, {"guild_id": "G1", "channel_id": "C1", "author_id": "U1"})
    assert o.raw["author_id"] == "U1"


# ============== 互动（INTERACTION 1<<26） ==============
def test_interaction_fields_latest():
    """最新文档：type 11~20，resolved 新增反馈/授权/快捷菜单字段。"""
    payload = {
        "id": "I1", "type": 13, "scene": "c2c", "chat_type": 2,
        "application_id": "APP1", "timestamp": "2026-07-20T21:54:38+08:00",
        "user_openid": "U1", "group_openid": "G1", "group_member_openid": "M1",
        "guild_id": "GUILD1", "channel_id": "C1", "version": 1,
        "data": {"type": 13, "resolved": {
            "button_id": "b1", "button_data": "d1", "message_id": "M1",
            "user_id": "U1", "feature_id": "F1",
            "feedback_opt": "LIKE", "checked": 1, "action": "ENTER_STORY",
            "message_scene": {"ext": ["disable_net_search=1"]},
            "authorize_data": {"opt_scene": "setting", "scope": "c2c_push"},
        }},
    }
    it = assert_fields(Interaction,
        ["id", "application_id", "type", "scene", "chat_type", "data",
         "guild_id", "channel_id", "user_openid", "group_openid",
         "group_member_openid", "timestamp", "version"],
        payload, "INTERACTION_CREATE")
    r = it.data.resolved
    # 最新文档 resolved 全部字段
    assert r.button_id == "b1" and r.button_data == "d1"
    assert r.message_id == "M1" and r.user_id == "U1" and r.feature_id == "F1"
    assert r.feedback_opt == "LIKE"
    assert r.checked == 1
    assert r.action == "ENTER_STORY"
    assert r.message_scene.ext == ["disable_net_search=1"]
    assert r.authorize_data.opt_scene == "setting"
    assert r.authorize_data.scope == "c2c_push"


# ============== 群/C2C（GROUP_AND_C2C_EVENT 1<<25） ==============
def test_group_manage_events_fields():
    # 文档字段表：timestamp/group_openid/op_member_openid
    g = assert_fields(GroupManageEvent,
        ["timestamp", "group_openid", "op_member_openid"],
        {"timestamp": 1, "group_openid": "G1", "op_member_openid": "M1"},
        "GROUP_ADD_ROBOT/DEL_ROBOT/MSG_REJECT/MSG_RECEIVE")
    assert g.op_member_openid == "M1"


def test_friend_add_del_fields_latest():
    """FRIEND_ADD 最新字段：scene/scene_param/author/short_code；FRIEND_DEL：+author。"""
    ev = assert_fields(C2CManageEvent,
        ["timestamp", "openid", "scene", "scene_param", "author", "short_code"],
        {"timestamp": 1784570600, "openid": "O1", "scene": 2003,
         "scene_param": "callback_abc", "author": {"union_openid": "UN1"},
         "short_code": "SC1"},
        "FRIEND_ADD")
    assert ev.scene == 2003
    assert ev.scene_param == "callback_abc"
    assert ev.author.union_openid == "UN1"
    assert ev.short_code == "SC1"
    # C2C_MSG_REJECT/RECEIVE 仅 timestamp/openid，兼容解析
    ev2 = C2CManageEvent(api, "EVT", {"timestamp": 1, "openid": "O2"})
    assert ev2.scene is None and ev2.author.union_openid is None


def test_group_c2c_message_author_full_user_structure():
    """文档 User 结构 8 个字段在群/单聊消息 author 上全部可读。"""
    author = {k: f"v-{k}" for k in DOC_USER_FIELDS}
    gm = GroupMessage(api, "EVT", {"id": "M1", "author": author, "group_openid": "G1"})
    for f in DOC_USER_FIELDS:
        assert getattr(gm.author, f) == f"v-{f}", f"GroupMessage.author 缺少 {f}"
    cm = C2CMessage(api, "EVT", {"id": "M2", "author": author})
    for f in DOC_USER_FIELDS:
        assert getattr(cm.author, f) == f"v-{f}", f"C2CMessage.author 缺少 {f}"


def test_join_request_fields():
    assert_fields(GroupJoinRequest,
        ["group_openid", "join_request_id", "risk_tips", "union_openid", "member_openid",
         "username", "apply_at", "apply_source", "invited_by", "bot", "verify_info",
         "auto_approved"],
        {f: "x" for f in ["group_openid", "join_request_id", "verify_info", "auto_approved"]},
        "GROUP_JOIN_REQUEST")


def test_group_member_event_fields():
    assert_fields(GroupMemberEvent,
        ["timestamp", "group_openid", "member_openid", "user_openid"],
        {"timestamp": 1, "group_openid": "G1", "member_openid": "M1", "user_openid": "U1"},
        "GROUP_MEMBER_ADD/QUIT")


def test_raw_payload_access():
    """平台未来新增字段可通过 raw 读取，无需等 SDK 更新。"""
    payload = {"id": "M1", "content": "hi", "brand_new_field": "future"}
    msg = GroupMessage(api, "EVT", payload)
    assert msg.raw["brand_new_field"] == "future"
