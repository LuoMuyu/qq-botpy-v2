# -*- coding: utf-8 -*-
# 群管理示例（2026.08 新增接口）：群信息、机器人状态、禁言管理、入群审批

import botpy
from botpy.manage import GroupJoinRequest, GroupMemberEvent


class MyClient(botpy.Client):
    async def on_group_join_request(self, request: GroupJoinRequest):
        """用户申请加群（需机器人为群管理员）。

        可直接审批，也可结合 verify_info 里的验证消息/问答做自动审核。
        """
        print(f"收到入群申请: {request.username}, 验证消息: {request.verify_info}")

        # 自动通过（也支持 request.decline(reason, add_to_member_blacklist=True)）
        await request.approve()

    async def on_group_member_add(self, event: GroupMemberEvent):
        """新成员入群（需订阅 group_member_event intents，新事件类型 1<<24）。"""
        info = await self.api.get_group_info(event.group_openid)
        print(f"群「{info['group_name']}」已有 {info['group_member_num']} 名成员")

    async def on_group_at_message_create(self, message):
        if message.content == "禁言状态":
            setting = await self.api.get_group_mute_setting(message.group_openid)
            await message.reply(content=f"全员禁言模式: {setting.get('global_rule', {}).get('mode')}")

        elif message.content.startswith("禁言 "):
            _, member_openid, minutes = message.content.split(" ")
            from datetime import datetime, timedelta, timezone

            expire = datetime.now(timezone(timedelta(hours=8))) + timedelta(minutes=int(minutes))
            await self.api.set_group_mute_setting(
                message.group_openid,
                members=[{
                    "op": "add",
                    "member_openid": member_openid,
                    "mute_expire_at": expire.isoformat(),
                }],
            )
            await message.reply(content=f"已禁言 {member_openid} {minutes} 分钟")

        elif message.content == "我的状态":
            state = await self.api.get_group_bot_state(message.group_openid)
            await message.reply(
                content=f"角色: {state['member_role']}, 主动消息: {'允许' if state['allow_proactive_msg'] else '不允许'}"
            )


intents = botpy.Intents(
    public_messages=True,       # 群/C2C 消息与 GROUP_JOIN_REQUEST 事件
    group_member_event=True,    # 群成员加入/退出事件（新增 intents）
)
client = MyClient(intents=intents)
client.run(appid="102623701", secret="你的AppSecret")
