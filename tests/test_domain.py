import importlib

import pytest

from outreach_agent.domain.models import IcpScore, LeadProfile, Route
from outreach_agent.domain.prompts import build_scoring_messages


def test_domain_prompts_reference_types_and_constants() -> None:
    profile = LeadProfile(
        lead_name="Ada Lovelace",
        company_name="ThinCo",
        company_domain="thinco.example",
    )

    messages = build_scoring_messages(profile)

    assert len(messages) == 2
    assert "B2B SaaS or AI/software" in messages[1]["content"]
    assert isinstance(IcpScore.model_json_schema(), dict)
    assert "hot" in Route.__args__


def test_legacy_domain_modules_no_longer_exist() -> None:
    for module_name in ("outreach_agent.models", "outreach_agent.llm.prompts"):
        with pytest.raises(ModuleNotFoundError):
            importlib.import_module(module_name)
