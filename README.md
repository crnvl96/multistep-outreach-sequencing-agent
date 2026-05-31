# Multistep Outreach Sequencing Agent

Local FastAPI MVP for lead intake, deterministic enrichment, ICP scoring, Hot/Warm/Cold routing, first-email generation, and auditable run artifacts.

## Quickstart

This demo only supports OpenAI for normal local runs. The provider and model are fixed in code: OpenAI with `gpt-5.4-mini`. They cannot be overridden from `.env` or exported shell environment variables.

Copy `.env.example` to `.env` and set the only required value:

```bash
cp .env.example .env
# edit .env and set OPENAI_API_KEY
```

The `.env` file should contain:

```bash
OPENAI_API_KEY=<your-openai-api-key>
```

Then run:

```bash
./scripts/run_server.sh
```

In another terminal, send the fixture requests:

```bash
./scripts/send_hot_fixture.sh
./scripts/send_warm_fixture.sh
./scripts/send_cold_fixture.sh
./scripts/send_insufficient_fixture.sh
```

Each fixture sends a `curl` request to the local HTTP API at `POST /leads` and prints the JSON response.

If your server is running on another host or port, set `BASE_URL`:

```bash
BASE_URL=http://127.0.0.1:8000 ./scripts/send_hot_fixture.sh
```

## Provider configuration

Provider settings are intentionally not configurable for this demo. Normal startup always uses the OpenAI provider and the fixed default model `gpt-5.4-mini`.

The only `.env` setting the user must provide is:

```bash
OPENAI_API_KEY=<your-openai-api-key>
```

Use `.env.example` as the reference for required local configuration. Exported shell environment variables are ignored by this simplified local configuration.

If `OPENAI_API_KEY` is missing, startup fails with a clear configuration error. The fake provider is only injected directly by automated tests and is not available through `.env`.

## Run artifacts

Every request writes a timestamped JSON decision-chain artifact under `runs/`. The API response includes the `artifact_path`, `run_id`, enrichment steps, thin-data checks, scoring result when present, final route, selected sequence, generated email when present, timings, and any workflow error.

## Documentation

Reviewer-facing docs live under `docs/`:

- `docs/architecture.md` documents the flat module layout, provider wiring, and import guard expectations.
- `docs/roadmap.md` explains the MVP goal, fictional ICP, target persona, and implemented paths.
- `docs/system-behavior.md` explains intake, enrichment, routing, sequence behavior, validation, and run artifacts.
- `docs/provider-and-prompts.md` explains OpenAI configuration, test fake-provider usage, prompt behavior, and prompt ownership.
- `docs/decisions.md` and `docs/tradeoffs.md` summarize major design choices and scope tradeoffs.

## Development checks

```bash
uv run pytest
```
