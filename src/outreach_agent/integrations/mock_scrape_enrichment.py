from outreach_agent.domain.models import EnrichmentStep, LeadProfile
from outreach_agent.fixtures import (
    MockEnrichmentData,
    apply_mock_enrichment,
    build_mock_enrichment_map,
)


class MockScrapeEnrichmentProvider:
    def __init__(self, enrichment_data: MockEnrichmentData | None = None) -> None:
        self.enrichment_data = enrichment_data or build_mock_enrichment_map("scrape")

    async def enrich(self, profile: LeadProfile) -> tuple[LeadProfile, EnrichmentStep]:
        return apply_mock_enrichment(profile, "scrape", self.enrichment_data)


__all__ = ["MockScrapeEnrichmentProvider"]
