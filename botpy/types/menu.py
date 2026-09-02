# -*- coding: utf-8 -*-
"""自定义菜单类型定义（GET/PUT /v2/menu）。

自定义菜单仅支持 C2C（单聊）场景，对所有用户生效。
"""

from typing import List, TypedDict


class Switch(TypedDict, total=False):
    switch_id: str  # 开关唯一标识；切换后消息 ext 字段携带标识（如 "search=1"）
    default: bool  # 初始状态：true 打开，false 关闭


class SubMenuItem(TypedDict, total=False):
    name: str  # 最多 14 个字符（约 7 个中文汉字）
    type: str  # 仅 send_message / link，二级菜单不支持 menu 类型
    send_message: str  # 点击后文本自动填入聊天输入框
    link: str  # 跳转链接，必须以 https:// 开头


class MenuItem(TypedDict, total=False):
    name: str  # 最多 10 个字符（1 个中文汉字算 2 个字符）
    type: str  # switch / send_message / link / menu
    sub_menu_items: List[SubMenuItem]  # 仅 type=menu 时有效；最多 5 个，不支持再嵌套
    send_message: str  # 仅 type=send_message 时有效
    link: str  # 仅 type=link 时有效
    switch: Switch  # 仅 type=switch 时有效


class Menu(TypedDict, total=False):
    items: List[MenuItem]  # 菜单项列表，最多 10 个，按列表顺序从左到右展示


class MenuRsp(TypedDict, total=False):
    """查询全局自定义菜单接口返回值。"""

    version: int  # 当前菜单的版本号
    menu: Menu  # 当前生效的菜单配置，未设置过菜单时该字段为空


class MenuUpdateRsp(TypedDict, total=False):
    """修改全局自定义菜单接口返回值。"""

    version: int  # 修改后的菜单版本号
