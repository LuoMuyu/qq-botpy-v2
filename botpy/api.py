# -*- coding: utf-8 -*-

# 异步api

from io import BufferedReader
from typing import Any, List, Union, BinaryIO, Dict

from .flags import Permission
from .http import BotHttp, Route
from .types import (
    guild,
    user,
    channel,
    message,
    audio,
    announce,
    permission,
    schedule,
    emoji,
    pins_message,
    reaction,
    forum,
    group,
    menu,
    panel,
)


class BotAPI:
    """
    机器人相关的API接口类

    使用注意:
        - 如果要直接使用api，可以通过client的内部成员变量，通过`self.api.xx`来使用
        - 设置超时时间: Client(timeout=5)
        - API当前返回的所有自定义类型数据为字典数据，通过TypedDict进行类型提示
        - 接口统一域名: https://api.bot.qq.com （沙箱环境: sandbox.api.bot.qq.com）
    """

    def __init__(self, http: BotHttp):
        """
        Args:
          http (BotHttp): 用于发送请求的 http 客户端。
        """
        self._http = http

    # ============== Websocket 接入点 ==============
    async def get_ws_url(self):
        """
        返回机器人的 websocket URL（带分片的 WSS 接入点，GET /gateway/bot）。

        Returns:
          url字典数据。通过 `data['url']` 获取，同时包含 `shards`、
          `session_start_limit` 等会话限制信息。
        """
        route = Route("GET", "/gateway/bot")
        return await self._http.request(route)

    async def get_gateway(self):
        """
        获取通用 WSS 接入点（GET /gateway）。

        与 :meth:`get_ws_url` 不同，该接口不返回分片信息，适用于单连接接入。

        Returns:
          url字典数据。通过 `data['url']` 获取 WebSocket 连接地址。
        """
        route = Route("GET", "/gateway")
        return await self._http.request(route)

    # ============== 频道相关接口 ==============
    async def get_guild(self, guild_id: str) -> guild.GuildPayload:
        """
        获取频道信息。

        Args:
          guild_id (str): 频道ID（一般从事件中获取相关的ID信息）

        Returns:
          GuildPayload (字典数据)
        """
        route = Route("GET", "/guilds/{guild_id}", guild_id=guild_id)
        return await self._http.request(route)

    # 频道身份组相关接口
    async def get_guild_roles(self, guild_id: str) -> guild.GuildRoles:
        """
        获取频道身份组列表

        Args:
          guild_id (str): 频道ID。

        Returns:
          GuildRolesPayload
        """
        route = Route("GET", "/guilds/{guild_id}/roles", guild_id=guild_id)
        return await self._http.request(route)

    async def create_guild_role(self, guild_id: str, **fields: Any) -> guild.GuildRole:
        """
        创建频道身份组

        Args:
          guild_id (str): 在其中创建角色的频道ID。

        Kwargs（fields）:
          name (str): 名称(非必填)
          color (int): ARGB 的 HEX 十六进制颜色值转换后的十进制数值(非必填)
          hoist (int): 在成员列表中单独展示: 0-否, 1-是(非必填)

        Returns:
          class:GuildRole
        """
        route = Route("POST", "/guilds/{guild_id}/roles", guild_id=guild_id)
        return await self._http.request(route, json=fields)

    async def update_guild_role(self, guild_id: str, role_id: str, **fields: Any) -> guild.GuildRole:
        """
        修改频道身份组

        Args:
          guild_id (str): 在其中创建角色的公会 ID。
          role_id (str): 您要修改的角色的 ID。

        Kwargs（fields）:
          name (str): 名称(非必填)
          color (int): ARGB 的 HEX 十六进制颜色值转换后的十进制数值(非必填)
          hoist (int): 在成员列表中单独展示: 0-否, 1-是(非必填)

        Returns:
          class:GuildRole
        """
        route = Route("PATCH", "/guilds/{guild_id}/roles/{role_id}", guild_id=guild_id, role_id=role_id)
        return await self._http.request(route, json=fields)

    async def delete_guild_role(self, guild_id: str, role_id: str) -> str:
        """
        删除频道身份组

        Args:
          guild_id (str): 频道 ID。
          role_id (str): 身份组 ID。

        Returns:
          成功执行返回`None`。
        """
        route = Route("DELETE", "/guilds/{guild_id}/roles/{role_id}", guild_id=guild_id, role_id=role_id)
        return await self._http.request(route)

    async def create_guild_role_member(
        self,
        guild_id: str,
        role_id: str,
        user_id: str,
        channel_id: str = None,
    ) -> str:
        """
        增加频道身份组成员。

        Args:
          guild_id (str): 频道 ID。
          role_id (str): 身份组 ID。
          user_id (str): 要添加到角色的用户的用户 ID。
          channel_id (str): 您要在其中创建角色的频道的 ID。如果要删除的身份组ID是5-子频道管理员，需要增加channel对象来指定具体是哪个子频道

        Returns:
          成功执行返回`None`。
        """
        payload = {"channel": {"id": channel_id}}

        route = Route(
            "PUT",
            "/guilds/{guild_id}/members/{user_id}/roles/{role_id}",
            guild_id=guild_id,
            user_id=user_id,
            role_id=role_id,
        )
        return await self._http.request(route, json=payload)

    async def delete_guild_role_member(self, guild_id: str, role_id: str, user_id: str, channel_id: str = None) -> str:
        """
        删除频道身份组成员。

        Args:
          guild_id (str): 频道 ID。
          role_id (str): 身份组 ID。
          user_id (str): 用户的标识。
          channel_id (str): 您要从中删除角色的子频道的 ID。
            如果要删除的身份组ID是5-子频道管理员，需要增加channel对象来指定具体是哪个子频道

        Returns:
          成功执行返回`None`。
        """
        payload = {"channel": {"id": channel_id}}

        route = Route(
            "DELETE",
            "/guilds/{guild_id}/members/{user_id}/roles/{role_id}",
            guild_id=guild_id,
            user_id=user_id,
            role_id=role_id,
        )
        return await self._http.request(route, json=payload)

    # 成员相关接口，添加成员到用户组等
    async def get_guild_member(self, guild_id: str, user_id: str) -> user.Member:
        """
        获取频道指定成员。

        Args:
          guild_id (str): 频道 ID。
          user_id (str): 用户 ID（一般从事件消息中获取。

        Returns:
          user.Member
        """
        route = Route(
            "GET",
            "/guilds/{guild_id}/members/{user_id}",
            guild_id=guild_id,
            user_id=user_id,
        )
        return await self._http.request(route)

    async def get_delete_member(
        self,
        guild_id: str,
        user_id: str,
        add_blacklist: bool = False,
        delete_history_msg_days: int = 0,
    ) -> str:
        """
        删除频道成员

        Args:
          guild_id (str): 频道ID
          user_id (str): 用户ID
          add_blacklist (bool): 是否同时添加黑名单
          delete_history_msg_days (int): 用于撤回该成员的消息，可以指定撤回消息的时间范围

        Returns:
          成功执行返回`None`。成功执行返回空字符串
        """
        # 注：消息撤回时间范围仅支持固定的天数：3，7，15，30。 特殊的时间范围：-1: 撤回全部消息。默认值为0不撤回任何消息。
        if delete_history_msg_days not in (3, 7, 15, 30, 0, -1):
            delete_history_msg_days = 0
        payload = {"add_blacklist": add_blacklist, "delete_history_msg_days": delete_history_msg_days}
        route = Route(
            "DELETE",
            "/guilds/{guild_id}/members/{user_id}",
            guild_id=guild_id,
            user_id=user_id,
        )
        return await self._http.request(route, json=payload)

    async def get_guild_members(self, guild_id: str, after: str = "0", limit: int = 1) -> List[user.Member]:
        """
        获取成员列表。

        注意:该接口为私域机器人权限, 需要在管理端申请权限

        Args:
          guild_id (str): 频道 ID。
          after (str): 上一批用户中最后一个用户的ID。如果这是第一个请求，请使用 0。. Defaults to 0
          limit (int): 分页大小，1-400。成员较多的频道尽量使用较大的limit值，以减少请求数。. Defaults to 1

        Returns:
          user.Member 对象的列表。
        """
        params = {"after": after, "limit": limit}

        route = Route(
            "GET",
            "/guilds/{guild_id}/members",
            guild_id=guild_id,
        )
        return await self._http.request(route, params=params)

    async def get_guild_role_members(
        self, guild_id: str, role_id: str, start_index: str = "0", limit: int = 1
    ) -> Dict[str, Union[List[user.Member], str]]:
        """
        获取频道身份组成员列表。

        注意:该接口为私域机器人权限, 需要在管理端申请权限

        Args:
          guild_id (str): 频道 ID。
          role_id (str): 身份组 ID。
          start_index (str): 将上一次回包中next填入， 如果是第一次请求填 0，默认为 0。. Defaults to 0
          limit (int): 分页大小，1-400。成员较多的频道尽量使用较大的limit值，以减少请求数。. Defaults to 1

        Returns:
          Dict[str, Union[List[user.Member], str]]
        """
        params = {"start_index": start_index, "limit": limit}

        route = Route(
            "GET",
            "/guilds/{guild_id}/roles/{role_id}/members",
            guild_id=guild_id,
            role_id=role_id,
        )
        return await self._http.request(route, params=params)

    async def get_voice_members(self, channel_id: str) -> List[user.Member]:
        """
        返回语音频道中的成员列表（暂未开放，内部测试使用）

        注意:
          公域机器人暂不支持申请，仅私域机器人可用，选择私域机器人后默认开通。
          注意: 开通后需要先将机器人从频道移除，然后重新添加，方可生效。

        Args:
          channel_id (str): 要获取其语音成员的频道的 ID。查询的子频道不是语音子频道，返回的status code为400

        Returns:
          user.Member 对象的列表。
        """
        route = Route("GET", "/channels/{channel_id}/voice/members", channel_id=channel_id)
        return await self._http.request(route)

    # 子频道相关接口
    async def get_channel(self, channel_id: str) -> channel.ChannelPayload:
        """
        获取频道信息

        Args:
          channel_id (str): 子频道 ID。

        Returns:
          channel.Channel
        """
        route = Route(
            "GET",
            "/channels/{channel_id}",
            channel_id=channel_id,
        )
        return await self._http.request(route)

    async def get_channels(self, guild_id: str) -> List[channel.ChannelPayload]:
        """
        获取频道下的子频道列表

        Args:
          guild_id (str): 频道 ID。

        Returns:
          List[channel.Channel]
        """
        route = Route(
            "GET",
            "/guilds/{guild_id}/channels",
            guild_id=guild_id,
        )
        return await self._http.request(route)

    async def create_channel(
        self, guild_id: str, name: str, type: channel.ChannelType, sub_type: channel.ChannelSubType, **fields
    ) -> channel.ChannelPayload:
        """
        创建子频道

        Args:
          guild_id (str): 频道 ID。
          name (str): 子频道名。
          type (channel.ChannelType): 子频道类型
          sub_type (channel.ChannelSubType): 子频道子类型

        Kwargs（fields）:
          position (int): 排序，非必填
          parent_id (str): 否,分组 ID
          private_type (int): 子频道私密类型 PrivateType
          private_user_ids (List[str]): 子频道私密类型成员 ID
          speak_permission (int): 子频道发言权限 SpeakPermission
          application_id (str): 应用类型子频道 AppID，仅应用子频道需要该字段

        Returns:
          通道对象。
        """
        payload = {
            "name": name,
            "type": int(type),
            "subtype": int(sub_type),
        }
        valid_keys = (
            "position",
            "parent_id",
            "private_type",
            "private_user_ids",
            "speak_permission",
            "application_id",
        )
        payload.update({k: v for k, v in fields.items() if k in valid_keys and v})
        route = Route("POST", "/guilds/{guild_id}/channels", guild_id=guild_id)
        return await self._http.request(route, json=payload)

    async def update_channel(self, channel_id: str, **fields) -> channel.ChannelPayload:
        """
        更新子频道。

        Args:
          channel_id (str): 要修改的子频道ID。

        Kwargs:
          name	            string	子频道名
          position	        int	    排序
          parent_id	        string	分组 id
          private_type	    int	    子频道私密类型 PrivateType
          speak_permission	int	    子频道发言权限 SpeakPermission

        Returns:Dict:
          channel.Channel
        """
        route = Route("PATCH", "/channels/{channel_id}", channel_id=channel_id)
        return await self._http.request(route, json=fields)

    async def delete_channel(self, channel_id: str) -> channel.ChannelPayload:
        """
        删除子频道

        Args:
          channel_id (str): 要删除的子频道 ID。

        Returns:Dict:
          删除后的channel.Channel
        """
        route = Route("DELETE", "/channels/{channel_id}", channel_id=channel_id)
        return await self._http.request(route)

    # 子频道权限相关接口
    async def get_channel_user_permissions(self, channel_id: str, user_id: str) -> channel.ChannelPermissions:
        """
        获取指定子频道用户的权限。

        Args:
          channel_id (str): 子频道 ID。
          user_id (str): 用户 ID。

        Returns:Dict
          channel.ChannelPermissions
        """
        route = Route(
            "GET", "/channels/{channel_id}/members/{user_id}/permissions", channel_id=channel_id, user_id=user_id
        )
        return await self._http.request(route)

    async def update_channel_user_permissions(
        self, channel_id: str, user_id: str, add: Permission = None, remove: Permission = None
    ) -> str:
        """
        修改指定子频道用户的权限。

        Args:
          channel_id (str): 子频道 ID。
          user_id (str): 您要更改其权限的用户的用户 ID。
          add (Permission): 添加到用户的权限。使用示例：`add = Permission(view_permission=True)`
          remove (Permission): 删除的权限类型，示例：`remove = Permission(view_permission=True,manager_permission=True)`

        Returns:
          成功执行返回`None`。
        """
        payload = {"add": str(add.value) if add else None, "remove": str(remove.value) if remove else None}

        route = Route(
            "PUT", "/channels/{channel_id}/members/{user_id}/permissions", channel_id=channel_id, user_id=user_id
        )
        return await self._http.request(route, json=payload)

    async def get_channel_role_permissions(self, channel_id: str, role_id: str) -> channel.ChannelPermissions:
        """
        获取指定子频道身份组的权限。

        Args:
          channel_id (str): 您要获取权限的子频道的 ID。
          role_id (str): 您要编辑的身份组 ID。

        Returns:Dict
          channel.ChannelPermissions 的字典数据
        """
        route = Route(
            "GET", "/channels/{channel_id}/roles/{role_id}/permissions", channel_id=channel_id, role_id=role_id
        )
        return await self._http.request(route)

    async def update_channel_role_permissions(
        self, channel_id: str, role_id: str, add: Permission = None, remove: Permission = None
    ) -> str:
        """
        修改指定子频道身份组的权限

        Args:
          channel_id (str): 您要更改权限的子频道的 ID。
          role_id (str): 要修改的身份组 ID。
          add (Permission):  添加的权限类型，示例：添加可读权限，`add = Permission(view_permission=True)`
          remove (Permission):  删除的权限类型，示例：删除可读和发言权限, `remove = Permission(view_permission=True,speak_permission=True)`

        Returns:
          成功执行返回`None`。
        """
        payload = {"add": str(add.value) if add else None, "remove": str(remove.value) if remove else None}

        route = Route(
            "PUT", "/channels/{channel_id}/roles/{role_id}/permissions", channel_id=channel_id, role_id=role_id
        )
        return await self._http.request(route, json=payload)

    # ============== 频道消息接口 ==============
    async def get_message(self, channel_id: str, message_id: str) -> message.MessagePayload:
        """
        获取指定消息。

        Args:
          channel_id (str): 您要从中获取消息的子频道的 ID。
          message_id (str): 要删除的消息的 ID。

        Returns:
          一个消息字典对象。
        """
        route = Route(
            "GET", "/channels/{channel_id}/messages/{message_id}", channel_id=channel_id, message_id=message_id
        )
        return await self._http.request(route)

    async def post_message(
        self,
        channel_id: str,
        content: str = None,
        embed: message.Embed = None,
        ark: message.Ark = None,
        message_reference: message.Reference = None,
        image: str = None,
        file_image: Union[bytes, BinaryIO, str] = None,
        msg_id: str = None,
        event_id: str = None,
        markdown: message.MarkdownPayload = None,
        keyboard: message.Keyboard = None,
        msg_seq: int = None,
    ) -> message.Message:
        """
        发送消息到子频道。

        注意:
        - 要求操作人在该子频道具有发送消息的权限。
        - 发送成功之后，会触发一个创建消息的事件。
        - 被动回复消息有效期为 5 分钟
        - 主动推送消息每日每个子频道限 2 条
        - 发送消息接口要求机器人接口需要链接到websocket gateway 上保持在线状态

        Args:
          channel_id (str): 您要将消息发送到的子频道的 ID。
          content (str): 消息的文本内容。
          embed (message.Embed): embed 消息，一种特殊的 ark
          ark (message.Ark): ark 模版消息
          message_reference (message.Reference): 对消息的引用。
          image (str): 要发送的图像的 URL。
          file_image (bytes): 要发送的本地图像的本地路径或数据。
          msg_id (str): 您要回复的消息的 ID。您可以从 AT_CREATE_MESSAGE 事件中获取此 ID。
          event_id (str): 您要回复的消息的事件 ID。
          markdown (message.MarkdownPayload): markdown 消息
          keyboard (message.Keyboard): keyboard 消息
          msg_seq (int): 回复消息的序号，与 msg_id 联合使用，默认是1。
            相同的 msg_id + msg_seq 重复发送会失败。（新增，与最新文档对齐）

        Returns:
          message.Message: 一个消息字典对象。
        """
        if isinstance(file_image, BufferedReader):
            file_image = file_image.read()
        elif isinstance(file_image, str):
            with open(file_image, "rb") as img:
                file_image = img.read()
        payload = {
            "content": content,
            "embed": embed,
            "ark": ark,
            "message_reference": message_reference,
            "image": image,
            "file_image": file_image,
            "msg_id": msg_id,
            "event_id": event_id,
            "markdown": markdown,
            "keyboard": keyboard,
            "msg_seq": msg_seq,
        }
        route = Route("POST", "/channels/{channel_id}/messages", channel_id=channel_id)
        return await self._http.request(route, json=payload)

    async def recall_message(self, channel_id: str, message_id: str, hidetip: bool = False) -> str:
        """
        撤回子频道消息。

        注意:
          管理员可以撤回普通成员的消息
          频道主可以撤回所有人的消息

        Args:
          channel_id (str): 您要将消息发送到的频道的 ID。
          message_id (str): 要撤回的消息的 ID。
          hidetip (bool): 是否隐藏撤回提示小灰条。. Defaults to False

        Returns:
          成功执行返回`None`。
        """
        params = {"hidetip": str(hidetip).lower()}

        route = Route(
            "DELETE",
            "/channels/{channel_id}/messages/{message_id}",
            channel_id=channel_id,
            message_id=message_id,
        )
        return await self._http.request(route, params=params)

    async def post_keyboard_message(
        self,
        channel_id: str,
        keyboard: message.KeyboardPayload = None,
        markdown: message.MarkdownPayload = None,
    ) -> message.Message:
        """
        `post_keyboard_message` 使用内联键盘发送消息

        Args:
          channel_id (str): 您要将消息发送到的频道的 ID。
          keyboard (message.KeyboardPayload): keyboard 消息的构建参数
          markdown (message.MarkdownPayload): markdown 消息的构建参数。

        Returns:
          一个消息的字典数据对象。
        """
        payload = {"keyboard": keyboard, "markdown": markdown}
        route = Route(
            "POST",
            "/channels/{channel_id}/messages",
            channel_id=channel_id,
        )
        return await self._http.request(route, json=payload)

    async def on_interaction_result(self, interaction_id: str, code: int):
        """
        `on_interaction_result` 消息按钮回调结果

        Args:
          interaction_id (str): 消息按钮回调事件的 ID。
          code (int): 回调结果 0 成功，1 操作失败，2 操作频繁，3 重复操作，4 没有权限，5 仅管理员操作

        Returns:
          无
        """
        payload = {"code": code}
        route = Route(
            "PUT",
            "/interactions/{id}",
            id=interaction_id,
        )
        return await self._http.request(route, json=payload)

    async def patch_guild_message(
        self,
        channel_id: str,
        patch_msg_id: str,
        msg_id: str = None,
        event_id: str = None,
        markdown: message.MarkdownPayload = None,
        keyboard: message.KeyboardPayload = None,
    ) -> message.Message:
        """
        修改频道markdown消息，需要先申请权限。

        Args:
          channel_id (str): 您要将消息发送到的频道的 ID。
          patch_msg_id (str): 需要修改的消息id。
          msg_id (str): 您要回复的消息的 ID。您可以从 AT_CREATE_MESSAGE 事件中获取此 ID。
          event_id (str): 您要回复的消息的事件 ID。
          markdown (message.MarkdownPayload): markdown 消息的构建参数。
          keyboard (message.KeyboardPayload): keyboard 消息的构建参数

        Returns:
          message.Message: 一个消息字典对象。
        """
        payload = {
            "msg_id": msg_id,
            "event_id": event_id,
            "markdown": markdown,
            "keyboard": keyboard if keyboard is not None else message.KeyboardPayload(content={}),
        }
        route = Route(
            "PATCH",
            "/channels/{channel_id}/messages/{patch_msg_id}",
            channel_id=channel_id,
            patch_msg_id=patch_msg_id,
        )
        return await self._http.request(route, json=payload)

    # ============== 频道私信接口 ==============
    async def create_dms(self, guild_id: str, user_id: str) -> message.DmsPayload:
        """
        创建私信会话。

        Args:
          guild_id (str): 您要将私信消息的来源频道 ID。
          user_id (str): 你要发送私信的用户 ID

        Returns:
          message.DmsPayload: 一个私信会话的字典对象。
        """
        # 创建私信频道
        payload = {"recipient_id": user_id, "source_guild_id": guild_id}
        route = Route("POST", "/users/@me/dms")
        return await self._http.request(route, json=payload)

    async def post_dms(
        self,
        guild_id: str,
        content: str = None,
        embed: message.Embed = None,
        ark: message.Ark = None,
        message_reference: message.Reference = None,
        image: str = None,
        file_image: Union[bytes, BinaryIO, str] = None,
        msg_id: str = None,
        event_id: str = None,
        markdown: message.MarkdownPayload = None,
        keyboard: message.Keyboard = None,
        msg_seq: int = None,
    ) -> message.Message:
        """
        发送私信。

        注意:
        - 要求操作人在该子频道具有发送消息的权限。
        - 发送成功之后，会触发一个创建消息的事件。
        - 被动回复消息有效期为 5 分钟
        - 主动推送消息每日每个子频道限 2 条
        - 发送消息接口要求机器人接口需要链接到websocket gateway 上保持在线状态

        Args:
          guild_id (str): 您要将私信会话的 ID, 从`create_dms`的返回可以获取。
          content (str): 消息的文本内容。
          embed (message.Embed): embed 消息，一种特殊的 ark
          ark (message.Ark): ark 模版消息
          message_reference (message.Reference): 对消息的引用。
          image (str): 要发送的图像的 URL。
          file_image (bytes): 本地图片
          msg_id (str): 您要回复的消息的 ID。您可以从 AT_CREATE_MESSAGE 事件中获取此 ID。
          event_id (str): 您要回复的消息的事件 ID。
          markdown (message.MarkdownPayload): markdown 消息
          keyboard (message.Keyboard): keyboard 消息
          msg_seq (int): 回复消息的序号，与 msg_id 联合使用。（新增）

        Returns:
          message.Message: 一个消息字典对象。
        """
        if isinstance(file_image, BufferedReader):
            file_image = file_image.read()
        elif isinstance(file_image, str):
            with open(file_image, "rb") as img:
                file_image = img.read()
        payload = {
            "content": content,
            "embed": embed,
            "ark": ark,
            "message_reference": message_reference,
            "image": image,
            "file_image": file_image,
            "msg_id": msg_id,
            "event_id": event_id,
            "markdown": markdown,
            "keyboard": keyboard,
            "msg_seq": msg_seq,
        }
        route = Route("POST", "/dms/{guild_id}/messages", guild_id=guild_id)
        return await self._http.request(route, json=payload)

    # ============== 音频接口 ==============
    async def update_audio(self, channel_id: str, audio_control: audio.AudioControl) -> str:
        """
        音频控制

        用于控制子频道 channel_id 下的音频。
        音频接口：仅限音频类机器人才能使用，后续会根据机器人类型自动开通接口权限，现如需调用，需联系平台申请权限。

        Args:
          channel_id (str): 要将音频发布到的频道的 ID。
          audio_control (audio.AudioControl): 音频.AudioControl 字典类型数据

        Returns:
          一个字符串
        """

        payload = audio_control
        route = Route("POST", "/channels/{channel_id}/audio", channel_id=channel_id)
        return await self._http.request(route, json=payload)

    async def on_microphone(self, channel_id) -> str:
        """
        机器人在 channel_id 对应的语音子频道上麦。

        注意:
          音频接口：仅限音频类机器人才能使用，后续会根据机器人类型自动开通接口权限，现如需调用，需联系平台申请权限。

        Args:
          channel_id: 子频道 ID。

        Returns:
          成功执行返回`None`。成功执行返回空字符串
        """
        route = Route("PUT", "/channels/{channel_id}/mic", channel_id=channel_id)
        return await self._http.request(route)

    async def off_microphone(self, channel_id) -> str:
        """
        机器人在 channel_id 对应的语音子频道下麦。

        注意:
          音频接口：仅限音频类机器人才能使用，后续会根据机器人类型自动开通接口权限，现如需调用，需联系平台申请权限。

        Args:
          channel_id: 子频道 ID。

        Returns:
          成功执行返回`None`。成功执行返回空字符串
        """
        route = Route("DELETE", "/channels/{channel_id}/mic", channel_id=channel_id)
        return await self._http.request(route)

    # ============== 用户相关接口 ==============
    async def me(self) -> user.User:
        """
        它返回当前用户的信息。

        Returns:
          一个用户对象。字典类型数据
        """
        route = Route("GET", "/users/@me")
        return await self._http.request(route)

    async def me_guilds(self, guild_id: str = None, limit: int = 100, desc: bool = False) -> List[guild.GuildPayload]:
        """
        它返回当前用户已加入的 Guild 对象列表。

        Args:
          guild_id (str): 列表的起始频道 ID。
          limit (int): 返回的最大频道数（1-100）。. Defaults to 100
          desc (bool): 如果为 True，则列表将按频道 ID 往前的数据并反序返回。. Defaults to False

        Returns:
          频道列表。
        """
        params = {"limit": limit}
        if desc and guild_id:
            params["before"] = guild_id
        elif guild_id:
            params["after"] = guild_id

        route = Route("GET", "/users/@me/guilds")
        return await self._http.request(route, params=params)

    # ============== 禁言接口 ==============
    async def mute_all(self, guild_id: str, mute_end_timestamp: str = None, mute_seconds: str = None) -> str:
        """
        使频道中的所有成员禁言。

        用于将频道的全体成员（非管理员）禁言。
        需要使用的 token 对应的用户具备管理员权限。如果是机器人，要求被添加为管理员。

        Args:
          guild_id (str): 要禁言的频道 ID。
          mute_end_timestamp (str): 禁言结束的时间。该值是自 1970 年 1 月 1 日 00:00:00 UTC 以来经过的毫秒数。
          mute_seconds (str): 禁言的秒数。两个字段二选一，默认以 mute_end_timestamp 为准

        Returns:
          成功执行返回`None`。
        """
        payload = {
            "mute_end_timestamp": mute_end_timestamp,
            "mute_seconds": mute_seconds,
        }
        route = Route("PATCH", "/guilds/{guild_id}/mute", guild_id=guild_id)
        return await self._http.request(route, json=payload)

    async def cancel_mute_all(self, guild_id: str) -> str:
        """
        取消频道中所有成员的禁言。

        Args:
          guild_id (str): 要取消禁言的频道 ID。

        Returns:
          成功执行返回`None`。
        """
        payload = {
            "mute_end_timestamp": "0",
            "mute_seconds": "0",
        }
        route = Route("PATCH", "/guilds/{guild_id}/mute", guild_id=guild_id)
        return await self._http.request(route, json=payload)

    async def mute_member(
        self, guild_id: str, user_id: str, mute_end_timestamp: str = None, mute_seconds: str = None
    ) -> str:
        """
        使频道中的指定成员禁言。

        用于将频道的指定成员（非管理员）禁言。
        需要使用的 token 对应的用户具备管理员权限。如果是机器人，要求被添加为管理员。

        Args:
          guild_id (str): 要禁言的频道 ID。
          user_id (str): 要禁言的成员 ID
          mute_end_timestamp (str): 禁言结束的时间。该值是自 1970 年 1 月 1 日 00:00:00 UTC 以来经过的毫秒数。
          mute_seconds (str): 禁言的秒数。两个字段二选一，默认以 mute_end_timestamp 为准

        Returns:
          成功执行返回`None`。
        """
        payload = {
            "mute_end_timestamp": mute_end_timestamp,
            "mute_seconds": mute_seconds,
        }
        route = Route("PATCH", "/guilds/{guild_id}/members/{user_id}/mute", guild_id=guild_id, user_id=user_id)
        return await self._http.request(route, json=payload)

    async def mute_multi_member(
        self, guild_id: str, user_ids: List[str], mute_end_timestamp: str = None, mute_seconds: str = None
    ) -> str:
        """
        使频道中的多个成员禁言

        Args:
          guild_id (str): 将用户禁言的频道 ID。
          user_ids (List[str]): 要禁言的用户 ID 列表。
          mute_end_timestamp (str): 禁言结束的时间。该值是自 1970 年 1 月 1 日 00:00:00 UTC 以来经过的毫秒数。
          mute_seconds (str): 将用户禁言的秒数。两个字段二选一，默认以 mute_end_timestamp 为准

        Returns:
          成功执行返回`None`。
        """
        payload = {
            "mute_end_timestamp": mute_end_timestamp,
            "mute_seconds": mute_seconds,
            "user_ids": user_ids,
        }
        route = Route("PATCH", "/guilds/{guild_id}/mute", guild_id=guild_id)
        return await self._http.request(route, json=payload)

    async def cancel_mute_multi_member(self, guild_id: str, user_ids: List[str]) -> str:
        """
        取消多个成员的禁言。

        Args:
          guild_id (str): 您想将用户禁言的频道 ID。
          user_ids (List[str]): 您要禁言的用户 ID 列表。

        Returns:
          成功执行返回`None`。
        """
        payload = {"mute_end_timestamp": "0", "mute_seconds": "0", "user_ids": user_ids}
        route = Route("PATCH", "/guilds/{guild_id}/mute", guild_id=guild_id)
        return await self._http.request(route, json=payload)

    # ============== 公告接口 ==============
    async def create_announce(self, guild_id: str, channel_id: str, message_id: str) -> announce.Announce:
        """
        创建消息类型的频道公告。

        注意:
          推荐子频道和消息类型全局公告不能同时存在，会互相顶替设置。
          同频道内推荐子频道最多只能创建 3 条。
          只有子频道权限为全体成员可见才可设置为推荐子频道。

        Args:
          guild_id (str): 创建频道的频道ID。
          channel_id (str): 您要将通知发送到的频道的子频道 ID。
          message_id (str): 公告的消息 ID。

        Returns:
          一个新的 Announce 对象。字典类型数据
        """
        payload = {"channel_id": channel_id, "message_id": message_id}
        route = Route("POST", "/guilds/{guild_id}/announces", guild_id=guild_id)
        return await self._http.request(route, json=payload)

    async def create_recommend_announce(
        self, guild_id: str, announces_type: announce.AnnouncesType, recommend_channels: List[announce.RecommendChannel]
    ) -> announce.Announce:
        """
        创建推荐子频道类型的频道公告

        注意:
          推荐子频道和消息类型全局公告不能同时存在，会互相顶替设置。
          同频道内推荐子频道最多只能创建 3 条。
          只有子频道权限为全体成员可见才可设置为推荐子频道。

        Args:
          guild_id (str): 发公告的频道 ID
          announces_type (announce.AnnouncesType): 公告的类型。
          recommend_channels (List[announce.RecommendChannel]): 列表[announce.RecommendChannel]

        Returns:
          一个新的 Announce 对象。字典类型数据
        """
        payload = {"announces_type": int(announces_type), "recommend_channels": recommend_channels}
        route = Route("POST", "/guilds/{guild_id}/announces", guild_id=guild_id)
        return await self._http.request(route, json=payload)

    async def delete_announce(self, guild_id: str, message_id: str = "all") -> str:
        """
        删除消息类型和推荐子频道类型的频道公告。

        注意:
          message_id 有值时，会校验 message_id 合法性，若不校验校验 message_id，请将 message_id 设置为 all

        Args:
          guild_id (str): 您要从中获取公告的频道的 ID。
          message_id (str): 要删除的公告消息的 ID。

        Returns:
          成功执行返回`None`。
        """
        route = Route("DELETE", "/guilds/{guild_id}/announces/{message_id}", guild_id=guild_id, message_id=message_id)
        return await self._http.request(route)

    # ============== 接口权限接口 ==============
    async def get_permissions(self, guild_id: str) -> List[permission.APIPermission]:
        """
        返回 bot 可以在具有给定 ID 的频道中使用的权限列表

        Args:
          guild_id (str): 获取权限的频道 ID。

        Returns:
          APIPermission 字典数据对象的列表。
        """
        route = Route("GET", "/guilds/{guild_id}/api_permission", guild_id=guild_id)
        # 多一层级
        data = await self._http.request(route)
        return data["apis"]

    async def post_permission_demand(
        self, guild_id: str, channel_id: str, api_identify: permission.APIPermissionDemandIdentify, desc: str
    ) -> permission.APIPermissionDemand:
        """
        用于创建 API 接口权限授权链接，该链接指向guild_id对应的频道

        Args:
          guild_id (str): 创建权限请求的频道ID。
          channel_id (str): 需要发送权限请求的通道的子频道ID。
          api_identify (permission.APIPermissionDemandIdentify): API 权限需求标识。
          desc (str): 权限请求的描述。

        Returns:
          一个 permission.APIPermissionDemand 字典数据对象。
        """
        payload = {"channel_id": channel_id, "api_identify": api_identify, "desc": desc}
        route = Route("POST", "/guilds/{guild_id}/api_permission/demand", guild_id=guild_id)
        return await self._http.request(route, json=payload)

    # ============== 日程接口 ==============
    async def get_schedules(self, channel_id: str, since: str = None) -> List[schedule.Schedule]:
        """
        获取某个日程子频道里中当天的日程列表。

        注意:
          若带了参数 since，则返回结束时间在 since 之后的日程列表；若未带参数 since，则默认返回当天的日程列表。

        Args:
          channel_id (str): 您要从中获取计划的子频道的 ID。
          since (str): 这个时间后的日程列表。如果不指定此参数，则默认值为当天的日程列表。

        Returns:
          列表[schedule.Schedule]
        """
        payload = {"since": since}
        route = Route("GET", "/channels/{channel_id}/schedules", channel_id=channel_id)
        return await self._http.request(route, json=payload)

    async def get_schedule(self, channel_id: str, schedule_id: str) -> schedule.Schedule:
        """
        获取日程子频道指定的的日程的详情

        Args:
          channel_id (str): 您要从中获取计划的频道的 ID。
          schedule_id (str): 要删除的计划的 ID。
        Returns:
          schedule.Schedule 字典数据
        """
        route = Route(
            "GET", "/channels/{channel_id}/schedules/{schedule_id}", channel_id=channel_id, schedule_id=schedule_id
        )
        return await self._http.request(route)

    async def create_schedule(
        self,
        channel_id: str,
        name: str,
        start_timestamp: str,
        end_timestamp: str,
        jump_channel_id: str,
        remind_type: schedule.RemindType,
    ) -> schedule.Schedule:
        """
        用于在日程子频道创建一个日程。

        注意:
          要求操作人具有管理频道的权限，如果是机器人，则需要将机器人设置为管理员。
          创建成功后，返回创建成功的日程对象。
          创建操作频次限制

        频率限制:
          单个管理员每天限10次
          单个频道每天100次

        Args:
          channel_id (str): 创建计划的通道的 ID。
          name (str): 计划的名称。
          start_timestamp (str): 事件的开始时间，格式为 Unix 时间戳。
          end_timestamp (str): 事件的结束时间，格式为 Unix 时间戳。
          jump_channel_id (str): 要跳转到的频道的频道 ID。
          remind_type (str): 0：无提醒，1：5分钟前，2：15分钟前，3：30分钟前，4：1小时前，5：2小时前，6：1天前，7：2天前

        Returns:
          创建好的schedule.Schedule对象
        """
        payload = {
            "schedule": {
                "name": name,
                "start_timestamp": start_timestamp,
                "end_timestamp": end_timestamp,
                "jump_channel_id": jump_channel_id,
                "reminder_id": remind_type,
            }
        }

        route = Route("POST", "/channels/{channel_id}/schedules", channel_id=channel_id)
        return await self._http.request(route, json=payload)

    async def update_schedule(
        self,
        channel_id: str,
        schedule_id: str,
        name: str,
        start_timestamp: str,
        end_timestamp: str,
        jump_channel_id: str,
        remind_type: schedule.RemindType,
    ) -> schedule.Schedule:
        """
        修改日程。

        注意:
          要求操作人具有管理频道的权限，如果是机器人，则需要将机器人设置为管理员。

        Args:
          channel_id (str): 修改日程的子频道的 ID。
          schedule_id (str): 日程ID
          name (str): 日程的名称。
          start_timestamp (str): 事件的开始时间，格式为 Unix 时间戳。
          end_timestamp (str): 事件的结束时间，格式为 Unix 时间戳。
          jump_channel_id (str): 要跳转到的频道的频道 ID。
          remind_type (str): 0：无提醒，1：5分钟前，2：15分钟前，3：30分钟前，4：1小时前，5：2小时前，6：1天前，7：2天前

        Returns:
          更新好的schedule.Schedule对象
        """
        payload = {
            "schedule": {
                "name": name,
                "start_timestamp": start_timestamp,
                "end_timestamp": end_timestamp,
                "jump_channel_id": jump_channel_id,
                "reminder_id": remind_type,
            }
        }

        route = Route(
            "PATCH", "/channels/{channel_id}/schedules/{schedule_id}", channel_id=channel_id, schedule_id=schedule_id
        )
        return await self._http.request(route, json=payload)

    async def delete_schedule(self, channel_id: str, schedule_id: str) -> str:
        """
        删除日程

        注意:
            要求操作人具有管理频道的权限，如果是机器人，则需要将机器人设置为管理员。

        Args:
          channel_id (str): 日程所属子频道的 ID。
          schedule_id (str): 要删除的日程的 ID。

        Returns:
          成功的话回复一个字符串
        """
        route = Route(
            "DELETE", "/channels/{channel_id}/schedules/{schedule_id}", channel_id=channel_id, schedule_id=schedule_id
        )
        return await self._http.request(route)

    # ============== 表情表态接口 ==============
    async def put_reaction(self, channel_id: str, message_id: str, emoji_type: emoji.EmojiType, emoji_id: str) -> str:
        """
        对一条消息进行表情表态。

        Args:
          channel_id (str): 消息发送的子频道的 ID。
          message_id (str): 表态的消息 ID。
          emoji_type (int): EmojiType 1: 系统表情 2: emoji表情
          emoji_id (str): 表情符号的 ID。
            参考: https://bot.q.qq.com/wiki/develop/api/openapi/emoji/model.html#emoji-%E5%88%97%E8%A1%A8

        Returns:
          成功返回空字符串。
        """
        route = Route(
            "PUT",
            "/channels/{channel_id}/messages/{message_id}/reactions/{type}/{id}",
            channel_id=channel_id,
            message_id=message_id,
            type=emoji_type,
            id=emoji_id,
        )
        return await self._http.request(route)

    async def delete_reaction(self, channel_id: str, message_id: str, emoji_type: emoji.EmojiType, emoji_id: str):
        """
        删除消息的表情表态。

        Args:
          channel_id (str): 消息发送的子频道的 ID。
          message_id (str): 表态的消息 ID。
          emoji_type (int): EmojiType 1: 系统表情 2: emoji表情
          emoji_id (str): 表情符号的 ID。

        Returns:
          成功返回空字符串。
        """
        route = Route(
            "DELETE",
            "/channels/{channel_id}/messages/{message_id}/reactions/{type}/{id}",
            channel_id=channel_id,
            message_id=message_id,
            type=emoji_type,
            id=emoji_id,
        )
        return await self._http.request(route)

    async def get_reaction_users(
        self,
        channel_id: str,
        message_id: str,
        emoji_type: emoji.EmojiType,
        emoji_id: str,
        cookie: str = None,
        limit: int = 20,
    ) -> reaction.ReactionUsers:
        """
        获取表情表态用户列表

        Args:
          channel_id (str): 消息所在子频道的 ID。
          message_id (str): 要从中获取表情表态的消息的 ID。
          emoji_type (emoji.EmojiType): 表情符号的类型。1: 系统表情, 2: emoji表情
          emoji_id (str): 表情符号的 ID。
          cookie (str): cookie 上次请求返回的cookie，第一次请求无需填写。
          limit (int): 返回的最大用户数 (1-100)。. Defaults to 20

        Returns:
          对带有特定表情符号的消息做出反应的用户列表。
        """
        route = Route(
            "GET",
            "/channels/{channel_id}/messages/{message_id}/reactions/{type}/{id}",
            channel_id=channel_id,
            message_id=message_id,
            type=emoji_type,
            id=emoji_id,
        )
        params = {"limit": limit, "cookie": cookie} if cookie else {"limit": limit}
        return await self._http.request(route, params=params)

    # ============== 精华消息API ==============
    async def put_pin(self, channel_id: str, message_id: str) -> pins_message.PinsMessage:
        """
        在子频道内添加精华消息。

        注意:
          每个子频道最多20条精华消息
          只有可见的消息才能被设置为精华消息
          返回对象中 message_ids 为当前请求后子频道内所有精华消息数组

        Args:
          channel_id (str): 用于固定消息的子频道 ID。
          message_id (str): 要固定的消息的 ID。

        Returns:
          频道中所有固定消息的列表。
        """
        route = Route(
            "PUT",
            "/channels/{channel_id}/pins/{message_id}",
            channel_id=channel_id,
            message_id=message_id,
        )
        return await self._http.request(route, json={})

    async def delete_pin(self, channel_id: str, message_id: str):
        """
        删除精华消息。

        注意:
          用于删除子频道 channel_id 下指定 message_id 的精华消息。
          删除子频道内全部精华消息，请将 message_id 设置为 all

        Args:
          channel_id (str): 用于固定消息的子频道 ID。
          message_id (str): 要固定的消息的 ID。

        Returns:
          成功返回空字符串。
        """
        route = Route(
            "DELETE",
            "/channels/{channel_id}/pins/{message_id}",
            channel_id=channel_id,
            message_id=message_id,
        )
        return await self._http.request(route)

    async def get_pins(self, channel_id: str) -> pins_message.PinsMessage:
        """
        用于获取子频道内的所有精华消息。

        Args:
          channel_id (str): 需要获取精华消息的子频道 ID

        Returns:
          频道中的精华消息。pins_message.PinsMessage 字典数据
        """
        route = Route(
            "GET",
            "/channels/{channel_id}/pins",
            channel_id=channel_id,
        )
        return await self._http.request(route)

    # ============== 帖子相关接口 ==============
    async def get_threads(self, channel_id: str) -> forum.ForumRsp:
        """
        该接口用于获取子频道下的帖子列表。

        Args:
          channel_id (str): 要获取其帖子列表的子频道的 ID。

        Returns:
          返回值是一个 ForumRsp 对象。
        """
        route = Route(
            "GET",
            "/channels/{channel_id}/threads",
            channel_id=channel_id,
        )
        return await self._http.request(route)

    async def get_thread_detail(self, channel_id: str, thread_id: str) -> forum.ThreadInfo:
        """
        该接口用于获取子频道下的帖子详情。

        Args:
          channel_id (str): 子频道的 ID。
          thread_id (str): 要查询的帖子的 ID。

        Returns:
          返回值是一个ThreadInfo 对象。
        """
        route = Route(
            "GET",
            "/channels/{channel_id}/threads/{thread_id}",
            channel_id=channel_id,
            thread_id=thread_id,
        )
        return await self._http.request(route)

    async def post_thread(self, channel_id: str, title: str, content: str, format: forum.Format) -> forum.PostThreadRsp:
        """
        该接口用于发表帖子。

        Args:
          channel_id (str): 子频道 ID。
          title (str): 线程的标题。
          content (str): 帖子的内容。
          format (forum.Format): 内容的格式。

        Returns:
          返回PostThreadRsp 对象。
        """
        route = Route(
            "PUT",
            "/channels/{channel_id}/threads",
            channel_id=channel_id,
        )

        payload = {"title": title, "content": content, "format": format}
        return await self._http.request(route, json=payload)

    async def delete_thread(self, channel_id: str, thread_id: str) -> str:
        """
        `该接口用于删除指定子频道下的某个帖子

        Args:
          channel_id (str): 要从中删除帖子的子频道的 ID。
          thread_id (str): 要删除的帖子的 ID。

        Returns:
          成功返回空字符串。
        """
        route = Route(
            "DELETE", "/channels/{channel_id}/threads/{thread_id}", channel_id=channel_id, thread_id=thread_id
        )
        return await self._http.request(route)

    # ============== 群聊消息接口 ==============
    async def post_group_message(
        self,
        group_openid: str,
        msg_type: int = 0,
        content: str = None,
        embed: message.Embed = None,
        ark: message.Ark = None,
        message_reference: message.Reference = None,
        media: message.MediaInfo = None,
        msg_id: str = None,
        msg_seq: int = 1,
        event_id: str = None,
        markdown: message.MessageMarkdown = None,
        keyboard: message.KeyboardPayload = None,
        is_wakeup: bool = None,
    ) -> message.MessageSendResult:
        """
        发送群聊消息（POST /v2/groups/{group_openid}/messages）。

        注意:
        - 被动消息有效时间 5 分钟，每条消息最多回复 5 次
        - 主动消息频控：认证机器人 60/qpm，未认证 30/qpm；单关系 20/qpm，每群每天最多 1000 条
        - 发送消息接口要求机器人连接到 websocket gateway 保持在线状态
        - msg_type: 0=纯文本(content)，2=Markdown(markdown)，7=富媒体(media)

        Args:
          group_openid (str): 您要将消息发送到的群的 ID（群 OpenID）。
          msg_type (int): 消息类型：0 是文本，2 是 markdown，7 media 富媒体
          content (str): 消息的文本内容。传了 markdown 后此字段必须为空
          embed (message.Embed): embed 消息，一种特殊的 ark
          ark (message.Ark): ark 模版消息
          message_reference (message.Reference): 引用回复，以引用形式展示
          media (message.MediaInfo): 富媒体消息，file_info 来自文件上传接口
          msg_id (str): 您要回复的消息的 ID，从事件 d.id 获取，5 分钟内有效
          msg_seq (int): 回复消息的序号，与 msg_id 联合使用，默认是1。相同的 msg_id + msg_seq 重复发送会失败。
          event_id (str): 被动回复事件 ID，与 msg_id 二选一；支持 INTERACTION_CREATE、GROUP_ADD_ROBOT、GROUP_MSG_RECEIVE
          markdown (message.MessageMarkdown): markdown 消息
          keyboard (message.KeyboardPayload): keyboard 消息
          is_wakeup (bool): 互动召回消息，与 msg_id/event_id 互斥（新增）

        Returns:
          message.MessageSendResult: 含 id（消息ID，可用于撤回）、timestamp、ext_info 的字典。
        """
        payload = {
            "msg_type": msg_type,
            "content": content,
            "embed": embed,
            "ark": ark,
            "message_reference": message_reference,
            "media": media,
            "msg_id": msg_id,
            "msg_seq": msg_seq,
            "event_id": event_id,
            "markdown": markdown,
            "keyboard": keyboard,
            "is_wakeup": is_wakeup,
        }
        route = Route("POST", "/v2/groups/{group_openid}/messages", group_openid=group_openid)
        return await self._http.request(route, json=payload)

    async def recall_group_message(self, group_openid: str, message_id: str) -> str:
        """
        撤回群聊消息（DELETE /v2/groups/{group_openid}/messages/{message_id}）。

        注意:
        - 发送超过 2 分钟的消息不可撤回
        - 机器人为群管理员时，可撤回自己的消息及普通群成员的消息；
          成员消息 ID 需从 GROUP_AT_MESSAGE_CREATE / GROUP_MESSAGE_CREATE 事件的 d.id 获取
        - 机器人为普通成员时，仅能撤回自己发送的消息，消息 ID 从发送接口响应中获取

        Args:
          group_openid (str): 群 OpenID。
          message_id (str): 消息 ID。

        Returns:
          成功执行返回空字符串。
        """
        route = Route(
            "DELETE",
            "/v2/groups/{group_openid}/messages/{message_id}",
            group_openid=group_openid,
            message_id=message_id,
        )
        return await self._http.request(route)

    async def post_group_file(
        self,
        group_openid: str,
        file_type: int,
        url: str = None,
        srv_send_msg: bool = False,
        file_name: str = None,
        upload_id: str = None,
    ) -> message.Media:
        """
        上传群聊富媒体（POST /v2/groups/{group_openid}/files）。

        Args:
          group_openid (str): 您要将消息发送到的群的 ID
          file_type (int): 媒体类型：1 图片png/jpg，2 视频mp4，3 语音silk，4 文件
          url (str): 需要发送媒体资源的url；分片上传合并时可为空
          srv_send_msg (bool): 设置 true 会直接发送消息到目标端，且会占用主动消息频次
          file_name (str): 文件名（可选，新增）
          upload_id (str): 分片上传任务 ID，来自 upload_prepare 响应；传入后走分片合并路径（新增）

        Returns:
          message.Media: 含 file_uuid、file_info、ttl 的字典。file_info 用于发送消息接口的 media 字段。
        """
        payload = {
            "file_type": file_type,
            "url": url,
            "srv_send_msg": srv_send_msg,
            "file_name": file_name,
            "upload_id": upload_id,
        }
        route = Route("POST", "/v2/groups/{group_openid}/files", group_openid=group_openid)
        return await self._http.request(route, json=payload)

    async def post_group_upload_prepare(
        self,
        group_openid: str,
        file_type: int,
        file_size: str,
        file_name: str,
        md5: str,
        sha1: str,
        md5_10m: str,
    ) -> Dict[str, Any]:
        """
        群聊富媒体分片上传第一步：预上传（POST /v2/groups/{group_openid}/upload_prepare）。

        返回 upload_id、block_size 和各分片的预签名 URL。
        客户端按 block_size 分片，逐片 HTTP PUT 到预签名 URL，每片完成后调用
        :meth:`post_group_upload_part_finish`，全部完成后携带 upload_id 调用
        :meth:`post_group_file` 完成合并。

        Args:
          group_openid (str): 群 OpenID。
          file_type (int): 业务类型：1=图片, 2=视频, 3=语音, 4=文件
          file_size (str): 文件大小（字节）
          file_name (str): 文件名
          md5 (str): 整个文件的 MD5 校验值
          sha1 (str): 整个文件的 SHA1 校验值
          md5_10m (str): 文件前 10002432 字节（约 10MB）的 MD5 校验值
        """
        payload = {
            "file_type": file_type,
            "file_size": file_size,
            "file_name": file_name,
            "md5": md5,
            "sha1": sha1,
            "md5_10m": md5_10m,
        }
        route = Route("POST", "/v2/groups/{group_openid}/upload_prepare", group_openid=group_openid)
        return await self._http.request(route, json=payload)

    async def post_group_upload_part_finish(
        self, group_openid: str, upload_id: str, part_index: int, block_size: str, md5: str
    ) -> str:
        """
        群聊富媒体分片上传第二步：通知服务端分片上传完成
        （POST /v2/groups/{group_openid}/upload_part_finish）。

        Args:
          group_openid (str): 群 OpenID。
          upload_id (str): 上传任务 ID，来自预上传响应。
          part_index (int): 分片序号，对应 UploadPart.index。
          block_size (str): 该分块的实际大小（字节）。
          md5 (str): 该分片的 MD5 校验值。
        """
        payload = {
            "upload_id": upload_id,
            "part_index": part_index,
            "block_size": block_size,
            "md5": md5,
        }
        route = Route("POST", "/v2/groups/{group_openid}/upload_part_finish", group_openid=group_openid)
        return await self._http.request(route, json=payload)

    # ============== 单聊（C2C）消息接口 ==============
    async def post_c2c_message(
        self,
        openid: str,
        msg_type: int = 0,
        content: str = None,
        embed: message.Embed = None,
        ark: message.Ark = None,
        message_reference: message.Reference = None,
        media: message.MediaInfo = None,
        msg_id: str = None,
        msg_seq: int = 1,
        event_id: str = None,
        markdown: message.MessageMarkdown = None,
        keyboard: message.KeyboardPayload = None,
        is_wakeup: bool = None,
        input_notify: message.InputNotify = None,
    ) -> message.MessageSendResult:
        """
        发送单聊消息（POST /v2/users/{user_openid}/messages）。

        注意:
        - 被动消息有效时间 60 分钟，每条消息最多回复 4 次
        - 主动消息频控：认证机器人 10/qps，未认证 5/qps & 30/qpm；单关系 20/qpm，每好友每天最多 1000 条
        - msg_type: 0=纯文本(content)，2=Markdown，6=输入中状态(input_notify)，7=富媒体(media)

        Args:
          openid (str): 您要将消息发送到的用户的 ID（用户 OpenID）。
          msg_type (int): 消息类型：0 是文本，2 是 markdown，6 输入中状态，7 media 富媒体
          content (str): 消息的文本内容。传了 markdown 后此字段必须为空
          embed (message.Embed): embed 消息，一种特殊的 ark
          ark (message.Ark): ark 模版消息
          message_reference (message.Reference): 引用回复，以引用形式展示
          media (message.MediaInfo): 富媒体消息，file_info 来自文件上传接口
          msg_id (str): 被动回复的消息 ID，从 C2C_MESSAGE_CREATE 等事件的 d.id 获取，5 分钟内有效
          msg_seq (int): 回复消息的序号，与 msg_id 联合使用，默认是1。相同的 msg_id + msg_seq 重复发送会失败。
          event_id (str): 被动回复事件 ID，与 msg_id 二选一；支持 INTERACTION_CREATE、C2C_MSG_RECEIVE、FRIEND_ADD
          markdown (message.MessageMarkdown): markdown 消息
          keyboard (message.KeyboardPayload): keyboard 消息
          is_wakeup (bool): 互动召回消息声明字段，与 msg_id/event_id 互斥（新增）
          input_notify (message.InputNotify): 输入中状态，msg_type=6 时使用（新增）

        Returns:
          message.MessageSendResult: 含 id（消息ID，可用于撤回）、timestamp、ext_info 的字典。
        """
        payload = {
            "msg_type": msg_type,
            "content": content,
            "embed": embed,
            "ark": ark,
            "message_reference": message_reference,
            "media": media,
            "msg_id": msg_id,
            "msg_seq": msg_seq,
            "event_id": event_id,
            "markdown": markdown,
            "keyboard": keyboard,
            "is_wakeup": is_wakeup,
            "input_notify": input_notify,
        }
        route = Route("POST", "/v2/users/{openid}/messages", openid=openid)
        return await self._http.request(route, json=payload)

    async def post_stream_message(
        self,
        openid: str,
        input_mode: str = "append",
        input_state: int = 1,
        index: int = 0,
        content_type: str = "text",
        content_raw: str = None,
        msg_id: str = None,
        event_id: str = None,
        stream_msg_id: str = None,
        msg_seq: int = 1,
        is_wakeup: bool = None,
    ) -> message.StreamMessageResult:
        """
        流式发送单聊消息（POST /v2/users/{user_openid}/stream_messages）。

        流式分批发送，各分片共用同一 stream_msg_id，index 从 0 递增，支持 markdown。
        首片（不携带 stream_msg_id）由服务端生成并返回 id，后续分片携带该 id；
        结束分片将 input_state 置为 10。

        注意: 仅单聊支持流式消息；群消息不支持流式参数。

        Args:
          openid (str): 用户 OpenID。
          input_mode (str): append（默认，拼接到已下发内容）/ replace（全量正文，须以上游已下发前缀开头）
          input_state (int): 1=生成中；10=生成结束
          index (int): 分片序号，从 0 递增
          content_type (str): `text` 或 `markdown`
          content_raw (str): 文本内容
          msg_id (str): 被动回复消息 ID（与 event_id 二选一）
          event_id (str): 被动回复事件 ID（与 msg_id 二选一）
          stream_msg_id (str): 流式消息 ID；首片不传，后续分片携带上一片返回的 id
          msg_seq (int): 消息序号，用于去重
          is_wakeup (bool): 是否为召回消息；true 时不校验 msg_id/event_id 有效期

        Returns:
          message.StreamMessageResult: 含 id、timestamp、ext_info、remain_msg_len 的字典。
        """
        payload = {
            "input_mode": input_mode,
            "input_state": input_state,
            "index": index,
            "content_type": content_type,
            "content_raw": content_raw,
            "msg_id": msg_id,
            "event_id": event_id,
            "stream_msg_id": stream_msg_id,
            "msg_seq": msg_seq,
            "is_wakeup": is_wakeup,
        }
        route = Route("POST", "/v2/users/{openid}/stream_messages", openid=openid)
        return await self._http.request(route, json=payload)

    async def recall_c2c_message(self, openid: str, message_id: str) -> str:
        """
        撤回单聊消息（DELETE /v2/users/{openid}/messages/{message_id}）。

        注意: 发送超过 2 分钟的消息不可撤回。

        Args:
          openid (str): 用户 OpenID。
          message_id (str): 消息 ID。

        Returns:
          成功执行返回空字符串。
        """
        route = Route(
            "DELETE",
            "/v2/users/{openid}/messages/{message_id}",
            openid=openid,
            message_id=message_id,
        )
        return await self._http.request(route)

    async def post_c2c_file(
        self,
        openid: str,
        file_type: int,
        url: str = None,
        srv_send_msg: bool = False,
        file_name: str = None,
        upload_id: str = None,
    ) -> message.Media:
        """
        上传单聊富媒体（POST /v2/users/{openid}/files）。

        注意: 单聊与群聊上传接口不互通。

        Args:
          openid (str): 您要将消息发送到的用户的 ID
          file_type (int): 媒体类型：1 图片png/jpg，2 视频mp4，3 语音silk，4 文件
          url (str): 需要发送媒体资源的url；分片上传合并时可为空
          srv_send_msg (bool): 设置 true 会直接发送消息到目标端，且会占用主动消息频次
          file_name (str): 文件名（可选，新增）
          upload_id (str): 分片上传任务 ID，来自 upload_prepare 响应（新增）

        Returns:
          message.Media: 含 file_uuid、file_info、ttl 的字典。
        """
        payload = {
            "file_type": file_type,
            "url": url,
            "srv_send_msg": srv_send_msg,
            "file_name": file_name,
            "upload_id": upload_id,
        }
        route = Route("POST", "/v2/users/{openid}/files", openid=openid)
        return await self._http.request(route, json=payload)

    async def post_c2c_upload_prepare(
        self,
        openid: str,
        file_type: int,
        file_size: str,
        file_name: str,
        md5: str,
        sha1: str,
        md5_10m: str,
    ) -> Dict[str, Any]:
        """
        单聊富媒体分片上传第一步：预上传（POST /v2/users/{openid}/upload_prepare）。

        参数含义同 :meth:`post_group_upload_prepare`。
        """
        payload = {
            "file_type": file_type,
            "file_size": file_size,
            "file_name": file_name,
            "md5": md5,
            "sha1": sha1,
            "md5_10m": md5_10m,
        }
        route = Route("POST", "/v2/users/{openid}/upload_prepare", openid=openid)
        return await self._http.request(route, json=payload)

    async def post_c2c_upload_part_finish(
        self, openid: str, upload_id: str, part_index: int, block_size: str, md5: str
    ) -> str:
        """
        单聊富媒体分片上传第二步：通知服务端分片上传完成
        （POST /v2/users/{openid}/upload_part_finish）。

        参数含义同 :meth:`post_group_upload_part_finish`。
        """
        payload = {
            "upload_id": upload_id,
            "part_index": part_index,
            "block_size": block_size,
            "md5": md5,
        }
        route = Route("POST", "/v2/users/{openid}/upload_part_finish", openid=openid)
        return await self._http.request(route, json=payload)

    # ============== 群聊管理接口（2026.08 新增） ==============
    async def get_group_info(self, group_openid: str) -> group.GroupInfo:
        """
        获取群基本信息（GET /v2/groups/{group_openid}/info）。

        注意: 该接口需要申请权限（白名单）。

        Args:
          group_openid (str): 群 OpenID。

        Returns:
          group.GroupInfo: 含 group_name、group_member_num 等字段的字典。
        """
        route = Route("GET", "/v2/groups/{group_openid}/info", group_openid=group_openid)
        return await self._http.request(route)

    async def get_group_bot_state(self, group_openid: str) -> group.GroupBotState:
        """
        获取机器人在指定群中的状态（GET /v2/groups/{group_openid}/bot_state）。

        Args:
          group_openid (str): 群 OpenID。

        Returns:
          group.GroupBotState: 含 member_openid、joined_at、allow_proactive_msg、
          recv_msg_setting、member_role 等字段的字典。
        """
        route = Route("GET", "/v2/groups/{group_openid}/bot_state", group_openid=group_openid)
        return await self._http.request(route)

    async def get_group_mute_setting(self, group_openid: str) -> group.GroupMuteSetting:
        """
        查询群禁言状态（GET /v2/groups/{group_openid}/restrict_chat_setting）。

        注意: 机器人需拥有群管理员身份；频率限制 30 QPM。

        Args:
          group_openid (str): 群 OpenID。

        Returns:
          group.GroupMuteSetting: 含 global_rule（群级禁言规则）与
          members（当前禁言中的成员列表）的字典。
        """
        route = Route("GET", "/v2/groups/{group_openid}/restrict_chat_setting", group_openid=group_openid)
        return await self._http.request(route)

    async def set_group_mute_setting(
        self, group_openid: str, members: List[group.SetMemberMuteState]
    ) -> str:
        """
        设置群成员禁言（POST /v2/groups/{group_openid}/restrict_chat_setting）。

        注意:
        - 机器人需拥有群管理员身份；最大禁言时长 30 天
        - 单次设置不能超过 10 个成员
        - 增加/更新禁言时只能操作普通成员，不能操作群主、管理员、机器人

        Args:
          group_openid (str): 群 OpenID。
          members (List[group.SetMemberMuteState]): 用户禁言列表，每项通过 op 控制增/改/删::

              {"op": "add", "member_openid": "xxx", "mute_expire_at": "2026-08-05T11:23:05+08:00"}
              op: add 增加禁言 / update 更新禁言到期时间 / del 解除禁言（可传空串表示立即解除）

        Returns:
          成功执行返回空字符串。
        """
        payload = {"members": members}
        route = Route("POST", "/v2/groups/{group_openid}/restrict_chat_setting", group_openid=group_openid)
        return await self._http.request(route, json=payload)

    async def get_group_join_requests(
        self, group_openid: str, cursor: str = None, limit: int = None
    ) -> group.JoinRequestListRsp:
        """
        拉取入群申请列表（GET /v2/groups/{group_openid}/join_request_list）。

        注意: 机器人需拥有群管理员身份。

        Args:
          group_openid (str): 群 OpenID。
          cursor (str): 分页游标，首次请求可不传或传空串。
          limit (int): 单页数量，默认 20，最大 100。

        Returns:
          group.JoinRequestListRsp: 含 list（JoinRequest 列表）与 next_cursor 的字典。
        """
        params = {}
        if cursor is not None:
            params["cursor"] = cursor
        if limit is not None:
            params["limit"] = limit
        route = Route("GET", "/v2/groups/{group_openid}/join_request_list", group_openid=group_openid)
        return await self._http.request(route, params=params)

    async def approve_group_join_request(
        self,
        group_openid: str,
        member_openid: str,
        op: str,
        join_request_id: str = None,
        reject_reason: str = None,
        add_to_member_blacklist: bool = None,
    ) -> str:
        """
        审批入群请求（POST /v2/groups/{group_openid}/approval_join_request/{member_openid}）。

        注意: 机器人需拥有群管理员身份；频率限制 60 QPM。

        Args:
          group_openid (str): 群 OpenID。
          member_openid (str): 申请人的成员 OpenID。
          op (str): 审批动作："approve" 通过，"decline" 拒绝。
          join_request_id (str): 申请 ID（从 GROUP_JOIN_REQUEST 事件或申请列表接口获取）。
          reject_reason (str): 拒绝理由，仅在 op=decline 时可填。
          add_to_member_blacklist (bool): 是否同时加入群黑名单，默认 false，仅在 decline 时可填。

        Returns:
          成功执行返回空字符串。
        """
        payload = {
            "op": op,
            "join_request_id": join_request_id,
            "reject_reason": reject_reason,
            "add_to_member_blacklist": add_to_member_blacklist,
        }
        route = Route(
            "POST",
            "/v2/groups/{group_openid}/approval_join_request/{member_openid}",
            group_openid=group_openid,
            member_openid=member_openid,
        )
        return await self._http.request(route, json=payload)

    async def create_join_approval_strategy(
        self,
        group_openids: List[str] = None,
        group_ids: List[int] = None,
        is_enable: str = "on",
        expire_at: str = None,
        remark: str = None,
    ) -> group.JoinApprovalStrategy:
        """
        创建入群自动审批策略（POST /v2/groups/join_approval_strategy）。

        注意:
        - 一个机器人最多 20 个策略
        - 群列表上限 100 个
        - 设置的规则只有当机器人拥有群管理员身份时才会生效

        Args:
          group_openids (List[str]): 关联群 openid 列表，与 group_ids 互斥（二选一必填）。
          group_ids (List[int]): 关联 QQ 群号列表，与 group_openids 互斥。
          is_enable (str): on-启用 / off-关闭，默认 on。
          expire_at (str): 过期时间（RFC3339 格式），不传默认一年过期。
          remark (str): 策略备注，最多 255 个汉字。

        Returns:
          group.JoinApprovalStrategy: 含 strategy_id、is_enable、expire_at 的字典。
        """
        payload = {
            "group_openids": group_openids,
            "group_ids": group_ids,
            "is_enable": is_enable,
            "expire_at": expire_at,
            "remark": remark,
        }
        route = Route("POST", "/v2/groups/join_approval_strategy")
        return await self._http.request(route, json=payload)

    async def get_join_approval_strategies(
        self, cursor: str = None, limit: int = None
    ) -> Dict[str, Any]:
        """
        查询入群自动审批策略列表（GET /v2/groups/join_approval_strategy）。

        按创建时间倒序，支持分页。

        Args:
          cursor (str): 分页游标，首次请求可不传。
          limit (int): 单页数量。

        Returns:
          含策略列表与分页信息的字典。
        """
        params = {}
        if cursor is not None:
            params["cursor"] = cursor
        if limit is not None:
            params["limit"] = limit
        route = Route("GET", "/v2/groups/join_approval_strategy")
        return await self._http.request(route, params=params)

    async def update_join_approval_strategy(
        self,
        strategy_id: str,
        group_openids: List[str] = None,
        group_ids: List[int] = None,
        is_enable: str = None,
        expire_at: str = None,
        remark: str = None,
    ) -> Dict[str, Any]:
        """
        修改入群自动审批策略（PATCH /v2/groups/join_approval_strategy/{strategy_id}）。

        Args:
          strategy_id (str): 策略 ID。
          group_openids (List[str]): 关联群 openid 列表，与 group_ids 互斥。
          group_ids (List[int]): 关联 QQ 群号列表，与 group_openids 互斥。
          is_enable (str): on / off。
          expire_at (str): 过期时间（RFC3339 格式）。
          remark (str): 策略备注。
        """
        payload = {
            "group_openids": group_openids,
            "group_ids": group_ids,
            "is_enable": is_enable,
            "expire_at": expire_at,
            "remark": remark,
        }
        route = Route(
            "PATCH", "/v2/groups/join_approval_strategy/{strategy_id}", strategy_id=strategy_id
        )
        return await self._http.request(route, json=payload)

    async def delete_join_approval_strategy(self, strategy_id: str) -> str:
        """
        删除入群自动审批策略（DELETE /v2/groups/join_approval_strategy/{strategy_id}）。

        Args:
          strategy_id (str): 策略 ID。
        """
        route = Route(
            "DELETE", "/v2/groups/join_approval_strategy/{strategy_id}", strategy_id=strategy_id
        )
        return await self._http.request(route)

    async def execute_join_approval_strategy(self, strategy_id: str) -> Dict[str, Any]:
        """
        执行入群自动审批策略（POST /v2/groups/join_approval_strategy/{strategy_id}/execute）。

        对存量申请全量扫描执行，异步完成（约 10 分钟）。

        Args:
          strategy_id (str): 策略 ID。
        """
        route = Route(
            "POST",
            "/v2/groups/join_approval_strategy/{strategy_id}/execute",
            strategy_id=strategy_id,
        )
        return await self._http.request(route, json={})

    # ============== 自定义菜单接口（2026.08 新增） ==============
    async def get_menu(self) -> menu.MenuRsp:
        """
        查询全局自定义菜单（GET /v2/menu）。

        注意: 自定义菜单仅支持 C2C（单聊）场景，对所有用户生效。

        Returns:
          menu.MenuRsp: 含 version（菜单版本号）与 menu（菜单配置）的字典。
        """
        route = Route("GET", "/v2/menu")
        return await self._http.request(route)

    async def update_menu(self, menu_payload: menu.Menu = None) -> menu.MenuUpdateRsp:
        """
        修改全局自定义菜单（PUT /v2/menu），传入后会覆盖原有的完整菜单配置。

        注意: 频率限制 5 QPM；菜单仅对 C2C（单聊）场景生效。

        Args:
          menu_payload (menu.Menu): 菜单配置::

              {"items": [
                  {"type": "send_message", "name": "帮助", "send_message": "/help"},
                  {"type": "link", "name": "官网", "link": "https://example.com"},
              ]}

        Returns:
          menu.MenuUpdateRsp: 含 version（修改后的菜单版本号）的字典。
        """
        payload = {"menu": menu_payload}
        route = Route("PUT", "/v2/menu")
        return await self._http.request(route, json=payload)

    # ============== 指令面板接口（2026.08 新增） ==============
    async def create_panel(
        self,
        scope: str,
        panel: panel.Panel,
        target_type: str = "all",
        user_openids: List[str] = None,
        group_openids: List[str] = None,
    ) -> panel.PanelCreateRsp:
        """
        创建指令面板（POST /v2/panels）。一个机器人最多创建 20 个面板。

        Args:
          scope (str): 生效场景：c2c（单聊）/ group（群聊）/ channel（文字子频道）/ dm（频道私信）
          panel (panel.Panel): 面板配置内容::

              {"items": [{"name": "签到", "desc": "每日签到", "type": "command"}], "remark": "备注"}

          target_type (str): 作用范围：all（全量生效）/ specific（仅指定用户/群生效）
          user_openids (List[str]): 用户 openid 列表，仅 c2c 且 target_type=specific 时有效，一次最多 20 个
          group_openids (List[str]): 群 openid 列表，仅 group 且 target_type=specific 时有效，一次最多 20 个

        Returns:
          panel.PanelCreateRsp: 含 panel_id 的字典。
        """
        payload = {
            "scope": scope,
            "target_type": target_type,
            "user_openids": user_openids,
            "group_openids": group_openids,
            "panel": panel,
        }
        route = Route("POST", "/v2/panels")
        return await self._http.request(route, json=payload)

    async def get_panels(self, scope: str, cursor: str = None, limit: int = None) -> panel.PanelListRsp:
        """
        查询指令面板列表（GET /v2/panels），分页拉取指定场景下已生效的面板，按设置时间倒序。

        Args:
          scope (str): 生效场景，必填：c2c / group / channel / dm
          cursor (str): 分页游标；首请求不传或传空串，后续传上次的 next_cursor
          limit (int): 每页条数，默认 20，最大 50

        Returns:
          panel.PanelListRsp: 含 records、next_cursor、is_end 的字典。
        """
        params = {"scope": scope}
        if cursor is not None:
            params["cursor"] = cursor
        if limit is not None:
            params["limit"] = limit
        route = Route("GET", "/v2/panels")
        return await self._http.request(route, params=params)

    async def get_panel(self, panel_id: str) -> panel.PanelRecord:
        """
        查询指令面板详情（GET /v2/panels/{panel_id}）。

        Args:
          panel_id (str): 面板 ID。

        Returns:
          panel.PanelRecord: 含面板内容、生效场景、关联 openid 列表等。
        """
        route = Route("GET", "/v2/panels/{panel_id}", panel_id=panel_id)
        return await self._http.request(route)

    async def update_panel(
        self,
        panel_id: str,
        panel_config: panel.Panel = None,
        target_type: str = None,
        user_openids: List[str] = None,
        group_openids: List[str] = None,
    ) -> Dict[str, Any]:
        """
        修改指令面板（PUT /v2/panels/{panel_id}）。

        Args:
          panel_id (str): 面板 ID。
          panel_config (panel.Panel): 面板配置内容。
          target_type (str): 作用范围：all / specific。
          user_openids (List[str]): 用户 openid 列表。
          group_openids (List[str]): 群 openid 列表。
        """
        payload = {
            "panel": panel_config,
            "target_type": target_type,
            "user_openids": user_openids,
            "group_openids": group_openids,
        }
        route = Route("PUT", "/v2/panels/{panel_id}", panel_id=panel_id)
        return await self._http.request(route, json=payload)

    async def update_panel_target(
        self,
        panel_id: str,
        add_user_openids: List[str] = None,
        del_user_openids: List[str] = None,
        add_group_openids: List[str] = None,
        del_group_openids: List[str] = None,
    ) -> str:
        """
        修改指令面板关联对象（PUT /v2/panels/{panel_id}/target）。

        对指定指令面板关联的用户或群进行添加或删除操作。
        c2c 场景操作用户 openid，group 场景操作群 openid；channel 和 dm 场景为全局生效。

        Args:
          panel_id (str): 面板 ID。
          add_user_openids (List[str]): 添加关联的用户 openid 列表。
          del_user_openids (List[str]): 删除关联的用户 openid 列表。
          add_group_openids (List[str]): 添加关联的群 openid 列表。
          del_group_openids (List[str]): 删除关联的群 openid 列表。
        """
        payload = {
            "add_user_openids": add_user_openids,
            "del_user_openids": del_user_openids,
            "add_group_openids": add_group_openids,
            "del_group_openids": del_group_openids,
        }
        route = Route("PUT", "/v2/panels/{panel_id}/target", panel_id=panel_id)
        return await self._http.request(route, json=payload)

    async def delete_panel(self, panel_id: str) -> str:
        """
        删除指令面板（DELETE /v2/panels/{panel_id}）。删除后该面板不再对任何用户或群生效。

        Args:
          panel_id (str): 面板 ID。
        """
        route = Route("DELETE", "/v2/panels/{panel_id}", panel_id=panel_id)
        return await self._http.request(route)
