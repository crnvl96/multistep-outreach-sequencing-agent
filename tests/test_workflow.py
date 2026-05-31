import asyncio
from pathlib import Path
from typing import Literal

import pytest

from outreach_agent.llm import LLMCallResult
from outreach_agent.models import (
    Confidence,
    EnrichmentStep,
    GeneratedEmail,
    IcpScore,
    LeadIntake,
    LeadProfile,
    Route,
    SequencePlan,
)
from outreach_agent.workflow import process_lead, route_from_score


class TrackingEnrichmentProvider:
    def __init__(
        self,
        enriched_profile: LeadProfile,
        *,
        source: Literal["api", "scrape"],
        fields_added: list[str],
        data: dict[str, object],
    ) -> None:
        self.enriched_profile = enriched_profile
        self.source = source
        self.fields_added = fields_added
        self.data = data
        self.calls: list[LeadProfile] = []

    async def enrich(self, profile: LeadProfile) -> tuple[LeadProfile, EnrichmentStep]:
        self.calls.append(profile)
        return self.enriched_profile, EnrichmentStep(
            source=self.source, fields_added=self.fields_added, data=self.data
        )


class DeterministicLLMProvider:
    async def score_icp(self, profile: LeadProfile) -> LLMCallResult[IcpScore]:
        score = IcpScore(
            score=72,
            confidence="medium",
            positive_evidence=["fixture"],
            negative_evidence=[],
            missing_evidence=[],
            reasoning="deterministic fixture score",
        )
        return LLMCallResult(
            value=score,
            calls=("score_icp",),
        )

    async def generate_first_email(
        self,
        profile: LeadProfile,
        scoring_result: IcpScore,
        final_route: Route,
        sequence: SequencePlan,
    ) -> LLMCallResult[GeneratedEmail]:
        email = GeneratedEmail(
            subject="Test \u2014 subject",
            body="Morgan\u2019s test \u2014 body",
            cta="Let\u2019s talk",
            personalization_notes=[
                f"Route: {final_route}",
                f"Company: {profile.company_name}",
            ],
        )
        return LLMCallResult(
            value=email,
            calls=("generate_first_email",),
        )


def make_score(score: int, confidence: Confidence = "high") -> IcpScore:
    return IcpScore(
        score=score,
        confidence=confidence,
        positive_evidence=["positive"],
        negative_evidence=[],
        missing_evidence=[],
        reasoning="reasoning",
    )


@pytest.mark.parametrize(
    ("score", "expected_route"),
    [
        (100, "hot"),
        (80, "hot"),
        (79, "warm"),
        (50, "warm"),
        (49, "cold"),
        (0, "cold"),
    ],
)
def test_route_from_score_uses_documented_score_boundaries(
    score: int,
    expected_route: Route,
) -> None:
    assert route_from_score(make_score(score)) == expected_route


@pytest.mark.parametrize("score", [100, 80])
def test_route_from_score_keeps_high_scores_warm_when_confidence_is_low(
    score: int,
) -> None:
    assert route_from_score(make_score(score, confidence="low")) == "warm"


def test_process_lead_runs_scrape_after_thin_api_result(
    tmp_path: Path,
) -> None:
    intake = LeadIntake(
        lead_name="Jordan Park",
        company_name="SignalSpring Software",
        company_domain="signalspring.io",
    )

    api_profile = LeadProfile(
        lead_name="Jordan Park",
        company_name="SignalSpring Software",
        company_domain="signalspring.io",
        lead_title="Head of Growth",
        industry="B2B SaaS",
        company_size_range="51-200 employees",
        region="Europe",
    )
    scrape_profile = api_profile.model_copy(
        update={
            "company_description": (
                "SignalSpring Software helps revenue teams monitor pipeline health "
                "and prioritize account follow-up."
            ),
            "business_signals": [
                "Publishing educational content about RevOps process gaps",
                "Evaluating outbound workflow improvements",
            ],
        }
    )

    api_provider = TrackingEnrichmentProvider(
        api_profile,
        source="api",
        fields_added=[
            "lead_title",
            "industry",
            "company_size_range",
            "region",
        ],
        data={},
    )
    scrape_provider = TrackingEnrichmentProvider(
        scrape_profile,
        source="scrape",
        fields_added=["company_description", "business_signals"],
        data={},
    )

    response = asyncio.run(
        process_lead(
            intake,
            artifact_dir=tmp_path,
            api_enrichment_provider=api_provider,
            scrape_enrichment_provider=scrape_provider,
            llm_provider=DeterministicLLMProvider(),
        )
    )

    assert [step.source for step in response.enrichment_steps] == ["api", "scrape"]
    assert len(response.thin_data_checks) == 2
    assert response.thin_data_checks[0].is_thin is True
    assert response.thin_data_checks[1].is_thin is False
    assert api_provider.calls == [LeadProfile(**intake.model_dump())]
    assert scrape_provider.calls == [api_profile]
    assert response.llm_calls == ["score_icp", "generate_first_email"]


def test_process_lead_skips_scrape_when_api_enrichment_is_complete(
    tmp_path: Path,
) -> None:
    intake = LeadIntake(
        lead_name="Morgan Lee",
        company_name="NimbusForge AI",
        company_domain="nimbusforge.ai",
    )
    api_profile = LeadProfile(
        lead_name="Morgan Lee",
        company_name="NimbusForge AI",
        company_domain="nimbusforge.ai",
        lead_title="VP Sales",
        industry="AI software",
        company_size_range="201-500 employees",
        region="North America",
        company_description=(
            "NimbusForge AI is a B2B software company helping enterprise GTM "
            "teams automate revenue workflows."
        ),
        business_signals=["scaling outbound"],
    )
    api_provider = TrackingEnrichmentProvider(
        api_profile,
        source="api",
        fields_added=[],
        data={},
    )
    scrape_provider = TrackingEnrichmentProvider(
        api_profile,
        source="scrape",
        fields_added=[],
        data={},
    )

    response = asyncio.run(
        process_lead(
            intake,
            artifact_dir=tmp_path,
            api_enrichment_provider=api_provider,
            scrape_enrichment_provider=scrape_provider,
            llm_provider=DeterministicLLMProvider(),
        )
    )

    assert [step.source for step in response.enrichment_steps] == ["api"]
    assert len(response.thin_data_checks) == 1
    assert response.thin_data_checks[0].is_thin is False
    assert response.llm_calls == ["score_icp", "generate_first_email"]
    assert scrape_provider.calls == []
    assert response.generated_email is not None
    assert response.generated_email.subject == "Test - subject"
    assert response.generated_email.body == "Morgan's test - body"
    assert response.generated_email.cta == "Let's talk"

    artifact_text = Path(response.artifact_path).read_text(encoding="utf-8")
    assert artifact_text.isascii()
    assert "\\u2014" not in artifact_text
    assert "\\u2019" not in artifact_text


def test_process_lead_stops_before_llm_when_scrape_still_thin(
    tmp_path: Path,
) -> None:
    intake = LeadIntake(
        lead_name="Riley Stone",
        company_name="PaperTrail Cafe",
        company_domain="papertrail-cafe.example",
    )

    api_profile = LeadProfile(
        lead_name="Riley Stone",
        company_name="PaperTrail Cafe",
        company_domain="papertrail-cafe.example",
        industry="Local hospitality",
        region="North America",
    )
    scrape_profile = api_profile.model_copy(
        update={
            "company_description": (
                "A small neighborhood cafe with a simple brochure site."
            ),
        }
    )

    api_provider = TrackingEnrichmentProvider(
        api_profile,
        source="api",
        fields_added=["industry", "region"],
        data={},
    )
    scrape_provider = TrackingEnrichmentProvider(
        scrape_profile,
        source="scrape",
        fields_added=["company_description"],
        data={},
    )

    response = asyncio.run(
        process_lead(
            intake,
            artifact_dir=tmp_path,
            api_enrichment_provider=api_provider,
            scrape_enrichment_provider=scrape_provider,
            llm_provider=DeterministicLLMProvider(),
        )
    )

    assert [step.source for step in response.enrichment_steps] == ["api", "scrape"]
    assert response.thin_data_checks[0].is_thin is True
    assert response.thin_data_checks[1].is_thin is True
    assert response.status == "insufficient_data"
    assert response.llm_calls == []
