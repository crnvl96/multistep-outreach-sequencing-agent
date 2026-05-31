import asyncio

from outreach_agent.enrichment import (
    MockAPIEnrichmentProvider,
    MockScrapeEnrichmentProvider,
)
from outreach_agent.llm import ValidatingLLMProvider
from outreach_agent.models import LeadProfile


def test_llm_validation_lives_in_flat_llm_module() -> None:
    assert ValidatingLLMProvider


def test_mock_api_enrichment_provider_uses_fixture_enrichment_map() -> None:
    provider = MockAPIEnrichmentProvider()
    profile = LeadProfile(
        lead_name="Jordan Park",
        company_name="SignalSpring Software",
        company_domain="signalspring.io",
    )

    enriched_profile, step = asyncio.run(provider.enrich(profile))

    assert step.source == "api"
    assert step.fields_added == [
        "lead_title",
        "industry",
        "company_size_range",
        "region",
    ]
    assert step.data == {
        "lead_title": "Head of Growth",
        "industry": "B2B SaaS",
        "company_size_range": "51-200 employees",
        "region": "Europe",
    }
    assert enriched_profile.lead_title == "Head of Growth"
    assert enriched_profile.industry == "B2B SaaS"
    assert enriched_profile.company_size_range == "51-200 employees"


def test_mock_scrape_enrichment_provider_uses_fixture_scrape_map() -> None:
    provider = MockScrapeEnrichmentProvider()
    profile = LeadProfile(
        lead_name="Jordan Park",
        company_name="SignalSpring Software",
        company_domain="signalspring.io",
    )

    enriched_profile, step = asyncio.run(provider.enrich(profile))

    assert step.source == "scrape"
    assert step.fields_added == ["company_description", "business_signals"]
    assert step.data == {
        "company_description": (
            "SignalSpring Software helps revenue teams monitor pipeline health "
            "and prioritize account follow-up."
        ),
        "business_signals": [
            "Publishing educational content about RevOps process gaps",
            "Evaluating outbound workflow improvements",
        ],
    }
    assert enriched_profile.company_description == (
        "SignalSpring Software helps revenue teams monitor pipeline health "
        "and prioritize account follow-up."
    )
    assert enriched_profile.business_signals == [
        "Publishing educational content about RevOps process gaps",
        "Evaluating outbound workflow improvements",
    ]
