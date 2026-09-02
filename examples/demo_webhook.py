# -*- coding: utf-8 -*-
# Webhook（HTTP 回调）接入示例
#
# 适用场景：无法维持 WebSocket 长连接（Serverless、部分托管环境）。
# 前置条件：
#   1. pip install pynacl
#   2. 在 QQ 开放平台管理端（https://q.qq.com/qqbot/#/developer/webhook-setting）
#      配置回调地址，如: https://your-domain.com:8080/bot/webhook
#      允许端口: 80 / 443 / 8080 / 8443
#   3. 公网需可访问；本地调试可用内网穿透工具

import botpy
from botpy.message import GroupMessage


class MyClient(botpy.Client):
    async def on_group_at_message_create(self, message: GroupMessage):
        await message.reply(content=f"webhook 收到: {message.content}")

    async def on_c2c_message_create(self, message):
        await message.reply(content="你好，我通过 Webhook 接收消息")


intents = botpy.Intents(public_messages=True)
client = MyClient(intents=intents, bot_log=True)

# webhook_run 会自动完成：
#   - op=13 回调地址验证（Ed25519 签名应答）
#   - 事件推送验签（X-Signature-Ed25519 / X-Signature-Timestamp 头）
#   - 处理成功返回 {"op": 12}
#   - 事件分发到与 WebSocket 模式相同的 on_xx 回调
client.webhook_run(
    appid="102623701",
    secret="你的AppSecret",
    host="0.0.0.0",
    port=8080,
    path="/bot/webhook",
)
