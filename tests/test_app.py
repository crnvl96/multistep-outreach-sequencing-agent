import json
import logging
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from outreach_agent.app import create_app
from outreach_agent.llm import LLMSettings
from support.fake_llm import FakeLLMProvider


def test_create_app_selects_default_provider_at_startup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "outreach_agent.app.load_llm_settings",
        lambda: LLMSettings(provider="unsupported"),
    )

    with pytest.raises(ValueError, match="Unsupported LLM_PROVIDER"):
        create_app(artifact_dir=tmp_path)


def test_create_app_accepts_configured_default_provider_at_startup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "outreach_agent.app.load_llm_settings",
        lambda: LLMSettings(provider="openai", openai_api_key="test-openai-key"),
    )
    client = TestClient(create_app(artifact_dir=tmp_path))

    response = client.post(
        "/leads",
        json={
            "lead_name": "Riley Stone",
            "company_name": "PaperTrail Cafe",
            "company_domain": "papertrail-cafe.example",
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "insufficient_data"


def test_post_leads_routes_hot_fixture_with_fake_llm(
    tmp_path: Path,
) -> None:
    client = TestClient(
        create_app(artifact_dir=tmp_path, llm_provider=FakeLLMProvider())
    )
    payload = {
        "lead_name": "Morgan Lee",
        "company_name": "NimbusForge AI",
        "company_domain": "nimbusforge.ai",
    }

    response = client.post("/leads", json=payload)

    assert response.status_code == 200
    data: dict[str, Any] = response.json()
    assert data["status"] == "routed"
    assert data["final_route"] == "hot"
    assert data["llm_calls"] == ["score_icp", "generate_first_email"]

    assert [step["source"] for step in data["enrichment_steps"]] == ["api"]
    assert data["thin_data_checks"] == [
        {
            "stage": "after_api_enrichment",
            "is_thin": False,
            "missing_required_fields": [],
        }
    ]
    assert data["missing_critical_fields"] == []
    assert data["profile"]["lead_title"] == "VP Sales"
    assert data["profile"]["business_signals"]

    scoring = data["scoring_result"]
    assert scoring["score"] == 92
    assert scoring["confidence"] == "high"
    assert scoring["positive_evidence"]
    assert scoring["negative_evidence"] == []
    assert scoring["missing_evidence"] == []
    assert scoring["reasoning"]
    assert "route" not in scoring

    sequence = data["selected_sequence"]
    assert sequence["route"] == "hot"
    assert sequence["name"] == "Hot sequence"
    assert sequence["planned_touches"]
    assert all("timing" in touch for touch in sequence["planned_touches"])

    email = data["generated_email"]
    assert email["subject"]
    assert email["body"]
    assert email["cta"]
    assert email["personalization_notes"]

    artifact_path = Path(data["artifact_path"])
    assert artifact_path.exists()
    assert json.loads(artifact_path.read_text(encoding="utf-8")) == data


def test_post_leads_routes_warm_fixture_after_scrape_fallback(
    tmp_path: Path,
) -> None:
    client = TestClient(
        create_app(artifact_dir=tmp_path, llm_provider=FakeLLMProvider())
    )
    payload = {
        "lead_name": "Jordan Park",
        "company_name": "SignalSpring Software",
        "company_domain": "signalspring.io",
    }

    response = client.post("/leads", json=payload)

    assert response.status_code == 200
    data: dict[str, Any] = response.json()
    assert data["status"] == "routed"
    assert data["final_route"] == "warm"
    assert data["llm_calls"] == ["score_icp", "generate_first_email"]

    assert [step["source"] for step in data["enrichment_steps"]] == [
        "api",
        "scrape",
    ]
    assert [check["stage"] for check in data["thin_data_checks"]] == [
        "after_api_enrichment",
        "after_scrape_enrichment",
    ]
    first_check = data["thin_data_checks"][0]
    assert first_check["is_thin"] is True
    assert first_check["missing_required_fields"] == [
        "company_description",
        "business_signals",
    ]
    second_check = data["thin_data_checks"][1]
    assert second_check == {
        "stage": "after_scrape_enrichment",
        "is_thin": False,
        "missing_required_fields": [],
    }
    assert data["missing_critical_fields"] == []
    assert data["profile"]["company_description"]
    assert data["profile"]["business_signals"]

    scoring = data["scoring_result"]
    assert scoring["score"] == 68
    assert scoring["confidence"] == "medium"
    assert scoring["positive_evidence"]
    assert scoring["negative_evidence"] == []
    assert scoring["missing_evidence"]

    sequence = data["selected_sequence"]
    assert sequence["route"] == "warm"
    assert sequence["name"] == "Warm sequence"
    assert sequence["planned_touches"]
    assert all("timing" in touch for touch in sequence["planned_touches"])

    email = data["generated_email"]
    assert "worth comparing notes" in email["subject"].lower()
    assert "useful" in email["body"].lower()
    assert "worth a brief conversation" in email["cta"].lower()
    assert email["personalization_notes"]

    artifact_path = Path(data["artifact_path"])
    assert artifact_path.exists()
    assert json.loads(artifact_path.read_text(encoding="utf-8")) == data


def test_post_leads_routes_cold_fixture_with_low_pressure_email(
    tmp_path: Path,
) -> None:
    client = TestClient(
        create_app(artifact_dir=tmp_path, llm_provider=FakeLLMProvider())
    )
    payload = {
        "lead_name": "Casey Morgan",
        "company_name": "GreenFork Catering",
        "company_domain": "greenfork-catering.example",
    }

    response = client.post("/leads", json=payload)

    assert response.status_code == 200
    data: dict[str, Any] = response.json()
    assert data["status"] == "routed"
    assert data["final_route"] == "cold"
    assert data["llm_calls"] == ["score_icp", "generate_first_email"]
    assert [step["source"] for step in data["enrichment_steps"]] == ["api"]
    assert data["thin_data_checks"] == [
        {
            "stage": "after_api_enrichment",
            "is_thin": False,
            "missing_required_fields": [],
        }
    ]
    assert data["missing_critical_fields"] == []

    scoring = data["scoring_result"]
    assert scoring["score"] < 50
    assert scoring["positive_evidence"]
    assert scoring["negative_evidence"]
    assert scoring["missing_evidence"]
    assert "weak icp fit" in scoring["reasoning"].lower()
    assert "route" not in scoring

    sequence = data["selected_sequence"]
    assert sequence["route"] == "cold"
    assert sequence["name"] == "Cold sequence"
    assert "light-touch" in sequence["style"].lower()
    assert "permission-based" in sequence["style"].lower()
    assert "low-pressure" in sequence["style"].lower()
    assert sequence["planned_touches"]
    assert all("timing" in touch for touch in sequence["planned_touches"])

    email = data["generated_email"]
    assert "checking" in email["subject"].lower()
    assert "if this is not a priority" in email["body"].lower()
    assert "worth exploring" in email["cta"].lower()
    assert email["personalization_notes"]

    artifact_path = Path(data["artifact_path"])
    assert artifact_path.exists()
    assert json.loads(artifact_path.read_text(encoding="utf-8")) == data


def test_post_leads_returns_insufficient_data_decision_chain(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    client = TestClient(
        create_app(artifact_dir=tmp_path, llm_provider=FakeLLMProvider())
    )
    payload = {
        "lead_name": "Riley Stone",
        "company_name": "PaperTrail Cafe",
        "company_domain": "papertrail-cafe.example",
    }

    with caplog.at_level(logging.INFO, logger="outreach_agent.workflow"):
        response = client.post("/leads", json=payload)

    assert response.status_code == 200
    data: dict[str, Any] = response.json()
    assert data["status"] == "insufficient_data"
    for key, value in payload.items():
        assert data["intake"][key] == value
    assert data["llm_calls"] == []

    assert [step["source"] for step in data["enrichment_steps"]] == [
        "api",
        "scrape",
    ]
    assert [check["stage"] for check in data["thin_data_checks"]] == [
        "after_api_enrichment",
        "after_scrape_enrichment",
    ]
    assert data["thin_data_checks"][0]["is_thin"] is True
    assert data["thin_data_checks"][1]["is_thin"] is True
    assert (
        "company_description" in data["thin_data_checks"][0]["missing_required_fields"]
    )
    assert "company_description" not in data["missing_critical_fields"]
    assert data["missing_critical_fields"] == [
        "lead_title",
        "company_size_range",
        "business_signals",
    ]
    assert data["timings"]["duration_ms"] >= 0

    artifact_path = Path(data["artifact_path"])
    assert artifact_path.exists()
    assert json.loads(artifact_path.read_text(encoding="utf-8")) == data
    assert "lead run completed" in caplog.text
    assert "insufficient_data" in caplog.text


@pytest.mark.parametrize(
    "payload",
    [
        {
            "company_name": "PaperTrail Cafe",
            "company_domain": "papertrail-cafe.example",
        },
        {
            "lead_name": "Riley Stone",
            "company_domain": "papertrail-cafe.example",
        },
        {
            "lead_name": "Riley Stone",
            "company_name": "PaperTrail Cafe",
        },
    ],
)
def test_post_leads_rejects_invalid_payloads(
    tmp_path: Path,
    payload: dict[str, str],
) -> None:
    client = TestClient(
        create_app(artifact_dir=tmp_path, llm_provider=FakeLLMProvider())
    )

    response = client.post("/leads", json=payload)

    assert response.status_code == 422
    assert response.json()["detail"]
