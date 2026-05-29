## Parent

`docs/designs/2026-05-29_11-42-29_multistep-outreach-sequencing-agent-mvp.md`

## Type

AFK

## User stories covered

- 6. As a reviewer, I want real LLM scoring against a documented ICP, so that the central reasoning step is not mocked.
- 7. As a reviewer, I want deterministic route selection from documented thresholds, so that routing is explainable and testable.
- 8. As a reviewer, I want each route to use a different email-generation strategy, so that Hot, Warm, and Cold sequences are meaningfully distinct.
- 9. As a reviewer, I want only the first email drafted, so that the MVP stays focused while still demonstrating route-specific personalization.
- 10. As a reviewer, I want the full decision chain in the API response and persisted locally, so that I can inspect why the system made each decision.
- 13. As a developer, I want automated tests with a fake LLM provider, so that orchestration logic can be verified without network calls, API keys, or LLM cost.

Requirements covered: 19, 22, 25-32, 35-40.

## What to build

Add the first successful scoring path using the fake LLM provider: a Hot fixture where mocked API enrichment alone produces a complete, strong-fit profile, the workflow skips mocked scraping, calls fake scoring, deterministically routes the lead to Hot, selects the Hot sequence plan, calls fake email generation, and returns a first email draft.

This slice should establish the LLM provider interface used by the workflow, but only the fake provider needs to work here. It should also establish route-specific sequence selection for Hot and include scoring/email outputs in the decision chain and run artifact.

## Acceptance criteria

- [ ] A fake LLM provider can be selected for tests/development without API keys or network access.
- [ ] The Hot fixture's mocked API enrichment fills all required scoring profile fields.
- [ ] The Hot fixture does not run mocked scraping.
- [ ] The workflow makes a scoring call before an email-generation call.
- [ ] Fake scoring returns structured data with score, confidence, positive evidence, negative evidence, missing evidence, and reasoning.
- [ ] Application routing maps the fake Hot score to final route `hot`; the fake provider does not own final routing.
- [ ] The selected sequence is the Hot sequence and includes planned touches/timing.
- [ ] The generated email contains `subject`, `body`, `cta`, and personalization notes/rationale.
- [ ] The API response and persisted artifact include enrichment steps, scoring result, deterministic route, selected sequence, generated first email, timings, and run id/artifact path.

## Verification

- [ ] Automated: run the project test command and confirm tests cover Hot API-only enrichment, no scrape call, scoring-before-email order, deterministic Hot routing, Hot sequence selection, and artifact contents.
- [ ] Manual: run the server with the fake provider and send the Hot fixture via `curl`; confirm route `hot`, no scrape step, and one first-email draft.
- [ ] Manual: inspect the run artifact and confirm it contains the same scoring, route, sequence, and email information returned by the API.

## Blocked by

- `01-insufficient-data-webhook.md`

## Implementation notes

- The design says real LLM behavior is required for normal demos, but the fake provider is explicitly allowed for tests/dev. This slice should not implement OpenAI/OpenRouter yet.
- Keep the LLM provider contract provider-agnostic so real providers can be added later without changing orchestration.
- LLM calls are sequential by design: scoring first, route-specific email generation second.
- Hot routing threshold: score 80-100, no critical missing data, and confidence/data confidence not low.
- Hot sequence style: high-priority, concise, highly personalized, direct CTA, focused on urgent GTM or revenue workflow pain.
- The email-generation step must receive the final deterministic route and must not be allowed to change it.

## Review

After implementation, run the slice's verification checks and then run `/skill:review all uncommitted changes` before considering this done.
