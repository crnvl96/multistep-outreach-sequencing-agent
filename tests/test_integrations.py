import importlib

import pytest

from outreach_agent.integrations.llm_validation import ValidatingLLMProvider


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
