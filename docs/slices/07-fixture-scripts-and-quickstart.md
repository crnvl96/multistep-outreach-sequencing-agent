## Parent

`docs/design/multistep-outreach-sequencing-agent-mvp.md`

## Type

AFK

## User stories covered

- 1. As a reviewer, I want to send a lead to a local HTTP endpoint with `curl`, so that I can evaluate the workflow without n8n or external orchestration tooling.
- 2. As a reviewer, I want fixture scripts for representative leads, so that I can quickly test the Hot, Warm, Cold, and Insufficient Data paths.
- 12. As a developer, I want provider configuration through project `.env` settings, so that OpenAI can be configured without changing workflow code.

Requirements covered: 41-42.

## What to build

Add reviewer-facing helper scripts and quickstart documentation. A reviewer should be able to start the local server, run Hot/Warm/Cold/Insufficient fixture requests with shell scripts, and understand how to configure the OpenAI provider.

This slice should make the existing implemented paths easy to demo, not add new workflow behavior.

## Acceptance criteria

- [x] A script starts the local server with sensible local defaults.
- [x] A Hot fixture script sends a predefined `curl` request and prints the response.
- [x] A Warm fixture script sends a predefined `curl` request and prints the response.
- [x] A Cold fixture script sends a predefined `curl` request and prints the response.
- [x] An Insufficient Data fixture script sends a predefined `curl` request and prints the response.
- [x] Scripts target the local HTTP endpoint and do not bypass the API.
- [x] Scripts are documented with copy-pasteable commands in README or a quickstart doc.
- [x] Docs explain the required project `.env` settings for OpenAI and clarify that the fake provider is test-only.
- [x] Docs explain where run artifacts are written.

## Verification

- [x] Automated: run the project test command to ensure script/doc changes did not break existing behavior.
- [x] Manual: start the server with the start script.
- [x] Manual: run each fixture script and confirm it returns the expected response/artifact shape.
- [x] Manual: inspect README or quickstart and confirm a new reviewer has enough commands to run the MVP locally.

## Blocked by

- `01-insufficient-data-webhook.md`
- `02-hot-api-only-fake-llm.md`
- `03-warm-scrape-fallback.md`
- `04-cold-route-and-thresholds.md`
- `06-openai-provider.md`

## Implementation notes

- Expected script names from the design:
  - `scripts/run_server.sh`
  - `scripts/send_hot_fixture.sh`
  - `scripts/send_warm_fixture.sh`
  - `scripts/send_cold_fixture.sh`
  - `scripts/send_insufficient_fixture.sh`
- Keep scripts simple and transparent. Prefer readable `curl` commands over clever wrappers.
- The fake provider should remain test-only; documentation should show the real OpenAI provider `.env` settings for local server startup.
- Do not add deployment or production hosting instructions in this slice.

## Review

After implementation, run the slice's verification checks and then run `/skill:review all uncommitted changes` before considering this done.
