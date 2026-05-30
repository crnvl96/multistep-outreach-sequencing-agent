#!/usr/bin/env bash
set -euo pipefail

HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8000}"

printf 'Starting outreach agent on http://%s:%s\n' "$HOST" "$PORT"
exec uv run uvicorn --app-dir src outreach_agent.app:app --host "$HOST" --port "$PORT"
