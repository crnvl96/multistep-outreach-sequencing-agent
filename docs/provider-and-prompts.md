# LLM Providers and Prompt Behavior

This document summarizes provider configuration and prompt responsibilities for the MVP. The full requirements live in the [design/spec artifact](design/multistep-outreach-sequencing-agent-mvp.md).

The implementation uses a flat module layout:

- `models.py`: schemas for intake, scoring, routing, email, errors, and artifacts.
- `prompts.py`: scoring, email, and repair prompt builders.
- `llm.py`: provider configuration, OpenAI client, transport, validation, and repair.
- `enrichment.py`: deterministic fixture-backed enrichment providers.
- `workflow.py` / `app.py`: orchestration and FastAPI wiring.

## Provider configuration

Provider selection is `.env`-driven:

```bash
LLM_PROVIDER=openai
LLM_MODEL=<model-name>
OPENAI_API_KEY=<key>        # required for OpenAI
```

These values are read from the project `.env` file. Exported shell environment variables are ignored by this simplified local configuration. `LLM_PROVIDER` is required; the app does not default to the fake provider.

Runtime provider wiring is owned by `outreach_agent.llm`:

1. `load_llm_settings()` reads `.env`.
2. `select_llm_provider()` checks provider/API-key settings and applies model defaults.
3. `ValidatingLLMProvider` validates structured outputs and performs one repair attempt if needed.

## Prompt ownership

Prompt construction lives in `outreach_agent.prompts` so policy remains easy to test independent of HTTP/provider details:

- `build_scoring_messages`
- `build_email_messages`
- `build_repair_messages`

## Fake provider

The fake provider is only injected directly by automated tests. It is not selectable through `.env` and is not presented as real model behavior.

## OpenAI provider

`LLM_PROVIDER=openai` selects the OpenAI chat-completions provider and requires `OPENAI_API_KEY`.

The real provider uses the same injected method names covered by the test fake provider: score first, validate/repair if needed, route in application code, then generate the first email for the chosen route.

## Scoring prompt behavior

The scoring request includes:

- the documented fictional ICP,
- the enriched lead profile,
- instructions to return only valid JSON,
- the strict scoring schema,
- and an instruction not to choose the final route.

The expected scoring JSON contains score, confidence, positive evidence, negative evidence, missing evidence, and reasoning.

## Email prompt behavior

The email request includes:

- the final deterministic route,
- the selected route sequence instructions,
- the selected sequence plan and planned touches,
- the lead profile,
- the scoring context,
- instructions to generate only the first email,
- instructions not to change the route,
- instructions not to invent facts,
- and the strict email schema.

The expected email JSON contains subject, body, CTA, and personalization notes.

## Repair behavior

Invalid scoring or email output triggers one repair attempt. If repair fails, the workflow records `llm_output_invalid` and persists the partial decision chain.
