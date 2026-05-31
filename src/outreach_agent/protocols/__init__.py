"""Protocol contracts for application boundaries."""

from outreach_agent.protocols.enrichment import (
    APIEnrichmentProvider,
    ScrapeEnrichmentProvider,
)
from outreach_agent.protocols.llm import (
    ChatTransport,
    LLMCall,
    LLMCallResult,
    LLMOutputInvalidError,
    LLMProvider,
    RawLLMProvider,
)

__all__ = [
    "APIEnrichmentProvider",
    "ScrapeEnrichmentProvider",
    "ChatTransport",
    "LLMCall",
    "LLMCallResult",
    "LLMOutputInvalidError",
    "LLMProvider",
    "RawLLMProvider",
]

