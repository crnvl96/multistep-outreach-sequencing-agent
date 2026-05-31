from dataclasses import dataclass
from typing import Literal

from outreach_agent.domain.models import EnrichmentStep, LeadProfile
from outreach_agent.protocols.enrichment import ScrapeEnrichmentProvider

EnrichmentStage = Literal["api", "scrape"]
MockPatch = dict[str, object]
MockEnrichmentData = dict[str, MockPatch]


@dataclass(frozen=True)
class MockLeadFixture:
    key: str
    aliases: tuple[str, ...]
    api_patch: MockPatch
    scrape_patch: MockPatch


MOCK_LEAD_FIXTURES = (
    MockLeadFixture(
        key="warm",
        aliases=("signalspring.io", "signalspring software"),
        api_patch={
            "lead_title": "Head of Growth",
            "industry": "B2B SaaS",
            "company_size_range": "51-200 employees",
            "region": "Europe",
        },
        scrape_patch={
            "company_description": (
                "SignalSpring Software helps revenue teams monitor pipeline health "
                "and prioritize account follow-up."
            ),
            "business_signals": [
                "Publishing educational content about RevOps process gaps",
                "Evaluating outbound workflow improvements",
            ],
        },
    ),
    MockLeadFixture(
        key="hot",
        aliases=("nimbusforge.ai", "nimbusforge ai"),
        api_patch={
            "lead_title": "VP Sales",
            "industry": "AI software",
            "company_size_range": "201-500 employees",
            "region": "North America",
            "company_description": (
                "NimbusForge AI is a B2B software company helping enterprise GTM "
                "teams automate revenue workflows."
            ),
            "business_signals": [
                "Hiring SDRs and RevOps roles",
                "Recently launched an AI workflow product",
                "Scaling outbound personalization for enterprise sales",
            ],
        },
        scrape_patch={},
    ),
    MockLeadFixture(
        key="cold",
        aliases=("greenfork-catering.example", "greenfork catering"),
        api_patch={
            "lead_title": "Owner",
            "industry": "Local catering",
            "company_size_range": "11-50 employees",
            "region": "North America",
            "company_description": (
                "GreenFork Catering provides local event catering and meal service "
                "for private gatherings."
            ),
            "business_signals": [
                "Promotes seasonal menus for local events",
                "No visible outbound sales team or SaaS revenue motion",
            ],
        },
        scrape_patch={},
    ),
    MockLeadFixture(
        key="insufficient_data",
        aliases=("papertrail-cafe.example", "papertrail cafe"),
        api_patch={
            "industry": "Local hospitality",
            "region": "North America",
        },
        scrape_patch={
            "company_description": (
                "A small neighborhood cafe with a simple brochure site."
            ),
        },
    ),
)


def normalize_lookup_key(value: str) -> str:
    normalized = value.strip().lower()
    normalized = normalized.removeprefix("https://")
    normalized = normalized.removeprefix("http://")
    normalized = normalized.removeprefix("www.")
    return normalized.rstrip("/")


FIXTURE_KEY_BY_ALIAS = {
    normalize_lookup_key(alias): fixture.key
    for fixture in MOCK_LEAD_FIXTURES
    for alias in fixture.aliases
}


def build_mock_enrichment_map(stage: EnrichmentStage) -> MockEnrichmentData:
    enrichment_map: MockEnrichmentData = {}
    for fixture in MOCK_LEAD_FIXTURES:
        patch = fixture.api_patch if stage == "api" else fixture.scrape_patch
        if not patch:
            continue
        for alias in fixture.aliases:
            enrichment_map[normalize_lookup_key(alias)] = copy_patch(patch)
    return enrichment_map


def copy_patch(patch: MockPatch) -> MockPatch:
    copied: MockPatch = {}
    for key, value in patch.items():
        copied[key] = list(value) if isinstance(value, list) else value
    return copied


def lookup_keys(profile: LeadProfile) -> list[str]:
    keys = [profile.company_domain, profile.company_name]
    if profile.lead_email and "@" in profile.lead_email:
        keys.append(profile.lead_email.rsplit("@", maxsplit=1)[1])
    return [normalize_lookup_key(key) for key in keys if key]


def lookup_mock_data(
    profile: LeadProfile,
    enrichment_data: MockEnrichmentData,
) -> dict[str, object]:
    for key in lookup_keys(profile):
        if key in enrichment_data:
            return enrichment_data[key]
    return {}


def merge_profile(
    profile: LeadProfile,
    patch: dict[str, object],
) -> tuple[LeadProfile, list[str]]:
    profile_data = profile.model_dump()
    fields_added: list[str] = []

    for field_name, value in patch.items():
        if value in (None, "", []):
            continue

        current_value = profile_data.get(field_name)
        if isinstance(current_value, list) and isinstance(value, list):
            original_length = len(current_value)
            current_value.extend(item for item in value if item not in current_value)
            if len(current_value) > original_length:
                fields_added.append(field_name)
        elif not current_value:
            profile_data[field_name] = value
            fields_added.append(field_name)

    return LeadProfile(**profile_data), fields_added


def apply_mock_enrichment(
    profile: LeadProfile,
    source: Literal["api", "scrape"],
    enrichment_data: MockEnrichmentData,
) -> tuple[LeadProfile, EnrichmentStep]:
    patch = lookup_mock_data(profile, enrichment_data)
    enriched_profile, fields_added = merge_profile(profile, patch)
    return enriched_profile, EnrichmentStep(
        source=source,
        fields_added=fields_added,
        data=patch,
    )


class MockScrapeEnrichmentProvider(ScrapeEnrichmentProvider):
    def __init__(self, enrichment_data: MockEnrichmentData | None = None) -> None:
        self.enrichment_data = enrichment_data or build_mock_enrichment_map("scrape")

    async def enrich(self, profile: LeadProfile) -> tuple[LeadProfile, EnrichmentStep]:
        return apply_mock_enrichment(profile, "scrape", self.enrichment_data)


__all__ = ["MockScrapeEnrichmentProvider"]
