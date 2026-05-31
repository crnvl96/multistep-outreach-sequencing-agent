import importlib

import pytest

from outreach_agent.models import IcpScore, LeadProfile, Route
from outreach_agent.prompts import build_scoring_messages


def test_prompts_reference_models_and_constants() -> None:
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


def test_legacy_layer_modules_no_longer_exist() -> None:
    for module_name in (
        "outreach_agent.domain",
        "outreach_agent.protocols",
        "outreach_agent.integrations",
    ):
        with pytest.raises(ModuleNotFoundError):
            importlib.import_module(module_name)
