# -*- coding: utf-8 -*-
"""APScheduler 定时任务扩展。

与原版 botpy 用法一致::

    from botpy.ext.cog_apscheduler import scheduler

    @scheduler.scheduled_job("cron", hour=9, minute=0)
    async def daily_task():
        ...

注意: Python 3.10+ 中 AsyncIOScheduler.start() 必须在运行中的事件循环内调用，
而本模块通常在程序导入阶段被使用（此时循环未运行）。因此导入阶段的启动请求
会被延迟，botpy.Client 启动、事件循环就绪后会自动完成启动。
"""

import asyncio

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from botpy import logging

_log = logging.get_logger()


class LazyAsyncIOScheduler(AsyncIOScheduler):
    """延迟启动的 AsyncIOScheduler，兼容"导入即注册任务"的用法。"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._lazy_started = False

    def start(self):
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            # 无运行中的事件循环，延迟启动
            _log.debug("[botpy] 事件循环未就绪，scheduler 启动已延迟")
            return None
        if not self.running:
            super().start()
            self._lazy_started = True
            _log.debug("[加载插件] APScheduler 定时任务")
        return None

    def ensure_started(self):
        """在事件循环运行后调用；Client 启动时会自动调用。"""
        if not self._lazy_started and not self.running:
            self.start()


scheduler = LazyAsyncIOScheduler()
scheduler.configure({"apscheduler.timezone": "Asia/Shanghai"})
scheduler.start()
