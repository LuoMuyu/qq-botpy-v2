# -*- coding: utf-8 -*-
# 频道 @机器人 消息回复示例（与原版 botpy 写法完全一致）

import botpy
from botpy import logging
from botpy.message import Message

_log = logging.get_logger()


class MyClient(botpy.Client):
    async def on_ready(self):
        _log.info(f"robot 「{self.robot.name}」 on_ready!")

    async def on_at_message_create(self, message: Message):
        await message.reply(content=f"收到了你的消息: {message.content}")


intents = botpy.Intents(public_guild_messages=True)  # 公域频道消息事件
client = MyClient(intents=intents)
client.run(appid="102623701", secret="你的AppSecret")
