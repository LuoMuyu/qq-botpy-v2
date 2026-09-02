# -*- coding: utf-8 -*-
"""扩展模块测试。"""

import asyncio

import pytest

from botpy.ext.cog_apscheduler import LazyAsyncIOScheduler


def _simulate_import() -> LazyAsyncIOScheduler:
    """在同步上下文中创建并 start，模拟模块导入阶段（无运行中的事件循环）。"""
    s = LazyAsyncIOScheduler()
    s.configure({"apscheduler.timezone": "Asia/Shanghai"})
    s.start()

    @s.scheduled_job("interval", seconds=60)
    async def tick():
        pass

    return s


def test_scheduler_import_without_loop():
    """导入阶段（无运行中的事件循环）不能报错，且任务可注册。"""
    s = _simulate_import()
    assert not s.running


@pytest.mark.asyncio
async def test_scheduler_start_in_running_loop():
    """事件循环运行后 ensure_started 应完成启动。"""
    # 注意：async 测试中循环已在运行，此处 start 会立即生效；
    # "导入期延迟启动"的行为由 test_scheduler_import_without_loop 覆盖
    s = LazyAsyncIOScheduler()
    s.configure({"apscheduler.timezone": "Asia/Shanghai"})
    s.start()

    async def scenario():
        s.ensure_started()
        assert s.running

    try:
        await scenario()
    finally:
        if s.running:
            s.shutdown(wait=False)
