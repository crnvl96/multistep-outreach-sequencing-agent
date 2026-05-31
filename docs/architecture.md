# Architecture Overview

## Flat MVP structure

The codebase keeps the reviewer-facing MVP intentionally small:

- `src/outreach_agent/models.py` owns Pydantic request, response, scoring, route, email, and artifact models.
- `src/outreach_agent/prompts.py` owns scoring, email, and repair prompt builders.
- `src/outreach_agent/enrichment.py` owns deterministic fixture-backed `MockAPI` and `MockScrape` enrichment.
- `src/outreach_agent/llm.py` owns OpenAI configuration, the chat completion client, response validation, and one-repair retry behavior.
- `src/outreach_agent/workflow.py` owns orchestration: enrichment, thin-data checks, scoring, deterministic route selection, email generation, and artifact persistence.
- `src/outreach_agent/app.py` wires the FastAPI app and default dependencies.

This replaces the previous domain/protocols/integrations layer split. The goal is to make the MVP easier to read and review rather than optimize for long-term library extension.

## Dependency wiring

For normal runtime startup:

1. `create_app()` in `app.py` calls `load_llm_settings()` from `outreach_agent.llm`.
2. `load_llm_settings()` reads only `OPENAI_API_KEY` from the project `.env` file.
3. `create_openai_client()` validates the API key and constructs the fixed `OpenAI` client with `gpt-5.4-mini`.
4. The concrete `OpenAI` client performs strict schema validation and one repair attempt.
5. `create_app()` wires `MockAPI` and `MockScrape` from `outreach_agent.enrichment`.

Workflow functions receive dependencies as parameters for testability, but they are typed to concrete `MockAPI`, `MockScrape`, and `OpenAI` classes instead of provider abstraction layers.

## Prompt ownership

Prompt construction lives in `outreach_agent.prompts`:

- `build_scoring_messages`
- `build_email_messages`
- `build_repair_messages`

The LLM client calls these builders and handles transport plus schema validation. Workflow policy stays in `workflow.py`.

## Architecture guard

`tests/test_architecture_guard.py` now checks that the package stays flat and that the removed `domain`, `protocols`, and `integrations` directories do not return.
