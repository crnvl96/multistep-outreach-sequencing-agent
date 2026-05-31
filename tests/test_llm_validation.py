import asyncio
import json
from pathlib import Path
from typing import Any

from outreach_agent.enrichment import (
    MockAPI,
    MockScrape,
)
from outreach_agent.llm import OpenAI
from outreach_agent.models import LeadIntake
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


class ScriptedChatTransport:
    def __init__(self, outputs: list[object]) -> None:
        self.outputs = outputs
        self.score_repairs = 0
        self.email_repairs = 0
        self.score_repair_prompt = ""
        self.email_repair_prompt = ""

    async def create_chat_completion(
        self,
        *,
        endpoint_url: str,
        api_key: str,
        model: str,
        messages: list[dict[str, str]],
    ) -> object:
        repair_prompt = messages[-1]["content"]
        if "Validation error" in repair_prompt:
            if "scoring schema" in repair_prompt:
                self.score_repairs += 1
                self.score_repair_prompt = repair_prompt
            elif "email generation schema" in repair_prompt:
                self.email_repairs += 1
                self.email_repair_prompt = repair_prompt

        output = self.outputs.pop(0)
        return json.dumps(output) if isinstance(output, dict) else output


def openai_with_transport(transport: ScriptedChatTransport) -> OpenAI:
    return OpenAI(
        api_key="test-openai-key",
        model="test-openai-model",
        transport=transport,
    )


def test_invalid_scoring_output_is_repaired_once_and_recorded(
    tmp_path: Path,
) -> None:
    provider = ScriptedChatTransport(
        [
            "{not valid json",
            json.dumps(valid_score()),
            valid_email(),
        ]
    )

    response = asyncio.run(
        process_lead(
            hot_intake(),
            artifact_dir=tmp_path,
            api=MockAPI(),
            scrape=MockScrape(),
            openai=openai_with_transport(provider),
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
    provider = ScriptedChatTransport(
        [
            valid_score(),
            {"subject": "Missing required email fields"},
            json.dumps(valid_email()),
        ]
    )

    response = asyncio.run(
        process_lead(
            hot_intake(),
            artifact_dir=tmp_path,
            api=MockAPI(),
            scrape=MockScrape(),
            openai=openai_with_transport(provider),
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
    provider = ScriptedChatTransport(
        [
            {"score": 92},
            {"score": "still invalid"},
        ]
    )

    response = asyncio.run(
        process_lead(
            hot_intake(),
            artifact_dir=tmp_path,
            api=MockAPI(),
            scrape=MockScrape(),
            openai=openai_with_transport(provider),
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
    provider = ScriptedChatTransport(
        [
            valid_score(),
            "not json",
            {"subject": "Still missing required email fields"},
        ]
    )

    response = asyncio.run(
        process_lead(
            hot_intake(),
            artifact_dir=tmp_path,
            api=MockAPI(),
            scrape=MockScrape(),
            openai=openai_with_transport(provider),
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
