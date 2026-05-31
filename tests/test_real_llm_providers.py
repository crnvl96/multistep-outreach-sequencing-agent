import asyncio
import json
from pathlib import Path
from typing import Any, cast

import pytest

from outreach_agent.llm import (
    DEFAULT_DOTENV_PATH,
    LLMConfigurationError,
    LLMSettings,
    OpenAIRawLLMProvider,
    ValidatingLLMProvider,
    load_llm_settings,
    select_llm_provider,
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


class RecordingChatTransport:
    def __init__(self, outputs: list[str]) -> None:
        self.outputs = outputs
        self.requests: list[dict[str, object]] = []

    async def create_chat_completion(
        self,
        *,
        endpoint_url: str,
        api_key: str,
        model: str,
        messages: list[dict[str, str]],
    ) -> str:
        self.requests.append(
            {
                "endpoint_url": endpoint_url,
                "api_key": api_key,
                "model": model,
                "messages": messages,
            }
        )
        return self.outputs.pop(0)


def test_openai_provider_selection_uses_configured_model() -> None:
    provider = select_llm_provider(
        LLMSettings(
            provider="openai",
            model="gpt-4.1-mini",
            openai_api_key="test-openai-key",
        )
    )

    assert isinstance(provider, ValidatingLLMProvider)
    assert isinstance(provider.raw_provider, OpenAIRawLLMProvider)
    assert provider.raw_provider.model == "gpt-4.1-mini"


def test_provider_selection_requires_configured_provider() -> None:
    with pytest.raises(LLMConfigurationError, match="LLM_PROVIDER is required"):
        select_llm_provider(LLMSettings())


def test_default_dotenv_points_to_project_root() -> None:
    assert DEFAULT_DOTENV_PATH == Path.cwd() / ".env"


def test_fake_provider_cannot_be_selected_from_config() -> None:
    with pytest.raises(LLMConfigurationError, match="not available through config"):
        select_llm_provider(LLMSettings(provider="fake"))


def test_openai_selection_without_api_key_fails_clearly() -> None:
    with pytest.raises(LLMConfigurationError, match="OPENAI_API_KEY"):
        select_llm_provider(LLMSettings(provider="openai"))


def test_unsupported_provider_fails_clearly() -> None:
    with pytest.raises(ValueError, match="Unsupported LLM_PROVIDER: unsupported"):
        select_llm_provider(LLMSettings(provider="unsupported"))


def test_missing_provider_in_dotenv_has_no_fake_default(tmp_path: Path) -> None:
    dotenv_path = tmp_path / ".env"
    dotenv_path.write_text("OPENAI_API_KEY=dotenv-openai-key\n", encoding="utf-8")

    settings = load_llm_settings(dotenv_path=dotenv_path)

    assert settings.provider is None


def test_provider_selection_reads_dotenv_file(tmp_path: Path) -> None:
    dotenv_path = tmp_path / ".env"
    dotenv_path.write_text(
        "LLM_PROVIDER=openai\n"
        "LLM_MODEL=gpt-5.4-mini\n"
        "OPENAI_API_KEY=dotenv-openai-key\n",
        encoding="utf-8",
    )

    provider = select_llm_provider(load_llm_settings(dotenv_path=dotenv_path))

    assert isinstance(provider, ValidatingLLMProvider)
    assert isinstance(provider.raw_provider, OpenAIRawLLMProvider)
    assert provider.raw_provider.api_key == "dotenv-openai-key"
    assert provider.raw_provider.model == "gpt-5.4-mini"


def test_provider_selection_uses_dotenv_without_environment_override(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "unsupported-provider")
    monkeypatch.setenv("LLM_MODEL", "env-model")
    monkeypatch.setenv("OPENAI_API_KEY", "env-openai-key")

    dotenv_path = tmp_path / ".env"
    dotenv_path.write_text(
        "LLM_PROVIDER=openai\n"
        "LLM_MODEL=dotenv-model\n"
        "OPENAI_API_KEY=dotenv-openai-key\n",
        encoding="utf-8",
    )

    provider = select_llm_provider(load_llm_settings(dotenv_path=dotenv_path))

    assert isinstance(provider, ValidatingLLMProvider)
    assert isinstance(provider.raw_provider, OpenAIRawLLMProvider)
    assert provider.raw_provider.api_key == "dotenv-openai-key"
    assert provider.raw_provider.model == "dotenv-model"


def test_openai_provider_selection_uses_default_model() -> None:
    provider = select_llm_provider(
        LLMSettings(
            provider="openai",
            openai_api_key="test-openai-key",
        )
    )

    assert isinstance(provider, ValidatingLLMProvider)
    assert isinstance(provider.raw_provider, OpenAIRawLLMProvider)
    assert provider.raw_provider.model == "gpt-5.4-mini"


def test_openai_scoring_request_includes_icp_profile_and_strict_json() -> None:
    transport = RecordingChatTransport([json.dumps(valid_score())])
    raw_provider = OpenAIRawLLMProvider(
        api_key="test-openai-key",
        model="gpt-4.1-mini",
        transport=transport,
    )

    result = asyncio.run(
        ValidatingLLMProvider(raw_provider).score_icp(complete_profile())
    )

    assert result.value.score == 92
    assert len(transport.requests) == 1
    request = transport.requests[0]
    assert request["endpoint_url"] == "https://api.openai.com/v1/chat/completions"
    assert request["api_key"] == "test-openai-key"
    assert request["model"] == "gpt-4.1-mini"
    prompt = prompt_text(request)
    assert "B2B SaaS or AI/software companies with 50–500 employees" in prompt
    assert "NimbusForge AI" in prompt
    assert "Scaling outbound sales" in prompt
    assert "Return only valid JSON" in prompt
    assert "positive_evidence" in prompt


def test_openai_email_request_includes_route_sequence_scoring_and_fact_guard() -> None:
    transport = RecordingChatTransport([json.dumps(valid_email())])
    raw_provider = OpenAIRawLLMProvider(
        api_key="test-openai-key",
        model="gpt-4.1-mini",
        transport=transport,
    )
    scoring_result = IcpScore.model_validate(valid_score())
    sequence = select_sequence("hot")

    result = asyncio.run(
        ValidatingLLMProvider(raw_provider).generate_first_email(
            complete_profile(),
            scoring_result,
            "hot",
            sequence,
        )
    )

    assert result.value.subject == "Reducing manual outbound research"
    assert len(transport.requests) == 1
    prompt = prompt_text(transport.requests[0])
    assert "Final deterministic route: hot" in prompt
    assert sequence.style in prompt
    assert "NimbusForge AI" in prompt
    assert "Strong software ICP fit" in prompt
    assert "Do not invent facts" in prompt
    assert "Generate only the first email" in prompt
    assert "personalization_notes" in prompt


def test_real_provider_responses_flow_through_validation_and_repair() -> None:
    transport = RecordingChatTransport(
        [
            json.dumps({"score": 92}),
            json.dumps(valid_score()),
        ]
    )
    raw_provider = OpenAIRawLLMProvider(
        api_key="test-openai-key",
        model="gpt-4.1-mini",
        transport=transport,
    )

    result = asyncio.run(
        ValidatingLLMProvider(raw_provider).score_icp(complete_profile())
    )

    assert result.value.score == 92
    assert result.calls == ("score_icp", "repair_score_icp")
    assert [repair.model_dump() for repair in result.repairs] == [
        {
            "call": "score_icp",
            "attempt_number": 1,
            "status": "repaired",
        }
    ]
    assert len(transport.requests) == 2
    repair_prompt = prompt_text(transport.requests[1])
    assert "Validation error" in repair_prompt
    assert '"score": 92' in repair_prompt


def prompt_text(request: dict[str, object]) -> str:
    messages = request["messages"]
    assert isinstance(messages, list)
    contents: list[str] = []
    for message in messages:
        assert isinstance(message, dict)
        message_payload = cast(dict[str, object], message)
        content = message_payload["content"]
        assert isinstance(content, str)
        contents.append(content)
    return "\n".join(contents)
