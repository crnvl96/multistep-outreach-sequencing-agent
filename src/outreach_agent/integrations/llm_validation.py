import json
from collections.abc import Awaitable, Callable

from pydantic import BaseModel, ValidationError

from outreach_agent.domain.models import (
    GeneratedEmail,
    IcpScore,
    LeadProfile,
    LLMRepairAttempt,
    Route,
    SequencePlan,
)
from outreach_agent.domain.prompts import build_repair_prompt
from outreach_agent.protocols import llm as _llm_protocols


class ValidatingLLMProvider(_llm_protocols.LLMProvider):
    def __init__(self, raw_provider: _llm_protocols.RawLLMProvider) -> None:
        self.raw_provider = raw_provider

    async def score_icp(
        self,
        profile: LeadProfile,
    ) -> _llm_protocols.LLMCallResult[IcpScore]:
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
    ) -> _llm_protocols.LLMCallResult[GeneratedEmail]:
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
    call: _llm_protocols.LLMCall,
    repair_call: str,
    schema: type[StructuredOutput],
    prompt_label: str,
    call_provider: Callable[[], Awaitable[object]],
    repair_provider: Callable[[object, str], Awaitable[object]],
) -> _llm_protocols.LLMCallResult[StructuredOutput]:
    output = await call_provider()
    calls = (call,)
    try:
        value = parse_structured_output(output, schema, call)
    except _llm_protocols.LLMOutputInvalidError as exc:
        repair_output = await repair_provider(
            output,
            build_repair_prompt(schema, prompt_label, exc),
        )
        repaired_calls = (call, repair_call)
        try:
            value = parse_structured_output(repair_output, schema, call)
        except _llm_protocols.LLMOutputInvalidError as repair_exc:
            repairs = (
                LLMRepairAttempt(
                    call=call,
                    attempt_number=1,
                    status="failed",
                ),
            )
            raise _llm_protocols.LLMOutputInvalidError(
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
        return _llm_protocols.LLMCallResult(
            value=value,
            calls=repaired_calls,
            repairs=repairs,
        )
    return _llm_protocols.LLMCallResult(value=value, calls=calls)


def parse_structured_output[StructuredOutput: BaseModel](
    output: object,
    schema: type[StructuredOutput],
    call: _llm_protocols.LLMCall,
) -> StructuredOutput:
    try:
        parsed_output = json.loads(output) if isinstance(output, str) else output
        return schema.model_validate(parsed_output)
    except (json.JSONDecodeError, ValidationError) as exc:
        message = format_validation_error(exc)
        raise _llm_protocols.LLMOutputInvalidError(
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
