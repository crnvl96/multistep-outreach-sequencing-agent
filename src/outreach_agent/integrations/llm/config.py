from dataclasses import dataclass
from pathlib import Path

from dotenv import dotenv_values

DEFAULT_DOTENV_PATH = Path(__file__).resolve().parents[4] / ".env"


@dataclass(frozen=True)
class LLMSettings:
    provider: str | None = None
    model: str | None = None
    openai_api_key: str | None = None
    openrouter_api_key: str | None = None


def read_dotenv(dotenv_path: Path) -> dict[str, str]:
    if not dotenv_path.exists():
        return {}
    return {
        key: value
        for key, value in dotenv_values(dotenv_path).items()
        if value is not None
    }


def load_llm_settings(
    *,
    dotenv_path: Path = DEFAULT_DOTENV_PATH,
) -> LLMSettings:
    dotenv_env = read_dotenv(dotenv_path)

    return LLMSettings(
        provider=dotenv_env.get("LLM_PROVIDER"),
        model=dotenv_env.get("LLM_MODEL"),
        openai_api_key=dotenv_env.get("OPENAI_API_KEY"),
        openrouter_api_key=dotenv_env.get("OPENROUTER_API_KEY"),
    )
