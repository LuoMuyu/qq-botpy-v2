# -*- coding: utf-8 -*-
# 群聊消息收发示例：文本回复、富媒体（图片）回复、撤回、引用回复

import botpy
from botpy.message import GroupMessage


class MyClient(botpy.Client):
    async def on_group_at_message_create(self, message: GroupMessage):
        # 1. 文本回复（被动回复，5 分钟内有效，最多 5 次，超过 1 次需递增 msg_seq）
        if message.content == "你好":
            await message.reply(content="你好，我是机器人！")
            return

        # 2. 富媒体回复：先上传图片拿到 file_info，再以 msg_type=7 发送
        if message.content == "图片":
            media = await self.api.post_group_file(
                group_openid=message.group_openid,
                file_type=1,  # 1 图片 / 2 视频 / 3 语音 / 4 文件
                url="https://example.com/demo.png",  # 平台会下载转存
            )
            await message.reply(msg_type=7, media={"file_info": media["file_info"]})
            return

        # 3. 引用回复：msg_idx 可从 message.get_scene_ext() 获取
        if message.content == "引用":
            msg_idx = message.get_scene_ext().get("msg_idx")
            await message.reply(
                content="这是一条引用回复",
                message_reference={"message_id": msg_idx} if msg_idx else None,
            )
            return

        # 4. 撤回机器人自己刚发的消息（发送超过 2 分钟不可撤回）
        if message.content == "echo":
            sent = await message.reply(content=f"echo: {message.content}")
            await self.api.recall_group_message(
                group_openid=message.group_openid,
                message_id=sent["id"],
            )


intents = botpy.Intents(public_messages=True)  # GROUP_AND_C2C_EVENT (1<<25)
client = MyClient(intents=intents)
client.run(appid="102623701", secret="你的AppSecret")
