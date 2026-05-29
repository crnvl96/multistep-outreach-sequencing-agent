from pathlib import Path

from fastapi import FastAPI

from outreach_agent.llm import select_llm_provider
from outreach_agent.llm_validation import LLMProvider
from outreach_agent.models import LeadIntake, LeadRunResponse
from outreach_agent.workflow import RUNS_DIR, process_lead


def create_app(
    *,
    artifact_dir: Path = RUNS_DIR,
    llm_provider: LLMProvider | None = None,
) -> FastAPI:
    app = FastAPI(title="Multistep Outreach Sequencing Agent")
    selected_llm_provider = llm_provider or select_llm_provider()

    @app.post("/leads", response_model=LeadRunResponse)
    async def receive_lead(lead: LeadIntake) -> LeadRunResponse:
        return await process_lead(
            lead,
            artifact_dir=artifact_dir,
            llm_provider=selected_llm_provider,
        )

    return app


app = create_app()
