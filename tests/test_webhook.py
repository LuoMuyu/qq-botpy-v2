# -*- coding: utf-8 -*-
"""Webhook 签名与 HTTP 回调服务测试。"""

import json

import pytest
from aiohttp.test_utils import TestClient, TestServer

from botpy import webhook
from botpy.webhook import (
    WEBHOOK_OP_HTTP_CALLBACK_ACK,
    WebhookServer,
    check_signature,
    generate_signature,
)

SECRET = "my-test-secret"


def _sign(secret: str, msg: str) -> str:
    """用与库相同的 seed 算法构造签名（模拟平台侧）。"""
    key = webhook.SigningKey(webhook._generate_seed(secret))
    return key.sign(msg.encode("utf-8")).signature.hex()


# ============== 签名工具 ==============
def test_generate_signature_is_hex_and_verifiable():
    sig = generate_signature("1725442341", "Arq0D5A61EgUu4OxUvOp", SECRET)
    assert isinstance(sig, str)
    bytes.fromhex(sig)  # 应为合法 hex
    assert len(sig) == 128  # ed25519 签名 64 字节


def test_check_signature_roundtrip():
    body = json.dumps({"op": 0, "id": "x", "d": {}, "s": 1, "t": "C2C_MESSAGE_CREATE"})
    ts = "1725442341"
    sig = _sign(SECRET, ts + body)
    assert check_signature(ts, sig, body, SECRET) is True


def test_check_signature_wrong_secret():
    body = "{}"
    ts = "1725442341"
    sig = _sign("other-secret", ts + body)
    assert check_signature(ts, sig, body, SECRET) is False


def test_check_signature_tampered_body():
    ts = "1725442341"
    sig = _sign(SECRET, ts + '{"a":1}')
    assert check_signature(ts, sig, '{"a":2}', SECRET) is False


def test_check_signature_missing_fields():
    assert check_signature("", "ff", "{}", SECRET) is False
    assert check_signature("123", "", "{}", SECRET) is False


def test_empty_secret_rejected():
    with pytest.raises(ValueError):
        generate_signature("1", "p", "")


# ============== WebhookServer HTTP 行为 ==============
@pytest.fixture
def dispatch_log():
    return []


@pytest.fixture
def client_cls():
    class FakeClient:
        def __init__(self, log):
            self.log = log

        def dispatch_event_payload(self, payload):
            self.log.append(payload)
            return True

    return FakeClient


@pytest.mark.asyncio
async def test_webhook_validate_request(dispatch_log, client_cls):
    app = WebhookServer(client_cls(dispatch_log), secret=SECRET).make_app()
    client = TestClient(TestServer(app))
    await client.start_server()
    resp = await client.post("/bot/webhook", json={
        "d": {"plain_token": "Arq0D5A61EgUu4OxUvOp", "event_ts": "1725442341"},
        "op": 13,
    })
    assert resp.status == 200
    data = await resp.json()
    assert data["plain_token"] == "Arq0D5A61EgUu4OxUvOp"
    # 签名可以用相同算法验证
    expected = generate_signature("1725442341", "Arq0D5A61EgUu4OxUvOp", SECRET)
    assert data["signature"] == expected
    assert dispatch_log == []
    await client.close()


@pytest.mark.asyncio
async def test_webhook_push_valid_signature(dispatch_log, client_cls):
    app = WebhookServer(client_cls(dispatch_log), secret=SECRET).make_app()
    client = TestClient(TestServer(app))
    await client.start_server()
    body = json.dumps({
        "op": 0, "id": "BTC1", "s": 9,
        "t": "GROUP_AT_MESSAGE_CREATE",
        "d": {"id": "M1", "group_openid": "G1", "content": "hello"},
    })
    ts = "1725442341"
    resp = await client.post(
        "/bot/webhook",
        data=body,
        headers={
            "X-Signature-Ed25519": _sign(SECRET, ts + body),
            "X-Signature-Timestamp": ts,
            "Content-Type": "application/json",
        },
    )
    assert resp.status == 200
    data = await resp.json()
    assert data == {"op": WEBHOOK_OP_HTTP_CALLBACK_ACK}
    assert len(dispatch_log) == 1
    assert dispatch_log[0]["t"] == "GROUP_AT_MESSAGE_CREATE"
    await client.close()


@pytest.mark.asyncio
async def test_webhook_push_invalid_signature(dispatch_log, client_cls):
    app = WebhookServer(client_cls(dispatch_log), secret=SECRET).make_app()
    client = TestClient(TestServer(app))
    await client.start_server()
    body = json.dumps({"op": 0, "id": "x", "d": {}, "s": 1, "t": "C2C_MESSAGE_CREATE"})
    resp = await client.post(
        "/bot/webhook",
        data=body,
        headers={
            "X-Signature-Ed25519": _sign("wrong", "1725442341" + body),
            "X-Signature-Timestamp": "1725442341",
            "Content-Type": "application/json",
        },
    )
    assert resp.status == 403
    assert dispatch_log == []
    await client.close()


@pytest.mark.asyncio
async def test_webhook_bad_json(dispatch_log, client_cls):
    app = WebhookServer(client_cls(dispatch_log), secret=SECRET).make_app()
    client = TestClient(TestServer(app))
    await client.start_server()
    resp = await client.post("/bot/webhook", data="not-json", headers={"Content-Type": "application/json"})
    assert resp.status == 400
    await client.close()
