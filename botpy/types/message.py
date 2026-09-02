# -*- coding: utf-8 -*-
from enum import Enum
from typing import List, TypedDict

from .gateway import MessagePayload
from .inline import Keyboard


class Attachment(TypedDict):
    url: str


class Thumbnail(TypedDict):
    url: str  # 图片地址


class EmbedField(TypedDict):
    name: str


class Embed(TypedDict, total=False):
    title: str  # 标题
    prompt: str  # 消息弹窗内容
    thumbnail: Thumbnail  # 缩略图
    fields: List[EmbedField]  # 消息创建时间


class ArkObjKv(TypedDict):
    key: str
    value: str


class ArkObj(TypedDict):
    obj_kv: List[ArkObjKv]


class ArkKv(TypedDict, total=False):
    key: str
    value: str
    obj: List[ArkObj]


class Ark(TypedDict):
    template_id: int
    kv: List[ArkKv]


class Reference(TypedDict):
    message_id: str
    ignore_get_message_error: bool


class MessageMarkdownParams(TypedDict):
    key: str
    values: List[str]


class MarkdownPayload(TypedDict, total=False):
    """频道消息 markdown 内容。"""

    custom_template_id: str
    params: List[MessageMarkdownParams]
    content: str


class KeyboardPayload(TypedDict, total=False):
    """频道消息 keyboard 内容。"""

    id: str
    content: Keyboard


class Media(TypedDict, total=False):
    """富媒体上传接口返回值，media.file_info 用于发送 msg_type=7 的消息。"""

    file_uuid: str  # 文件ID
    file_info: str  # 文件信息，用于发消息接口的media字段使用
    ttl: int  # 有效期，标识剩余多少秒到期，到期后 file_info 失效，当等于 0 时，表示可长期使用
    id: str  # 消息唯一ID，仅 srv_send_msg=true 时返回
    raw_url: str  # COS 预签名下载链接（仅分片合并路径且为图片/视频/语音时返回）


class MediaInfo(TypedDict, total=False):
    """发送群/单聊富媒体消息（msg_type=7）时的 media 字段。"""

    file_info: str  # 来自文件上传接口返回值


class MessageMarkdown(TypedDict, total=False):
    """群/单聊消息 markdown 内容（最新文档结构）。"""

    template_id: int  # 【已废弃】平台 Markdown 模板 ID
    content: str  # Markdown 内容
    custom_template_id: str  # 【已废弃】自定义模板 ID
    force_verify_image_resource: bool  # 为 true 时图片转存失败则报错且不发送


class InputNotify(TypedDict, total=False):
    """单聊"输入中"状态（msg_type=6）。"""

    input_type: int  # 填 1
    input_second: int  # 最长 60 秒


class MessageExtInfo(TypedDict, total=False):
    """群/单聊消息发送接口返回的扩展信息。"""

    ref_idx: str  # 引用消息索引（可用于 message_reference 引用机器人自己的消息）


class MessageSendResult(TypedDict, total=False):
    """群/单聊消息发送接口返回值。"""

    id: str  # 消息 ID，可用于后续撤回
    timestamp: str  # 发送时间，RFC3339 东八区
    ext_info: MessageExtInfo


class StreamMessagePayload(TypedDict, total=False):
    """单聊流式消息（POST /v2/users/{user_openid}/stream_messages）请求体。"""

    input_mode: str  # append（默认，拼接到已下发内容）/ replace（全量正文，须以上游已下发前缀开头）
    input_state: int  # 1=生成中；10=生成结束
    index: int  # 分片序号，从 0 递增
    content_type: str  # text / markdown
    content_raw: str  # 文本内容
    event_id: str  # 被动回复事件 ID（与 msg_id 二选一）
    msg_id: str  # 被动回复消息 ID（与 event_id 二选一）
    stream_msg_id: str  # 流式消息 ID，首片由服务端生成返回，后续分片透传
    msg_seq: int  # 消息序号，用于去重
    is_wakeup: bool  # 是否为互动召回消息


class StreamMessageResult(TypedDict, total=False):
    """单聊流式消息返回值。"""

    id: str  # 消息 ID；首片返回 stream_msg_id 供后续分片使用
    timestamp: str
    ext_info: MessageExtInfo
    remain_msg_len: int  # 流式消息剩余字符数


class Message(MessagePayload):
    edited_timestamp: str
    mention_everyone: str
    attachments: List[Attachment]
    embeds: List[Embed]
    ark: Ark
    message_reference: Reference
    markdown: MarkdownPayload
    keyboard: KeyboardPayload


class TypesEnum(Enum):
    around = "around"
    before = "before"
    after = "after"
    latest = ""


class MessagesPager(TypedDict):
    type: TypesEnum
    id: str
    limit: str


class DmsPayload(TypedDict):
    guild_id: str  # 注意，这里是私信会话的guild_id， 每个私信会话居然是个单独的guild
    channel_id: str
    creat_time: str


class DMOriginalAuthor(TypedDict):
    id: str
    username: str
    bot: bool


class DeletedMessage(TypedDict):
    guild_id: str
    channel_id: str
    id: str
    author: DMOriginalAuthor


class DeletionOperator(TypedDict):
    id: str


class DeletedMessageInfo(TypedDict):
    message: DeletedMessage
    op_user: DeletionOperator
