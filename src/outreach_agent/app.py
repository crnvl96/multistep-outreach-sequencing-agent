from pathlib import Path

from fastapi import FastAPI

from outreach_agent.models import LeadIntake, LeadRunResponse
from outreach_agent.workflow import RUNS_DIR, process_lead


def create_app(*, artifact_dir: Path = RUNS_DIR) -> FastAPI:
    app = FastAPI(title="Multistep Outreach Sequencing Agent")

    @app.post("/leads", response_model=LeadRunResponse)
    async def receive_lead(lead: LeadIntake) -> LeadRunResponse:
        return process_lead(lead, artifact_dir=artifact_dir)

    return app


app = create_app()
