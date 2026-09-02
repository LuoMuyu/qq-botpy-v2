from typing import Dict
from .api import BotAPI
from .types.group import JoinRequestEventPayload, GroupMemberEventPayload


class GroupManageEvent:
    """群管理事件（机器人加入/退出群聊、消息接收开关）。

    事件体字段（与最新文档一致）：timestamp、group_openid、op_member_openid。
    """

    __slots__ = (
        "_api",
        "event_id",
        "timestamp",
        "group_openid",
        "op_member_openid",
        "raw",
    )

    def __init__(self, api: BotAPI, event_id, data: Dict):
        self._api = api
        self.event_id = event_id
        self.timestamp = data.get("timestamp", None)
        self.group_openid = data.get("group_openid", None)
        self.op_member_openid = data.get("op_member_openid", None)
        self.raw = data  # 原始事件体，平台新增字段可从此读取

    def __repr__(self):
        return str({items: str(getattr(self, items)) for items in self.__slots__ if not items.startswith("_")})


class C2CManageEvent:
    """C2C 管理事件。

    覆盖事件：
      - FRIEND_ADD / FRIEND_DEL（用户添加/删除机器人好友）
        最新文档字段：timestamp、openid、scene、scene_param、author、short_code
        其中 scene/scene_param/short_code 仅 FRIEND_ADD 事件携带
      - C2C_MSG_REJECT / C2C_MSG_RECEIVE（用户关闭/开启机器人主动消息）
        事件体字段：timestamp、openid
    """

    __slots__ = (
        "_api",
        "event_id",
        "timestamp",
        "openid",
        "scene",
        "scene_param",
        "author",
        "short_code",
        "raw",
    )

    def __init__(self, api: BotAPI, event_id, data: Dict):
        self._api = api
        self.event_id = event_id
        self.timestamp = data.get("timestamp", None)
        self.openid = data.get("openid", None)
        # FRIEND_ADD / FRIEND_DEL 事件新增字段
        self.scene = data.get("scene", None)  # 加好友场景值，如 1001=网络搜索、2003=开发者分享链接
        self.scene_param = data.get("scene_param", None)  # 开发者自定义的回调数据（callback_data）
        self.author = self._FriendAuthor(data.get("author", None))
        self.short_code = data.get("short_code", None)  # 机器人分享链接的短链 code
        self.raw = data  # 原始事件体，平台新增字段可从此读取

    def __repr__(self):
        return str({items: str(getattr(self, items)) for items in self.__slots__ if not items.startswith("_")})

    class _FriendAuthor:
        """好友用户信息（跨应用标识）。"""

        def __init__(self, data):
            data = data or {}
            self.union_openid = data.get("union_openid", None)

        def __repr__(self):
            return str(self.__dict__)


class GroupJoinRequest:
    """用户申请加群事件（GROUP_JOIN_REQUEST，2026.08 新增）。

    只有当机器人是群管理员时才可以收到此事件。
    可通过 :meth:`approve` / :meth:`decline` 直接完成审批。
    """

    __slots__ = (
        "_api",
        "event_id",
        "group_openid",
        "join_request_id",
        "risk_tips",
        "union_openid",
        "member_openid",
        "username",
        "apply_at",
        "apply_source",
        "invited_by",
        "bot",
        "verify_info",
        "auto_approved",
        "raw",
    )

    def __init__(self, api: BotAPI, event_id, data: JoinRequestEventPayload):
        self._api = api
        self.event_id = event_id
        self.group_openid = data.get("group_openid", None)
        self.join_request_id = data.get("join_request_id", None)
        self.risk_tips = data.get("risk_tips", None)
        self.union_openid = data.get("union_openid", None)
        self.member_openid = data.get("member_openid", None)
        self.username = data.get("username", None)
        self.apply_at = data.get("apply_at", None)
        self.apply_source = data.get("apply_source", None)  # self_apply / invited
        self.invited_by = data.get("invited_by", None)
        self.bot = data.get("bot", None)
        self.verify_info = data.get("verify_info", None)
        self.auto_approved = data.get("auto_approved", None)
        self.raw = data  # 原始事件体，平台新增字段可从此读取

    def __repr__(self):
        return str({items: str(getattr(self, items)) for items in self.__slots__ if not items.startswith("_")})

    async def approve(self) -> str:
        """通过入群申请。"""
        return await self._api.approve_group_join_request(
            group_openid=self.group_openid,
            member_openid=self.member_openid,
            op="approve",
            join_request_id=self.join_request_id,
        )

    async def decline(self, reject_reason: str = None, add_to_member_blacklist: bool = False) -> str:
        """
        拒绝入群申请。

        Args:
          reject_reason (str): 拒绝理由。
          add_to_member_blacklist (bool): 是否同时加入群黑名单，默认 False。
        """
        return await self._api.approve_group_join_request(
            group_openid=self.group_openid,
            member_openid=self.member_openid,
            op="decline",
            join_request_id=self.join_request_id,
            reject_reason=reject_reason,
            add_to_member_blacklist=add_to_member_blacklist,
        )


class GroupMemberEvent:
    """群成员加入/退出事件（GROUP_MEMBER_ADD / GROUP_MEMBER_QUIT，新增）。"""

    __slots__ = (
        "_api",
        "event_id",
        "timestamp",
        "group_openid",
        "member_openid",
        "user_openid",
        "raw",
    )

    def __init__(self, api: BotAPI, event_id, data: GroupMemberEventPayload):
        self._api = api
        self.event_id = event_id
        self.timestamp = data.get("timestamp", None)
        self.group_openid = data.get("group_openid", None)
        self.member_openid = data.get("member_openid", None)
        self.user_openid = data.get("user_openid", None)
        self.raw = data  # 原始事件体，平台新增字段可从此读取

    def __repr__(self):
        return str({items: str(getattr(self, items)) for items in self.__slots__ if not items.startswith("_")})
