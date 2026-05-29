import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from dotenv import dotenv_values

DEFAULT_DOTENV_PATH = Path(__file__).resolve().parents[2] / ".env"


@dataclass(frozen=True)
class LLMSettings:
    provider: str = "fake"
    model: str | None = None
    openai_api_key: str | None = None
    openrouter_api_key: str | None = None


def load_llm_settings(
    *,
    env: Mapping[str, str] | None = None,
    dotenv_path: Path | None = DEFAULT_DOTENV_PATH,
) -> LLMSettings:
    env_values = os.environ if env is None else env
    dotenv_env = read_dotenv(dotenv_path)

    return LLMSettings(
        provider=config_value("LLM_PROVIDER", env_values, dotenv_env) or "fake",
        model=config_value("LLM_MODEL", env_values, dotenv_env),
        openai_api_key=config_value("OPENAI_API_KEY", env_values, dotenv_env),
        openrouter_api_key=config_value("OPENROUTER_API_KEY", env_values, dotenv_env),
    )


def read_dotenv(dotenv_path: Path | None) -> dict[str, str]:
    if dotenv_path is None or not dotenv_path.exists():
        return {}
    return {
        key: value
        for key, value in dotenv_values(dotenv_path).items()
        if value is not None
    }


def config_value(
    name: str,
    env: Mapping[str, str],
    dotenv_env: Mapping[str, str],
) -> str | None:
    return env.get(name) or dotenv_env.get(name)
