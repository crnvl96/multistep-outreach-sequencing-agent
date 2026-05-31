import asyncio
import importlib

import pytest

from outreach_agent.domain.models import LeadProfile
from outreach_agent.integrations.llm_validation import ValidatingLLMProvider
from outreach_agent.integrations.mock_api_enrichment import MockAPIEnrichmentProvider


def test_validating_llm_provider_lives_in_integrations_layer() -> None:
    assert ValidatingLLMProvider


def test_old_validation_provider_ownership_locations_removed() -> None:
    try:
        importlib.import_module("outreach_agent.llm.validation")
    except ModuleNotFoundError:
        pass
    else:
        raise AssertionError("outreach_agent.llm.validation should have been removed")

    assert not hasattr(
        importlib.import_module("outreach_agent.llm"),
        "ValidatingLLMProvider",
    )


@pytest.mark.parametrize(
    "module_name",
    [
        "outreach_agent.llm.config",
        "outreach_agent.llm.factory",
        "outreach_agent.llm.real",
        "outreach_agent.llm.transport",
    ],
)
def test_old_real_llm_ownership_modules_removed(module_name: str) -> None:
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module(module_name)


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
