# -*- coding: utf-8 -*-
# 单聊流式消息示例：像打字机一样分段发送 AI 生成内容

import asyncio

import botpy
from botpy.message import C2CMessage


class MyClient(botpy.Client):
    async def on_c2c_message_create(self, message: C2CMessage):
        if message.content != "流式":
            return

        # 首片：不携带 stream_msg_id，服务端生成并返回 id
        chunks = ["# 流式消息演示\n\n", "这是第二段内容。\n\n", "结束。"]
        stream_msg_id = None
        for index, chunk in enumerate(chunks):
            is_last = index == len(chunks) - 1
            rsp = await self.api.post_stream_message(
                openid=message.openid,
                input_mode="append",        # append: 追加；replace: 全量替换
                input_state=10 if is_last else 1,  # 1=生成中，10=生成结束
                index=index,                # 分片序号，从 0 递增
                content_type="markdown",
                content_raw=chunk,
                msg_id=message.id,          # 被动回复
                msg_seq=1,
                stream_msg_id=stream_msg_id,
            )
            stream_msg_id = rsp["id"]


intents = botpy.Intents(public_messages=True)
client = MyClient(intents=intents)
client.run(appid="102623701", secret="你的AppSecret")
