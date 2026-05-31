# Tradeoffs

The implementation follows the [design/spec artifact](design/multistep-outreach-sequencing-agent-mvp.md) and intentionally optimizes for a clear reviewer-facing MVP.

## Mocked enrichment vs. real LLM behavior

Enrichment is mocked so the Hot, Warm, Cold, and Insufficient Data paths are deterministic and testable. The API-first and scrape-fallback decisions are still real application behavior, but no live scraping or third-party enrichment API is called.

LLM scoring and email generation are real in OpenAI/OpenRouter modes because model reasoning is central to the demo. A fake provider exists under `tests/` for automated tests only.

## Sequential LLM calls vs. parallelism

The system performs scoring before email generation. This adds latency compared with parallel calls, but it is simpler and correct: the generated email needs the final application-owned route and selected sequence instructions.

## Local-only/no auth vs. production hardening

The service is designed for local review, not public deployment. It does not include webhook authentication, request signing, rate limits, tenant isolation, background jobs, or production observability. That keeps the MVP easy to run and inspect.

## JSON artifacts vs. database persistence

Run artifacts are local JSON files under `runs/`. This is enough for auditability in the MVP and avoids database setup. A production system would likely add durable storage, search, retention policy, and access controls.

## Narrow MVP scope vs. full sequencing platform

The repository defines route-specific sequence plans, but only generates the first email. It does not send emails, integrate with a CRM/SEP, generate all touches, or implement human approval. The narrow scope keeps attention on the lead intake, enrichment, scoring, routing, prompt, and audit chain.

## Strict validation vs. model flexibility

Strict schemas and one repair attempt make failures explicit and testable. The tradeoff is less tolerance for loosely formatted model responses, but that is intentional for an auditable workflow.
