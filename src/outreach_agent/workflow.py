import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from typing import Literal
from uuid import uuid4

from outreach_agent.domain.models import (
    EnrichmentStep,
    GeneratedEmail,
    IcpScore,
    LeadIntake,
    LeadProfile,
    LeadRunResponse,
    LLMRepairAttempt,
    PlannedTouch,
    Route,
    RunError,
    RunTimings,
    SequencePlan,
    ThinDataCheck,
)
from outreach_agent.fixtures import apply_mock_enrichment, build_mock_enrichment_map
from outreach_agent.protocols.enrichment import APIEnrichmentProvider
from outreach_agent.protocols.llm import LLMOutputInvalidError, LLMProvider

logger = logging.getLogger(__name__)
server_logger = logging.getLogger("uvicorn.error")

ThinDataStage = Literal["after_api_enrichment", "after_scrape_enrichment"]


@dataclass(frozen=True)
class LLMPhaseOutcome:
    status: Literal["routed", "llm_output_invalid"]
    llm_calls: list[str]
    llm_repairs: list[LLMRepairAttempt]
    scoring_result: IcpScore | None = None
    final_route: Route | None = None
    selected_sequence: SequencePlan | None = None
    generated_email: GeneratedEmail | None = None
    error: RunError | None = None


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

MOCK_SCRAPE_ENRICHMENT = build_mock_enrichment_map("scrape")

SEQUENCES_BY_ROUTE: dict[Route, SequencePlan] = {
    "hot": SequencePlan(
        route="hot",
        name="Hot sequence",
        style=(
            "High-priority, concise, highly personalized, direct CTA focused on "
            "urgent GTM or revenue workflow pain."
        ),
        planned_touches=[
            PlannedTouch(
                touch_number=1,
                timing="day 0",
                channel="email",
                goal="Lead with the strongest GTM pain signal and ask for a meeting.",
            ),
            PlannedTouch(
                touch_number=2,
                timing="day 2",
                channel="email",
                goal="Reinforce urgency with a relevant outbound workflow angle.",
            ),
            PlannedTouch(
                touch_number=3,
                timing="day 5",
                channel="email",
                goal="Offer a concise proof point and direct next step.",
            ),
        ],
    ),
    "warm": SequencePlan(
        route="warm",
        name="Warm sequence",
        style=(
            "Consultative, educational, moderate CTA focused on relevance and "
            "potential fit."
        ),
        planned_touches=[
            PlannedTouch(
                touch_number=1,
                timing="day 0",
                channel="email",
                goal="Share a relevant observation and invite a light conversation.",
            ),
            PlannedTouch(
                touch_number=2,
                timing="day 4",
                channel="email",
                goal="Offer a useful GTM workflow angle tied to the observed signals.",
            ),
            PlannedTouch(
                touch_number=3,
                timing="day 9",
                channel="email",
                goal="Ask whether improving outbound qualification is a priority.",
            ),
        ],
    ),
    "cold": SequencePlan(
        route="cold",
        name="Cold sequence",
        style=(
            "Light-touch, permission-based, low-pressure CTA focused on "
            "confirming whether the topic matters."
        ),
        planned_touches=[
            PlannedTouch(
                touch_number=1,
                timing="day 0",
                channel="email",
                goal="Ask permission to confirm whether GTM workflow pain is relevant.",
            ),
            PlannedTouch(
                touch_number=2,
                timing="day 7",
                channel="email",
                goal="Offer an easy opt-out if the topic is not relevant.",
            ),
            PlannedTouch(
                touch_number=3,
                timing="day 14",
                channel="email",
                goal="Close the loop with a low-pressure relevance check.",
            ),
        ],
    ),
}


async def process_lead(
    intake: LeadIntake,
    *,
    artifact_dir: Path = RUNS_DIR,
    api_enrichment_provider: APIEnrichmentProvider,
    llm_provider: LLMProvider,
) -> LeadRunResponse:
    started_at = datetime.now(UTC)
    started_timer = perf_counter()
    run_id = uuid4().hex

    enrichment_steps: list[EnrichmentStep] = []
    thin_data_checks: list[ThinDataCheck] = []

    profile = LeadProfile(**intake.model_dump())

    profile, api_step = await api_enrichment_provider.enrich(profile)
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
    missing_critical_fields = final_check.missing_required_fields
    llm_calls: list[str] = []
    llm_repairs: list[LLMRepairAttempt] = []
    scoring_result: IcpScore | None = None
    final_route: Route | None = None
    selected_sequence: SequencePlan | None = None
    generated_email: GeneratedEmail | None = None
    error: RunError | None = None
    status: Literal[
        "insufficient_data",
        "routed",
        "llm_output_invalid",
    ] = "insufficient_data"

    if not final_check.is_thin:
        llm_phase = await run_llm_phase(profile, llm_provider)
        status = llm_phase.status
        llm_calls = llm_phase.llm_calls
        llm_repairs = llm_phase.llm_repairs
        scoring_result = llm_phase.scoring_result
        final_route = llm_phase.final_route
        selected_sequence = llm_phase.selected_sequence
        generated_email = llm_phase.generated_email
        error = llm_phase.error

    completed_at = datetime.now(UTC)
    artifact_path = build_artifact_path(artifact_dir, started_at, run_id)
    response = LeadRunResponse(
        run_id=run_id,
        status=status,
        intake=intake,
        profile=profile,
        enrichment_steps=enrichment_steps,
        thin_data_checks=thin_data_checks,
        missing_critical_fields=missing_critical_fields,
        llm_calls=llm_calls,
        llm_repairs=llm_repairs,
        scoring_result=scoring_result,
        final_route=final_route,
        selected_sequence=selected_sequence,
        generated_email=generated_email,
        error=error,
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


async def run_llm_phase(
    profile: LeadProfile,
    llm_provider: LLMProvider,
) -> LLMPhaseOutcome:
    llm_calls: list[str] = []
    llm_repairs: list[LLMRepairAttempt] = []
    scoring_result: IcpScore | None = None
    final_route: Route | None = None
    selected_sequence: SequencePlan | None = None

    try:
        score_call = await llm_provider.score_icp(profile)
        llm_calls.extend(score_call.calls)
        llm_repairs.extend(score_call.repairs)
        scoring_result = score_call.value

        final_route = route_from_score(scoring_result)
        selected_sequence = select_sequence(final_route)

        email_call = await llm_provider.generate_first_email(
            profile,
            scoring_result,
            final_route,
            selected_sequence,
        )
        llm_calls.extend(email_call.calls)
        llm_repairs.extend(email_call.repairs)
        return LLMPhaseOutcome(
            status="routed",
            llm_calls=llm_calls,
            llm_repairs=llm_repairs,
            scoring_result=scoring_result,
            final_route=final_route,
            selected_sequence=selected_sequence,
            generated_email=email_call.value,
        )
    except LLMOutputInvalidError as exc:
        llm_calls.extend(exc.calls)
        llm_repairs.extend(exc.repairs)
        return LLMPhaseOutcome(
            status="llm_output_invalid",
            llm_calls=llm_calls,
            llm_repairs=llm_repairs,
            scoring_result=scoring_result,
            final_route=final_route,
            selected_sequence=selected_sequence,
            error=RunError(
                code="llm_output_invalid",
                failed_step=exc.call,
                message=str(exc),
            ),
        )


def route_from_score(scoring_result: IcpScore) -> Route:
    if scoring_result.score >= 80:
        if scoring_result.confidence != "low":
            return "hot"
        return "warm"
    if scoring_result.score >= 50:
        return "warm"
    return "cold"


def select_sequence(route: Route) -> SequencePlan:
    try:
        return SEQUENCES_BY_ROUTE[route]
    except KeyError as exc:
        raise ValueError(f"No sequence plan implemented for route: {route}") from exc


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


def run_mock_scrape_enrichment(
    profile: LeadProfile,
) -> tuple[LeadProfile, EnrichmentStep]:
    return apply_mock_enrichment(profile, "scrape", MOCK_SCRAPE_ENRICHMENT)


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
