from pathlib import Path
from typing import Any

from fastapi import FastAPI

from outreach_agent.enrichment import (
    MockAPIEnrichmentProvider,
    MockScrapeEnrichmentProvider,
)
from outreach_agent.llm import load_llm_settings, select_llm_provider
from outreach_agent.models import LeadIntake, LeadRunResponse
from outreach_agent.workflow import RUNS_DIR, process_lead


def create_app(
    *,
    artifact_dir: Path = RUNS_DIR,
    api_enrichment_provider: Any | None = None,
    scrape_enrichment_provider: Any | None = None,
    llm_provider: Any | None = None,
) -> FastAPI:
    app = FastAPI(title="Multistep Outreach Sequencing Agent")

    selected_llm_provider = llm_provider
    selected_api_enrichment_provider = (
        api_enrichment_provider or MockAPIEnrichmentProvider()
    )
    selected_scrape_enrichment_provider = (
        scrape_enrichment_provider or MockScrapeEnrichmentProvider()
    )

    if selected_llm_provider is None:
        selected_llm_settings = load_llm_settings()
        selected_llm_provider = select_llm_provider(selected_llm_settings)

    @app.post("/leads", response_model=LeadRunResponse)
    async def receive_lead(lead: LeadIntake) -> LeadRunResponse:
        return await process_lead(
            lead,
            artifact_dir=artifact_dir,
            api_enrichment_provider=selected_api_enrichment_provider,
            scrape_enrichment_provider=selected_scrape_enrichment_provider,
            llm_provider=selected_llm_provider,
        )

    return app
