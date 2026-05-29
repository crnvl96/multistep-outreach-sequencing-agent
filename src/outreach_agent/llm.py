import os
from collections.abc import Callable
from typing import Protocol

from outreach_agent.fixtures import fixture_key_for_profile
from outreach_agent.models import (
    GeneratedEmail,
    IcpScore,
    LeadProfile,
    Route,
    SequencePlan,
)

ScoreBuilder = Callable[[LeadProfile], IcpScore]
EmailBuilder = Callable[[LeadProfile, IcpScore, Route, SequencePlan], GeneratedEmail]


class LLMProvider(Protocol):
    async def score_icp(self, profile: LeadProfile) -> IcpScore: ...

    async def generate_first_email(
        self,
        profile: LeadProfile,
        scoring_result: IcpScore,
        final_route: Route,
        sequence: SequencePlan,
    ) -> GeneratedEmail: ...


class FakeLLMProvider:
    async def score_icp(self, profile: LeadProfile) -> IcpScore:
        fixture_key = fixture_key_for_profile(profile)
        try:
            build_score = FAKE_SCORE_BY_FIXTURE[fixture_key]
        except KeyError as exc:
            raise ValueError(
                f"No fake scoring fixture configured for {fixture_key}"
            ) from exc
        return build_score(profile)

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


FAKE_SCORE_BY_FIXTURE: dict[str, ScoreBuilder] = {
    "hot": build_hot_score,
    "warm": build_warm_score,
}

FAKE_EMAIL_BY_ROUTE: dict[Route, EmailBuilder] = {
    "hot": build_hot_email,
    "warm": build_warm_email,
}


def select_llm_provider() -> LLMProvider:
    provider_name = os.getenv("LLM_PROVIDER", "fake").lower()
    if provider_name == "fake":
        return FakeLLMProvider()
    raise ValueError(f"Unsupported LLM_PROVIDER for this slice: {provider_name}")
