# -*- coding: utf-8 -*-
import os

from setuptools import setup, find_packages

setup(
    name="qq-botpy",
    version=os.getenv("VERSION_NAME", "1.0.0"),
    author="qqbotpy contributors",
    description="QQ 机器人 Python SDK，基于官方 API v2 最新文档适配，接口兼容原版 botpy",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/tencent-connect/botpy",
    packages=find_packages(exclude=["*.tests", "*.tests.*", "tests.*", "tests", "examples", "reference"]),
    python_requires=">=3.8",
    license="MIT",
    install_requires=["aiohttp>=3.7.4,<4", "PyYAML", "APScheduler"],
    extras_require={
        # Webhook（HTTP 回调）接入模式需要 Ed25519 签名支持
        "webhook": ["PyNaCl>=1.4.0"],
        "test": ["pytest", "pytest-asyncio", "PyNaCl>=1.4.0"],
    },
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
    ],
)
