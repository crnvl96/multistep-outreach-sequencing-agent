import os
from typing import Protocol

from outreach_agent.models import (
    GeneratedEmail,
    IcpScore,
    LeadProfile,
    Route,
    SequencePlan,
)


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

    async def generate_first_email(
        self,
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
                (
                    f"Referenced score {scoring_result.score} and outbound scaling "
                    "signals."
                ),
            ],
        )


def select_llm_provider() -> LLMProvider:
    provider_name = os.getenv("LLM_PROVIDER", "fake").lower()
    if provider_name == "fake":
        return FakeLLMProvider()
    raise ValueError(f"Unsupported LLM_PROVIDER for this slice: {provider_name}")
