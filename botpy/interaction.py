from .api import BotAPI
from .types import interaction


class Interaction:
    """互动事件（INTERACTION_CREATE）。

    按最新文档，type 支持：11=消息按钮、12=单聊快捷菜单、13=消息反馈、
    14=清空会话、15=进出故事集、16=切换模型、18=用户授权、19=群授权、
    20=群授权状态变更。
    """

    __slots__ = (
        "_api",
        "_ctx",
        "id",
        "application_id",
        "type",
        "scene",
        "chat_type",
        "event_id",
        "data",
        "guild_id",
        "channel_id",
        "user_openid",
        "group_openid",
        "group_member_openid",
        "timestamp",
        "version",
        "raw",
    )

    def __init__(self, api: BotAPI, event_id, data: interaction.InteractionPayload):
        self._api = api

        self.id = data.get("id", None)
        self.type = data.get("type", None)
        self.scene = data.get("scene", None)  # c2c=单聊, group=群聊, guild=频道
        self.chat_type = data.get("chat_type", None)  # 0=频道, 1=群聊, 2=单聊
        self.application_id = data.get("application_id", None)
        self.event_id = event_id
        self.data = self._Data(data.get("data", {}))
        self.guild_id = data.get("guild_id", None)
        self.channel_id = data.get("channel_id", None)
        self.user_openid = data.get("user_openid", None)
        self.group_openid = data.get("group_openid", None)
        self.group_member_openid = data.get("group_member_openid", None)
        self.timestamp = data.get("timestamp", None)
        self.version = data.get("version", None)
        self.raw = data  # 原始事件体，平台新增字段可从此读取

    def __repr__(self):
        return str({items: str(getattr(self, items)) for items in self.__slots__ if not items.startswith("_")})

    class _Data:
        def __init__(self, data):
            data = data or {}
            self.type = data.get("type", None)
            self.resolved = Interaction._Resolved(data.get("resolved", None))

        def __repr__(self):
            return str(self.__dict__)

    class _Resolved:
        def __init__(self, data):
            data = data or {}
            self.button_id = data.get("button_id", None)
            self.button_data = data.get("button_data", None)
            self.message_id = data.get("message_id", None)
            self.user_id = data.get("user_id", None)
            self.feature_id = data.get("feature_id", None)
            # 最新文档新增字段
            self.feedback_opt = data.get("feedback_opt", None)  # 仅 type=13：LIKE=点赞, UNLIKE=点踩
            self.checked = data.get("checked", None)  # 仅 type=13：反馈选项是否选中
            self.action = data.get("action", None)  # type=15：ENTER_STORY/QUIT_STORY；type=16 为对应操作动作
            self.message_scene = self._MessageScene(data.get("message_scene", None))  # 仅 type=13
            self.authorize_data = self._AuthorizeData(data.get("authorize_data", None))  # 仅 type=18/19

        def __repr__(self):
            return str(self.__dict__)

        class _MessageScene:
            def __init__(self, data):
                data = data or {}
                self.ext = data.get("ext", None)  # 扩展键值对列表，如 "disable_net_search=1"

            def __repr__(self):
                return str(self.__dict__)

        class _AuthorizeData:
            def __init__(self, data):
                data = data or {}
                # setting=资料页设置, dialog=弹窗授权
                self.opt_scene = data.get("opt_scene", None)
                # c2c_push=C2C 主动消息推送, group_push=群主动消息推送
                self.scope = data.get("scope", None)

            def __repr__(self):
                return str(self.__dict__)
