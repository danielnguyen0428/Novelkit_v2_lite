"""Unit tests for LLM endpoint resolution and response parsing."""

from __future__ import annotations

import json

import httpx

import pytest

from provider.llm_client import (
    LLMClient,
    LLMConfig,
    LLMError,
    LLMTruncated,
    _parse_completion_json,
    resolve_endpoint,
    validate_llm_base_url,
)


def _fake_client_returning(monkeypatch, *, status=200, headers=None, text=""):
    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def post(self, url, headers=None, json=None):
            return httpx.Response(
                status,
                headers=headers or {"content-type": "application/json"},
                text=text,
            )

    monkeypatch.setattr(httpx, "Client", FakeClient)
    return LLMClient(
        LLMConfig(api_key="sk-test-key", model="m", base_url="https://example.com/v1")
    )


def test_complete_raises_truncated_when_finish_reason_length(monkeypatch):
    # Non-empty content cut off at the token ceiling must raise LLMTruncated
    # (previously it was silently returned, losing the tail of the document).
    body = json.dumps(
        {
            "choices": [
                {
                    "message": {"content": "phần đầu tài liệu bị cắt"},
                    "finish_reason": "length",
                }
            ]
        }
    )
    client = _fake_client_returning(monkeypatch, text=body)
    with pytest.raises(LLMTruncated) as excinfo:
        client.complete(user="hi")
    assert excinfo.value.partial == "phần đầu tài liệu bị cắt"


def test_complete_returns_content_when_finish_reason_stop(monkeypatch):
    body = json.dumps(
        {
            "choices": [
                {"message": {"content": "hoàn chỉnh"}, "finish_reason": "stop"}
            ]
        }
    )
    client = _fake_client_returning(monkeypatch, text=body)
    assert client.complete(user="hi") == "hoàn chỉnh"


def test_complete_empty_content_length_raises_plain_error(monkeypatch):
    # Empty content + length still raises the "empty content" error, not
    # LLMTruncated (there is no partial to salvage).
    body = json.dumps(
        {"choices": [{"message": {"content": ""}, "finish_reason": "length"}]}
    )
    client = _fake_client_returning(monkeypatch, text=body)
    with pytest.raises(LLMError) as excinfo:
        client.complete(user="hi")
    assert not isinstance(excinfo.value, LLMTruncated)


def test_resolve_endpoint_appends_chat_completions_for_base_url():
    assert (
        resolve_endpoint("https://api.openai.com/v1")
        == "https://api.openai.com/v1/chat/completions"
    )
    assert (
        resolve_endpoint("https://api.xah.io/v1")
        == "https://api.xah.io/v1/chat/completions"
    )


def test_llm_transport_rejects_http_before_network(monkeypatch):
    called = False

    class FakeClient:
        def __init__(self, *args, **kwargs):
            nonlocal called
            called = True

    monkeypatch.setattr(httpx, "Client", FakeClient)
    client = LLMClient(
        LLMConfig(
            api_key="sk-test-key",
            model="m",
            base_url="http://api.example.com/v1",
        )
    )
    with pytest.raises(LLMError, match="must use HTTPS"):
        client.complete(user="hi")
    assert called is False


def test_loopback_http_transport_requires_explicit_flag(monkeypatch):
    monkeypatch.delenv("NOVELKIT_ALLOW_INSECURE_LLM_URLS", raising=False)
    with pytest.raises(ValueError, match="must use HTTPS"):
        validate_llm_base_url("http://localhost:11434/v1")

    monkeypatch.setenv("NOVELKIT_ALLOW_INSECURE_LLM_URLS", "1")
    assert (
        validate_llm_base_url("http://localhost:11434/v1")
        == "http://localhost:11434/v1"
    )
    with pytest.raises(ValueError, match="must use HTTPS"):
        validate_llm_base_url("http://api.example.com/v1")


def test_resolve_endpoint_uses_full_xah_urls_as_is():
    assert (
        resolve_endpoint("https://api.xah.io/v1/chat/completions")
        == "https://api.xah.io/v1/chat/completions"
    )
    assert (
        resolve_endpoint("https://api.xah.io/v1/messages")
        == "https://api.xah.io/v1/messages"
    )
    assert (
        resolve_endpoint("https://api.xah.io/v1/responses")
        == "https://api.xah.io/v1/responses"
    )
    assert (
        resolve_endpoint(
            "https://api.xah.io/v1beta/models/w3leee/claude-sonnet-4.6:generateContent"
        )
        == "https://api.xah.io/v1beta/models/w3leee/claude-sonnet-4.6:generateContent"
    )
    assert (
        resolve_endpoint("https://api.xah.io/api/chat")
        == "https://api.xah.io/api/chat"
    )


def test_resolve_endpoint_shopaikey():
    assert (
        resolve_endpoint("https://api.shopaikey.com/v1")
        == "https://api.shopaikey.com/v1/chat/completions"
    )
    assert (
        resolve_endpoint("https://api.shopaikey.com/v1/chat/completions")
        == "https://api.shopaikey.com/v1/chat/completions"
    )
    assert (
        resolve_endpoint("https://api.shopaikey.com/v1/messages")
        == "https://api.shopaikey.com/v1/messages"
    )
    assert (
        resolve_endpoint("https://api.shopaikey.com/v1/completions")
        == "https://api.shopaikey.com/v1/completions"
    )


def test_complete_requests_non_streaming(monkeypatch):
    captured: dict = {}

    class FakeClient:
        def __init__(self, *args, **kwargs):
            captured["client_kwargs"] = kwargs

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def post(self, url, headers=None, json=None):
            captured["url"] = url
            captured["json"] = json
            return httpx.Response(
                200,
                headers={"content-type": "application/json"},
                text='{"choices":[{"message":{"content":"OK"}}]}',
            )

    monkeypatch.setattr(httpx, "Client", FakeClient)
    client = LLMClient(
        LLMConfig(api_key="sk-test-key", model="m", base_url="https://example.com/v1")
    )
    assert client.complete(user="hi") == "OK"
    assert captured["json"]["stream"] is False
    assert captured["client_kwargs"]["trust_env"] is False


def test_parse_completion_json_reads_sse_event_stream():
    body = (
        'data: {"choices":[{"message":{"content":"OK"}}]}\n\n'
        "data: [DONE]\n\n"
    )
    resp = httpx.Response(
        200,
        headers={"content-type": "text/event-stream"},
        text=body,
    )
    data = _parse_completion_json(resp)
    assert data["choices"][0]["message"]["content"] == "OK"


def test_complete_parses_sse_when_gateway_streams_anyway(monkeypatch):
    body = (
        'data: {"choices":[{"message":{"content":"OK"}}]}\n\n'
        "data: [DONE]\n\n"
    )

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def post(self, url, headers=None, json=None):
            return httpx.Response(
                200,
                headers={"content-type": "text/event-stream"},
                text=body,
            )

    monkeypatch.setattr(httpx, "Client", FakeClient)
    client = LLMClient(
        LLMConfig(api_key="sk-test-key", model="m", base_url="https://example.com/v1")
    )
    assert client.complete(user="hi") == "OK"


def test_parse_completion_json_reads_plain_json():
    resp = httpx.Response(
        200,
        headers={"content-type": "application/json"},
        text=json.dumps({"choices": [{"message": {"content": "Hi"}}]}),
    )
    data = _parse_completion_json(resp)
    assert data["choices"][0]["message"]["content"] == "Hi"
