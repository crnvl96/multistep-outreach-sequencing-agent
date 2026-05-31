# Multistep Outreach Sequencing Agent MVP Spec

## Problem Statement

A reviewer/evaluator needs to see a complete, working outreach automation workflow that demonstrates agentic orchestration, API-style integration, LLM-driven scoring, route selection, personalized email generation, and auditable decision logging.

The original project brief asked for a lead webhook, enrichment, ICP scoring, Hot/Warm/Cold routing, personalized first email generation, and a full decision chain. Success means a reviewer can run a local service, send a lead with `curl`, and observe an end-to-end workflow that is simple, consistent, documented, and complete.

The MVP should prioritize one reliable vertical slice over breadth: receive one lead, enrich it through deterministic staged sources, decide whether more data is needed, score it with a real LLM, route it deterministically, generate the first route-specific email, and persist the full run artifact.

## Solution

Build a local-only Python FastAPI service with one primary lead intake endpoint. The service accepts a minimal lead payload, enriches it with mocked deterministic sources, checks whether the lead profile is complete enough to score, calls a real LLM provider to score ICP fit, deterministically maps the score to a Hot/Warm/Cold route, and calls the LLM again to generate the first email using the chosen route's instructions.

The system returns the full decision chain in the HTTP response, logs it server-side, and writes a timestamped JSON artifact for each run. Fixture shell scripts make it easy to exercise the Hot, Warm, Cold, and Insufficient Data paths with `curl`.

The MVP uses real LLM behavior for scoring and email generation through injected provider objects. OpenAI is the supported real provider. A clearly labeled fake provider is available only inside automated tests.

## User Stories

1. As a reviewer, I want to send a lead to a local HTTP endpoint with `curl`, so that I can evaluate the workflow without n8n or external orchestration tooling.
2. As a reviewer, I want fixture scripts for representative leads, so that I can quickly test the Hot, Warm, Cold, and Insufficient Data paths.
3. As a reviewer, I want the workflow to enrich sparse lead inputs, so that I can see how the system combines input and external-style data before scoring.
4. As a reviewer, I want the system to detect thin data before scoring, so that it does not blindly ask the LLM to judge incomplete profiles.
5. As a reviewer, I want the system to autonomously run a second enrichment source only when needed, so that the core agentic decision from the brief is demonstrated.
6. As a reviewer, I want real LLM scoring against a documented ICP, so that the central reasoning step is not mocked.
7. As a reviewer, I want deterministic route selection from documented thresholds, so that routing is explainable and testable.
8. As a reviewer, I want each route to use a different email-generation strategy, so that Hot, Warm, and Cold sequences are meaningfully distinct.
9. As a reviewer, I want only the first email drafted, so that the MVP stays focused while still demonstrating route-specific personalization.
10. As a reviewer, I want the full decision chain in the API response and persisted locally, so that I can inspect why the system made each decision.
11. As a developer, I want strict structured LLM output validation and one repair attempt, so that invalid model responses fail clearly instead of corrupting the workflow.
12. As a developer, I want provider configuration through project `.env` settings, so that OpenAI can be configured without changing workflow code.
13. As a developer, I want automated tests with a fake LLM provider, so that orchestration logic can be verified without network calls, API keys, or LLM cost.

## Requirements

1. The application must expose a local HTTP lead intake endpoint, expected as `POST /leads`.
2. The endpoint must accept JSON with:
   - required: `lead_name`, `company_name`
   - required one-of: `company_domain` or `lead_email`
   - optional: `lead_title`, `linkedin_url`, `company_url`, `notes`
3. The application must reject invalid intake payloads with a clear 4xx validation response.
4. The MVP must not use n8n.
5. The enrichment workflow must use two deterministic mocked source types:
   - mocked external API enrichment
   - mocked web-scraping enrichment
6. The mocked external API enrichment source must run first.
7. The mocked web-scraping enrichment source must run only if the thin-data check finds missing required profile fields or important evidence after API enrichment.
8. Each enrichment source must run at most once per lead.
9. Mock enrichment data must be keyed by normalized company domain and/or company name.
10. Mock enrichment fixtures must cover at least four deterministic scenarios:
    - Hot path: API enrichment is already complete and strong-fit.
    - Warm path: API enrichment is thin; scraping fills enough data; fit is moderate.
    - Cold path: data is complete enough but ICP fit is weak.
    - Insufficient Data path: API plus scraping still leaves critical required fields missing.
11. The lead profile used for scoring must distinguish required fields from optional/evidence fields.
12. Required scoring profile fields must include, at minimum:
    - `lead_name`
    - `company_name`
    - `company_domain`
    - `lead_title`
    - `industry`
    - `company_size_range`
    - `region`
    - `company_description`
    - at least one `business_signals` entry
13. Optional/evidence profile fields may include:
    - `tech_stack`
    - `funding_stage`
    - `hiring_signals`
    - `outbound_tools`
    - `recent_events`
    - `pain_points`
    - `website_summary`
14. If critical required fields are still missing after both enrichment sources have run, the workflow must return an `insufficient_data` result and must not call the LLM for scoring or email generation.
15. If required fields are present but optional/evidence fields are weak, the workflow may proceed to LLM scoring. The final route must not be Hot when the LLM reports low confidence.
16. The ICP must be fictional, concrete, and documented in the project.
17. The MVP ICP is: B2B SaaS or AI/software companies with 50–500 employees, selling to mid-market or enterprise customers, operating in North America or Europe, and actively scaling outbound sales or go-to-market operations. Strong positive signals include SDR/AE/RevOps hiring, recent funding or launch activity, CRM/sales engagement tooling, manual lead qualification pain, personalization bottlenecks, or fragmented enrichment workflows. Strong negative signals include local/B2C businesses, very small companies without a sales motion, non-software businesses, unclear company identity, or no credible outbound/GTM need.
18. The target buyer/persona for personalization must be documented as VP Sales, Head of Growth, Head of RevOps, Founder/CEO, or another GTM owner at the target company.
19. LLM scoring must be real for normal demos and must not be mocked in the main OpenAI path.
20. The LLM integration must allow provider injection so tests can supply fakes without changing workflow code.
21. The MVP must include an OpenAI real provider implementation.
22. The MVP must include a clearly labeled fake provider for automated tests only.
23. Provider selection and credentials must be configured through the project `.env` file, expected as:
    - `LLM_PROVIDER=openai`
    - `LLM_MODEL=<model-name>`
    - `OPENAI_API_KEY=<key>` for OpenAI
24. If a real provider is selected and its required API key is missing, startup or request handling must fail with a clear configuration error.
25. LLM calls must be asynchronous-capable but executed sequentially for correctness:
    - first call: ICP scoring
    - second call: route-specific first email generation
26. The scoring LLM call must return strict structured JSON validated by application schemas.
27. The scoring output must include, at minimum:
    - numeric `score` from 0 to 100
    - `confidence` such as `high`, `medium`, or `low`
    - positive evidence
    - negative evidence
    - missing evidence
    - concise reasoning or summary
28. The LLM must not own final route selection. The application must compute the final route from the LLM score and confidence after required-field checks pass.
29. Routing thresholds must be documented and deterministic:
    - Hot: score 80–100, no critical missing data, and LLM confidence not low.
    - Warm: score 50–79, or score 80–100 with low confidence.
    - Cold: score below 50 with enough data to make a judgment.
    - Insufficient Data: critical required fields missing after all allowed enrichment.
30. The route-specific email generation LLM call must receive the final deterministic route and route instructions, and must not be allowed to change the route.
31. The email generation output must be strict structured JSON validated by application schemas.
32. The generated email output must include, at minimum:
    - `subject`
    - `body`
    - `cta`
    - personalization notes or rationale
33. If any LLM output fails validation, the application must retry once with a repair prompt.
34. If the repair attempt also fails validation, the workflow must fail with a clear `llm_output_invalid` error and persist the failed decision chain.
35. The MVP must define three route-specific sequence plans and use them to guide email generation:
    - Hot sequence: high-priority, concise, highly personalized, direct CTA, focused on urgent GTM or revenue workflow pain.
    - Warm sequence: consultative, educational, moderate CTA, focused on relevance and potential fit.
    - Cold sequence: light-touch, permission-based, low-pressure CTA, focused on confirming whether the topic matters.
36. Each sequence plan must include planned touches and timing, but the MVP must generate only the first email.
37. The email generation prompt must instruct the LLM not to invent facts beyond the lead profile and decision chain.
38. The API response must include the full decision chain, including intake, enrichment steps, thin-data checks, LLM scoring result when present, final route, selected sequence, generated email when present, timings, and artifact path or run id.
39. The application must write one timestamped JSON artifact per run under a local run-artifacts directory such as `runs/`.
40. The application must log the decision chain server-side in addition to returning and persisting it.
41. The repository must include documentation artifacts under `docs/` describing roadmap, decisions, system behavior, tradeoffs, ICP, routing policy, and prompt behavior.
42. The repository must include helper scripts to start the server and send fixture requests, expected examples:
    - `scripts/run_server.sh`
    - `scripts/send_hot_fixture.sh`
    - `scripts/send_warm_fixture.sh`
    - `scripts/send_cold_fixture.sh`
    - `scripts/send_insufficient_fixture.sh`
43. The implementation must favor clarity, completeness, and deterministic orchestration over broad feature scope.

## Acceptance Criteria

- [ ] Running the local server exposes `POST /leads` and accepts a valid JSON lead payload via `curl`.
- [ ] A payload missing `lead_name` or `company_name` receives a clear validation error.
- [ ] A payload with neither `company_domain` nor `lead_email` receives a clear validation error.
- [ ] The Hot fixture completes without running mocked scraping when mocked API enrichment already supplies enough required data.
- [ ] The Warm fixture runs mocked API enrichment, detects thin data, then runs mocked scraping before scoring.
- [ ] The Cold fixture reaches scoring with enough data and returns a Cold route when using the fake test provider.
- [ ] The Insufficient Data fixture runs all allowed enrichment sources, returns `insufficient_data`, and does not call scoring or email generation.
- [ ] For non-insufficient leads, the response contains an LLM score, confidence, evidence lists, deterministic final route, selected sequence, and first email draft.
- [ ] For all leads, the response contains enrichment steps, thin-data checks, timing information, and a run identifier or artifact path.
- [ ] Each request writes one JSON artifact under `runs/` or the chosen run-artifacts directory.
- [ ] Selecting `LLM_PROVIDER=openai` with a valid `OPENAI_API_KEY` can process a non-insufficient fixture and return validated scoring and email JSON.
- [ ] Selecting a real provider without its required API key fails with a clear configuration error.
- [ ] Automated tests can inject the fake provider directly and do not require network access or real API keys.
- [ ] Tests verify the thin-data branching behavior, insufficient-data behavior, deterministic route thresholds, route-specific email prompt selection, and LLM validation/repair behavior.
- [ ] Documentation under `docs/` explains the ICP, routing thresholds, enrichment policy, LLM provider configuration, decision-chain artifacts, and important tradeoffs.
- [ ] README or docs include copy-pasteable commands for starting the server and running fixture curl scripts.

## Decisions

- Use a coded solution only. n8n is explicitly out of scope.
- Use the existing Python project as the foundation. Repository evidence: `pyproject.toml` defines a Python project and `src/outreach_agent/app.py` exposes the FastAPI app.
- Use FastAPI and Pydantic for the local HTTP API and request/response validation.
- Expose a real local HTTP webhook-style endpoint instead of only a CLI runner, because the brief explicitly starts with receiving a lead webhook.
- Include fixture shell scripts for convenience, but keep the HTTP endpoint as the primary interface.
- Mock external API enrichment and web-scraping enrichment. This keeps demos deterministic and focuses the project on orchestration rather than third-party data-source selection.
- Keep enrichment staged and bounded: API first, then scrape only if thin, with each source used at most once.
- Use deterministic rule-based thin-data checks instead of LLM thin-data checks. This makes the agent's enrichment decision easier to test and explain.
- Use real LLM calls for scoring and email generation. This is the core reasoning part of the task and should not be mocked in the main demo path.
- Use simple provider injection so the OpenAI provider and test fake provider share the same workflow method names without extra protocol layers.
- Support a fake LLM provider only inside automated tests.
- Use two sequential LLM calls: scoring first, email generation second. This trades latency for correctness because the selected route determines which email prompt should be used.
- Make routing deterministic in application code from LLM score and confidence rather than asking the LLM to choose the route directly.
- Generate only the first email, but define complete sequence plans so route choice has visible behavioral consequences.
- Return, log, and persist the full decision chain because auditability is a core project goal.
- Validate all LLM outputs strictly with Pydantic-style schemas. Retry once with a repair prompt, then fail clearly.
- Keep the MVP local-only with no webhook authentication, rate limiting, public deployment, or production hardening.
- Store project documentation in the repository under `docs/` so the reasoning process is reviewable without access to the user's Obsidian vault.

Likely implementation areas:

- API layer for `POST /leads` and validation errors.
- Lead intake and enriched profile schemas.
- Mock enrichment providers and fixture data.
- Thin-data/completeness evaluator.
- ICP definition and routing policy.
- Injected LLM provider objects: an OpenAI provider and a test-only fake provider.
- Prompt builders for scoring and route-specific email generation.
- Decision-chain/run artifact writer.
- Tests and fixture scripts.
- Documentation under `docs/`.

## Testing Decisions

- Automated tests should focus on orchestration behavior, not live LLM provider behavior.
- Default automated test runs must use the fake provider and must not require API keys, network access, or OpenAI.
- Tests should verify:
  - intake validation rules
  - API-first enrichment
  - scrape-only-if-thin branching
  - max-one-pass-per-enrichment-source behavior
  - insufficient-data short-circuiting before LLM calls
  - deterministic routing thresholds
  - Hot/Warm/Cold route-specific email instruction selection
  - strict LLM output validation
  - one repair attempt for invalid LLM output
  - persisted run artifact creation
- Manual verification should cover real provider behavior with OpenAI using project `.env` settings and fixture curl scripts.
- Live LLM tests should not run by default because they are slower, non-deterministic, require credentials, and may incur cost.

## Out of Scope

- n8n workflows or n8n integration.
- Live scraping from public websites.
- Live third-party enrichment APIs.
- Repeated enrichment loops beyond one mocked API pass and one mocked scraping pass.
- Public deployment.
- Webhook authentication, request signing, rate limiting, or production security hardening.
- CRM integration or sequence-tool integration.
- Sending emails.
- Generating every email in each sequence.
- Human approval workflow.
- Multi-tenant support.
- Background job queues.
- Database persistence beyond local JSON run artifacts.
- Broad configurability beyond the LLM provider/model and necessary local settings.

## Open Questions

None blocking issue creation or implementation.

Implementation may choose exact module/file names, exact fake fixture company names, and exact run artifact filename format as long as the observable behavior in this spec is satisfied.

## References

- Obsidian briefing: `Projects/Multistep Outreach Sequencing Agent/Briefing.md`
  - Describes the target workflow: receive lead webhook, enrich via scrape/API, LLM-score against ICP, route to Hot/Warm/Cold sequence, generate personalized first email, and log full decision chain.
  - Emphasizes the twist: decide when enrichment is too thin and autonomously gather more data before scoring.
- Repository scaffold:
  - `pyproject.toml` defines the Python project and dependencies.
  - `src/outreach_agent/app.py` contains the FastAPI app wiring.
  - `README.md` contains the reviewer quickstart.
- Discovery decisions from this session:
  - Code-only MVP, no n8n.
  - FastAPI/Pydantic local HTTP endpoint.
  - Mock enrichment, real LLM scoring/email generation.
  - OpenAI provider plus fake test provider.
  - Deterministic routing thresholds.
  - Full decision-chain response/log/artifact.
  - Documentation-first workflow under `docs/`.
