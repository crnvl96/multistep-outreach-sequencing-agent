## Parent

`docs/designs/2026-05-29_11-42-29_multistep-outreach-sequencing-agent-mvp.md`

## Type

AFK

## User stories covered

- 1. As a reviewer, I want to send a lead to a local HTTP endpoint with `curl`, so that I can evaluate the workflow without n8n or external orchestration tooling.
- 3. As a reviewer, I want the workflow to enrich sparse lead inputs, so that I can see how the system combines input and external-style data before scoring.
- 4. As a reviewer, I want the system to detect thin data before scoring, so that it does not blindly ask the LLM to judge incomplete profiles.
- 5. As a reviewer, I want the system to autonomously run a second enrichment source only when needed, so that the core agentic decision from the brief is demonstrated.
- 10. As a reviewer, I want the full decision chain in the API response and persisted locally, so that I can inspect why the system made each decision.

Requirements covered: 1-14, 38-40.

## What to build

Build the first end-to-end vertical path: a local `POST /leads` endpoint that accepts a minimal lead payload, validates required intake fields, runs mocked API enrichment, detects that the lead is still thin, runs mocked scraping once, detects that critical required fields are still missing, and returns an `insufficient_data` result without calling any LLM.

This slice should also create the initial decision-chain shape and persist one timestamped JSON artifact per request. The artifact and response should make it obvious which enrichment sources ran, what fields were missing at each check, and why the workflow stopped before scoring.

## Acceptance criteria

- [ ] A local FastAPI service exposes `POST /leads`.
- [ ] Valid intake requires `lead_name`, `company_name`, and at least one of `company_domain` or `lead_email`.
- [ ] Invalid intake payloads receive clear 4xx validation responses.
- [ ] The insufficient-data fixture runs mocked API enrichment exactly once.
- [ ] The insufficient-data fixture runs mocked scraping exactly once after the first thin-data check.
- [ ] The workflow returns status/result `insufficient_data` when critical required fields are still missing after both enrichment sources.
- [ ] No scoring or email-generation LLM provider method is called for the insufficient-data path.
- [ ] The API response includes intake data, enrichment steps, thin-data checks, missing critical fields, timing information, and a run id or artifact path.
- [ ] One local JSON artifact is written for the run under the chosen run-artifacts directory, such as `runs/`.
- [ ] Server logs include the decision chain or a useful summary of the run.

## Verification

- [ ] Automated: run the project test command and confirm tests cover intake validation, insufficient-data branching, no LLM calls, and artifact creation.
- [ ] Manual: start the local server and send a valid insufficient-data lead with `curl`; confirm the response returns `insufficient_data` and includes both enrichment attempts.
- [ ] Manual: send invalid payloads missing `lead_name`, missing `company_name`, and missing both `company_domain` and `lead_email`; confirm clear 4xx responses.
- [ ] Manual: inspect the generated JSON artifact and confirm it matches the response decision chain.

## Blocked by

None - can start immediately.

## Implementation notes

- Keep the first slice narrow: do not implement Hot/Warm/Cold scoring or real LLM providers yet.
- Use deterministic mocked enrichment keyed by normalized company name/domain.
- The required scoring profile fields from the design are: `lead_name`, `company_name`, `company_domain`, `lead_title`, `industry`, `company_size_range`, `region`, `company_description`, and at least one `business_signal`.
- A source should run at most once per lead.
- The response/artifact schema can be refined later, but it should already contain the full decision chain needed for review.
- Prefer simple, explicit Pydantic models and orchestration logic over broad abstractions.

## Review

After implementation, run the slice's verification checks and then run `/skill:review all uncommitted changes` before considering this done.
