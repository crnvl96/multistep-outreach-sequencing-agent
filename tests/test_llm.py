import asyncio

import pytest

from outreach_agent.models import LeadProfile
from support.fake_llm import FakeOpenAI


def test_fake_llm_fails_loudly_for_unknown_fixture() -> None:
    profile = LeadProfile(
        lead_name="Taylor Reed",
        company_name="Unknown SaaS",
        company_domain="unknown-saas.example",
        lead_title="VP Sales",
        industry="B2B SaaS",
        company_size_range="51-200 employees",
        region="North America",
        company_description="A complete but unconfigured fake fixture profile.",
        business_signals=["Scaling outbound sales"],
    )

    with pytest.raises(ValueError, match="No mock lead fixture configured"):
        asyncio.run(FakeOpenAI().score_icp(profile))
