# -*- coding: utf-8 -*-
"""Bot 的 WebSocket 实现。

按照最新官方文档：
  - 连接建立后收到的 Hello（op=10）携带 ``heartbeat_interval``（毫秒），
    心跳按该间隔发送，而非固定 30 秒
  - 心跳（op=1）的 d 字段为最新收到的消息序号 s，首次为 null
  - Identify（op=2）时 token 格式为 "QQBot {AccessToken}"
"""

import asyncio
import json
import ssl
import traceback
from typing import Optional

from aiohttp import WSMessage, ClientWebSocketResponse, TCPConnector, ClientSession, WSMsgType

from . import logging
from .connection import ConnectionSession
from .types import gateway
from .types.session import Session

_log = logging.get_logger()


class BotWebSocket:
    """Bot的Websocket实现

    CODE	名称	客户端操作	描述
    0	Dispatch	Receive	服务端进行消息推送
    1	Heartbeat	Send/Receive	客户端或服务端发送心跳
    2	Identify	Send	客户端发送鉴权
    6	Resume	Send	客户端恢复连接
    7	Reconnect	Receive	服务端通知客户端重新连接
    9	Invalid Session	Receive	当identify或resume的时候，如果参数有错，服务端会返回该消息
    10	Hello	Receive	当客户端与网关建立ws连接之后，网关下发的第一条消息
    11	Heartbeat ACK	Receive	当发送心跳成功之后，就会收到该消息
    """

    WS_DISPATCH_EVENT = 0
    WS_HEARTBEAT = 1
    WS_IDENTITY = 2
    WS_RESUME = 6
    WS_RECONNECT = 7
    WS_INVALID_SESSION = 9
    WS_HELLO = 10
    WS_HEARTBEAT_ACK = 11

    # 心跳间隔兜底值（秒），正常情况下以 Hello 下发的 heartbeat_interval 为准
    DEFAULT_HEARTBEAT_INTERVAL = 30

    def __init__(self, session: Session, _connection: ConnectionSession):
        self._conn: Optional[ClientWebSocketResponse] = None
        self._session = session
        self._connection = _connection
        self._parser = _connection.parser
        self._can_reconnect = True
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._INVALID_RECONNECT_CODE = [9001, 9005]
        self._AUTH_FAIL_CODE = [4004]

    async def on_error(self, exception: BaseException):
        _log.error("[botpy] websocket连接: %s, 异常信息 : %s" % (self._conn, exception))
        traceback.print_exc()
        self._connection.add(self._session)

    async def on_closed(self, close_status_code, close_msg):
        _log.info("[botpy] 关闭, 返回码: %s" % close_status_code + ", 返回信息: %s" % close_msg)
        self._stop_heartbeat()
        if close_status_code in self._AUTH_FAIL_CODE:
            _log.info("[botpy] 鉴权失败，重置token...")
            self._session["token"].access_token = None
        # 这种不能重新链接
        if close_status_code in self._INVALID_RECONNECT_CODE or not self._can_reconnect:
            _log.info("[botpy] 无法重连，创建新连接!")
            self._session["session_id"] = ""
            self._session["last_seq"] = 0
        # 断连后启动一个新的链接并透传当前的session，不使用内部重连的方式，避免死循环
        self._connection.add(self._session)

    def _stop_heartbeat(self):
        if self._heartbeat_task and not self._heartbeat_task.done():
            self._heartbeat_task.cancel()
        self._heartbeat_task = None

    async def on_message(self, ws, message):
        _log.debug("[botpy] 接收消息: %s" % message)
        msg = json.loads(message)

        if await self._is_system_event(msg, ws):
            return

        event = msg.get("t")
        opcode = msg.get("op")
        event_seq = msg.get("s", 0)
        if event_seq and event_seq > 0:
            self._session["last_seq"] = event_seq

        if event == "READY":
            # 心跳检查
            self._stop_heartbeat()
            self._heartbeat_task = self._connection.loop.create_task(self._send_heart(self._heartbeat_interval))
            ready = await self._ready_handler(msg)
            _log.info(f"[botpy] 机器人「{ready['user']['username']}」启动成功！")

        if event == "RESUMED":
            # 心跳检查
            self._stop_heartbeat()
            self._heartbeat_task = self._connection.loop.create_task(self._send_heart(self._heartbeat_interval))
            _log.info("[botpy] 机器人重连成功! ")

        if event and opcode == self.WS_DISPATCH_EVENT:
            event = msg["t"].lower()
            try:
                func = self._parser[event]
            except KeyError:
                _log.error("_parser unknown event %s.", event)
            else:
                func(msg)

    async def on_connected(self, ws: ClientWebSocketResponse):
        self._conn = ws
        if self._conn is None:
            raise Exception("[botpy] websocket连接失败")
        if self._session["session_id"]:
            await self.ws_resume()
        else:
            await self.ws_identify()

    async def ws_connect(self):
        """
        websocket向服务器端发起链接，并定时发送心跳
        """

        _log.info("[botpy] 启动中...")
        ws_url = self._session["url"]
        if not ws_url:
            raise Exception("[botpy] 会话url为空")

        self._heartbeat_interval = self.DEFAULT_HEARTBEAT_INTERVAL

        # using a default SSL context in the connector to prevent SSL certificate verify failed error
        async with ClientSession(connector=TCPConnector(limit=10, ssl=ssl.create_default_context())) as session:
            async with session.ws_connect(self._session["url"]) as ws_conn:
                while True:
                    msg: WSMessage
                    msg = await ws_conn.receive()
                    if msg.type == WSMsgType.TEXT:
                        await self.on_message(ws_conn, msg.data)
                    elif msg.type == WSMsgType.ERROR:
                        await self.on_error(ws_conn.exception())
                        await ws_conn.close()
                    elif msg.type == WSMsgType.CLOSED or msg.type == WSMsgType.CLOSE:
                        await self.on_closed(ws_conn.close_code, msg.extra)
                    if ws_conn.closed:
                        _log.info("[botpy] ws关闭, 停止接收消息!")
                        break

    async def ws_identify(self):
        """websocket鉴权"""
        if not self._session["intent"]:
            self._session["intent"] = 1

        _log.info("[botpy] 鉴权中...")
        await self._session["token"].check_token()
        payload = {
            "op": self.WS_IDENTITY,
            "d": {
                "shard": [
                    self._session["shards"]["shard_id"],
                    self._session["shards"]["shard_count"],
                ],
                "token": self._session["token"].get_string(),
                "intents": self._session["intent"],
                "properties": {},
            },
        }

        await self.send_msg(json.dumps(payload))

    async def send_msg(self, event_json):
        """
        websocket发送消息
        :param event_json:
        """
        send_msg = event_json
        _log.debug("[botpy] 发送消息: %s" % send_msg)
        if isinstance(self._conn, ClientWebSocketResponse):
            if self._conn.closed:
                _log.debug("[botpy] ws连接已关闭! ws对象: %s" % self._conn)
            else:
                await self._conn.send_str(data=send_msg)

    async def ws_resume(self):
        """
        websocket重连
        """
        _log.info("[botpy] 重连启动...")
        await self._session["token"].check_token()
        payload = {
            "op": self.WS_RESUME,
            "d": {
                "token": self._session["token"].get_string(),
                "session_id": self._session["session_id"],
                "seq": self._session["last_seq"],
            },
        }

        await self.send_msg(json.dumps(payload))

    async def _ready_handler(self, message_event) -> gateway.ReadyEvent:
        data = message_event["d"]
        self.version = data["version"]
        self._session["session_id"] = data["session_id"]
        self._session["shards"]["shard_id"] = data["shard"][0]
        self._session["shards"]["shard_count"] = data["shard"][1]
        self.user = data["user"]
        return data

    async def _is_system_event(self, message_event, ws):
        """
        系统事件
        :param message_event:消息
        :param ws:websocket
        :return:
        """
        event_op = message_event["op"]
        if event_op == self.WS_HELLO:
            # Hello 消息携带心跳周期（毫秒），按其设置心跳间隔
            interval_ms = (message_event.get("d") or {}).get("heartbeat_interval", None)
            if interval_ms:
                self._heartbeat_interval = max(1, int(interval_ms) / 1000)
                _log.debug("[botpy] 心跳间隔: %ss" % self._heartbeat_interval)
            await self.on_connected(ws)
            return True
        if event_op == self.WS_HEARTBEAT_ACK:
            return True
        if event_op == self.WS_RECONNECT:
            self._can_reconnect = True
            # 服务端要求重连，主动断开当前连接并重连
            if self._conn and not self._conn.closed:
                await self._conn.close(code=4000)
            return True
        if event_op == self.WS_INVALID_SESSION:
            self._can_reconnect = False
            return True
        return False

    async def _send_heart(self, interval):
        """
        心跳包
        :param interval: 间隔时间（秒）
        """
        _log.info("[botpy] 心跳维持启动...")
        while True:
            payload = {
                "op": self.WS_HEARTBEAT,
                "d": self._session["last_seq"] or None,
            }

            if self._conn is None:
                _log.debug("[botpy] 连接已关闭!")
                return
            if self._conn.closed:
                _log.debug("[botpy] ws连接已关闭, 心跳检测停止，ws对象: %s" % self._conn)
                return

            await self.send_msg(json.dumps(payload))
            await asyncio.sleep(interval)
