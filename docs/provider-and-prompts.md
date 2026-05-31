# LLM Providers and Prompt Behavior

This document summarizes provider configuration and prompt responsibilities for the MVP. The full requirements live in the [design/spec artifact](design/multistep-outreach-sequencing-agent-mvp.md).

The implementation uses a flat module layout:

- `models.py`: schemas for intake, scoring, routing, email, errors, and artifacts.
- `prompts.py`: scoring, email, and repair prompt builders.
- `llm.py`: provider configuration, OpenAI client, transport, validation, and repair.
- `enrichment.py`: deterministic fixture-backed enrichment providers.
- `workflow.py` / `app.py`: orchestration and FastAPI wiring.

## Provider configuration

Provider selection is intentionally fixed for the demo: normal runtime always uses OpenAI with the model `gpt-5.4-mini`. The provider and model cannot be overridden from `.env` or exported shell environment variables.

The only `.env` value read for normal startup is:

```bash
OPENAI_API_KEY=<key>
```

Use the repository `.env.example` as the reference. Exported shell environment variables are ignored by this simplified local configuration.

Runtime provider wiring is owned by `outreach_agent.llm`:

1. `load_llm_settings()` reads `OPENAI_API_KEY` from `.env`.
2. `select_llm_provider()` requires the API key and constructs the fixed OpenAI provider/model.
3. `ValidatingLLMProvider` validates structured outputs and performs one repair attempt if needed.

## Prompt ownership

Prompt construction lives in `outreach_agent.prompts` so policy remains easy to test independent of HTTP/provider details:

- `build_scoring_messages`
- `build_email_messages`
- `build_repair_messages`

## Fake provider

The fake provider is only injected directly by automated tests. It is not selectable through `.env` and is not presented as real model behavior.

## OpenAI provider

Normal runtime always selects the OpenAI chat-completions provider and requires `OPENAI_API_KEY`.

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
