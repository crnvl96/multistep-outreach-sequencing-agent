from outreach_agent.llm.prompts import (
    build_email_messages,
    build_repair_messages,
    build_scoring_messages,
)
from outreach_agent.llm.transport import ChatTransport, UrllibChatTransport
from outreach_agent.models import IcpScore, LeadProfile, Route, SequencePlan

OPENAI_CHAT_COMPLETIONS_URL = "https://api.openai.com/v1/chat/completions"
OPENROUTER_CHAT_COMPLETIONS_URL = "https://openrouter.ai/api/v1/chat/completions"


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
