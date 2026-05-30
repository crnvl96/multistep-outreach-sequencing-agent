# LLM Providers and Prompt Behavior

This document summarizes provider configuration and prompt responsibilities for the MVP. The full requirements live in the [design/spec artifact](designs/2026-05-29_11-42-29_multistep-outreach-sequencing-agent-mvp.md).

## Provider configuration

Provider selection is environment-driven:

```bash
LLM_PROVIDER=openai|openrouter|fake
LLM_MODEL=<model-name>
OPENAI_API_KEY=<key>        # required for OpenAI
OPENROUTER_API_KEY=<key>    # required for OpenRouter
```

Environment variables may be supplied directly or through `.env`; real environment variables take precedence.

## Fake provider

`LLM_PROVIDER=fake` is the default no-credential mode for automated tests and local development. It returns deterministic scoring and email fixtures for the Hot, Warm, and Cold demo leads. It is not presented as real model behavior.

## OpenAI and OpenRouter providers

`LLM_PROVIDER=openai` selects the OpenAI chat-completions provider and requires `OPENAI_API_KEY`.

`LLM_PROVIDER=openrouter` selects the OpenRouter chat-completions provider and requires `OPENROUTER_API_KEY`.

Both real providers use the same workflow contract as the fake provider: score first, validate/repair if needed, route in application code, then generate the first email for the chosen route.

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
