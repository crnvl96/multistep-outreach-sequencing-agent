## Parent

`docs/design/multistep-outreach-sequencing-agent-mvp.md`

## Type

AFK

## User stories covered

- 11. As a developer, I want strict structured LLM output validation and one repair attempt, so that invalid model responses fail clearly instead of corrupting the workflow.

Requirements covered: 26-27, 31-34.

## What to build

Add strict structured validation around LLM scoring and email-generation outputs. If a provider returns invalid JSON or JSON that does not match the expected schema, the workflow should make one repair attempt with a repair prompt. If repair still fails, the workflow should return or raise a clear `llm_output_invalid` failure and persist the failed decision chain.

This slice should be testable entirely with fake provider variants that simulate invalid initial output, successful repair, and failed repair.

## Acceptance criteria

- [ ] Scoring output is validated against a strict schema with score, confidence, positive evidence, negative evidence, missing evidence, and reasoning.
- [ ] Email-generation output is validated against a strict schema with subject, body, CTA, and personalization notes/rationale.
- [ ] Invalid scoring output triggers exactly one scoring repair attempt.
- [ ] Invalid email output triggers exactly one email repair attempt.
- [ ] If repair succeeds, the workflow continues and records the repair attempt in the decision chain.
- [ ] If repair fails, the workflow returns or surfaces a clear `llm_output_invalid` error.
- [ ] Failed LLM validation runs still write a run artifact containing the error and the decision chain up to failure.
- [ ] Tests prove repair is attempted once, not zero times and not repeatedly.

## Verification

- [ ] Automated: run the project test command and confirm tests cover invalid scoring repaired, invalid email repaired, scoring repair failure, email repair failure, and artifact persistence on failure.
- [ ] Manual: if a debug/fake fixture is exposed for repair behavior, run it and inspect that the decision chain records the repair attempt. Manual exposure is optional; automated tests are sufficient for this slice.

## Blocked by

- `02-hot-api-only-fake-llm.md`

## Implementation notes

- Do not add complex retry loops. The settled decision is one repair attempt only.
- The repair prompt should ask the provider to return only valid JSON matching the expected schema.
- Keep validation/provider concerns separated from deterministic routing.
- Preserve the failed raw/invalid output in logs or artifacts only if it is safe and useful; avoid leaking secrets from provider errors.
- This slice prepares the real OpenAI/OpenRouter providers for reliable structured output handling.

## Review

After implementation, run the slice's verification checks and then run `/skill:review all uncommitted changes` before considering this done.
