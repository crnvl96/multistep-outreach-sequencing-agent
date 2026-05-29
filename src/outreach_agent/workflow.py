import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from typing import Literal
from uuid import uuid4

from outreach_agent.models import (
    EnrichmentStep,
    LeadIntake,
    LeadProfile,
    LeadRunResponse,
    RunTimings,
    ThinDataCheck,
)

logger = logging.getLogger(__name__)
server_logger = logging.getLogger("uvicorn.error")

EnrichmentSource = Literal["mock_api", "mock_scrape"]
ThinDataStage = Literal["after_api_enrichment", "after_scrape_enrichment"]
MockEnrichmentData = dict[str, dict[str, object]]

RUNS_DIR = Path("runs")
REQUIRED_PROFILE_FIELDS = (
    "lead_name",
    "company_name",
    "company_domain",
    "lead_title",
    "industry",
    "company_size_range",
    "region",
    "company_description",
    "business_signals",
)

MOCK_API_ENRICHMENT: MockEnrichmentData = {
    "papertrail-cafe.example": {
        "industry": "Local hospitality",
        "region": "North America",
    },
    "papertrail cafe": {
        "industry": "Local hospitality",
        "region": "North America",
    },
}

MOCK_SCRAPE_ENRICHMENT: MockEnrichmentData = {
    "papertrail-cafe.example": {
        "company_description": "A small neighborhood cafe with a simple brochure site.",
    },
    "papertrail cafe": {
        "company_description": "A small neighborhood cafe with a simple brochure site.",
    },
}


def process_lead(
    intake: LeadIntake,
    *,
    artifact_dir: Path = RUNS_DIR,
) -> LeadRunResponse:
    started_at = datetime.now(UTC)
    started_timer = perf_counter()
    run_id = uuid4().hex
    profile = profile_from_intake(intake)
    enrichment_steps: list[EnrichmentStep] = []
    thin_data_checks: list[ThinDataCheck] = []

    profile, api_step = run_mock_api_enrichment(profile)
    enrichment_steps.append(api_step)

    first_check = check_thin_data(profile, stage="after_api_enrichment")
    thin_data_checks.append(first_check)

    if first_check.is_thin:
        profile, scrape_step = run_mock_scrape_enrichment(profile)
        enrichment_steps.append(scrape_step)
        thin_data_checks.append(
            check_thin_data(profile, stage="after_scrape_enrichment")
        )

    final_check = thin_data_checks[-1]
    completed_at = datetime.now(UTC)
    artifact_path = build_artifact_path(artifact_dir, started_at, run_id)
    response = LeadRunResponse(
        run_id=run_id,
        status="insufficient_data",
        intake=intake,
        profile=profile,
        enrichment_steps=enrichment_steps,
        thin_data_checks=thin_data_checks,
        missing_critical_fields=final_check.missing_required_fields,
        llm_calls=[],
        timings=RunTimings(
            started_at=started_at.isoformat(),
            completed_at=completed_at.isoformat(),
            duration_ms=round((perf_counter() - started_timer) * 1000, 2),
        ),
        artifact_path=str(artifact_path),
    )
    persist_run_artifact(response, artifact_path)
    log_run_summary(response)
    return response


def log_run_summary(response: LeadRunResponse) -> None:
    message = "lead run completed run_id=%s status=%s enrichment_sources=%s missing=%s"
    args = (
        response.run_id,
        response.status,
        [step.source for step in response.enrichment_steps],
        response.missing_critical_fields,
    )
    logger.info(message, *args)
    server_logger.info(message, *args)


def profile_from_intake(intake: LeadIntake) -> LeadProfile:
    return LeadProfile(**intake.model_dump())


def run_mock_api_enrichment(profile: LeadProfile) -> tuple[LeadProfile, EnrichmentStep]:
    return apply_mock_enrichment(profile, "mock_api", MOCK_API_ENRICHMENT)


def run_mock_scrape_enrichment(
    profile: LeadProfile,
) -> tuple[LeadProfile, EnrichmentStep]:
    return apply_mock_enrichment(profile, "mock_scrape", MOCK_SCRAPE_ENRICHMENT)


def apply_mock_enrichment(
    profile: LeadProfile,
    source: EnrichmentSource,
    enrichment_data: MockEnrichmentData,
) -> tuple[LeadProfile, EnrichmentStep]:
    patch = lookup_mock_data(profile, enrichment_data)
    enriched_profile, fields_added = merge_profile(profile, patch)
    return enriched_profile, EnrichmentStep(
        source=source,
        fields_added=fields_added,
        data=patch,
    )


def lookup_mock_data(
    profile: LeadProfile,
    enrichment_data: MockEnrichmentData,
) -> dict[str, object]:
    for key in lookup_keys(profile):
        if key in enrichment_data:
            return enrichment_data[key]
    return {}


def lookup_keys(profile: LeadProfile) -> list[str]:
    keys = [profile.company_domain, profile.company_name]
    if profile.lead_email and "@" in profile.lead_email:
        keys.append(profile.lead_email.rsplit("@", maxsplit=1)[1])
    return [normalize_lookup_key(key) for key in keys if key]


def normalize_lookup_key(value: str) -> str:
    normalized = value.strip().lower()
    normalized = normalized.removeprefix("https://")
    normalized = normalized.removeprefix("http://")
    normalized = normalized.removeprefix("www.")
    return normalized.rstrip("/")


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


def check_thin_data(
    profile: LeadProfile,
    *,
    stage: ThinDataStage,
) -> ThinDataCheck:
    missing_fields = missing_required_fields(profile)
    return ThinDataCheck(
        stage=stage,
        is_thin=bool(missing_fields),
        missing_required_fields=missing_fields,
    )


def missing_required_fields(profile: LeadProfile) -> list[str]:
    profile_data = profile.model_dump()
    missing_fields: list[str] = []
    for field_name in REQUIRED_PROFILE_FIELDS:
        value = profile_data[field_name]
        if not value:
            missing_fields.append(field_name)
    return missing_fields


def build_artifact_path(artifact_dir: Path, started_at: datetime, run_id: str) -> Path:
    timestamp = started_at.strftime("%Y%m%dT%H%M%S%fZ")
    return artifact_dir / f"{timestamp}_{run_id}.json"


def persist_run_artifact(response: LeadRunResponse, artifact_path: Path) -> None:
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_text(
        json.dumps(response.model_dump(mode="json"), indent=2) + "\n",
        encoding="utf-8",
    )
