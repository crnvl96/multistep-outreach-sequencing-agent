# Multistep Outreach Sequencing Agent

Local FastAPI MVP for lead intake, deterministic enrichment, ICP scoring, Hot/Warm/Cold routing, first-email generation, and auditable run artifacts.

## Local setup

### Prerequisites

- Python 3.14 or newer. This project is configured with `.python-version` and `requires-python = ">=3.14"`.
- [`uv`](https://docs.astral.sh/uv/) for Python and dependency management.
- An OpenAI API key. Normal local runs use OpenAI with the fixed model `gpt-5.4-mini`.

Install `uv` if you do not already have it:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Then open a new terminal or reload your shell so the `uv` command is available.

### 1. Get the code

```bash
git clone <repository-url>
cd multistep-outreach-sequencing-agent
```

If you already have the repository, start from the project root directory.

### 2. Install Python and dependencies

```bash
uv python install 3.14
uv sync --dev
```

`uv sync --dev` creates the local virtual environment and installs runtime and development dependencies from `pyproject.toml` and `uv.lock`.

### 3. Configure environment variables

Copy the example environment file:

```bash
cp .env.example .env
```

Edit `.env` so it contains:

```bash
OPENAI_API_KEY=<your-openai-api-key>
```

The `.env` file is required for normal local startup. Exported shell environment variables are intentionally ignored by this simplified local configuration.

### 4. Start the API server

```bash
./scripts/run_server.sh
```

By default the server starts at:

```text
http://127.0.0.1:8000
```

To use a different host or port:

```bash
HOST=0.0.0.0 PORT=8080 ./scripts/run_server.sh
```

### 5. Send sample requests

In another terminal, run the fixture scripts:

```bash
./scripts/send_hot_fixture.sh
./scripts/send_warm_fixture.sh
./scripts/send_cold_fixture.sh
./scripts/send_insufficient_fixture.sh
```

Each fixture sends a `curl` request to `POST /leads` and prints the JSON response.

If your server is running on another host or port, set `BASE_URL`:

```bash
BASE_URL=http://127.0.0.1:8080 ./scripts/send_hot_fixture.sh
```

## OpenAI configuration

LLM settings are intentionally not configurable for this demo. Normal startup always uses the concrete OpenAI client and the fixed default model `gpt-5.4-mini`.

The only `.env` setting the user must provide is:

```bash
OPENAI_API_KEY=<your-openai-api-key>
```

Use `.env.example` as the reference for required local configuration. Exported shell environment variables are ignored by this simplified local configuration.

If `OPENAI_API_KEY` is missing, startup fails with a clear configuration error. Test fakes are only passed directly by automated tests and are not available through `.env`.

## Run artifacts

Every request writes a timestamped JSON decision-chain artifact under `runs/`. The API response includes the `artifact_path`, `run_id`, enrichment steps, thin-data checks, scoring result when present, final route, selected sequence, generated email when present, timings, and any workflow error.

## Documentation

Reviewer-facing docs live under `docs/`:

- `docs/architecture.md` documents the flat module layout, dependency wiring, and import guard expectations.
- `docs/roadmap.md` explains the MVP goal, fictional ICP, target persona, and implemented paths.
- `docs/system-behavior.md` explains intake, enrichment, routing, sequence behavior, validation, and run artifacts.
- `docs/provider-and-prompts.md` explains OpenAI configuration, test fake usage, prompt behavior, and prompt ownership.
- `docs/decisions.md` and `docs/tradeoffs.md` summarize major design choices and scope tradeoffs.

## Development checks

Run the test suite:

```bash
uv run pytest
```

Run linting and formatting checks:

```bash
uv run ruff check .
uv run ruff format --check .
```

## Troubleshooting

- `uv: command not found`: install `uv`, then reload your shell.
- Python version errors: run `uv python install 3.14`, then `uv sync --dev` again.
- Missing `.env` or `OPENAI_API_KEY`: confirm `.env` exists in the project root and contains `OPENAI_API_KEY=<your-openai-api-key>`.
- Fixture scripts fail to connect: confirm `./scripts/run_server.sh` is still running and that `BASE_URL` matches the server URL.
