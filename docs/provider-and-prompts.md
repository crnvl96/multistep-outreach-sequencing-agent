# OpenAI and Prompt Behavior

This document summarizes OpenAI configuration and prompt responsibilities for the MVP. The full requirements live in the [design/spec artifact](design/multistep-outreach-sequencing-agent-mvp.md).

The implementation uses a flat module layout:

- `models.py`: schemas for intake, scoring, routing, email, errors, and artifacts.
- `prompts.py`: scoring, email, and repair prompt builders.
- `llm.py`: OpenAI configuration, client, transport, validation, and repair.
- `enrichment.py`: deterministic fixture-backed `MockAPI` and `MockScrape` enrichment.
- `workflow.py` / `app.py`: orchestration and FastAPI wiring.

## OpenAI configuration

LLM configuration is intentionally fixed for the demo: normal runtime always uses OpenAI with the model `gpt-5.4-mini`. The model cannot be overridden from `.env` or exported shell environment variables.

The only `.env` value read for normal startup is:

```bash
OPENAI_API_KEY=<key>
```

Use the repository `.env.example` as the reference. Exported shell environment variables are ignored by this simplified local configuration.

Runtime OpenAI wiring is owned by `outreach_agent.llm`:

1. `load_llm_settings()` reads `OPENAI_API_KEY` from `.env`.
2. `create_openai_client()` requires the API key and constructs the fixed `OpenAI` client/model.
3. The concrete `OpenAI` client validates structured outputs and performs one repair attempt if needed.

## Prompt ownership

Prompt construction lives in `outreach_agent.prompts` so policy remains easy to test independent of HTTP client details:

- `build_scoring_messages`
- `build_email_messages`
- `build_repair_messages`

## Test fakes

Automated tests can pass fake LLM clients directly. They are not selectable through `.env` and are not presented as real model behavior.

## OpenAI client

Normal runtime always selects the OpenAI chat-completions client and requires `OPENAI_API_KEY`.

The concrete `OpenAI` client scores first, validates/repairs if needed, lets application code route, then generates the first email for the chosen route.

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
