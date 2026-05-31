def test_protocol_contracts_are_available_from_protocols_layer() -> None:
    from outreach_agent.protocols.enrichment import (
        APIEnrichmentProviderProtocol,
        ScrapeEnrichmentProviderProtocol,
    )
    from outreach_agent.protocols.llm import (
        ChatTransportProtocol,
        LLMCall,
        LLMCallResult,
        LLMOutputInvalidError,
        LLMProviderProtocol,
        RawLLMProviderProtocol,
    )

    assert ChatTransportProtocol
    assert LLMCall
    assert LLMCallResult
    assert LLMOutputInvalidError
    assert LLMProviderProtocol
    assert RawLLMProviderProtocol
    assert APIEnrichmentProviderProtocol
    assert ScrapeEnrichmentProviderProtocol


def test_enrichment_protocols_are_exported_from_protocols_layer() -> None:
    import outreach_agent.protocols as protocols

    assert hasattr(protocols, "APIEnrichmentProvider")
    assert hasattr(protocols, "ScrapeEnrichmentProvider")


def test_old_llm_package_does_not_own_protocol_contracts() -> None:
    import outreach_agent.llm as llm_package

    assert not hasattr(llm_package, "LLMCallResult")
    assert not hasattr(llm_package, "LLMOutputInvalidError")
    assert not hasattr(llm_package, "LLMProvider")
    assert not hasattr(llm_package, "RawLLMProvider")
