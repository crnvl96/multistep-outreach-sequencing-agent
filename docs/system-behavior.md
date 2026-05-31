# System Behavior

See the [design/spec artifact](design/multistep-outreach-sequencing-agent-mvp.md) for the full requirements behind this implementation.

## Lead intake

`POST /leads` accepts JSON with these fields:

- Required: `lead_name`, `company_name`
- Required one-of: `company_domain` or `lead_email`
- Optional intake context: `lead_title`, `linkedin_url`, `company_url`, `notes`

Invalid payloads receive FastAPI/Pydantic 4xx validation responses.

## Scoring profile fields

The workflow converts intake into a lead profile and enriches it before scoring.

Required profile fields for scoring are:

- `lead_name`
- `company_name`
- `company_domain`
- `lead_title`
- `industry`
- `company_size_range`
- `region`
- `company_description`
- at least one entry in `business_signals`

Optional/evidence fields from the spec include `tech_stack`, `funding_stage`, `hiring_signals`, `outbound_tools`, `recent_events`, `pain_points`, and `website_summary`. The current MVP keeps the schema small and represents important evidence mainly through `business_signals` plus profile description fields.

## Enrichment policy

Enrichment is deterministic and fixture-backed so demos and tests are repeatable.

1. Enrichment step `source` values are logical labels: `api` and `scrape`.
2. Enrichment is routed through two concrete dependencies: `MockAPI` first, then `MockScrape` only if needed.
3. Both enrichment dependencies are explicit and fixture-backed in `outreach_agent.enrichment`.
4. The application still performs a thin-data check against required scoring fields.
5. Mocked scraping runs only when the API result is still thin.
6. Each source runs at most once per lead.
7. A second thin-data check runs after scraping when scraping was needed.

If critical required fields are still missing after all allowed enrichment, the run returns `insufficient_data`. In that case the workflow does not call the LLM for scoring or email generation.

## Routing policy

The LLM returns structured ICP scoring evidence, but it does not choose the final route. The application owns routing so thresholds are deterministic, testable, and auditable.

Current thresholds:

- **Hot**: score 80-100 and LLM confidence is not `low`.
- **Warm**: score 50-79, or score 80-100 when confidence concerns prevent Hot.
- **Cold**: score below 50 when the profile is complete enough to judge.
- **Insufficient Data**: critical required fields are missing after API plus optional scrape fallback.

## Sequence behavior

The application defines complete planned sequences for Hot, Warm, and Cold routes. Each sequence includes planned touches and timing, but the MVP generates only the first email.

- **Hot sequence**: high-priority, concise, highly personalized, direct CTA focused on urgent GTM or revenue workflow pain.
- **Warm sequence**: consultative, educational, moderate CTA focused on relevance and potential fit.
- **Cold sequence**: light-touch, permission-based, low-pressure CTA focused on confirming whether the topic matters.

The email-generation prompt receives the final deterministic route and selected sequence instructions. It is instructed not to change the route and not to invent facts beyond the lead profile and decision chain.

## LLM validation and failure behavior

LLM scoring output must validate as strict JSON with:

- `score`
- `confidence`
- `positive_evidence`
- `negative_evidence`
- `missing_evidence`
- `reasoning`

LLM email output must validate as strict JSON with:

- `subject`
- `body`
- `cta`
- `personalization_notes`

If either output is invalid, the `OpenAI` client makes exactly one repair attempt with a repair prompt. If repair also fails, the run returns status `llm_output_invalid`, records the failed step, and still writes the decision-chain artifact.

## Run artifacts

Every request writes one timestamped JSON file under `runs/`. The API response includes the artifact path and mirrors the artifact content.

Artifacts contain the decision chain: intake, enriched profile, enrichment steps, thin-data checks, missing critical fields, LLM calls and repair attempts, scoring result when present, final route, selected sequence, generated email when present, timing metadata, and any workflow error.
