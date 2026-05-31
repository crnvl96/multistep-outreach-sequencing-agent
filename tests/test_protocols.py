def test_llm_protocol_contracts_are_available_from_protocols_layer() -> None:
    from outreach_agent.protocols.llm import (
        ChatTransport,
        LLMCall,
        LLMCallResult,
        LLMOutputInvalidError,
        LLMProvider,
        RawLLMProvider,
    )

    assert ChatTransport
    assert LLMCall
    assert LLMCallResult
    assert LLMOutputInvalidError
    assert LLMProvider
    assert RawLLMProvider


def test_old_llm_package_does_not_own_protocol_contracts() -> None:
    import outreach_agent.llm as llm_package

    assert not hasattr(llm_package, "LLMCallResult")
    assert not hasattr(llm_package, "LLMOutputInvalidError")
    assert not hasattr(llm_package, "LLMProvider")
    assert not hasattr(llm_package, "RawLLMProvider")
