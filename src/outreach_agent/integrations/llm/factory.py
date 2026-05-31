from collections.abc import Callable
from dataclasses import dataclass

from outreach_agent.integrations.llm.config import LLMSettings
from outreach_agent.integrations.llm.providers import (
    ChatCompletionRawLLMProvider,
    OpenAIRawLLMProvider,
    OpenRouterRawLLMProvider,
)
from outreach_agent.integrations.llm_validation import ValidatingLLMProvider
from outreach_agent.protocols import llm as _llm_protocols


class LLMConfigurationError(ValueError):
    pass


@dataclass(frozen=True)
class RealProviderSpec:
    raw_provider: type[ChatCompletionRawLLMProvider]
    api_key: Callable[[LLMSettings], str | None]
    api_key_name: str
    default_model: str


REAL_PROVIDER_SPECS = {
    "openai": RealProviderSpec(
        raw_provider=OpenAIRawLLMProvider,
        api_key=lambda settings: settings.openai_api_key,
        api_key_name="OPENAI_API_KEY",
        default_model="gpt-5.4-mini",
    ),
    "openrouter": RealProviderSpec(
        raw_provider=OpenRouterRawLLMProvider,
        api_key=lambda settings: settings.openrouter_api_key,
        api_key_name="OPENROUTER_API_KEY",
        default_model="deepseek-v4-flash",
    ),
}


def select_llm_provider(settings: LLMSettings) -> _llm_protocols.LLMProvider:
    if settings.provider is None:
        raise LLMConfigurationError("LLM_PROVIDER is required")

    provider_name = settings.provider.lower()

    if provider_name == "fake":
        raise LLMConfigurationError(
            "The fake LLM provider is not available through config; "
            "inject a test LLMProvider directly in tests instead"
        )

    provider_spec = REAL_PROVIDER_SPECS.get(provider_name)

    if not provider_spec:
        raise ValueError(f"Unsupported LLM_PROVIDER for this slice: {provider_name}")

    api_key = provider_spec.api_key(settings)

    if not api_key:
        raise LLMConfigurationError(
            f"{provider_spec.api_key_name} is required when "
            f"LLM_PROVIDER={provider_name}"
        )

    return ValidatingLLMProvider(
        provider_spec.raw_provider(
            api_key=api_key,
            model=settings.model or provider_spec.default_model,
        )
    )
