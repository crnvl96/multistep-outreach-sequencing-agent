from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


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


class RunTimings(BaseModel):
    started_at: str
    completed_at: str
    duration_ms: float


class LeadRunResponse(BaseModel):
    run_id: str
    status: Literal["insufficient_data"]
    intake: LeadIntake
    profile: LeadProfile
    enrichment_steps: list[EnrichmentStep]
    thin_data_checks: list[ThinDataCheck]
    missing_critical_fields: list[str]
    llm_calls: list[str] = Field(default_factory=list)
    timings: RunTimings
    artifact_path: str
