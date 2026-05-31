"""Protocol contracts for application boundaries."""

from outreach_agent.protocols.enrichment import (
    APIEnrichmentProvider,
    APIEnrichmentProviderProtocol,
    ScrapeEnrichmentProvider,
    ScrapeEnrichmentProviderProtocol,
)
from outreach_agent.protocols.llm import (
    ChatTransport,
    ChatTransportProtocol,
    LLMCall,
    LLMCallResult,
    LLMOutputInvalidError,
    LLMProvider,
    LLMProviderProtocol,
    RawLLMProvider,
    RawLLMProviderProtocol,
)

__all__ = [
    "APIEnrichmentProvider",
    "APIEnrichmentProviderProtocol",
    "ScrapeEnrichmentProvider",
    "ScrapeEnrichmentProviderProtocol",
    "ChatTransport",
    "ChatTransportProtocol",
    "LLMCall",
    "LLMCallResult",
    "LLMOutputInvalidError",
    "LLMProvider",
    "LLMProviderProtocol",
    "RawLLMProvider",
    "RawLLMProviderProtocol",
]
