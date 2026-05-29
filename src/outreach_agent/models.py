from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

Route = Literal["hot", "warm", "cold"]
Confidence = Literal["high", "medium", "low"]


class LeadIntake(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    lead_name: str = Field(min_length=1)
    company_name: str = Field(min_length=1)
    company_domain: str | None = None
    lead_email: str | None = None
    lead_title: str | None = None
    linkedin_url: str | None = None
    company_url: str | None = None
    notes: str | None = None

    @model_validator(mode="after")
    def require_domain_or_email(self) -> Self:
        if not self.company_domain and not self.lead_email:
            raise ValueError("Either company_domain or lead_email is required")
        return self


class LeadProfile(BaseModel):
    lead_name: str
    company_name: str
    company_domain: str | None = None
    lead_email: str | None = None
    lead_title: str | None = None
    linkedin_url: str | None = None
    company_url: str | None = None
    notes: str | None = None
    industry: str | None = None
    company_size_range: str | None = None
    region: str | None = None
    company_description: str | None = None
    business_signals: list[str] = Field(default_factory=list)


class EnrichmentStep(BaseModel):
    source: Literal["mock_api", "mock_scrape"]
    status: Literal["completed"] = "completed"
    fields_added: list[str]
    data: dict[str, object]


class ThinDataCheck(BaseModel):
    stage: Literal["after_api_enrichment", "after_scrape_enrichment"]
    is_thin: bool
    missing_required_fields: list[str]


class IcpScore(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    score: int = Field(ge=0, le=100)
    confidence: Confidence
    positive_evidence: list[str]
    negative_evidence: list[str]
    missing_evidence: list[str]
    reasoning: str


class PlannedTouch(BaseModel):
    touch_number: int
    timing: str
    channel: Literal["email"]
    goal: str


class SequencePlan(BaseModel):
    route: Route
    name: str
    style: str
    planned_touches: list[PlannedTouch]


class GeneratedEmail(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    subject: str
    body: str
    cta: str
    personalization_notes: list[str]


class LLMRepairAttempt(BaseModel):
    call: Literal["score_icp", "generate_first_email"]
    attempt_number: int
    status: Literal["repaired", "failed"]


class RunError(BaseModel):
    code: Literal["llm_output_invalid"]
    failed_step: Literal["score_icp", "generate_first_email"]
    message: str


class RunTimings(BaseModel):
    started_at: str
    completed_at: str
    duration_ms: float


class LeadRunResponse(BaseModel):
    run_id: str
    status: Literal["insufficient_data", "routed", "llm_output_invalid"]
    intake: LeadIntake
    profile: LeadProfile
    enrichment_steps: list[EnrichmentStep]
    thin_data_checks: list[ThinDataCheck]
    missing_critical_fields: list[str]
    llm_calls: list[str] = Field(default_factory=list)
    llm_repairs: list[LLMRepairAttempt] = Field(default_factory=list)
    scoring_result: IcpScore | None = None
    final_route: Route | None = None
    selected_sequence: SequencePlan | None = None
    generated_email: GeneratedEmail | None = None
    error: RunError | None = None
    timings: RunTimings
    artifact_path: str
