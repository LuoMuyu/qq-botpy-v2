# -*- coding: utf-8 -*-
"""机器人身份凭证（Token）与机器人账号信息（Robot）。

按照最新官方文档：
  - access_token 获取接口为 ``https://api.bot.qq.com/app/getAppAccessToken``
  - 默认有效期 7200 秒，且重复获取不会自动续期，需自行刷新
  - 调用 OpenAPI 时请求头使用 ``Authorization: QQBot {access_token}``
"""

import asyncio
import time
from typing import Optional

import aiohttp

from . import logging
from .types import robot

_log = logging.get_logger()

# token 过期前提前刷新的秒数（官方说明在过期前 60 秒内获取的新 token 存在重叠期）
_TOKEN_REFRESH_BUFFER = 60


class Robot:
    """机器人账号信息，从 ``/users/@me`` 接口获取。"""

    def __init__(self, data: robot.Robot):
        self._update(data)

    def _update(self, data: robot.Robot) -> None:
        self.name = data.get("username")
        self.id = int(data["id"])
        self.avatar = data.get("avatar")

    def __repr__(self):
        return f"<Robot id={self.id} name={self.name}>"


class Token:
    TYPE_BOT = "QQBot"
    TYPE_NORMAL = "Bearer"

    def __init__(self, app_id: str, secret: str):
        """
        Args:
          app_id (str): 机器人 appid
          secret (str): 机器人密钥 AppSecret
        """
        self.app_id = app_id
        self.secret = secret
        self.access_token: Optional[str] = None
        self.expires_in: int = 0
        self.Type = self.TYPE_BOT

    async def check_token(self):
        """检查 token 是否有效，无效或即将过期（60 秒内）时自动刷新。"""
        if self.access_token is None or int(time.time()) >= self.expires_in - _TOKEN_REFRESH_BUFFER:
            await self.update_access_token()

    async def update_access_token(self):
        """调用平台接口获取新的 access_token。

        获取接口：``POST https://api.bot.qq.com/app/getAppAccessToken``
        """
        session = aiohttp.ClientSession()
        data = None
        try:
            async with session.post(
                url="https://api.bot.qq.com/app/getAppAccessToken",
                timeout=(aiohttp.ClientTimeout(total=20)),
                json={
                    "appId": self.app_id,
                    "clientSecret": self.secret,
                },
            ) as response:
                data = await response.json()
        except asyncio.TimeoutError as e:
            _log.info("[botpy] access_token TimeoutError:" + str(e))
            raise
        finally:
            await session.close()
        if not data or "access_token" not in data or "expires_in" not in data:
            _log.error("[botpy] 获取token失败，请检查appid和secret填写是否正确！")
            raise RuntimeError(str(data))
        _log.info("[botpy] access_token expires_in " + str(data["expires_in"]))
        self.access_token = data["access_token"]
        self.expires_in = int(data["expires_in"]) + int(time.time())

    # BotToken 机器人身份的 token
    def bot_token(self) -> "Token":
        return self

    # GetString 获取授权头字符串
    def get_string(self) -> str:
        if self.Type == self.TYPE_NORMAL:
            return self.access_token
        return "{} {}".format(self.Type, self.access_token)

    def get_type(self):
        return self.Type
