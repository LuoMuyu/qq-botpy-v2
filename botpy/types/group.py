# -*- coding: utf-8 -*-
"""群聊/C2C 单聊相关类型定义。

对应最新官方文档中群聊管理、群消息（全量模式）等接口与事件的数据结构。
"""

from typing import List, TypedDict, Union


class V2User(TypedDict, total=False):
    """群/C2C 事件中的用户对象。"""

    id: str  # 用户唯一标识（OpenID 格式）
    username: str  # 用户昵称
    bot: bool  # 是否为机器人
    union_openid: str  # 跨应用统一用户 OpenID（可能为空）
    union_user_account: str  # 跨应用统一用户账号（可能为空）
    user_openid: str  # 用户 OpenID（单聊场景使用）
    member_openid: str  # 群成员 OpenID（群聊场景使用）
    member_role: str  # 群内角色：member / admin / owner


class MessageScene(TypedDict, total=False):
    """消息场景上下文。"""

    source: str  # 场景来源，default=默认聊天窗口
    ext: List[str]  # 扩展数据（key=value）：msg_idx、ref_msg_idx、auth_token


class MessageAttachment(TypedDict, total=False):
    """消息附件。"""

    url: str  # 附件下载 URL
    filename: str
    width: int
    height: int
    size: int  # 文件大小（字节）
    content_type: str  # voice / image/jpeg / image/png / image/gif / video/mp4 / file
    voice_wav_url: str  # 语音转 WAV 后的文件 URL
    asr_refer_text: str  # 语音 ASR 参考结果


class ARKData(TypedDict, total=False):
    """结构化卡片消息数据。"""

    prompt: str  # 用户操作提示文本
    ark_type: str  # tuwen / feed / miniapp / map / contact_card / video_share / music_together
    ark_name: str  # 卡片类型中文名称
    fields: dict  # 卡片字段：title、desc、jump_url、preview、source 等


class MsgElement(TypedDict, total=False):
    """消息元素（递归结构，message_type=103 引用消息时携带被引用内容）。"""

    msg_idx: str  # 元素的引用消息索引
    author: V2User
    message_type: int  # 0=普通文本 3=结构化卡片 101=并行消息 102=聊天记录 103=引用消息
    content: str
    attachments: List[MessageAttachment]
    ark_data: List[ARKData]
    msg_elements: List["MsgElement"]


class GroupMessagePayload(TypedDict, total=False):
    """GROUP_AT_MESSAGE_CREATE / GROUP_MESSAGE_CREATE 事件体。"""

    id: str  # 消息 ID，可用于被动回复和撤回
    author: V2User
    content: str  # 消息文本内容（已去除@机器人的前缀）
    group_openid: str
    timestamp: str  # RFC3339
    message_type: int
    message_scene: MessageScene
    attachments: List[MessageAttachment]
    mentions: List[V2User]
    ark_data: List[ARKData]
    msg_elements: List[MsgElement]


class C2CMessagePayload(TypedDict, total=False):
    """C2C_MESSAGE_CREATE 事件体。"""

    id: str
    author: V2User  # user_openid 有值
    content: str
    timestamp: str
    message_type: int
    message_scene: MessageScene
    attachments: List[MessageAttachment]
    ark_data: List[ARKData]
    msg_elements: List[MsgElement]


class GroupInfo(TypedDict, total=False):
    """获取群基本信息接口返回值（GET /v2/groups/{group_openid}/info）。"""

    group_openid: str
    group_name: str
    group_finger_memo: str  # 群简介
    group_class_text: str  # 群分类
    group_tags: List[str]
    group_member_num: int


class GroupBotState(TypedDict, total=False):
    """获取机器人群内状态接口返回值（GET /v2/groups/{group_openid}/bot_state）。"""

    member_openid: str  # 机器人的 openid
    joined_at: str  # 入群时间戳（RFC3339）
    allow_proactive_msg: bool  # 是否接收主动推送
    recv_msg_setting: str  # 群内接收消息设置：all / only_mention / mention_and_context
    member_role: str  # member / owner / admin


class SetMemberMuteState(TypedDict, total=False):
    """设置群禁言时的成员项。"""

    op: str  # add 增加禁言 / update 更新禁言到期时间 / del 解除禁言
    member_openid: str
    mute_expire_at: str  # 禁言到期时间（RFC3339）；op=del 时可传空串表示立即解除


class MuteScheduleRule(TypedDict, total=False):
    task_id: str
    start_at: str  # RFC3339
    end_at: str  # RFC3339
    enabled: bool


class MuteRecurringRule(TypedDict, total=False):
    task_id: str
    weekdays: List[int]  # 1~7，1=周一
    start_time: str  # HH:mm（北京时间）
    end_time: str  # HH:mm；小于 start_time 表示跨天
    enabled: bool


class GlobalMuteRule(TypedDict, total=False):
    """群级禁言规则。"""

    mode: str  # none 未开启 / always 始终禁言 / schedule 定时禁言
    schedule_rules: List[MuteScheduleRule]
    recurring_rules: List[MuteRecurringRule]


class MemberMuteState(TypedDict, total=False):
    """处于禁言中的成员状态。"""

    member_openid: str
    mute_expire_at: str  # RFC3339
    username: str
    union_openid: str


class GroupMuteSetting(TypedDict, total=False):
    """查询群禁言状态接口返回值（GET /v2/groups/{group_openid}/restrict_chat_setting）。"""

    global_rule: GlobalMuteRule
    members: List[MemberMuteState]


class ReviewQA(TypedDict, total=False):
    question: str
    answer: str


class VerifyInfo(TypedDict, total=False):
    """入群验证方式。"""

    method: str  # verify_message / admin_review_qa
    verify_message: str
    review_qa_list: List[ReviewQA]


class AutoApproved(TypedDict, total=False):
    """自动审批通过的扩展信息（仅事件下行携带）。"""

    strategy_id: str


class JoinRequest(TypedDict, total=False):
    """入群申请。"""

    join_request_id: str  # 申请ID，需在审批接口回传
    risk_tips: str  # 安全提示语
    union_openid: str
    member_openid: str  # 申请人 openid
    username: str  # 申请人昵称
    apply_at: str  # 申请时间戳（RFC3339）
    apply_source: str  # self_apply 主动申请 / invited 被邀请
    invited_by: str  # 邀请人 openid（apply_source=invited 时有效）
    bot: bool  # 是否为机器人账号
    verify_info: VerifyInfo


class JoinRequestListRsp(TypedDict, total=False):
    """入群申请列表接口返回值。"""

    list: List[JoinRequest]
    next_cursor: str  # 下一页游标，空串表示已到末页


class JoinApprovalStrategy(TypedDict, total=False):
    """入群自动审批策略。"""

    strategy_id: str
    group_openids: List[str]  # 关联群 openid 列表（与 group_ids 互斥）
    group_ids: List[int]  # 关联 QQ 群号列表（与 group_openids 互斥）
    is_enable: str  # on / off
    expire_at: str  # 过期时间（RFC3339），不传默认一年
    remark: str  # 备注，最多 255 个汉字


class JoinRequestEventPayload(TypedDict, total=False):
    """GROUP_JOIN_REQUEST 事件体。"""

    group_openid: str
    join_request_id: str
    risk_tips: str
    union_openid: str
    member_openid: str
    username: str
    apply_at: str
    apply_source: str
    invited_by: str
    bot: bool
    verify_info: VerifyInfo
    auto_approved: AutoApproved


class GroupMemberEventPayload(TypedDict, total=False):
    """GROUP_MEMBER_ADD / GROUP_MEMBER_QUIT 事件体。"""

    timestamp: int  # 事件时间戳（Unix 秒）
    group_openid: str
    member_openid: str
    user_openid: str
