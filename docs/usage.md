# qq-botpy 使用文档

基于 QQ 机器人开放平台 API v2 最新文档（https://bot.q.qq.com/wiki/develop/api-v2/ ）适配的 Python SDK 使用指南。接口名与官方原版 [tencent-connect/botpy](https://github.com/tencent-connect/botpy) 完全兼容。

> 本文档对应 SDK 版本 1.0.x，官方文档更新至 2026.08。

## 目录

1. [简介与特性](#一简介与特性)
2. [安装](#二安装)
3. [准备工作：创建机器人](#三准备工作创建机器人)
4. [快速开始](#四快速开始)
5. [事件订阅（Intents）](#五事件订阅intents)
6. [事件回调与消息对象](#六事件回调与消息对象)
7. [API 调用参考](#七api-调用参考)
8. [富媒体上传](#八富媒体上传)
9. [流式消息与输入状态](#九流式消息与输入状态)
10. [Webhook 接入模式](#十webhook-接入模式)
11. [从原版 botpy 迁移](#十一从原版-botpy-迁移)
12. [沙箱环境、日志与错误处理](#十二沙箱环境日志与错误处理)
13. [消息规则与频率限制](#十三消息规则与频率限制)
14. [常见问题 FAQ](#十四常见问题-faq)

---

## 一、简介与特性

`qq-botpy`（导入包名为 `botpy`）是用于开发 QQ 机器人的异步 Python SDK，支持：

- **频道（Guild）**：子频道消息、私信、身份组、公告、日程、精华消息、表情表态、论坛、音频等
- **群聊（Group）**：@机器人消息、全量消息模式、富媒体、引用回复、撤回、禁言管理、入群审批
- **单聊（C2C）**：单聊消息、富媒体、流式消息、输入中状态、互动召回
- **两种接入方式**：WebSocket 长连接（推荐）与 Webhook HTTP 回调

相比原版 botpy 的主要更新：

| 变更点 | 说明 |
| --- | --- |
| 接口域名 | 统一为 `api.bot.qq.com`（原 `api.sgroup.qq.com`） |
| 鉴权 | Access Token（`QQBot {access_token}`），SDK 自动获取与刷新 |
| 新增接口 | 消息撤回（群/单聊）、流式消息、群管理、自定义菜单、指令面板、分片上传等 27 个 |
| 新增事件 | 群消息全量模式、用户申请加群、群成员加入/退出 |
| 事件体增强 | `message_type`、`message_scene`（`msg_idx` 引用索引）、语音转写、引用消息元素等 |
| 新增接入模式 | Webhook（HTTP 回调 + Ed25519 验签） |
| 心跳 | 按 Hello 下发的 `heartbeat_interval` 动态设置 |

## 二、安装

要求 Python 3.8+。

```bash
# 从源码安装
pip install .

# 需要 Webhook 模式时（Ed25519 签名，依赖 PyNaCl）
pip install ".[webhook]"
```

核心依赖：`aiohttp`（异步 HTTP/WebSocket）、`PyYAML`（配置读取）、`APScheduler`（定时任务扩展）。

## 三、准备工作：创建机器人

1. 前往 [QQ 开放平台](https://q.qq.com/) 注册开发者账号，创建机器人，获得 **AppID** 与 **AppSecret**。
2. 在管理端配置机器人能力（消息收发、群聊/单聊场景等），按需申请接口权限。
3. 机器人在沙箱测试群/频道中先行验证，再发布上线。

> 原来的静态 `Token` 鉴权方式已废弃，本 SDK 统一使用 Access Token 鉴权（自动完成，无需关心）。

## 四、快速开始

### 4.1 频道机器人

```python
import botpy
from botpy.message import Message

class MyClient(botpy.Client):
    async def on_ready(self):
        print(f"机器人 {self.robot.name} 已就绪")

    async def on_at_message_create(self, message: Message):
        # 被动回复（5 分钟内有效）
        await message.reply(content=f"收到：{message.content}")

intents = botpy.Intents(public_guild_messages=True)  # 频道公域消息
client = MyClient(intents=intents)
client.run(appid="你的appid", secret="你的AppSecret")
```

### 4.2 群聊机器人

```python
import botpy
from botpy.message import GroupMessage

class MyClient(botpy.Client):
    async def on_group_at_message_create(self, message: GroupMessage):
        if message.content == "你好":
            await message.reply(content="你好！")
        elif message.content.startswith("复述 "):
            await message.reply(content=message.content[3:])

intents = botpy.Intents(public_messages=True)
client = MyClient(intents=intents)
client.run(appid="你的appid", secret="你的AppSecret")
```

### 4.3 单聊机器人

```python
import botpy
from botpy.message import C2CMessage

class MyClient(botpy.Client):
    async def on_c2c_message_create(self, message: C2CMessage):
        await message.reply(content=f"你说的是：{message.content}")

intents = botpy.Intents(public_messages=True)  # 群聊与单聊共用
client = MyClient(intents=intents)
client.run(appid="你的appid", secret="你的AppSecret")
```

### 4.4 异步上下文中使用

```python
import botpy

intents = botpy.Intents(public_messages=True)

async def main():
    async with MyClient(intents=intents) as client:
        await client.start(appid="你的appid", secret="你的AppSecret")
```

## 五、事件订阅（Intents）

构造 `Client` 时通过 `Intents` 声明需要订阅的事件。多个事件用布尔参数组合：

```python
intents = botpy.Intents(public_messages=True, interaction=True)

# 或使用快捷方式
intents = botpy.Intents.all()      # 全部事件（含需要私域权限的）
intents = botpy.Intents.default()  # 全部公域事件
intents = botpy.Intents.none()     # 不订阅
```

| Intents 属性 | 位值 | 需要权限 | 包含事件 |
| --- | --- | --- | --- |
| `guilds` | `1 << 0` | 基础 | 频道创建/更新/删除、子频道创建/更新/删除 |
| `guild_members` | `1 << 1` | 需申请 | 频道成员进入/资料变更/移除 |
| `guild_messages` | `1 << 9` | 仅私域 | 频道内全部消息（MESSAGE_CREATE/DELETE） |
| `guild_message_reactions` | `1 << 10` | 需申请 | 频道消息表情表态添加/删除 |
| `direct_message` | `1 << 12` | 需申请 | 频道私信消息 |
| `open_forum_event` | `1 << 18` | 公域可用 | 开放论坛主题/帖子/评论事件 |
| `audio_or_live_channel_member` | `1 << 19` | 需申请 | 音视频/直播子频道成员进出 |
| **`group_member_event`** 🆕 | `1 << 24` | 需申请 | **群成员加入/退出**（GROUP_MEMBER_ADD/QUIT） |
| `public_messages` | `1 << 25` | 公域可用 | 群聊/单聊消息、机器人入群退群、消息接收开关、好友增删、**入群申请** |
| `interaction` | `1 << 26` | 需申请 | 按钮等互动事件 |
| `message_audit` | `1 << 27` | 需申请 | 频道消息审核结果 |
| `forums` | `1 << 28` | 仅私域 | 论坛事件 |
| `audio_action` | `1 << 29` | 需申请 | 音频开始/结束、上麦/下麦 |
| `public_guild_messages` | `1 << 30` | 公域可用 | 频道 @机器人消息、公域消息删除 |

> ⚠️ 订阅了无权限的 intents 会导致 WebSocket 连接直接报错关闭，请按实际申请到的权限配置。

## 六、事件回调与消息对象

在 `Client` 子类中定义 `on_事件名` 的 `async` 方法即可接收对应事件。事件名对照：

### 6.1 群聊 / 单聊（`public_messages`，1<<25）

| 事件回调 | 触发条件 | 参数对象 |
| --- | --- | --- |
| `on_group_at_message_create` | 群内用户 @机器人 | `GroupMessage` |
| `on_group_message_create` 🆕 | 群消息**全量模式**：群内所有消息（需在管理端开通"接收所有消息"） | `GroupMessage` |
| `on_c2c_message_create` | 用户给机器人发单聊消息 | `C2CMessage` |
| `on_group_add_robot` / `on_group_del_robot` | 机器人被拉入/移出群聊 | `GroupManageEvent` |
| `on_group_msg_reject` / `on_group_msg_receive` | 群开启/关闭机器人主动消息 | `GroupManageEvent` |
| `on_friend_add` / `on_friend_del` | 用户添加/删除机器人好友（🆕 含 `scene`/`scene_param`/`author`/`short_code`） | `C2CManageEvent` |
| `on_c2c_msg_reject` / `on_c2c_msg_receive` | 用户关闭/开启机器人主动消息 | `C2CManageEvent` |
| `on_group_join_request` 🆕 | 用户申请加群（需机器人为群管理员） | `GroupJoinRequest` |

### 6.2 群成员（`group_member_event`，1<<24）🆕

| 事件回调 | 触发条件 | 参数对象 |
| --- | --- | --- |
| `on_group_member_add` | 有新成员加入群聊 | `GroupMemberEvent` |
| `on_group_member_quit` | 有成员退出群聊 | `GroupMemberEvent` |

### 6.3 频道

| 事件回调 | Intents | 参数对象 |
| --- | --- | --- |
| `on_at_message_create` | 公域消息 | `Message` |
| `on_public_message_delete` | 公域消息 | `Message` |
| `on_message_create` / `on_message_delete` | 频道消息（私域） | `Message` |
| `on_direct_message_create` / `on_direct_message_delete` | 频道私信 | `DirectMessage` |
| `on_guild_create` / `on_guild_update` / `on_guild_delete` | 频道 | `Guild` |
| `on_channel_create` / `on_channel_update` / `on_channel_delete` | 频道 | `Channel` |
| `on_guild_member_add` / `on_guild_member_update` / `on_guild_member_remove` | 频道成员 | `Member` |
| `on_message_reaction_add` / `on_message_reaction_remove` | 表情表态 | `Reaction` |
| `on_interaction_create` | 互动 | `Interaction` |
| `on_message_audit_pass` / `on_message_audit_reject` | 消息审核 | `MessageAudit` |
| `on_audio_start` / `on_audio_finish` / `on_audio_on_mic` / `on_audio_off_mic` | 音频 | `Audio` |
| `on_forum_thread_*` / `on_forum_post_*` / `on_forum_reply_*` | 论坛（私域） | `Thread`/dict |
| `on_open_forum_*` | 开放论坛 | `OpenThread`/dict |
| `on_ready` / `on_resumed` | 连接生命周期 | 无 |

### 6.4 群/单聊消息对象

`GroupMessage` 与 `C2CMessage` 的常用属性（按最新文档新增了多项字段）：

| 属性 | 类型 | 说明 |
| --- | --- | --- |
| `id` | str | 消息 ID，用于被动回复（`msg_id`）与撤回 |
| `content` | str | 文本内容（群聊已去除 @机器人前缀） |
| `author` | `_User` | 发送者。群聊含 `member_openid`、`member_role`；单聊含 `user_openid` |
| `group_openid` | str | 群 OpenID（仅 GroupMessage） |
| `timestamp` | str | 发送时间（RFC3339） |
| `message_type` | int | 🆕 0=普通文本、3=结构化卡片、101=并行消息、102=聊天记录、103=引用消息 |
| `message_scene` | 🆕 | 消息场景上下文，含 `msg_idx`（引用回复用）、`ref_msg_idx`、`auth_token` |
| `attachments` | list | 🆕 附件，语音类含 `voice_wav_url`（WAV 转码）与 `asr_refer_text`（语音转写结果） |
| `ark_data` | dict | 🆕 卡片消息数据（`ark_type`：miniapp/map/music_together 等） |
| `msg_elements` | list | 🆕 消息元素列表（引用消息 103 时含被引用内容） |
| `mentions` | list | 被 @ 的用户列表 |

便捷方法：

```python
# 解析 message_scene.ext，如 {"msg_idx": "REFIDX_xxx", "ref_msg_idx": "REFIDX_yyy"}
ext = message.get_scene_ext()

# 回复（等价于 self.api.post_group_message(group_openid=..., msg_id=message.id, ...)）
await message.reply(content="text")
await message.reply(msg_type=7, media={"file_info": file_info})
```

### 6.5 入群申请对象（GroupJoinRequest）🆕

```python
class MyClient(botpy.Client):
    async def on_group_join_request(self, request: GroupJoinRequest):
        print(request.username, request.verify_info)  # 申请人昵称、验证消息/问答

        await request.approve()      # 通过
        # 或
        await request.decline(       # 拒绝
            reject_reason="群已满",
            add_to_member_blacklist=True,
        )
```

属性：`group_openid`、`join_request_id`、`member_openid`、`username`、`apply_at`、
`apply_source`（`self_apply` 主动申请 / `invited` 被邀请）、`invited_by`、`risk_tips`、
`verify_info`（`method`：`verify_message`/`admin_review_qa`）、`auto_approved`（自动审批通过的策略 ID）。

### 6.6 原始载荷访问（raw）

所有事件对象均提供 `raw` 属性，保存平台下发的原始事件体字典。若平台未来新增字段而 SDK 尚未跟进，
可直接从 `raw` 读取，无需等待版本更新：

```python
async def on_group_at_message_create(self, message: GroupMessage):
    # message.raw 即事件 payload 的 d 字段（原始字典）
    print(message.raw)
```

各事件对象均已对齐最新文档字段表，包括：

- `Guild` / `Channel` / `Member`：`op_user_id`（操作人）
- `C2CManageEvent`（`on_friend_add`）：`scene`（加好友场景值）、`scene_param`（callback_data）、
  `author.union_openid`、`short_code`（机器人分享短链）
- `Interaction.data.resolved`：`feedback_opt`、`checked`、`action`、`message_scene`、`authorize_data`
  （对应最新互动类型 13 消息反馈 / 15 进出故事集 / 16 切换模型 / 18 用户授权 / 19 群授权 / 20 群授权状态变更）

## 七、API 调用参考

所有接口通过 `client.api`（`BotAPI` 实例）调用。以下按场景列出；标注 🆕 的为对齐最新文档新增的接口，其余接口与原版 botpy 兼容（内部已按最新域名/鉴权适配）。

### 7.1 Websocket 接入点

| 方法 | 说明 |
| --- | --- |
| `get_ws_url()` | 获取带分片的 WSS 接入点（`GET /gateway/bot`），返回 `url`、`shards`、`session_start_limit` |
| `get_gateway()` 🆕 | 获取通用 WSS 接入点（`GET /gateway`），单连接接入用 |

### 7.2 群聊消息

| 方法 | 说明 |
| --- | --- |
| `post_group_message(group_openid, msg_type=0, content=None, embed=None, ark=None, message_reference=None, media=None, msg_id=None, msg_seq=1, event_id=None, markdown=None, keyboard=None, is_wakeup=None)` | 发送群消息。`msg_type`：0 文本 / 2 Markdown / 7 富媒体。返回 `{"id", "timestamp", "ext_info"}` |
| `recall_group_message(group_openid, message_id)` 🆕 | 撤回群消息（发送 2 分钟内） |
| `post_group_file(group_openid, file_type, url=None, srv_send_msg=False, file_name=None, upload_id=None)` | 上传群富媒体。`file_type`：1 图片 / 2 视频 / 3 语音 / 4 文件。返回 `{"file_uuid", "file_info", "ttl"}` |

```python
# 文本被动回复
await client.api.post_group_message(group_openid=gid, content="hello", msg_id=msg_id)

# 第二次回复同一条消息需递增 msg_seq
await client.api.post_group_message(group_openid=gid, content="again", msg_id=msg_id, msg_seq=2)

# Markdown（需申请权限）
await client.api.post_group_message(
    group_openid=gid, msg_type=2,
    markdown={"content": "# 标题\n**加粗**"},   # 模板参数方式已废弃
    msg_id=msg_id,
)

# 引用回复：message_id 从事件 get_scene_ext()["msg_idx"] 获取（机器人自己的消息从响应 ext_info.ref_idx 获取）
await client.api.post_group_message(
    group_openid=gid, content="引用回复",
    message_reference={"message_id": msg_idx}, msg_id=msg_id,
)

# 互动召回消息（用户 30 天内主动对话过的召回，与 msg_id/event_id 互斥）
await client.api.post_group_message(group_openid=gid, content="召回", is_wakeup=True)
```

### 7.3 单聊（C2C）消息

| 方法 | 说明 |
| --- | --- |
| `post_c2c_message(openid, msg_type=0, ..., is_wakeup=None, input_notify=None)` | 发送单聊消息。`msg_type`：0 文本 / 2 Markdown / 6 输入中 / 7 富媒体 |
| `recall_c2c_message(openid, message_id)` 🆕 | 撤回单聊消息（2 分钟内） |
| `post_c2c_file(openid, file_type, url=None, srv_send_msg=False, file_name=None, upload_id=None)` | 上传单聊富媒体 |
| `post_stream_message(openid, ...)` 🆕 | 流式发送单聊消息（见第九节） |

```python
# 富媒体：先上传再发送
media = await client.api.post_c2c_file(openid=uid, file_type=1, url="https://example.com/a.png")
await client.api.post_c2c_message(openid=uid, msg_type=7, media={"file_info": media["file_info"]}, msg_id=msg_id)

# "输入中"状态（最长 60 秒）
await client.api.post_c2c_message(
    openid=uid, msg_type=6,
    input_notify={"input_type": 1, "input_second": 30},
    msg_id=msg_id,
)
```

### 7.4 群管理（🆕 2026.08 新增）

| 方法 | 频率限制 | 说明 |
| --- | --- | --- |
| `get_group_info(group_openid)` | 30 QPM | 群基本信息：名称、简介、分类、标签、成员数 |
| `get_group_bot_state(group_openid)` | 30 QPM | 机器人群内状态：入群时间、是否允许主动消息、消息接收设置、角色 |
| `get_group_mute_setting(group_openid)` | 30 QPM | 查询禁言状态：全员禁言规则 + 禁言中的成员列表 |
| `set_group_mute_setting(group_openid, members)` | 60 QPM | 设置禁言。单次 ≤10 人，最长 30 天，仅普通成员 |
| `get_group_join_requests(group_openid, cursor=None, limit=None)` | 30 QPM | 拉取入群申请列表 |
| `approve_group_join_request(group_openid, member_openid, op, join_request_id=None, reject_reason=None, add_to_member_blacklist=None)` | 60 QPM | 审批入群：`op="approve"` / `"decline"` |
| `create_join_approval_strategy(group_openids=None, group_ids=None, is_enable="on", expire_at=None, remark=None)` | 60 QPM | 创建入群自动审批策略（`group_openids` 与 `group_ids` 互斥，二选一必填；机器人 ≤20 个策略） |
| `get_join_approval_strategies(cursor=None, limit=None)` | — | 策略列表 |
| `update_join_approval_strategy(strategy_id, ...)` | — | 修改策略（PATCH） |
| `delete_join_approval_strategy(strategy_id)` | — | 删除策略 |
| `execute_join_approval_strategy(strategy_id)` | — | 手动执行策略（全量扫描存量申请，异步约 10 分钟） |

```python
# 禁言某成员 10 分钟
from datetime import datetime, timedelta, timezone

expire = datetime.now(timezone(timedelta(hours=8))) + timedelta(minutes=10)
await client.api.set_group_mute_setting(
    group_openid=gid,
    members=[{
        "op": "add",                       # add / update / del
        "member_openid": member_openid,
        "mute_expire_at": expire.isoformat(),
    }],
)

# 解除禁言
await client.api.set_group_mute_setting(
    group_openid=gid,
    members=[{"op": "del", "member_openid": member_openid, "mute_expire_at": ""}],
)
```

> ⚠️ 禁言与入群审批类接口均要求机器人拥有**群管理员**身份。

### 7.5 自定义菜单与指令面板（🆕 2026.08 新增）

| 方法 | 频率限制 | 说明 |
| --- | --- | --- |
| `get_menu()` | 30 QPM | 查询全局自定义菜单（`GET /v2/menu`），仅 C2C 场景生效 |
| `update_menu(menu)` | 5 QPM | 修改全局自定义菜单（`PUT /v2/menu`），整体覆盖 |
| `create_panel(scope, panel, target_type="all", user_openids=None, group_openids=None)` | 10 QPM | 创建指令面板（机器人 ≤20 个） |
| `get_panels(scope, cursor=None, limit=None)` | 30 QPM | 面板列表，`scope` 必填：`c2c`/`group`/`channel`/`dm` |
| `get_panel(panel_id)` | 30 QPM | 面板详情 |
| `update_panel(panel_id, panel_config=None, ...)` | 10 QPM | 修改面板 |
| `update_panel_target(panel_id, add_user_openids=None, del_user_openids=None, add_group_openids=None, del_group_openids=None)` | — | 修改面板关联对象 |
| `delete_panel(panel_id)` | — | 删除面板 |

```python
# 设置单聊全局菜单
await client.api.update_menu(menu={
    "items": [
        {"type": "send_message", "name": "帮助", "send_message": "/help"},
        {"type": "link", "name": "官网", "link": "https://example.com"},
        {"type": "menu", "name": "更多", "sub_menu_items": [
            {"type": "send_message", "name": "设置", "send_message": "/settings"},
        ]},
    ],
})

# 创建群聊指令面板（用户输入 / 时拉起）
rsp = await client.api.create_panel(
    scope="group",
    panel={"items": [
        {"name": "签到", "desc": "每日签到领奖励", "type": "command"},
        {"name": "帮助", "desc": "查看帮助", "type": "command", "only_admin": False},
    ]},
    target_type="all",
)
panel_id = rsp["panel_id"]
```

### 7.6 频道相关接口（与原版兼容）

频道（Guild）、子频道（Channel）、身份组、成员、频道消息、频道私信、禁言、公告、日程、精华消息、表情表态、帖子、音频、接口权限等接口全部保留，方法名与参数与原版 botpy 一致：

<details>
<summary>完整方法列表（点击展开）</summary>

- 频道：`get_guild`、`me_guilds`
- 子频道：`get_channel`、`get_channels`、`create_channel`、`update_channel`、`delete_channel`
- 身份组：`get_guild_roles`、`create_guild_role`、`update_guild_role`、`delete_guild_role`、`create_guild_role_member`、`delete_guild_role_member`、`get_guild_role_members`
- 成员：`get_guild_member`、`get_guild_members`、`get_delete_member`、`get_voice_members`
- 子频道权限：`get_channel_user_permissions`、`update_channel_user_permissions`、`get_channel_role_permissions`、`update_channel_role_permissions`
- 频道消息：`get_message`、`post_message`（🆕 新增 `msg_seq` 参数）、`recall_message`、`post_keyboard_message`、`patch_guild_message`、`on_interaction_result`
- 频道私信：`create_dms`、`post_dms`（🆕 新增 `msg_seq` 参数）
- 表情表态：`put_reaction`、`delete_reaction`、`get_reaction_users`
- 精华消息：`put_pin`、`delete_pin`、`get_pins`
- 频道禁言：`mute_all`、`cancel_mute_all`、`mute_member`、`mute_multi_member`、`cancel_mute_multi_member`
- 公告：`create_announce`、`create_recommend_announce`、`delete_announce`
- 日程：`get_schedules`、`get_schedule`、`create_schedule`、`update_schedule`、`delete_schedule`
- 帖子：`get_threads`、`get_thread_detail`、`post_thread`、`delete_thread`
- 音频：`update_audio`、`on_microphone`、`off_microphone`
- 用户：`me`
- 接口权限：`get_permissions`、`post_permission_demand`

</details>

## 八、富媒体上传

### 8.1 URL 直传

平台从 `url` 下载并转存，适合公开可访问的文件：

```python
media = await client.api.post_group_file(
    group_openid=gid,
    file_type=1,                      # 1 图片(png/jpg) / 2 视频(mp4) / 3 语音(silk) / 4 文件
    url="https://example.com/a.png",
    srv_send_msg=False,               # False 仅上传；True 直接发送并占用主动消息频次
)
# 返回 {"file_uuid", "file_info", "ttl"}
# file_info 有时效（ttl 秒），过期需重新上传
```

大小限制：图片/语音软限 20MB、视频 30MB、文件 200MB；超软限降级为文件类型，超 200MB 报错。

### 8.2 分片上传（推荐用于大文件）

无需提供公网 URL，SDK 提供完整流程接口：

```python
import hashlib

data = open("big.mp4", "rb").read()
head = data[:10002432]  # 前 ~10MB

# 1. 预上传：获取 upload_id、block_size、各分片预签名 URL
prepare = await client.api.post_group_upload_prepare(
    group_openid=gid,
    file_type=2,
    file_size=str(len(data)),
    file_name="big.mp4",
    md5=hashlib.md5(data).hexdigest(),
    sha1=hashlib.sha1(data).hexdigest(),
    md5_10m=hashlib.md5(head).hexdigest(),
)

# 2. 按 block_size 分片，PUT 到预签名 URL，每片完成后通知服务端
block_size = int(prepare["block_size"])
for part in prepare["parts"]:
    chunk = data[part["index"] * block_size: (part["index"] + 1) * block_size]
    await upload_to_presigned_url(part["presigned_url"], chunk)   # HTTP PUT，见下
    await client.api.post_group_upload_part_finish(
        group_openid=gid,
        upload_id=prepare["upload_id"],
        part_index=part["index"],
        block_size=str(len(chunk)),
        md5=hashlib.md5(chunk).hexdigest(),
    )

# 3. 全部分片完成后，携带 upload_id 合并（此时 url 可为空）
media = await client.api.post_group_file(
    group_openid=gid,
    file_type=2,
    upload_id=prepare["upload_id"],
    file_name="big.mp4",
)
```

其中"PUT 到预签名 URL"可用 aiohttp 直接实现（预签名 URL 无需鉴权头）：

```python
import aiohttp

async def upload_to_presigned_url(url, chunk: bytes):
    async with aiohttp.ClientSession() as session:
        async with session.put(url, data=chunk) as resp:
            resp.raise_for_status()
```

> 单聊分片上传使用对应的 `post_c2c_upload_prepare` / `post_c2c_upload_part_finish`，
> 群聊与单聊的上传接口不互通。

## 九、流式消息与输入状态

### 9.1 流式消息（仅单聊）

适合 AI 生成内容的"打字机"效果。各分片共用同一 `stream_msg_id`，`index` 从 0 递增，结束片 `input_state=10`：

```python
chunks = ["# 回答\n", "第二段…\n", "完成。"]
stream_msg_id = None
for i, chunk in enumerate(chunks):
    last = i == len(chunks) - 1
    rsp = await client.api.post_stream_message(
        openid=uid,
        input_mode="append",              # append 追加 / replace 全量替换（须以上游已下发前缀开头）
        input_state=10 if last else 1,    # 1 生成中 / 10 结束
        index=i,
        content_type="markdown",          # text / markdown
        content_raw=chunk,
        msg_id=msg_id,                    # 被动回复
        stream_msg_id=stream_msg_id,      # 首片不传，服务端生成
    )
    stream_msg_id = rsp["id"]
```

频率限制 50 QPS。**群消息不支持流式参数**。

### 9.2 输入中状态（仅单聊）

```python
await client.api.post_c2c_message(
    openid=uid, msg_type=6,
    input_notify={"input_type": 1, "input_second": 30},
    msg_id=msg_id,
)
```

## 十、Webhook 接入模式

除 WebSocket 外，平台支持通过 HTTP 回调（Webhook）接收事件，适用于 Serverless、函数计算等无法维持长连接的场景。

### 10.1 使用方式

```bash
pip install "qq-botpy[webhook]"   # 依赖 PyNaCl
```

```python
import botpy

class MyClient(botpy.Client):
    async def on_group_at_message_create(self, message):
        await message.reply(content="webhook 收到")

client = MyClient(intents=botpy.Intents(public_messages=True))
client.webhook_run(
    appid="你的appid",
    secret="你的AppSecret",
    host="0.0.0.0",
    port=8080,                # 平台仅允许 80 / 443 / 8080 / 8443
    path="/bot/webhook",
)
```

然后在 [管理端 Webhook 设置](https://q.qq.com/qqbot/#/developer/webhook-setting) 配置回调地址，如 `https://your.domain.com:8080/bot/webhook`。事件回调写法与 WebSocket 模式**完全一致**。

### 10.2 协议细节

SDK 自动处理了以下协议（也可用 `botpy.webhook` 模块自定义接入）：

- **回调地址验证（op=13）**：平台请求 `d` 中携带 `plain_token`、`event_ts`，服务端返回 `{"plain_token": ..., "signature": ...}`，signature 为对 `event_ts + plain_token` 的 Ed25519 签名（hex）
- **推送验签**：请求头 `X-Signature-Ed25519`（hex 签名）与 `X-Signature-Timestamp`，签名内容为 `timestamp + body`；私钥 seed 由 AppSecret 循环填充至 32 字节生成
- **HTTP Callback ACK**：处理成功返回 `{"op": 12}`

自定义用法：

```python
from botpy.webhook import WebhookServer, generate_signature, check_signature

server = WebhookServer(client, secret="你的AppSecret", path="/bot/webhook")
await server.start(host="0.0.0.0", port=8080)   # 在 asyncio 环境中
```

## 十一、从原版 botpy 迁移

**代码层面无需任何修改**。原版 64 个 `BotAPI` 方法、全部事件回调、`types` 类型、`ext` 扩展（指令装饰器等）均保持兼容。

需要注意的行为变化：

1. **域名与鉴权自动更新**：SDK 内部使用 `api.bot.qq.com` 与 Access Token，无需改动。
2. **沙箱环境**：`Client(is_sandbox=True)` 对应 `sandbox.api.bot.qq.com`。
3. **`msg_seq` 参数补充**：`post_message` / `post_dms` 新增可选 `msg_seq` 参数（原调用不受影响）。
4. **群/单聊消息返回值**：`post_group_message` / `post_c2c_message` 现按最新文档返回 `{"id", "timestamp", "ext_info"}`。
5. **消息对象新增字段**：`GroupMessage` / `C2CMessage` 新增 `message_type`、`message_scene`、`ark_data`、`msg_elements` 等属性；原有属性（`id`、`content`、`author`、`reply()` 等）不变。
6. **心跳间隔**：由固定 30 秒改为按平台 Hello 下发的 `heartbeat_interval` 动态设置，无需改动。
7. **Python 版本**：修复了 Python 3.12+ 中 `asyncio.get_event_loop()` 无运行循环时的报错问题。

## 十二、沙箱环境、日志与错误处理

### 12.1 沙箱环境

```python
client = MyClient(intents=intents, is_sandbox=True)
```

### 12.2 日志

```python
# 方式一：构造参数
client = MyClient(
    intents=intents,
    log_format="%(asctime)s [%(levelname)s] %(message)s",
    log_level=logging.INFO,
    bot_log=True,           # True 启用 / None 禁用扩展 / False 禁用扩展+控制台输出
    ext_handlers=True,      # True 时启用按天轮转的文件日志 botpy.log
)

# 方式二：代码中获取
from botpy import get_logger
logger = get_logger()
```

### 12.3 错误处理

```python
from botpy.errors import (
    ApiError,                    # 🆕 携带平台业务错误码，如 err.code == 40034005
    AuthenticationFailedError,   # 401
    ForbiddenError,              # 403
    NotFoundError,               # 404
    SequenceNumberError,         # 429 频率限制
    ServerError,                 # 500/504
)

try:
    await client.api.post_group_message(group_openid=gid, content="x", msg_id=msg_id)
except ApiError as e:
    if e.code == 40054005:      # msg_id + msg_seq 重复
        ...
    elif e.code == 40034005:    # msg_id 过期
        ...
```

常见业务错误码：

| 错误码 | 含义 |
| --- | --- |
| 22006 | 消息类型与内容不匹配 |
| 40034005 / 304103 | 消息 ID（msg_id）已过期 |
| 40054005 | 消息去重（相同 msg_id+msg_seq），更换 msg_seq 重试 |
| 40034100 | 主动消息超过频控 |
| 40034127 | 无 markdown 模板权限 |
| 40064004 | 已超出消息撤回时限（2 分钟） |
| 850018 | 群或机器人被禁言 |
| 850026 | 平台下载原始文件失败（检查 URL 可访问性） |
| 850031 | 上传文件超过大小限制 |

### 12.4 定时任务扩展

```python
from botpy.ext.cog_apscheduler import scheduler   # 已配置 Asia/Shanghai 的 AsyncIOScheduler

@scheduler.scheduled_job("cron", hour=9, minute=0)
async def daily_task():
    await client.api.post_group_message(group_openid=gid, content="早安")
```

## 十三、消息规则与频率限制

| 场景 | 被动消息有效期/次数 | 主动消息频控 |
| --- | --- | --- |
| 群聊 | 5 分钟 / 每条消息 5 次 | 认证 60 qpm、未认证 30 qpm；单关系 20 qpm；每群每天 1000 条 |
| 单聊 | 60 分钟 / 每条消息 4 次 | 认证 10 qps、未认证 5 qps 且 30 qpm；单关系 20 qpm；每好友每天 1000 条 |
| 频道文字子频道 | 5 分钟 | 默认每天每子频道 20 条；需 WebSocket 在线 |
| 频道私信 | 5 分钟 | 每用户每天 2 条、每天累计 200 条 |

- 相同 `msg_id` 可能重复推送，用 `msg_seq` 去重；相同 `msg_id + msg_seq` 的发送会失败
- 撤回时限：发送超过 **2 分钟** 不可撤回
- 互动召回消息（`is_wakeup=True`）：用户主动对话后 30 天内 4 个周期（当天/1-3 天/3-7 天/7-30 天），每周期 1 条

## 十四、常见问题 FAQ

**Q1: WebSocket 连接建立后立即被关闭？**
订阅了未申请权限的 intents（如 `guild_messages`、`forums`），请在管理端申请对应权限，或仅订阅已开通的事件。

**Q2: 群消息回复报 40034102 无权限？**
未携带 `msg_id` 的发送会按主动消息处理。回复用户消息时务必带上事件中的 `message.id` 作为 `msg_id`。

**Q3: 第二次回复同一条消息失败（40054005）？**
相同 `msg_id + msg_seq` 会判重，多次回复需递增 `msg_seq`（1、2、3…），且不超过被动消息次数上限。

**Q4: `is_sandbox=True` 连接失败？**
沙箱环境需要使用沙箱频道的机器人，并确认 AppID/Secret 为同一应用。

**Q5: Webhook 模式验签失败（403）？**
确认 `secret` 与平台配置的 AppSecret 一致；确认请求体未被代理/网关改写（验签使用原始 body）；本地调试建议用内网穿透并保证透传 `X-Signature-Ed25519` 与 `X-Signature-Timestamp` 头。

**Q6: 收不到群内非 @机器人 的消息？**
全量消息事件 `on_group_message_create` 需要在管理端开通"接收所有消息"功能。

**Q7: 富媒体上传后发送报 file_info 失效？**
`file_info` 有 ttl 时效，过期需重新上传；群聊与单聊的上传接口不互通，不能用群上传的 file_info 发单聊。

**Q8: 如何获取用户/群的真实 QQ 号？**
平台基于 OpenID 体系，事件与接口中均为 `openid` 形式（`group_openid`、`member_openid`、`user_openid`），不提供真实 QQ 号。
