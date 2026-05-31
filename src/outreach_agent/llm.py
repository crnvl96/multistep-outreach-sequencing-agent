import asyncio
import json
import urllib.error
import urllib.request
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from dotenv import dotenv_values
from pydantic import BaseModel, Field, ValidationError

from outreach_agent.models import (
    GeneratedEmail,
    IcpScore,
    LeadProfile,
    LLMRepairAttempt,
    Route,
    SequencePlan,
)
from outreach_agent.prompts import (
    build_email_messages,
    build_repair_messages,
    build_repair_prompt,
    build_scoring_messages,
)

LLMCall = Literal["score_icp", "generate_first_email"]
OPENAI_CHAT_COMPLETIONS_URL = "https://api.openai.com/v1/chat/completions"
DEFAULT_OPENAI_MODEL = "gpt-5.4-mini"
DEFAULT_DOTENV_PATH = Path(__file__).resolve().parents[2] / ".env"


@dataclass(frozen=True)
class LLMCallResult[StructuredOutput: BaseModel]:
    value: StructuredOutput
    calls: tuple[str, ...]
    repairs: tuple[LLMRepairAttempt, ...] = ()


class LLMOutputInvalidError(ValueError):
    def __init__(
        self,
        call: LLMCall,
        message: str,
        *,
        calls: tuple[str, ...],
        repairs: tuple[LLMRepairAttempt, ...],
    ) -> None:
        self.call = call
        self.calls = calls
        self.repairs = repairs
        super().__init__(message)


@dataclass(frozen=True)
class LLMSettings:
    openai_api_key: str | None = None


class LLMConfigurationError(ValueError):
    pass


def read_dotenv(dotenv_path: Path) -> dict[str, str]:
    if not dotenv_path.exists():
        return {}
    return {
        key: value
        for key, value in dotenv_values(dotenv_path).items()
        if value is not None
    }


def load_llm_settings(
    *,
    dotenv_path: Path = DEFAULT_DOTENV_PATH,
) -> LLMSettings:
    dotenv_env = read_dotenv(dotenv_path)

    return LLMSettings(openai_api_key=dotenv_env.get("OPENAI_API_KEY"))


def select_llm_provider(settings: LLMSettings) -> ValidatingLLMProvider:
    if not settings.openai_api_key:
        raise LLMConfigurationError("OPENAI_API_KEY is required")

    return ValidatingLLMProvider(
        OpenAIRawLLMProvider(
            api_key=settings.openai_api_key,
            model=DEFAULT_OPENAI_MODEL,
        )
    )


class ChatCompletionMessage(BaseModel):
    content: str = Field(min_length=1)


class ChatCompletionChoice(BaseModel):
    message: ChatCompletionMessage


class ChatCompletionResponse(BaseModel):
    choices: list[ChatCompletionChoice] = Field(min_length=1)


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


def extract_chat_completion_content(response_payload: object) -> str:
    try:
        response = ChatCompletionResponse.model_validate(response_payload)
    except ValidationError as exc:
        raise RuntimeError(
            "LLM provider response did not match chat completion response shape"
        ) from exc
    return response.choices[0].message.content


class OpenAIRawLLMProvider:
    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        transport: Any | None = None,
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
            endpoint_url=OPENAI_CHAT_COMPLETIONS_URL,
            api_key=self.api_key,
            model=self.model,
            messages=messages,
        )


class ValidatingLLMProvider:
    def __init__(self, raw_provider: Any) -> None:
        self.raw_provider = raw_provider

    async def score_icp(
        self,
        profile: LeadProfile,
    ) -> LLMCallResult[IcpScore]:
        async def call_provider() -> object:
            return await self.raw_provider.score_icp(profile)

        async def repair_provider(
            invalid_output: object,
            repair_prompt: str,
        ) -> object:
            return await self.raw_provider.repair_score_icp(
                profile,
                invalid_output,
                repair_prompt,
            )

        return await call_with_one_repair(
            call="score_icp",
            repair_call="repair_score_icp",
            schema=IcpScore,
            prompt_label="scoring",
            call_provider=call_provider,
            repair_provider=repair_provider,
        )

    async def generate_first_email(
        self,
        profile: LeadProfile,
        scoring_result: IcpScore,
        final_route: Route,
        sequence: SequencePlan,
    ) -> LLMCallResult[GeneratedEmail]:
        async def call_provider() -> object:
            return await self.raw_provider.generate_first_email(
                profile,
                scoring_result,
                final_route,
                sequence,
            )

        async def repair_provider(
            invalid_output: object,
            repair_prompt: str,
        ) -> object:
            return await self.raw_provider.repair_first_email(
                profile,
                scoring_result,
                final_route,
                sequence,
                invalid_output,
                repair_prompt,
            )

        return await call_with_one_repair(
            call="generate_first_email",
            repair_call="repair_first_email",
            schema=GeneratedEmail,
            prompt_label="email generation",
            call_provider=call_provider,
            repair_provider=repair_provider,
        )


async def call_with_one_repair[StructuredOutput: BaseModel](
    *,
    call: LLMCall,
    repair_call: str,
    schema: type[StructuredOutput],
    prompt_label: str,
    call_provider: Callable[[], Awaitable[object]],
    repair_provider: Callable[[object, str], Awaitable[object]],
) -> LLMCallResult[StructuredOutput]:
    output = await call_provider()
    calls = (call,)

    try:
        value = parse_structured_output(output, schema, call)

    except LLMOutputInvalidError as exc:
        repair_output = await repair_provider(
            output,
            build_repair_prompt(schema, prompt_label, exc),
        )

        repaired_calls = (call, repair_call)

        try:
            value = parse_structured_output(repair_output, schema, call)

        except LLMOutputInvalidError as repair_exc:
            repairs = (
                LLMRepairAttempt(
                    call=call,
                    attempt_number=1,
                    status="failed",
                ),
            )

            raise LLMOutputInvalidError(
                call,
                str(repair_exc),
                calls=repaired_calls,
                repairs=repairs,
            ) from repair_exc

        repairs = (
            LLMRepairAttempt(
                call=call,
                attempt_number=1,
                status="repaired",
            ),
        )

        return LLMCallResult(
            value=value,
            calls=repaired_calls,
            repairs=repairs,
        )

    return LLMCallResult(value=value, calls=calls)


def parse_structured_output[StructuredOutput: BaseModel](
    output: object,
    schema: type[StructuredOutput],
    call: LLMCall,
) -> StructuredOutput:
    try:
        parsed_output = json.loads(output) if isinstance(output, str) else output
        return schema.model_validate(parsed_output)
    except (json.JSONDecodeError, ValidationError) as exc:
        message = format_validation_error(exc)
        raise LLMOutputInvalidError(
            call,
            f"Invalid {call} output: {message}",
            calls=(call,),
            repairs=(),
        ) from exc


def format_validation_error(exc: json.JSONDecodeError | ValidationError) -> str:
    if isinstance(exc, json.JSONDecodeError):
        return exc.msg

    errors = exc.errors(include_input=False, include_url=False)
    return "; ".join(
        f"{'.'.join(str(part) for part in error['loc'])}: {error['msg']}"
        for error in errors
    )
