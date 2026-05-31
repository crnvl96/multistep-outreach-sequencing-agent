import json

from outreach_agent.llm.prompts import (
    ICP_DEFINITION,
    build_email_messages,
    build_repair_messages,
    build_scoring_messages,
)
from outreach_agent.models import IcpScore, LeadProfile
from outreach_agent.workflow import select_sequence


def complete_profile() -> LeadProfile:
    return LeadProfile(
        lead_name="Morgan Lee",
        company_name="NimbusForge AI",
        company_domain="nimbusforge.ai",
        lead_title="VP Sales",
        industry="B2B SaaS",
        company_size_range="201-500 employees",
        region="North America",
        company_description="AI workflow software for revenue teams.",
        business_signals=["Scaling outbound sales", "RevOps hiring"],
    )


def valid_score() -> dict[str, object]:
    return {
        "score": 92,
        "confidence": "high",
        "positive_evidence": ["Strong software ICP fit"],
        "negative_evidence": [],
        "missing_evidence": [],
        "reasoning": "Strong fit for the target ICP.",
    }


def test_build_scoring_messages_includes_icp_profile_and_json_contract() -> None:
    profile = complete_profile()
    messages = build_scoring_messages(profile)

    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"

    user_prompt = messages[1]["content"]
    assert f"Documented ICP:\n{ICP_DEFINITION}" in user_prompt
    assert (
        json.dumps(profile.model_dump(mode="json"), sort_keys=True, indent=2)
        in user_prompt
    )
    assert "Return strict structured JSON matching this schema:" in user_prompt
    assert "positive_evidence" in user_prompt
    assert "NimbusForge AI" in user_prompt
    assert "Scaling outbound sales" in user_prompt


def test_build_email_messages_includes_route_sequence_scoring_and_schema() -> None:
    profile = complete_profile()
    scoring_result = IcpScore.model_validate(valid_score())
    sequence = select_sequence("hot")

    messages = build_email_messages(profile, scoring_result, "hot", sequence)

    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"

    user_prompt = messages[1]["content"]
    assert "Final deterministic route: hot" in user_prompt
    assert sequence.style in user_prompt
    assert "Selected sequence plan:" in user_prompt
    assert (
        json.dumps(sequence.model_dump(mode="json"), sort_keys=True, indent=2)
        in user_prompt
    )
    assert (
        json.dumps(profile.model_dump(mode="json"), sort_keys=True, indent=2)
        in user_prompt
    )
    assert (
        json.dumps(scoring_result.model_dump(mode="json"), sort_keys=True, indent=2)
        in user_prompt
    )
    assert (
        "Do not invent facts beyond the lead profile and scoring context."
        in messages[0]["content"]
    )
    assert "Generate only the first email" in user_prompt
    assert "personalization_notes" in user_prompt


def test_build_repair_messages_appends_invalid_output_then_prompt() -> None:
    original_messages = [
        {"role": "system", "content": "system"},
        {"role": "user", "content": "user"},
    ]
    invalid_output = {"error": "invalid"}
    repair_prompt = "Please fix the output"

    messages = build_repair_messages(original_messages, invalid_output, repair_prompt)

    assert len(messages) == 4
    assert messages[:2] == original_messages
    assert messages[2] == {
        "role": "assistant",
        "content": json.dumps(invalid_output, indent=2, sort_keys=True),
    }
    assert messages[3] == {"role": "user", "content": repair_prompt}
