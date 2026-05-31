import asyncio
import json
import urllib.error
import urllib.request

from pydantic import BaseModel, Field, ValidationError

from outreach_agent.protocols.llm import ChatTransportProtocol


class ChatCompletionMessage(BaseModel):
    content: str = Field(min_length=1)


class ChatCompletionChoice(BaseModel):
    message: ChatCompletionMessage


class ChatCompletionResponse(BaseModel):
    choices: list[ChatCompletionChoice] = Field(min_length=1)


class UrllibChatTransport(ChatTransportProtocol):
    async def create_chat_completion(
        self,
        *,
        endpoint_url: str,
        api_key: str,
        model: str,
        messages: list[dict[str, str]],
    ) -> str:
        return await asyncio.to_thread(
            self._create_chat_completion,
            endpoint_url=endpoint_url,
            api_key=api_key,
            model=model,
            messages=messages,
        )

    def _create_chat_completion(
        self,
        *,
        endpoint_url: str,
        api_key: str,
        model: str,
        messages: list[dict[str, str]],
    ) -> str:
        request_body = json.dumps(
            {
                "model": model,
                "messages": messages,
                "temperature": 0.2,
                "response_format": {"type": "json_object"},
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            endpoint_url,
            data=request_body,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                response_body = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                f"LLM provider request failed with HTTP {exc.code}: {detail}"
            ) from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"LLM provider request failed: {exc.reason}") from exc

        return extract_chat_completion_content(json.loads(response_body))


def extract_chat_completion_content(response_payload: object) -> str:
    try:
        response = ChatCompletionResponse.model_validate(response_payload)
    except ValidationError as exc:
        raise RuntimeError(
            "LLM provider response did not match chat completion response shape"
        ) from exc
    return response.choices[0].message.content


__all__ = [
    "ChatCompletionMessage",
    "ChatCompletionChoice",
    "ChatCompletionResponse",
    "UrllibChatTransport",
    "extract_chat_completion_content",
]
