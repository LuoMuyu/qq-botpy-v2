# qq-botpy-v2

基于 QQ 机器人开放平台 **API v2 最新文档**（https://bot.q.qq.com/wiki/develop/api-v2/ ）适配的 Python SDK。
项目基于官方 [tencent-connect/botpy](https://github.com/tencent-connect/botpy) 开发（该库已两年未更新），**接口名与原版完全兼容**，已有代码可直接迁移。

> PyPI 包名为 `qq-botpy-v2`，代码导入名保持 `botpy`（与原版一致）。
> 📖 完整使用文档：[docs/usage.md](docs/usage.md) ｜ 🚀 发布指南：[docs/publish.md](docs/publish.md)

## 特性

- ✅ **兼容原版 botpy**：`botpy.Client`、`botpy.Intents`、`client.api.*` 全部 64 个接口方法签名不变，事件回调（`on_at_message_create`、`on_group_at_message_create` 等）不变
- ✅ **对齐最新文档**（更新至 2026.08）：
  - 接口统一域名 `api.bot.qq.com`，鉴权使用 Access Token（`QQBot {token}`）
  - 群聊/单聊消息收发、**撤回**（2 分钟内）、**引用回复**、互动召回（`is_wakeup`）
  - 单聊**流式消息**（打字机效果）与"输入中"状态（`input_notify`）
  - 富媒体上传：URL 直传 + **分片上传**（`upload_prepare` / `upload_part_finish`）
  - 群管理接口：群信息、机器人群内状态、**禁言管理**、**入群申请审批**、**入群自动审批策略**
  - **自定义菜单**（`/v2/menu`）与**指令面板**（`/v2/panels`）管理接口
  - 新增事件：群消息全量模式（`GROUP_MESSAGE_CREATE`）、用户申请加群（`GROUP_JOIN_REQUEST`）、群成员加入/退出（`GROUP_MEMBER_ADD/QUIT`，新 intents 位 `1<<24`）
  - 事件体新增字段：`message_type`、`message_scene`（含 `msg_idx` 引用索引）、语音转写（`voice_wav_url`/`asr_refer_text`）、`msg_elements` 引用消息等
- ✅ **新增 Webhook 接入模式**：HTTP 回调 + Ed25519 签名校验，适用于 Serverless 等无法维持长连接的场景
- ✅ WebSocket 心跳间隔按平台 Hello 下发的 `heartbeat_interval` 动态设置；兼容 Python 3.8 ~ 3.14

## 安装

```bash
# 从 PyPI 安装（发布后可用）
pip install qq-botpy-v2

# 或从源码安装
pip install .

# 如需 Webhook 模式（Ed25519 签名校验）
pip install "qq-botpy-v2[webhook]"
```

依赖：`aiohttp`、`PyYAML`、`APScheduler`；Webhook 模式额外需要 `PyNaCl`。

## 快速开始

### 频道机器人（与原版 botpy 写法一致）

```python
import botpy
from botpy.message import Message

class MyClient(botpy.Client):
    async def on_at_message_create(self, message: Message):
        await message.reply(content="hello")

intents = botpy.Intents(public_guild_messages=True)
client = MyClient(intents=intents)
client.run(appid="你的appid", secret="你的AppSecret")
```

### 群聊 / 单聊机器人

```python
import botpy
from botpy.message import GroupMessage, C2CMessage

class MyClient(botpy.Client):
    async def on_group_at_message_create(self, message: GroupMessage):
        await message.reply(content="群聊收到！")

    async def on_c2c_message_create(self, message: C2CMessage):
        await message.reply(content="单聊收到！")

intents = botpy.Intents(public_messages=True)  # 群聊/单聊事件
client = MyClient(intents=intents)
client.run(appid="你的appid", secret="你的AppSecret")
```

### Webhook 模式（新增）

```python
client = MyClient(intents=botpy.Intents(public_messages=True))
client.webhook_run(appid="你的appid", secret="你的AppSecret", port=8080)
```

## 从原版 botpy 迁移

无需修改任何调用代码，直接替换安装源即可。原版 64 个 `BotAPI` 方法、全部事件回调、`types` 类型定义均保持兼容。详见使用文档中的 [从 botpy 迁移](docs/usage.md#十一从原版-botpy-迁移) 一节。

## 目录结构

```
qqbotpy/
├── botpy/            # SDK 源码（包名与原版一致，import botpy 即可）
│   ├── client.py     # Client（WebSocket / Webhook 模式）
│   ├── api.py        # BotAPI（64 个兼容接口 + 27 个新增接口）
│   ├── webhook.py    # Webhook HTTP 回调服务（新增）
│   ├── gateway.py    # WebSocket 网关
│   ├── flags.py      # Intents / Permission
│   ├── message.py    # 事件消息模型
│   ├── manage.py     # 群/C2C 管理事件模型（含入群申请）
│   ├── types/        # TypedDict 类型定义
│   └── ext/          # 扩展工具（指令装饰器等）
├── examples/         # 使用示例
├── tests/            # 单元测试（pytest，62 个用例，含伪造网关的集成测试）
└── docs/usage.md     # 使用文档
```

## 运行测试

```bash
pip install -e ".[test]"
python -m pytest tests/ -v
```

## 发布到 PyPI

推送 `v*` tag 即自动构建并发布（GitHub Actions + Trusted Publishing，无需 token），详见 [docs/publish.md](docs/publish.md)：

```bash
git tag v1.0.0 && git push origin v1.0.0
```

## 相关链接

- QQ 机器人官方文档：https://bot.q.qq.com/wiki/develop/api-v2/
- 原版 botpy：https://github.com/tencent-connect/botpy
