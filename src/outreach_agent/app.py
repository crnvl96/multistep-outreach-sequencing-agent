from pathlib import Path

from fastapi import FastAPI

from outreach_agent.enrichment import (
    MockAPI,
    MockScrape,
)
from outreach_agent.llm import OpenAI, create_openai_client, load_llm_settings
from outreach_agent.models import LeadIntake, LeadRunResponse
from outreach_agent.workflow import RUNS_DIR, process_lead


def create_app(
    *,
    artifact_dir: Path = RUNS_DIR,
    api: MockAPI | None = None,
    scrape: MockScrape | None = None,
    openai: OpenAI | None = None,
) -> FastAPI:
    app = FastAPI(title="Multistep Outreach Sequencing Agent")

    selected_openai = openai
    selected_api = api or MockAPI()
    selected_scrape = scrape or MockScrape()

    if selected_openai is None:
        selected_llm_settings = load_llm_settings()
        selected_openai = create_openai_client(selected_llm_settings)

    @app.post("/leads", response_model=LeadRunResponse)
    async def receive_lead(lead: LeadIntake) -> LeadRunResponse:
        return await process_lead(
            lead,
            artifact_dir=artifact_dir,
            api=selected_api,
            scrape=selected_scrape,
            openai=selected_openai,
        )

    return app
