# Architecture Overview

## Layered structure

The codebase uses a small, explicit layer split:

- **Domain (`src/outreach_agent/domain/`)**
  - Stable business models and prompt builders used across the system.
  - Owns `LeadIntake`, `LeadProfile`, `IcpScore`, `LeadRunResponse`, and prompt composition helpers.

- **Protocols (`src/outreach_agent/protocols/`)**
  - Dependency-inversion contracts and support types shared by callers and implementations.
  - Owns `LLMProvider`, `RawLLMProvider`, `ChatTransport`, `LLMOutputInvalidError`.
  - Owns enrichment contracts for `APIEnrichmentProvider` and `ScrapeEnrichmentProvider`.

- **Integrations (`src/outreach_agent/integrations/`)**
  - Concrete implementations and wiring for external services.
  - Owns provider factory/config, raw chat-completion providers, HTTP transport, validation decorator, and mock enrichment providers.
  - `MockAPIEnrichmentProvider` and `MockScrapeEnrichmentProvider` are explicit fixture-backed placeholders for now.

- **Application (`src/outreach_agent/` orchestrators)**
  - `app.py` creates the FastAPI app and selects concrete integrations.
  - `workflow.py` drives orchestration, routing, enrichment, persistence, and response composition.

## Provider wiring

For normal runtime startup:

1. `create_app()` in `app.py` loads settings via
   `outreach_agent.integrations.llm.config.load_llm_settings`.
2. `select_llm_provider()` composes API-key checks, model defaults, and provider choice.
3. The selected raw provider is wrapped with `ValidatingLLMProvider` for one-repair JSON
   validation on scoring and email generation.
4. `create_app()` also wires `MockAPIEnrichmentProvider` and `MockScrapeEnrichmentProvider` as the enrichment providers.

Only the composition root (`app.py`) imports concrete integrations directly.

## Prompt ownership

Prompt construction remains in the domain layer:

- `outreach_agent.domain.prompts.build_scoring_messages`
- `outreach_agent.domain.prompts.build_email_messages`
- `outreach_agent.domain.prompts.build_repair_messages`

Integrations call those builders and only transform between raw transport calls and
contracted provider protocols; they do not own policy. Enrichment policy stays in
workflow orchestration and chooses which provider to invoke and when.

## Architecture guard

`tests/test_architecture_guard.py` enforces import rules for `src/` modules:

- Domain cannot depend on application/protocols/integrations.
- Protocols can depend on domain and standard/library/contract dependencies only.
- Workflow/application orchestration modules cannot import concrete integrations.
- Only `outreach_agent.app` may import concrete integrations in application code.

Tests are intentionally exempt so they can import concrete providers for integration-style
coverage.
