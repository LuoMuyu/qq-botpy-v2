# -*- coding: utf-8 -*-
"""指令面板类型定义（/v2/panels 系列接口）。

指令面板对应 C 端在单聊/群聊/文字子频道/频道私信场景下
输入框 "/" 拉起的指令面板。一个机器人最多创建 20 个面板。
"""

from typing import List, TypedDict


class PanelItem(TypedDict, total=False):
    name: str  # 元素名称，最多 14 字符（约 7 个汉字）；command 点击后填入输入框
    desc: str  # 元素描述，面板中展示给用户，最多 30 字符
    type: str  # command（指令）/ link（链接跳转）
    only_admin: bool  # true 时仅频道/群管理员可点击
    link: str  # 跳转 URL，仅 type=link 时有效，必须以 https:// 开头


class Panel(TypedDict, total=False):
    items: List[PanelItem]  # 面板元素列表，最多 20 个
    remark: str  # 面板备注，最多 255 字符，不对用户展示
    version: int  # 当前版本号


class PanelRecord(TypedDict, total=False):
    """面板记录（列表/详情接口返回）。"""

    panel_id: str
    scope: str  # c2c / group / channel / dm
    target_type: str  # all（全局）/ specific（指定用户/群，仅 c2c、group）
    panel: Panel
    created_at: str  # RFC3339
    updated_at: str  # RFC3339
    version: int


class PanelListRsp(TypedDict, total=False):
    """查询指令面板列表接口返回值。"""

    records: List[PanelRecord]
    next_cursor: str  # 空串表示最后一页
    is_end: bool


class PanelCreateRsp(TypedDict, total=False):
    """创建指令面板接口返回值。"""

    panel_id: str
