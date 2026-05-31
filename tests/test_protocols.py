import importlib

import pytest

from outreach_agent import llm


def test_llm_contract_helpers_are_available_from_flat_module() -> None:
    assert llm.ChatTransport
    assert llm.LLMCall
    assert llm.LLMCallResult
    assert llm.LLMOutputInvalidError
    assert llm.LLMProvider
    assert llm.RawLLMProvider


def test_removed_protocol_package_is_not_part_of_flat_layout() -> None:
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("outreach_agent.protocols")
