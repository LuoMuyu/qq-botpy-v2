# -*- coding: utf-8 -*-
"""botpy — QQ 机器人 Python SDK（适配最新官方 API）。

基于 tencent-connect/botpy 开发，接口名与原版保持兼容，
并适配 QQ 机器人开放平台最新文档（https://bot.q.qq.com/wiki/develop/api-v2/）：

  - 接口统一域名 api.bot.qq.com，鉴权使用 Access Token
  - 群聊/单聊消息（含撤回、流式消息、输入中状态、互动召回）
  - 富媒体上传（URL 直传与分片上传）
  - 群管理（群信息/机器人状态/禁言管理/入群审批/自动审批策略）
  - 自定义菜单与指令面板
  - 新增事件：群消息全量模式、用户申请加群、群成员加入/退出
  - 新增 Webhook（HTTP 回调）接入模式
"""

from .logging import get_logger
from .client import *
from .flags import *

logger = get_logger()

__version__ = "1.0.2"
