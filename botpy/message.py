from typing import List

from .api import BotAPI
from .types import gateway
from .types.group import ARKData, MsgElement, MessageScene


class Message:
    """频道内消息（GUILD_MESSAGES / PUBLIC_GUILD_MESSAGES 事件）。"""

    __slots__ = (
        "_api",
        "author",
        "content",
        "channel_id",
        "id",
        "guild_id",
        "member",
        "message_reference",
        "mentions",
        "attachments",
        "seq",
        "seq_in_channel",
        "timestamp",
        "raw",
        "event_id",
    )

    def __init__(self, api: BotAPI, event_id, data: gateway.MessagePayload):
        self._api = api
        self.raw = data  # 原始事件体，平台新增字段可从此读取

        self.author = self._User(data.get("author", {}))
        self.channel_id = data.get("channel_id", None)
        self.id = data.get("id", None)
        self.content = data.get("content", None)
        self.guild_id = data.get("guild_id", None)
        self.member = self._Member(data.get("member", {}))
        self.message_reference = self._MessageRef(data.get("message_reference", {}))
        self.mentions = [self._User(items) for items in data.get("mentions", {})]
        self.attachments = [self._Attachments(items) for items in data.get("attachments", {})]
        self.seq = data.get("seq", None)  # 全局消息序号
        self.seq_in_channel = data.get("seq_in_channel", None)  # 子频道消息序号
        self.timestamp = data.get("timestamp", None)
        self.event_id = event_id

    def __repr__(self):
        return str({items: str(getattr(self, items)) for items in self.__slots__ if not items.startswith("_")})

    class _User:
        def __init__(self, data):
            self.id = data.get("id", None)
            self.username = data.get("username", None)
            self.bot = data.get("bot", None)
            self.avatar = data.get("avatar", None)

        def __repr__(self):
            return str(self.__dict__)

    class _Member:
        def __init__(self, data):
            self.nick = data.get("nick", None)
            self.roles = data.get("roles", None)
            self.joined_at = data.get("joined_at", None)

        def __repr__(self):
            return str(self.__dict__)

    class _MessageRef:
        def __init__(self, data):
            self.message_id = data.get("message_id", None)

        def __repr__(self):
            return str(self.__dict__)

    class _Attachments:
        def __init__(self, data):
            self.content_type = data.get("content_type", None)
            self.filename = data.get("filename", None)
            self.height = data.get("height", None)
            self.width = data.get("width", None)
            self.id = data.get("id", None)
            self.size = data.get("size", None)
            self.url = data.get("url", None)

        def __repr__(self):
            return str(self.__dict__)

    async def reply(self, **kwargs):
        return await self._api.post_message(channel_id=self.channel_id, msg_id=self.id, **kwargs)


class DirectMessage:
    """频道私信消息（DIRECT_MESSAGE 事件）。"""

    __slots__ = (
        "_api",
        "author",
        "content",
        "direct_message",
        "channel_id",
        "id",
        "guild_id",
        "member",
        "message_reference",
        "attachments",
        "seq",
        "seq_in_channel",
        "src_guild_id",
        "timestamp",
        "raw",
        "event_id",
    )

    def __init__(self, api: BotAPI, event_id, data: gateway.DirectMessagePayload):
        self._api = api
        self.raw = data  # 原始事件体，平台新增字段可从此读取

        self.author = self._User(data.get("author", {}))
        self.channel_id = data.get("channel_id", None)
        self.id = data.get("id", None)
        self.content = data.get("content", None)
        self.direct_message = data.get("direct_message", None)
        self.guild_id = data.get("guild_id", None)
        self.member = self._Member(data.get("member", {}))
        self.message_reference = self._MessageRef(data.get("message_reference", {}))
        self.attachments = [self._Attachments(items) for items in data.get("attachments", {})]
        self.seq = data.get("seq", None)  # 全局消息序号
        self.seq_in_channel = data.get("seq_in_channel", None)  # 子频道消息序号
        self.src_guild_id = data.get("src_guild_id", None)
        self.timestamp = data.get("timestamp", None)
        self.event_id = event_id

    def __repr__(self):
        return str({items: str(getattr(self, items)) for items in self.__slots__ if not items.startswith("_")})

    class _User:
        def __init__(self, data):
            self.id = data.get("id", None)
            self.username = data.get("username", None)
            self.avatar = data.get("avatar", None)

        def __repr__(self):
            return str(self.__dict__)

    class _Member:
        def __init__(self, data):
            self.joined_at = data.get("joined_at", None)

        def __repr__(self):
            return str(self.__dict__)

    class _MessageRef:
        def __init__(self, data):
            self.message_id = data.get("message_id", None)

        def __repr__(self):
            return str(self.__dict__)

    class _Attachments:
        def __init__(self, data):
            self.content_type = data.get("content_type", None)
            self.filename = data.get("filename", None)
            self.height = data.get("height", None)
            self.width = data.get("width", None)
            self.id = data.get("id", None)
            self.size = data.get("size", None)
            self.url = data.get("url", None)

        def __repr__(self):
            return str(self.__dict__)

    async def reply(self, **kwargs):
        return await self._api.post_dms(guild_id=self.guild_id, msg_id=self.id, **kwargs)


class MessageAudit:
    """频道消息审核事件。"""

    __slots__ = (
        "_api",
        "audit_id",
        "message_id",
        "channel_id",
        "guild_id",
        "raw",
        "event_id",
    )

    def __init__(self, api: BotAPI, event_id, data: gateway.MessageAuditPayload):
        self._api = api

        self.audit_id = data.get("audit_id", None)
        self.channel_id = data.get("channel_id", None)
        self.message_id = data.get("message_id", None)
        self.guild_id = data.get("guild_id", None)
        self.raw = data  # 原始事件体，平台新增字段可从此读取
        self.event_id = event_id

    def __repr__(self):
        return str({items: str(getattr(self, items)) for items in self.__slots__ if not items.startswith("_")})


class BaseMessage:
    """群聊/单聊消息的基类。

    按照最新文档，事件体新增 message_type、message_scene、ark_data、msg_elements
    等字段，附件支持语音转写（voice_wav_url / asr_refer_text）。
    """

    __slots__ = (
        "_api",
        "content",
        "id",
        "message_reference",
        "mentions",
        "attachments",
        "msg_seq",
        "timestamp",
        "event_id",
        "message_type",
        "message_scene",
        "ark_data",
        "msg_elements",
        "raw",
    )

    def __init__(self, api: BotAPI, event_id, data: gateway.MessagePayload):
        self._api = api
        self.raw = data  # 原始事件体，平台新增字段可从此读取
        self.id = data.get("id", None)
        self.content = data.get("content", None)
        self.message_reference = self._MessageRef(data.get("message_reference", {}))
        self.mentions = [self._User(items) for items in data.get("mentions", {})]
        self.attachments = [self._Attachments(items) for items in data.get("attachments", {})]
        self.msg_seq = data.get("msg_seq", None)  # 全局消息序号
        self.timestamp = data.get("timestamp", None)
        self.event_id = event_id
        # 最新文档新增字段
        self.message_type = data.get("message_type", None)
        self.message_scene = self._MessageScene(data.get("message_scene", None))
        self.ark_data = data.get("ark_data", None)
        self.msg_elements = data.get("msg_elements", None)

    def __repr__(self):
        return str({items: str(getattr(self, items)) for items in self.__slots__ if not items.startswith("_")})

    def get_scene_ext(self) -> dict:
        """返回 message_scene.ext 的 key=value 解析结果。

        常见 key:
          - msg_idx: 消息索引（可作为 message_reference.message_id 用于引用回复）
          - ref_msg_idx: 引用的消息索引
          - auth_token: 鉴权令牌
        """
        result = {}
        if self.message_scene and self.message_scene.ext:
            for item in self.message_scene.ext:
                if "=" in item:
                    key, value = item.split("=", 1)
                    result[key] = value
        return result

    class _MessageScene:
        def __init__(self, data):
            if not data:
                self.source = None
                self.ext = None
                return
            self.source = data.get("source", None)
            self.ext: List[str] = data.get("ext", None)

        def __repr__(self):
            return str(self.__dict__)

    class _MessageRef:
        def __init__(self, data):
            self.message_id = data.get("message_id", None)

        def __repr__(self):
            return str(self.__dict__)

    class _Attachments:
        def __init__(self, data):
            self.content_type = data.get("content_type", None)
            self.filename = data.get("filename", None)
            self.height = data.get("height", None)
            self.width = data.get("width", None)
            self.id = data.get("id", None)
            self.size = data.get("size", None)
            self.url = data.get("url", None)
            # 最新文档新增：语音附件支持转写
            self.voice_wav_url = data.get("voice_wav_url", None)
            self.asr_refer_text = data.get("asr_refer_text", None)

        def __repr__(self):
            return str(self.__dict__)


class GroupMessage(BaseMessage):
    """群聊消息（GROUP_AT_MESSAGE_CREATE / GROUP_MESSAGE_CREATE 事件）。"""

    __slots__ = (
        "author",
        "group_openid",
    )

    def __init__(self, api: BotAPI, event_id, data: gateway.MessagePayload):
        super().__init__(api, event_id, data)
        self.author = self._User(data.get("author", {}))
        self.group_openid = data.get("group_openid", None)

    def __repr__(self):
        slots = self.__slots__ + super().__slots__
        return str({items: str(getattr(self, items)) for items in slots if not items.startswith("_")})

    class _User:
        def __init__(self, data):
            self.member_openid = data.get("member_openid", None)
            # 最新文档 User 结构字段
            self.id = data.get("id", None)
            self.username = data.get("username", None)
            self.member_role = data.get("member_role", None)
            self.union_openid = data.get("union_openid", None)
            self.union_user_account = data.get("union_user_account", None)
            self.user_openid = data.get("user_openid", None)
            self.bot = data.get("bot", None)

        def __repr__(self):
            return str(self.__dict__)

    async def reply(self, **kwargs):
        return await self._api.post_group_message(group_openid=self.group_openid, msg_id=self.id, **kwargs)


class C2CMessage(BaseMessage):
    """单聊消息（C2C_MESSAGE_CREATE 事件）。"""

    __slots__ = ("author",)

    def __init__(self, api: BotAPI, event_id, data: gateway.MessagePayload):
        super().__init__(api, event_id, data)

        self.author = self._User(data.get("author", {}))

    def __repr__(self):
        slots = self.__slots__ + super().__slots__
        return str({items: str(getattr(self, items)) for items in slots if not items.startswith("_")})

    class _User:
        def __init__(self, data):
            self.user_openid = data.get("user_openid", None)
            # 最新文档 User 结构字段
            self.id = data.get("id", None)
            self.username = data.get("username", None)
            self.union_openid = data.get("union_openid", None)
            self.union_user_account = data.get("union_user_account", None)
            self.member_openid = data.get("member_openid", None)
            self.member_role = data.get("member_role", None)
            self.bot = data.get("bot", None)

        def __repr__(self):
            return str(self.__dict__)

    @property
    def openid(self):
        """作者的用户 OpenID，与 author.user_openid 等价。"""
        return self.author.user_openid

    async def reply(self, **kwargs):
        return await self._api.post_c2c_message(openid=self.author.user_openid, msg_id=self.id, **kwargs)
