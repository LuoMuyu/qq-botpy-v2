# -*- coding: utf-8 -*-
"""botpy 异常类型定义

与原版 botpy 保持兼容，并补充了带平台错误码的 :class:`ApiError`。
"""


class AuthenticationFailedError(RuntimeError):
    """401 鉴权失败（access_token 无效或过期）"""

    def __init__(self, msg):
        self.msgs = msg

    def __str__(self):
        return self.msgs


class NotFoundError(RuntimeError):
    """404 资源不存在"""

    def __init__(self, msg):
        self.msgs = msg

    def __str__(self):
        return self.msgs


class MethodNotAllowedError(RuntimeError):
    """405 请求方法不允许"""

    def __init__(self, msg):
        self.msgs = msg

    def __str__(self):
        return self.msgs


class SequenceNumberError(RuntimeError):
    """429 频率限制"""

    def __init__(self, msg):
        self.msgs = msg

    def __str__(self):
        return self.msgs


class ServerError(RuntimeError):
    """500/504 服务端错误"""

    def __init__(self, msg):
        self.msgs = msg

    def __str__(self):
        return self.msgs


class ForbiddenError(RuntimeError):
    """403 无权限"""

    def __init__(self, msg):
        self.msgs = msg

    def __str__(self):
        return self.msgs


class ApiError(RuntimeError):
    """携带平台业务错误码的接口异常。

    QQ 机器人平台在 HTTP 层之外还会返回业务错误码（如 40034005 消息ID过期、
    40054005 消息去重等），业务错误码存放在 :attr:`code` 中，
    便于开发者针对具体错误做处理。

    Attributes:
      code (int): 平台业务错误码，无法解析时为 0。
      msgs (str): 错误描述。
    """

    def __init__(self, msg, code: int = 0):
        self.msgs = msg
        self.code = code

    def __str__(self):
        return f"[{self.code}] {self.msgs}" if self.code else self.msgs


HttpErrorDict = {
    401: AuthenticationFailedError,
    404: NotFoundError,
    405: MethodNotAllowedError,
    403: ForbiddenError,
    429: SequenceNumberError,
    500: ServerError,
    504: ServerError,
}
