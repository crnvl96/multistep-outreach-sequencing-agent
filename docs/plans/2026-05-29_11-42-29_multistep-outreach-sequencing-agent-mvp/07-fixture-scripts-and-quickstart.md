## Parent

`docs/designs/2026-05-29_11-42-29_multistep-outreach-sequencing-agent-mvp.md`

## Type

AFK

## User stories covered

- 1. As a reviewer, I want to send a lead to a local HTTP endpoint with `curl`, so that I can evaluate the workflow without n8n or external orchestration tooling.
- 2. As a reviewer, I want fixture scripts for representative leads, so that I can quickly test the Hot, Warm, Cold, and Insufficient Data paths.
- 12. As a developer, I want provider configuration through environment variables, so that OpenAI and OpenRouter can be swapped without changing workflow code.

Requirements covered: 41-42.

## What to build

Add reviewer-facing helper scripts and quickstart documentation. A reviewer should be able to start the local server, run Hot/Warm/Cold/Insufficient fixture requests with shell scripts, and understand how to switch between fake, OpenAI, and OpenRouter providers.

This slice should make the existing implemented paths easy to demo, not add new workflow behavior.

## Acceptance criteria

- [ ] A script starts the local server with sensible local defaults.
- [ ] A Hot fixture script sends a predefined `curl` request and prints the response.
- [ ] A Warm fixture script sends a predefined `curl` request and prints the response.
- [ ] A Cold fixture script sends a predefined `curl` request and prints the response.
- [ ] An Insufficient Data fixture script sends a predefined `curl` request and prints the response.
- [ ] Scripts target the local HTTP endpoint and do not bypass the API.
- [ ] Scripts are documented with copy-pasteable commands in README or a quickstart doc.
- [ ] Docs explain the required environment variables for fake, OpenAI, and OpenRouter provider modes.
- [ ] Docs explain where run artifacts are written.

## Verification

- [ ] Automated: run the project test command to ensure script/doc changes did not break existing behavior.
- [ ] Manual: start the server with the start script.
- [ ] Manual: run each fixture script and confirm it returns the expected route/result shape.
- [ ] Manual: inspect README or quickstart and confirm a new reviewer has enough commands to run the MVP locally.

## Blocked by

- `01-insufficient-data-webhook.md`
- `02-hot-api-only-fake-llm.md`
- `03-warm-scrape-fallback.md`
- `04-cold-route-and-thresholds.md`
- `06-openai-openrouter-providers.md`

## Implementation notes

- Expected script names from the design:
  - `scripts/run_server.sh`
  - `scripts/send_hot_fixture.sh`
  - `scripts/send_warm_fixture.sh`
  - `scripts/send_cold_fixture.sh`
  - `scripts/send_insufficient_fixture.sh`
- Keep scripts simple and transparent. Prefer readable `curl` commands over clever wrappers.
- The fake provider should be the easiest no-credential path for local verification, but documentation should also show real provider environment variables.
- Do not add deployment or production hosting instructions in this slice.

## Review

After implementation, run the slice's verification checks and then run `/skill:review all uncommitted changes` before considering this done.
