from dataclasses import dataclass
from typing import Literal, Protocol

from pydantic import BaseModel

from outreach_agent.domain.models import (
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


class ChatTransport(Protocol):
    async def create_chat_completion(
        self,
        *,
        endpoint_url: str,
        api_key: str,
        model: str,
        messages: list[dict[str, str]],
    ) -> str: ...


__all__ = [
    "ChatTransport",
    "LLMCall",
    "LLMCallResult",
    "LLMOutputInvalidError",
    "LLMProvider",
    "RawLLMProvider",
]
