import importlib

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
