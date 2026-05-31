## Parent

`docs/designs/2026-05-29_11-42-29_multistep-outreach-sequencing-agent-mvp.md`

## Type

AFK

## User stories covered

- 6. As a reviewer, I want real LLM scoring against a documented ICP, so that the central reasoning step is not mocked.
- 7. As a reviewer, I want deterministic route selection from documented thresholds, so that routing is explainable and testable.
- 8. As a reviewer, I want each route to use a different email-generation strategy, so that Hot, Warm, and Cold sequences are meaningfully distinct.
- 13. As a developer, I want automated tests with a fake LLM provider, so that orchestration logic can be verified without network calls, API keys, or LLM cost.

Requirements covered: 28-30, 35.

## What to build

Add the Cold path and strengthen deterministic routing threshold coverage. The Cold fixture should have enough enriched data to score, but fake scoring should produce a weak ICP fit. The application must route it to Cold by policy, select the Cold sequence plan, and generate a low-pressure first email.

This slice should also add focused tests around route thresholds so routing behavior is explainable and not delegated to the LLM provider.

## Acceptance criteria

- [ ] The Cold fixture reaches scoring with enough required data and does not return `insufficient_data`.
- [ ] Fake scoring for the Cold fixture returns a score below 50 with evidence explaining weak fit.
- [ ] Application routing maps score below 50 to final route `cold`.
- [ ] Tests cover Hot, Warm, and Cold threshold boundaries.
- [ ] Tests cover that a high score with low confidence/data confidence is not routed Hot.
- [ ] The selected sequence is the Cold sequence and includes planned touches/timing.
- [ ] The generated email follows Cold-style instructions: light-touch, permission-based, low-pressure CTA, focused on confirming whether the topic matters.
- [ ] The response and persisted artifact include the scoring evidence and deterministic route calculation.

## Verification

- [ ] Automated: run the project test command and confirm tests cover Cold fixture behavior and routing thresholds/boundaries.
- [ ] Manual: run the server with the fake provider and send the Cold fixture via `curl`; confirm route `cold` and one Cold-style email draft.
- [ ] Manual: inspect the artifact and confirm the route is explained by score/confidence policy rather than provider-selected route.

## Blocked by

- `02-hot-api-only-fake-llm.md`

## Implementation notes

- The LLM scoring output should include score, confidence, positive evidence, negative evidence, missing evidence, and reasoning. It should not include or control final route.
- Routing thresholds from the design:
  - Hot: score 80-100, no critical missing data, and confidence/data confidence not low.
  - Warm: score 50-79, or score 80-100 with confidence/data-confidence concerns that prevent Hot.
  - Cold: score below 50 with enough data to make a judgment.
  - Insufficient Data: critical required fields missing after all allowed enrichment.
- Keep threshold tests independent from HTTP when possible, but ensure the fixture path is also covered end-to-end.

## Review

After implementation, run the slice's verification checks and then run `/skill:review all uncommitted changes` before considering this done.
