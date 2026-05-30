import json
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Literal, Protocol

from pydantic import BaseModel, ValidationError

from outreach_agent.models import (
    GeneratedEmail,
    IcpScore,
    LeadProfile,
    LLMRepairAttempt,
    Route,
    SequencePlan,
)

LLMCall = Literal["score_icp", "generate_first_email"]


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


class RawLLMProvider(Protocol):
    async def score_icp(self, profile: LeadProfile) -> object: ...

    async def repair_score_icp(
        self,
        profile: LeadProfile,
        invalid_output: object,
        repair_prompt: str,
    ) -> object: ...

    async def generate_first_email(
        self,
        profile: LeadProfile,
        scoring_result: IcpScore,
        final_route: Route,
        sequence: SequencePlan,
    ) -> object: ...

    async def repair_first_email(
        self,
        profile: LeadProfile,
        scoring_result: IcpScore,
        final_route: Route,
        sequence: SequencePlan,
        invalid_output: object,
        repair_prompt: str,
    ) -> object: ...


class LLMProvider(Protocol):
    async def score_icp(self, profile: LeadProfile) -> LLMCallResult[IcpScore]: ...

    async def generate_first_email(
        self,
        profile: LeadProfile,
        scoring_result: IcpScore,
        final_route: Route,
        sequence: SequencePlan,
    ) -> LLMCallResult[GeneratedEmail]: ...


class ValidatingLLMProvider:
    def __init__(self, raw_provider: RawLLMProvider) -> None:
        self.raw_provider = raw_provider

    async def score_icp(self, profile: LeadProfile) -> LLMCallResult[IcpScore]:
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
        return LLMCallResult(value=value, calls=repaired_calls, repairs=repairs)
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


def build_repair_prompt(
    schema: type[BaseModel],
    step_name: str,
    error: Exception,
) -> str:
    fields = ", ".join(schema.model_fields)
    return (
        f"Return only valid JSON matching the {step_name} schema. "
        f"Required fields: {fields}. "
        "Do not include markdown fences, prose, or commentary. "
        f"Validation error: {error}"
    )
