## Parent

`docs/design/multistep-outreach-sequencing-agent-mvp.md`

## Type

AFK

## User stories covered

- 3. As a reviewer, I want the workflow to enrich sparse lead inputs, so that I can see how the system combines input and external-style data before scoring.
- 4. As a reviewer, I want the system to detect thin data before scoring, so that it does not blindly ask the LLM to judge incomplete profiles.
- 5. As a reviewer, I want the system to autonomously run a second enrichment source only when needed, so that the core agentic decision from the brief is demonstrated.
- 6. As a reviewer, I want real LLM scoring against a documented ICP, so that the central reasoning step is not mocked.
- 7. As a reviewer, I want deterministic route selection from documented thresholds, so that routing is explainable and testable.
- 8. As a reviewer, I want each route to use a different email-generation strategy, so that Hot, Warm, and Cold sequences are meaningfully distinct.
- 9. As a reviewer, I want only the first email drafted, so that the MVP stays focused while still demonstrating route-specific personalization.
- 10. As a reviewer, I want the full decision chain in the API response and persisted locally, so that I can inspect why the system made each decision.

Requirements covered: 5-10, 15, 25-40.

## What to build

Add the Warm path where the first enrichment source is intentionally thin. The workflow should run mocked API enrichment, record a thin-data check with missing fields/evidence, run mocked scraping once to target those gaps, re-check completeness, proceed to fake scoring, deterministically route the lead to Warm, select the Warm sequence, and generate the first Warm-style email.

This slice demonstrates the core agentic fallback behavior from the brief: the system decides that enrichment is too thin and autonomously gathers one additional source before scoring.

## Acceptance criteria

- [ ] The Warm fixture's mocked API enrichment leaves required fields or important evidence missing.
- [ ] The first thin-data check records the missing fields/evidence that caused the scrape fallback.
- [ ] Mocked scraping runs exactly once for the Warm fixture.
- [ ] The second thin-data check shows the profile is complete enough to score.
- [ ] The workflow proceeds to fake scoring after scrape fallback.
- [ ] Application routing maps the fake Warm score or confidence policy to final route `warm`.
- [ ] The selected sequence is the Warm sequence and includes planned touches/timing.
- [ ] The generated email follows Warm-style instructions: consultative, educational, moderate CTA, focused on relevance and potential fit.
- [ ] The response and persisted artifact show both enrichment steps, both thin-data checks, scoring, route, sequence, email, and timings.

## Verification

- [ ] Automated: run the project test command and confirm tests cover scrape fallback only when thin, one scrape pass, successful post-scrape scoring, deterministic Warm routing, and Warm sequence/email selection.
- [ ] Automated/API-level: inject the fake provider and send the Warm fixture; confirm API then scrape, route `warm`, and one Warm-style email draft.
- [ ] Manual: inspect the run artifact and confirm the first thin-data check explains why scraping was triggered.

## Blocked by

- `02-hot-api-only-fake-llm.md`

## Implementation notes

- Do not create repeated enrichment loops. The design allows one API pass and one scrape pass only.
- Scraping is mocked/deterministic, not live web scraping.
- If required fields are present but evidence is weak, the workflow may proceed to scoring; Hot is prevented when LLM confidence is low.
- Warm routing threshold: score 50-79, or score 80-100 with low confidence.
- Warm sequence style: consultative, educational, moderate CTA, focused on relevance and potential fit.

## Review

After implementation, run the slice's verification checks and then run `/skill:review all uncommitted changes` before considering this done.
