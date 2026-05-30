#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"

curl -sS -X POST "$BASE_URL/leads" \
  -H "Content-Type: application/json" \
  -d '{
    "lead_name": "Jordan Park",
    "company_name": "SignalSpring Software",
    "company_domain": "signalspring.io"
  }'
printf '\n'
