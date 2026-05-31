from typing import Protocol

from outreach_agent.domain.models import EnrichmentStep, LeadProfile


class APIEnrichmentProviderProtocol(Protocol):
    async def enrich(
        self,
        profile: LeadProfile,
    ) -> tuple[LeadProfile, EnrichmentStep]: ...


class ScrapeEnrichmentProviderProtocol(Protocol):
    async def enrich(
        self,
        profile: LeadProfile,
    ) -> tuple[LeadProfile, EnrichmentStep]: ...


APIEnrichmentProvider = APIEnrichmentProviderProtocol
ScrapeEnrichmentProvider = ScrapeEnrichmentProviderProtocol


__all__ = [
    "APIEnrichmentProvider",
    "APIEnrichmentProviderProtocol",
    "ScrapeEnrichmentProvider",
    "ScrapeEnrichmentProviderProtocol",
]
