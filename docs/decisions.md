# Key Decisions

These decisions summarize the implemented MVP and link back to the [design/spec artifact](design/multistep-outreach-sequencing-agent-mvp.md).

## Local FastAPI service

The primary interface is `POST /leads` on a local FastAPI app. This keeps the reviewer path simple: start the server, send fixture requests with `curl`, and inspect the response/artifact.

## No n8n or external orchestration

The workflow is implemented directly in Python. The goal is to demonstrate the orchestration logic in code rather than delegate it to a workflow tool.

## Deterministic mocked enrichment

API enrichment and scraping are modeled as injectable providers, with concrete fixture-backed implementations `MockAPIEnrichmentProvider` and `MockScrapeEnrichmentProvider` in `outreach_agent.enrichment`. The application still models API-first enrichment, scrape fallback, thin-data checks, and max-one-pass behavior, but avoids live third-party dependencies.

## Application-owned routing

The LLM scores fit and explains evidence. The application maps score and confidence to Hot, Warm, or Cold so route selection is deterministic and covered by tests.

## Sequential LLM calls

The workflow calls the LLM sequentially: first ICP scoring, then route-specific email generation. This is slower than parallelism, but the second prompt depends on the deterministic route selected after scoring.

## Provider abstraction

The workflow depends on a provider interface. The test fake provider and the OpenAI provider share the same validation and repair path, which keeps tests deterministic while allowing real provider demos.

## Strict JSON validation and one repair

Scoring and email outputs are validated against strict schemas. The system makes one repair attempt, then fails clearly with `llm_output_invalid` instead of accepting malformed model output.

## First email only

Each route has a complete sequence plan with planned touches and timing, but the MVP generates only the first email to keep the scope focused.

## Local run artifacts

Every request returns and writes the decision chain as a local JSON artifact under `runs/`. This makes reviewer inspection possible without databases, queues, or external observability tools.

## Local-only MVP

Authentication, request signing, rate limiting, deployment, CRM integration, email sending, and database persistence are intentionally out of scope.
