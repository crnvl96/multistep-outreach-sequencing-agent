from typing import Protocol

from outreach_agent.domain.models import EnrichmentStep, LeadProfile


class APIEnrichmentProvider(Protocol):
    async def enrich(
        self,
        profile: LeadProfile,
    ) -> tuple[LeadProfile, EnrichmentStep]:
        ...


__all__ = ["APIEnrichmentProvider"]
