# -*- coding: utf-8 -*-
"""HTTP 请求封装。

按照最新官方文档：
  - 所有 OpenAPI 接口统一使用域名 ``api.bot.qq.com``
  - 沙箱环境为 ``sandbox.api.bot.qq.com``
  - 鉴权头 ``Authorization: QQBot {access_token}``，同时携带 ``X-Union-Appid``
"""

import asyncio
from json.decoder import JSONDecodeError
import ssl
from typing import Any, Optional, ClassVar, Union, Dict

import aiohttp
from aiohttp import ClientResponse, FormData, TCPConnector, multipart, hdrs, payload

from . import logging
from .errors import ApiError, HttpErrorDict, ServerError
from .robot import Token
from .types import robot

X_TPS_TRACE_ID = "X-Tps-trace-Id"

_log = logging.get_logger()

# 请求成功的返回码
HTTP_OK_STATUS = [200, 202, 204]


class _FormData(FormData):
    def _gen_form_data(self) -> multipart.MultipartWriter:
        """Encode a list of fields using the multipart/form-data MIME format"""
        if self._is_processed:
            return self._writer  # rewrite this part of FormData object to enable retry of request
        for dispparams, headers, value in self._fields:
            try:
                if hdrs.CONTENT_TYPE in headers:
                    part = payload.get_payload(
                        value,
                        content_type=headers[hdrs.CONTENT_TYPE],
                        headers=headers,
                        encoding=self._charset,
                    )
                else:
                    part = payload.get_payload(
                        value,
                        headers=headers,
                        encoding=self._charset,
                    )
            except Exception as exc:
                print(value)
                raise TypeError(
                    "Can not serialize value type: %r\n " "headers: %r\n value: %r" % (type(value), headers, value)
                ) from exc

            if dispparams:
                part.set_content_disposition(
                    "form-data",
                    quote_fields=self._quote_fields,
                    **dispparams,
                )
                assert part.headers is not None
                part.headers.popall(hdrs.CONTENT_LENGTH, None)

            self._writer.append_payload(part)

        self._is_processed = True
        return self._writer


def _clean_payload(payload_dict: dict) -> dict:
    """去除值为 None 的字段，避免与平台"字段必须为空"的校验规则冲突。"""
    return {k: v for k, v in payload_dict.items() if v is not None}


async def _handle_response(response: ClientResponse) -> Union[Dict[str, Any], str]:
    url = response.request_info.url
    try:
        condition = response.headers["content-type"] == "application/json"
        # note that when content-type is application/json, aiohttp will directly auto-sub encoding to be utf-8
        data = await response.json() if condition else await response.text()
    except (KeyError, JSONDecodeError):
        data = None
    if response.status in HTTP_OK_STATUS:
        _log.debug(f"[botpy] 请求成功, 请求连接: {url}, 返回内容: {data}, trace_id:{response.headers.get(X_TPS_TRACE_ID)}")
        return data
    else:
        _log.error(
            f"[botpy] 接口请求异常，请求连接: {url}, "
            f"错误代码: {response.status}, 返回内容: {data}, trace_id:{response.headers.get(X_TPS_TRACE_ID)}"
            # trace_id 用于定位接口问题
        )
        error_dict_get = HttpErrorDict.get(response.status)
        # type of data should be dict or str or None, so there should be a condition to check and prevent bug
        message = data["message"] if isinstance(data, dict) else str(data)
        code = data.get("code", 0) if isinstance(data, dict) else 0
        if not error_dict_get:
            # 携带平台业务错误码（如 40034005 消息ID过期、40054005 消息去重等），便于业务层判断
            raise ApiError(message, code) from None
        err = error_dict_get(msg=message)
        if isinstance(err, Exception) and code:
            err.code = code
        raise err from None


class Route:
    """API 请求路由。

    按照最新文档，接口统一域名：``api.bot.qq.com``；
    沙箱环境：``sandbox.api.bot.qq.com``。
    """

    DOMAIN: ClassVar[str] = "api.bot.qq.com"
    SANDBOX_DOMAIN: ClassVar[str] = "sandbox.api.bot.qq.com"
    SCHEME: ClassVar[str] = "https"

    def __init__(self, method: str, path: str, is_sandbox: str = False, **parameters: Any) -> None:
        self.method: str = method
        self.path: str = path
        self.is_sandbox = is_sandbox
        self.parameters = parameters

    @property
    def url(self):
        if self.is_sandbox:
            d = self.SANDBOX_DOMAIN
        else:
            d = self.DOMAIN
        _url = "{}://{}{}".format(self.SCHEME, d, self.path)

        # path的参数:
        if self.parameters:
            _url = _url.format_map(self.parameters)
        return _url


class BotHttp:
    """异步 HTTP 客户端，负责 OpenAPI 请求与 access_token 的自动附加。"""

    def __init__(
        self,
        timeout: int,
        is_sandbox: bool = False,
        app_id: str = None,
        secret: str = None,
    ):
        self.timeout = timeout
        self.is_sandbox = is_sandbox

        self._token: Optional[Token] = None if not app_id else Token(app_id=app_id, secret=secret)
        self._session: Optional[aiohttp.ClientSession] = None
        self._global_over: Optional[asyncio.Event] = None
        self._headers: Optional[dict] = None

    def __del__(self):
        if self._session and not self._session.closed:
            try:
                _loop = asyncio.get_event_loop()
                _loop.create_task(self._session.close())
            except RuntimeError:
                pass

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()

    async def check_session(self):
        await self._token.check_token()
        self._headers = {
            "Authorization": self._token.get_string(),
            "X-Union-Appid": self._token.app_id,
        }

        if not self._session or self._session.closed:
            self._session = aiohttp.ClientSession(
                connector=TCPConnector(limit=500, ssl=ssl.create_default_context(), force_close=True),
            )

    async def request(self, route: Route, retry_time: int = 0, **kwargs: Any):
        if retry_time > 2:
            return
        # some checking if it's a JSON request
        if "json" in kwargs:
            json_ = kwargs["json"]
            if isinstance(json_, dict):
                if "file_image" in json_ and isinstance(json_["file_image"], bytes):
                    # 携带本地图片时，改用 multipart/form-data 提交
                    kwargs["data"] = _FormData()
                    for k, v in kwargs.pop("json").items():
                        if v is not None:
                            if isinstance(v, dict):
                                if k == "message_reference":
                                    _log.error(
                                        f"[botpy] 接口参数传入异常, 请求连接: {route.url}, "
                                        f"错误原因: file_image与message_reference不能同时传入，"
                                        f"备注: sdk已按照优先级，去除message_reference参数"
                                    )
                            else:
                                kwargs["data"].add_field(k, v)
                else:
                    kwargs["json"] = _clean_payload(json_)

        await self.check_session()
        route.is_sandbox = self.is_sandbox
        _log.debug(f"[botpy] 请求头部: {self._headers}, 请求方式: {route.method}, 请求url: {route.url}")
        _log.debug(self._session)
        try:
            async with self._session.request(
                method=route.method,
                url=route.url,
                headers=self._headers,
                timeout=(aiohttp.ClientTimeout(total=self.timeout)),
                **kwargs,
            ) as response:
                _log.debug(response)
                return await _handle_response(response)
        except asyncio.TimeoutError:
            _log.warning(f"请求超时，请求连接: {route.url}")
        except ConnectionResetError:
            _log.debug("session connection broken retry")
            await self.request(route, retry_time + 1, **kwargs)

    async def login(self, token: Token) -> robot.Robot:
        """login后保存token和session"""

        self._token = token
        await self.check_session()
        self._global_over = asyncio.Event()
        self._global_over.set()

        data = await self.request(Route("GET", "/users/@me"))
        return data
