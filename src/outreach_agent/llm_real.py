import asyncio
import json
import urllib.error
import urllib.request
from typing import Protocol

from pydantic import BaseModel, Field, ValidationError

from outreach_agent.models import (
    GeneratedEmail,
    IcpScore,
    LeadProfile,
    Route,
    SequencePlan,
)


class ChatCompletionMessage(BaseModel):
    content: str = Field(min_length=1)


class ChatCompletionChoice(BaseModel):
    message: ChatCompletionMessage


class ChatCompletionResponse(BaseModel):
    choices: list[ChatCompletionChoice] = Field(min_length=1)


class ChatTransport(Protocol):
    async def create_chat_completion(
        self,
        *,
        endpoint_url: str,
        api_key: str,
        model: str,
        messages: list[dict[str, str]],
    ) -> str: ...


OPENAI_CHAT_COMPLETIONS_URL = "https://api.openai.com/v1/chat/completions"
OPENROUTER_CHAT_COMPLETIONS_URL = "https://openrouter.ai/api/v1/chat/completions"
ICP_DEFINITION = (
    "B2B SaaS or AI/software companies with 50–500 employees, selling to "
    "mid-market or enterprise customers, operating in North America or Europe, "
    "and actively scaling outbound sales or go-to-market operations. Strong "
    "positive signals include SDR/AE/RevOps hiring, recent funding or launch "
    "activity, CRM/sales engagement tooling, manual lead qualification pain, "
    "personalization bottlenecks, or fragmented enrichment workflows. Strong "
    "negative signals include local/B2C businesses, very small companies without "
    "a sales motion, non-software businesses, unclear company identity, or no "
    "credible outbound/GTM need."
)


class UrllibChatTransport:
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


class ChatCompletionRawLLMProvider:
    endpoint_url: str

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        transport: ChatTransport | None = None,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.transport = transport or UrllibChatTransport()

    async def score_icp(self, profile: LeadProfile) -> object:
        return await self.complete(build_scoring_messages(profile))

    async def repair_score_icp(
        self,
        profile: LeadProfile,
        invalid_output: object,
        repair_prompt: str,
    ) -> object:
        return await self.complete(
            build_repair_messages(
                build_scoring_messages(profile),
                invalid_output,
                repair_prompt,
            )
        )

    async def generate_first_email(
        self,
        profile: LeadProfile,
        scoring_result: IcpScore,
        final_route: Route,
        sequence: SequencePlan,
    ) -> object:
        return await self.complete(
            build_email_messages(profile, scoring_result, final_route, sequence)
        )

    async def repair_first_email(
        self,
        profile: LeadProfile,
        scoring_result: IcpScore,
        final_route: Route,
        sequence: SequencePlan,
        invalid_output: object,
        repair_prompt: str,
    ) -> object:
        return await self.complete(
            build_repair_messages(
                build_email_messages(profile, scoring_result, final_route, sequence),
                invalid_output,
                repair_prompt,
            )
        )

    async def complete(self, messages: list[dict[str, str]]) -> str:
        return await self.transport.create_chat_completion(
            endpoint_url=self.endpoint_url,
            api_key=self.api_key,
            model=self.model,
            messages=messages,
        )


class OpenAIRawLLMProvider(ChatCompletionRawLLMProvider):
    endpoint_url = OPENAI_CHAT_COMPLETIONS_URL


class OpenRouterRawLLMProvider(ChatCompletionRawLLMProvider):
    endpoint_url = OPENROUTER_CHAT_COMPLETIONS_URL


def build_scoring_messages(profile: LeadProfile) -> list[dict[str, str]]:
    profile_json = json_for_prompt(profile.model_dump(mode="json"))
    score_schema_json = json_for_prompt(IcpScore.model_json_schema())
    return [
        {
            "role": "system",
            "content": (
                "You are an ICP scoring analyst for a GTM automation product. "
                "Return only valid JSON. Do not include markdown fences, prose, "
                "or commentary outside the JSON object."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Documented ICP:\n{ICP_DEFINITION}\n\n"
                "Score the enriched lead profile against the ICP. The application "
                "will choose the final route deterministically, so do not choose "
                "a route.\n\n"
                f"Enriched lead profile:\n{profile_json}\n\n"
                "Return strict structured JSON matching this schema:\n"
                f"{score_schema_json}"
            ),
        },
    ]


def build_email_messages(
    profile: LeadProfile,
    scoring_result: IcpScore,
    final_route: Route,
    sequence: SequencePlan,
) -> list[dict[str, str]]:
    sequence_json = json_for_prompt(sequence.model_dump(mode="json"))
    profile_json = json_for_prompt(profile.model_dump(mode="json"))
    score_json = json_for_prompt(scoring_result.model_dump(mode="json"))
    email_schema_json = json_for_prompt(GeneratedEmail.model_json_schema())
    return [
        {
            "role": "system",
            "content": (
                "You write first-touch outbound emails for a GTM automation "
                "product. Return only valid JSON. Do not include markdown fences, "
                "prose, or commentary outside the JSON object. Do not invent facts "
                "beyond the lead profile and scoring context."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Final deterministic route: {final_route}\n"
                "Do not change, relabel, or second-guess the route.\n\n"
                f"Selected route instructions:\n{sequence.style}\n\n"
                f"Selected sequence plan:\n{sequence_json}\n\n"
                f"Lead profile:\n{profile_json}\n\n"
                f"Scoring context:\n{score_json}\n\n"
                "Generate only the first email. Return strict structured JSON "
                "matching this schema:\n"
                f"{email_schema_json}"
            ),
        },
    ]


def build_repair_messages(
    original_messages: list[dict[str, str]],
    invalid_output: object,
    repair_prompt: str,
) -> list[dict[str, str]]:
    return [
        *original_messages,
        {
            "role": "assistant",
            "content": stringify_llm_output(invalid_output),
        },
        {
            "role": "user",
            "content": repair_prompt,
        },
    ]


def stringify_llm_output(output: object) -> str:
    if isinstance(output, str):
        return output
    return json_for_prompt(output)


def json_for_prompt(value: object) -> str:
    return json.dumps(value, indent=2, sort_keys=True)


def extract_chat_completion_content(response_payload: object) -> str:
    try:
        response = ChatCompletionResponse.model_validate(response_payload)
    except ValidationError as exc:
        raise RuntimeError(
            "LLM provider response did not match chat completion response shape"
        ) from exc
    return response.choices[0].message.content
