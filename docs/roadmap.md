# MVP Roadmap

This repository implements the local-only MVP described in the [design/spec artifact](designs/2026-05-29_11-42-29_multistep-outreach-sequencing-agent-mvp.md).

## Goal

Demonstrate a complete outreach orchestration workflow that can be reviewed from the repository alone:

1. Receive a lead at `POST /leads`.
2. Enrich the lead through deterministic mocked sources.
3. Decide whether the profile is complete enough to score.
4. Score ICP fit with an LLM provider.
5. Route deterministically to Hot, Warm, or Cold.
6. Generate only the first route-specific email.
7. Return and persist the full decision chain.

## Fictional ICP

The product targets B2B SaaS or AI/software companies with 50-500 employees that sell to mid-market or enterprise buyers in North America or Europe and are scaling outbound sales or go-to-market operations.

Positive fit signals include SDR/AE/RevOps hiring, recent funding or launches, CRM or sales engagement tooling, manual lead qualification pain, personalization bottlenecks, or fragmented enrichment workflows.

Negative fit signals include local or B2C businesses, very small companies without a sales motion, non-software businesses, unclear company identity, or no credible outbound/GTM need.

## Target buyer/persona

Personalization is written for GTM owners such as VP Sales, Head of Growth, Head of RevOps, Founder/CEO, or another leader responsible for outbound pipeline and revenue workflow quality.

## Implemented paths

- **Hot**: mocked API enrichment is already complete; scoring indicates strong ICP fit; the system skips scraping and generates a concise direct first email.
- **Warm**: mocked API enrichment is thin; mocked scraping fills the gaps; scoring indicates moderate fit; the system generates a consultative first email.
- **Cold**: enrichment is complete enough, but scoring shows weak ICP fit; the system generates a light-touch permission-based first email.
- **Insufficient Data**: API plus scrape still leave critical fields missing; the system stops before LLM scoring or email generation.

## Current scope

The MVP intentionally stays narrow: one local FastAPI service, deterministic mocked enrichment, sequential LLM calls, first-email generation only, local JSON run artifacts, and no production auth/deployment concerns.
