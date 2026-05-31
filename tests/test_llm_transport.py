import asyncio
import json
import urllib.request
from types import TracebackType
from typing import cast

import pytest

from outreach_agent.integrations.llm.transport import (
    UrllibChatTransport,
    extract_chat_completion_content,
)


class _FakeHTTPResponse:
    def __init__(self, body: str) -> None:
        self._body = body

    def read(self) -> bytes:
        return self._body.encode("utf-8")

    def __enter__(self) -> _FakeHTTPResponse:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        return None


def test_urllib_chat_transport_posts_expected_request_and_returns_content(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def fake_urlopen(
        request: urllib.request.Request,
        timeout: float,
    ) -> _FakeHTTPResponse:
        captured["request"] = request
        captured["timeout"] = timeout
        payload = json.dumps(
            {
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "score": 92,
                                },
                                sort_keys=True,
                            ),
                        },
                    },
                ],
            },
        )
        return _FakeHTTPResponse(payload)

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)

    transport = UrllibChatTransport()
    result = asyncio.run(
        transport.create_chat_completion(
            endpoint_url="https://api.example.com/v1/chat/completions",
            api_key="example-key",
            model="gpt-4.1-mini",
            messages=[{"role": "system", "content": "hello"}],
        )
    )

    assert result == '{"score": 92}'

    request = captured.get("request")
    assert isinstance(request, urllib.request.Request)
    assert request.full_url == "https://api.example.com/v1/chat/completions"
    assert request.get_method() == "POST"
    assert request.get_header("Authorization") == "Bearer example-key"
    assert request.headers["Content-type"] == "application/json"
    assert captured["timeout"] == 60

    request_body = json.loads(cast(bytes, request.data).decode("utf-8"))
    assert request_body == {
        "model": "gpt-4.1-mini",
        "messages": [{"role": "system", "content": "hello"}],
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
    }


def test_extract_chat_completion_content_rejects_invalid_payload() -> None:
    with pytest.raises(
        RuntimeError,
        match="LLM provider response did not match chat completion response shape",
    ):
        extract_chat_completion_content({"unexpected": "payload"})
