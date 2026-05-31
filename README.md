# Multistep Outreach Sequencing Agent

Local FastAPI MVP for lead intake, deterministic enrichment, ICP scoring, Hot/Warm/Cold routing, first-email generation, and auditable run artifacts.

## Quickstart

Configure a real provider in `.env` first; the fake provider is test-only and cannot be selected for normal server startup.

```bash
# .env
LLM_PROVIDER=openai
LLM_MODEL=<openai-model-name>
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

Provider settings are read from the project `.env` file. Exported shell environment variables are ignored by this simplified local configuration.

`LLM_PROVIDER` is required for normal app startup. If it is missing, startup fails instead of falling back to the fake test provider.

### OpenAI provider

```bash
# .env
LLM_PROVIDER=openai
LLM_MODEL=<openai-model-name>
OPENAI_API_KEY=<your-openai-api-key>
```

Then run:

```bash
./scripts/run_server.sh
```

### OpenRouter provider

```bash
# .env
LLM_PROVIDER=openrouter
LLM_MODEL=<openrouter-model-name>
OPENROUTER_API_KEY=<your-openrouter-api-key>
```

Then run:

```bash
./scripts/run_server.sh
```

If `LLM_PROVIDER` is missing, unsupported, set to `fake`, or points to a real provider without the matching API key, startup fails with a clear configuration error. The fake provider is only injected directly by automated tests.

## Run artifacts

Every request writes a timestamped JSON decision-chain artifact under `runs/`. The API response includes the `artifact_path`, `run_id`, enrichment steps, thin-data checks, scoring result when present, final route, selected sequence, generated email when present, timings, and any workflow error.

## Documentation

Reviewer-facing docs live under `docs/`:

- `docs/architecture.md` documents the production layer split, provider wiring, and import guard expectations.
- `docs/roadmap.md` explains the MVP goal, fictional ICP, target persona, and implemented paths.
- `docs/system-behavior.md` explains intake, enrichment, routing, sequence behavior, validation, and run artifacts.
- `docs/provider-and-prompts.md` explains OpenAI/OpenRouter configuration, test fake-provider usage, prompt behavior, and prompt ownership.
- `docs/decisions.md` and `docs/tradeoffs.md` summarize major design choices and scope tradeoffs.

## Development checks

```bash
uv run pytest
```
