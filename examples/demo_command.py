# -*- coding: utf-8 -*-
# 指令装饰器示例（botpy.ext.command_util，与原版兼容）

import botpy
from botpy.ext.command_util import Commands
from botpy.message import Message


class MyClient(botpy.Client):
    @Commands("点歌")
    async def search_music(self, params: str, message: Message):
        await message.reply(content=f"为你点播: {params}")

    @Commands("天气")
    async def query_weather(self, params: str, message: Message):
        await message.reply(content=f"{params} 今天晴，25℃")

    async def on_at_message_create(self, message: Message):
        await self.invoke_search_music(message=message)
        await self.invoke_query_weather(message=message)
        # 上面未命中任何指令时，可继续处理其它逻辑


intents = botpy.Intents(public_guild_messages=True)
client = MyClient(intents=intents)
client.run(appid="102623701", secret="你的AppSecret")
