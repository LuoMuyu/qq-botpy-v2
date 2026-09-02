# -*- coding: utf-8 -*-
# 单聊（C2C）消息示例：文本/富媒体回复、"输入中"状态、语音识别

import asyncio

import botpy
from botpy.message import C2CMessage


class MyClient(botpy.Client):
    async def on_c2c_message_create(self, message: C2CMessage):
        # 收到语音消息时，平台会附带转写结果与 WAV 转码地址
        for att in message.attachments:
            if att.content_type == "voice":
                print("语音转写结果:", att.asr_refer_text)
                print("WAV 地址:", att.voice_wav_url)

        # 单聊被动消息 60 分钟内有效，每条消息最多回复 4 次

        # 发送"输入中"状态（msg_type=6，最长 60 秒）
        await self.api.post_c2c_message(
            openid=message.openid,
            msg_type=6,
            input_notify={"input_type": 1, "input_second": 30},
            msg_id=message.id,
        )

        await asyncio.sleep(2)  # 模拟处理耗时

        await message.reply(content=f"你说的是：{message.content}")


intents = botpy.Intents(public_messages=True)  # 群聊 + 单聊事件共用 GROUP_AND_C2C_EVENT
client = MyClient(intents=intents)
client.run(appid="102623701", secret="你的AppSecret")
