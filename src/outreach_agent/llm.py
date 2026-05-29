from collections.abc import Callable
from dataclasses import dataclass

from outreach_agent.fixtures import fixture_key_for_profile
from outreach_agent.llm_config import LLMSettings, load_llm_settings
from outreach_agent.llm_real import (
    ChatCompletionRawLLMProvider,
    OpenAIRawLLMProvider,
    OpenRouterRawLLMProvider,
)
from outreach_agent.llm_validation import LLMProvider, ValidatingLLMProvider
from outreach_agent.models import (
    GeneratedEmail,
    IcpScore,
    LeadProfile,
    Route,
    SequencePlan,
)

ScoreBuilder = Callable[[LeadProfile], IcpScore]
EmailBuilder = Callable[[LeadProfile, IcpScore, Route, SequencePlan], GeneratedEmail]


class LLMConfigurationError(ValueError):
    pass


OPENAI_DEFAULT_MODEL = "gpt-5.4-mini"
OPENROUTER_DEFAULT_MODEL = "deepseek-v4-flash"


@dataclass(frozen=True)
class RealProviderSpec:
    raw_provider: type[ChatCompletionRawLLMProvider]
    api_key: Callable[[LLMSettings], str | None]
    api_key_name: str
    default_model: str


REAL_PROVIDER_SPECS = {
    "openai": RealProviderSpec(
        raw_provider=OpenAIRawLLMProvider,
        api_key=lambda settings: settings.openai_api_key,
        api_key_name="OPENAI_API_KEY",
        default_model=OPENAI_DEFAULT_MODEL,
    ),
    "openrouter": RealProviderSpec(
        raw_provider=OpenRouterRawLLMProvider,
        api_key=lambda settings: settings.openrouter_api_key,
        api_key_name="OPENROUTER_API_KEY",
        default_model=OPENROUTER_DEFAULT_MODEL,
    ),
}


class FakeRawLLMProvider:
    async def score_icp(self, profile: LeadProfile) -> IcpScore:
        fixture_key = fixture_key_for_profile(profile)
        try:
            build_score = FAKE_SCORE_BY_FIXTURE[fixture_key]
        except KeyError as exc:
            raise ValueError(
                f"No fake scoring fixture configured for {fixture_key}"
            ) from exc
        return build_score(profile)

    async def repair_score_icp(
        self,
        profile: LeadProfile,
        invalid_output: object,
        repair_prompt: str,
    ) -> IcpScore:
        return await self.score_icp(profile)

    async def generate_first_email(
        self,
        profile: LeadProfile,
        scoring_result: IcpScore,
        final_route: Route,
        sequence: SequencePlan,
    ) -> GeneratedEmail:
        try:
            build_email = FAKE_EMAIL_BY_ROUTE[final_route]
        except KeyError as exc:
            raise ValueError(
                f"No fake email fixture configured for route: {final_route}"
            ) from exc
        return build_email(profile, scoring_result, final_route, sequence)

    async def repair_first_email(
        self,
        profile: LeadProfile,
        scoring_result: IcpScore,
        final_route: Route,
        sequence: SequencePlan,
        invalid_output: object,
        repair_prompt: str,
    ) -> GeneratedEmail:
        return await self.generate_first_email(
            profile,
            scoring_result,
            final_route,
            sequence,
        )


class FakeLLMProvider(ValidatingLLMProvider):
    def __init__(self) -> None:
        super().__init__(FakeRawLLMProvider())


def build_hot_score(profile: LeadProfile) -> IcpScore:
    return IcpScore(
        score=92,
        confidence="high",
        positive_evidence=[
            f"{profile.company_name} is a B2B AI/software company.",
            "Company size and region match the ICP.",
            "Signals show active outbound and RevOps scaling pain.",
        ],
        negative_evidence=[],
        missing_evidence=[],
        reasoning=(
            "Strong ICP fit: the profile shows a mid-market AI company in North "
            "America with clear outbound scaling and personalization needs."
        ),
    )


def build_warm_score(profile: LeadProfile) -> IcpScore:
    return IcpScore(
        score=68,
        confidence="medium",
        positive_evidence=[
            f"{profile.company_name} matches the B2B SaaS ICP.",
            "Revenue workflow and RevOps signals suggest possible relevance.",
        ],
        negative_evidence=[],
        missing_evidence=[
            "No strong hiring or funding urgency signal was found.",
        ],
        reasoning=(
            "Moderate ICP fit: the company is in the right market and has some GTM "
            "workflow relevance, but urgency is not strong enough for a Hot route."
        ),
    )


def build_cold_score(profile: LeadProfile) -> IcpScore:
    return IcpScore(
        score=32,
        confidence="medium",
        positive_evidence=[
            "The profile is complete enough to judge fit.",
            f"{profile.company_name} has a clear owner contact and region.",
        ],
        negative_evidence=[
            "The company is a local catering business, not B2B SaaS or AI software.",
            "There is no visible outbound sales team or GTM scaling motion.",
            "Company size is below the target 50-500 employee ICP range.",
        ],
        missing_evidence=[
            "No evidence of CRM, sales engagement, or RevOps tooling needs.",
            "No funding, launch, hiring, or outbound growth urgency was found.",
        ],
        reasoning=(
            "Weak ICP fit: the lead has enough data to score, but the business is "
            "local-services oriented and lacks the software/GTM scaling signals "
            "that define the target ICP."
        ),
    )


def build_hot_email(
    profile: LeadProfile,
    scoring_result: IcpScore,
    final_route: Route,
    sequence: SequencePlan,
) -> GeneratedEmail:
    return GeneratedEmail(
        subject="Reducing manual outbound research at NimbusForge",
        body=(
            f"Hi {profile.lead_name},\n\n"
            f"Saw {profile.company_name} is scaling outbound around AI workflow "
            "launches and RevOps hiring. Teams at that stage often lose time "
            "stitching enrichment, fit scoring, and first-touch personalization "
            "together before reps can act.\n\n"
            "We help GTM teams turn those signals into prioritized, explainable "
            "first-touch sequences without adding manual research steps."
        ),
        cta="Open to a 15-minute conversation this week?",
        personalization_notes=[
            f"Used final deterministic route: {final_route}.",
            f"Used {sequence.name} style: {sequence.style}.",
            f"Referenced score {scoring_result.score} and outbound scaling signals.",
        ],
    )


def build_warm_email(
    profile: LeadProfile,
    scoring_result: IcpScore,
    final_route: Route,
    sequence: SequencePlan,
) -> GeneratedEmail:
    return GeneratedEmail(
        subject="Worth comparing notes on outbound workflow fit?",
        body=(
            f"Hi {profile.lead_name},\n\n"
            f"Noticed {profile.company_name} is sharing signals around RevOps "
            "process gaps and outbound workflow improvements. It may be useful "
            "to compare notes on where qualification and personalization slow "
            "the team down, especially before adding more manual research.\n\n"
            "If the topic is relevant, I can share a lightweight way teams map "
            "enrichment signals into first-touch prioritization."
        ),
        cta="Would it be worth a brief conversation next week?",
        personalization_notes=[
            f"Used final deterministic route: {final_route}.",
            f"Used {sequence.name} style: {sequence.style}.",
            "Kept the CTA moderate because the score indicates possible fit.",
        ],
    )


def build_cold_email(
    profile: LeadProfile,
    scoring_result: IcpScore,
    final_route: Route,
    sequence: SequencePlan,
) -> GeneratedEmail:
    return GeneratedEmail(
        subject="Checking whether outbound workflow is relevant",
        body=(
            f"Hi {profile.lead_name},\n\n"
            f"I saw {profile.company_name} is focused on local catering and "
            "event services, so this may not be a priority. We usually help "
            "teams when outbound qualification or first-touch research starts "
            "taking too much manual time.\n\n"
            "If this is not a priority, no worries — I mainly wanted to check "
            "whether improving outbound workflow is on your radar at all."
        ),
        cta="Is this worth exploring, or should I close the loop?",
        personalization_notes=[
            f"Used final deterministic route: {final_route}.",
            f"Used {sequence.name} style: {sequence.style}.",
            f"Kept the note low-pressure because the score was {scoring_result.score}.",
        ],
    )


FAKE_SCORE_BY_FIXTURE: dict[str, ScoreBuilder] = {
    "hot": build_hot_score,
    "warm": build_warm_score,
    "cold": build_cold_score,
}

FAKE_EMAIL_BY_ROUTE: dict[Route, EmailBuilder] = {
    "hot": build_hot_email,
    "warm": build_warm_email,
    "cold": build_cold_email,
}


def select_llm_provider(settings: LLMSettings | None = None) -> LLMProvider:
    selected_settings = settings or load_llm_settings()
    provider_name = selected_settings.provider.lower()
    if provider_name == "fake":
        return FakeLLMProvider()

    provider_spec = REAL_PROVIDER_SPECS.get(provider_name)
    if not provider_spec:
        raise ValueError(f"Unsupported LLM_PROVIDER for this slice: {provider_name}")

    api_key = provider_spec.api_key(selected_settings)
    if not api_key:
        raise LLMConfigurationError(
            f"{provider_spec.api_key_name} is required when "
            f"LLM_PROVIDER={provider_name}"
        )

    return ValidatingLLMProvider(
        provider_spec.raw_provider(
            api_key=api_key,
            model=selected_settings.model or provider_spec.default_model,
        )
    )
