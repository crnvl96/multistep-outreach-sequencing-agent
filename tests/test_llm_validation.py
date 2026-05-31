import asyncio
import json
from pathlib import Path
from typing import Any

from outreach_agent.domain.models import (
    IcpScore,
    LeadIntake,
    LeadProfile,
    Route,
    SequencePlan,
)
from outreach_agent.integrations.llm_validation import ValidatingLLMProvider
from outreach_agent.integrations.mock_api_enrichment import MockAPIEnrichmentProvider
from outreach_agent.integrations.mock_scrape_enrichment import (
    MockScrapeEnrichmentProvider,
)
from outreach_agent.protocols.llm import RawLLMProvider
from outreach_agent.workflow import process_lead


def hot_intake() -> LeadIntake:
    return LeadIntake(
        lead_name="Morgan Lee",
        company_name="NimbusForge AI",
        company_domain="nimbusforge.ai",
    )


def valid_score() -> dict[str, Any]:
    return {
        "score": 92,
        "confidence": "high",
        "positive_evidence": ["Strong software ICP fit"],
        "negative_evidence": [],
        "missing_evidence": [],
        "reasoning": "Strong fit for the target ICP.",
    }


def valid_email() -> dict[str, Any]:
    return {
        "subject": "Reducing manual outbound research",
        "body": "Hi Morgan, saw the outbound scaling signals.",
        "cta": "Open to a quick conversation?",
        "personalization_notes": ["Referenced deterministic route."],
    }


class ScriptedRepairProvider(RawLLMProvider):
    def __init__(
        self,
        *,
        score_output: object = None,
        score_repair_output: object = None,
        email_output: object = None,
        email_repair_output: object = None,
    ) -> None:
        self.score_output = valid_score() if score_output is None else score_output
        self.score_repair_output = (
            valid_score() if score_repair_output is None else score_repair_output
        )
        self.email_output = valid_email() if email_output is None else email_output
        self.email_repair_output = (
            valid_email() if email_repair_output is None else email_repair_output
        )
        self.score_repairs = 0
        self.email_repairs = 0
        self.score_repair_prompt = ""
        self.email_repair_prompt = ""

    async def score_icp(self, profile: LeadProfile) -> object:
        return self.score_output

    async def repair_score_icp(
        self,
        profile: LeadProfile,
        invalid_output: object,
        repair_prompt: str,
    ) -> object:
        self.score_repairs += 1
        self.score_repair_prompt = repair_prompt
        return self.score_repair_output

    async def generate_first_email(
        self,
        profile: LeadProfile,
        scoring_result: IcpScore,
        final_route: Route,
        sequence: SequencePlan,
    ) -> object:
        return self.email_output

    async def repair_first_email(
        self,
        profile: LeadProfile,
        scoring_result: IcpScore,
        final_route: Route,
        sequence: SequencePlan,
        invalid_output: object,
        repair_prompt: str,
    ) -> object:
        self.email_repairs += 1
        self.email_repair_prompt = repair_prompt
        return self.email_repair_output



def test_invalid_scoring_output_is_repaired_once_and_recorded(
    tmp_path: Path,
) -> None:
    provider = ScriptedRepairProvider(
        score_output="{not valid json",
        score_repair_output=json.dumps(valid_score()),
    )

    response = asyncio.run(
        process_lead(
            hot_intake(),
            artifact_dir=tmp_path,
            api_enrichment_provider=MockAPIEnrichmentProvider(),
            scrape_enrichment_provider=MockScrapeEnrichmentProvider(),
            llm_provider=ValidatingLLMProvider(provider),
        )
    )

    assert response.status == "routed"
    assert response.scoring_result
    assert response.scoring_result.score == 92
    assert provider.score_repairs == 1
    assert provider.email_repairs == 0
    assert "Return only valid JSON" in provider.score_repair_prompt
    assert response.llm_calls == [
        "score_icp",
        "repair_score_icp",
        "generate_first_email",
    ]
    assert [repair.model_dump() for repair in response.llm_repairs] == [
        {
            "call": "score_icp",
            "attempt_number": 1,
            "status": "repaired",
        }
    ]

    artifact_path = Path(response.artifact_path)
    assert artifact_path.exists()
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    assert artifact["status"] == "routed"
    assert artifact["llm_repairs"] == [
        {
            "call": "score_icp",
            "attempt_number": 1,
            "status": "repaired",
        }
    ]


def test_invalid_email_output_is_repaired_once_and_recorded(
    tmp_path: Path,
) -> None:
    provider = ScriptedRepairProvider(
        email_output={"subject": "Missing required email fields"},
        email_repair_output=json.dumps(valid_email()),
    )

    response = asyncio.run(
        process_lead(
            hot_intake(),
            artifact_dir=tmp_path,
            api_enrichment_provider=MockAPIEnrichmentProvider(),
            scrape_enrichment_provider=MockScrapeEnrichmentProvider(),
            llm_provider=ValidatingLLMProvider(provider),
        )
    )

    assert response.status == "routed"
    assert response.generated_email
    assert response.generated_email.subject == "Reducing manual outbound research"
    assert provider.score_repairs == 0
    assert provider.email_repairs == 1
    assert "Return only valid JSON" in provider.email_repair_prompt
    assert response.llm_calls == [
        "score_icp",
        "generate_first_email",
        "repair_first_email",
    ]
    assert [repair.model_dump() for repair in response.llm_repairs] == [
        {
            "call": "generate_first_email",
            "attempt_number": 1,
            "status": "repaired",
        }
    ]

    artifact_path = Path(response.artifact_path)
    assert artifact_path.exists()
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    assert artifact["status"] == "routed"
    assert artifact["llm_repairs"] == [
        {
            "call": "generate_first_email",
            "attempt_number": 1,
            "status": "repaired",
        }
    ]


def test_failed_scoring_repair_returns_error_and_persists_artifact(
    tmp_path: Path,
) -> None:
    provider = ScriptedRepairProvider(
        score_output={"score": 92},
        score_repair_output={"score": "still invalid"},
    )

    response = asyncio.run(
        process_lead(
            hot_intake(),
            artifact_dir=tmp_path,
            api_enrichment_provider=MockAPIEnrichmentProvider(),
            scrape_enrichment_provider=MockScrapeEnrichmentProvider(),
            llm_provider=ValidatingLLMProvider(provider),
        )
    )

    assert response.status == "llm_output_invalid"
    assert response.error
    assert response.error.code == "llm_output_invalid"
    assert response.error.failed_step == "score_icp"
    assert provider.score_repairs == 1
    assert response.llm_calls == ["score_icp", "repair_score_icp"]
    assert [repair.model_dump() for repair in response.llm_repairs] == [
        {
            "call": "score_icp",
            "attempt_number": 1,
            "status": "failed",
        }
    ]
    assert response.scoring_result is None
    assert response.final_route is None
    assert response.generated_email is None

    artifact_path = Path(response.artifact_path)
    assert artifact_path.exists()
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    assert artifact["status"] == "llm_output_invalid"
    assert artifact["error"]["code"] == "llm_output_invalid"
    assert artifact["error"]["failed_step"] == "score_icp"
    assert artifact["llm_calls"] == ["score_icp", "repair_score_icp"]


def test_failed_email_repair_returns_error_and_persists_decision_chain(
    tmp_path: Path,
) -> None:
    provider = ScriptedRepairProvider(
        email_output="not json",
        email_repair_output={"subject": "Still missing required email fields"},
    )

    response = asyncio.run(
        process_lead(
            hot_intake(),
            artifact_dir=tmp_path,
            api_enrichment_provider=MockAPIEnrichmentProvider(),
            scrape_enrichment_provider=MockScrapeEnrichmentProvider(),
            llm_provider=ValidatingLLMProvider(provider),
        )
    )

    assert response.status == "llm_output_invalid"
    assert response.error
    assert response.error.code == "llm_output_invalid"
    assert response.error.failed_step == "generate_first_email"
    assert provider.email_repairs == 1
    assert response.llm_calls == [
        "score_icp",
        "generate_first_email",
        "repair_first_email",
    ]
    assert [repair.model_dump() for repair in response.llm_repairs] == [
        {
            "call": "generate_first_email",
            "attempt_number": 1,
            "status": "failed",
        }
    ]
    assert response.scoring_result
    assert response.scoring_result.score == 92
    assert response.final_route == "hot"
    assert response.selected_sequence
    assert response.selected_sequence.route == "hot"
    assert response.generated_email is None

    artifact_path = Path(response.artifact_path)
    assert artifact_path.exists()
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    assert artifact["status"] == "llm_output_invalid"
    assert artifact["error"]["code"] == "llm_output_invalid"
    assert artifact["error"]["failed_step"] == "generate_first_email"
    assert artifact["scoring_result"]["score"] == 92
    assert artifact["final_route"] == "hot"
    assert artifact["selected_sequence"]["route"] == "hot"
    assert artifact["generated_email"] is None
