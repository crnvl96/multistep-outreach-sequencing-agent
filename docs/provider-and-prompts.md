# LLM Providers and Prompt Behavior

This document summarizes provider configuration and prompt responsibilities for the MVP. The full requirements live in the [design/spec artifact](designs/2026-05-29_11-42-29_multistep-outreach-sequencing-agent-mvp.md).

The implementation follows a stable architecture split:

- `domain`: schemas and prompt ownership.
- `protocols`: provider and transport interfaces.
- `integrations`: concrete provider implementations and provider/config/transport wiring.
- `workflow`/`app`: orchestration and composition root.

For full package-level ownership details, see [`architecture.md`](architecture.md).

## Provider configuration

Provider selection is `.env`-driven:

```bash
LLM_PROVIDER=openai|openrouter
LLM_MODEL=<model-name>
OPENAI_API_KEY=<key>        # required for OpenAI
OPENROUTER_API_KEY=<key>    # required for OpenRouter
```

These values are read from the project `.env` file. Exported shell environment variables are ignored by this simplified local configuration.
`LLM_PROVIDER` is required; the app does not default to the fake provider.

Runtime provider wiring is owned by the composition root (`outreach_agent.app`) and proceeds through:

1. `load_llm_settings` (`outreach_agent.integrations.llm.config`)
2. `select_llm_provider` (`outreach_agent.integrations.llm.factory`)
3. `ValidatingLLMProvider` (`outreach_agent.integrations.llm_validation`) for strict schema validation and one-repair retry.  

## Prompt ownership

Prompt construction is in the domain layer so policy remains stable and testable independent of transport details:

- `build_scoring_messages`
- `build_email_messages`
- `build_repair_messages`

All integration implementations call these builders and focus only on transport, provider details, and schema validation.

## Fake provider

The fake provider is only injected directly by automated tests. It is not selectable through `.env` and is not presented as real model behavior.

## OpenAI and OpenRouter providers

`LLM_PROVIDER=openai` selects the OpenAI chat-completions provider and requires `OPENAI_API_KEY`.

`LLM_PROVIDER=openrouter` selects the OpenRouter chat-completions provider and requires `OPENROUTER_API_KEY`.

Both real providers use the workflow contract covered by the test fake provider: score first, validate/repair if needed, route in application code, then generate the first email for the chosen route.

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

Both providers flow through the same strict validation wrapper. Invalid scoring or email output triggers one repair attempt. If repair fails, the workflow records `llm_output_invalid` and persists the partial decision chain.
