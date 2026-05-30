#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"

curl -sS -X POST "$BASE_URL/leads" \
  -H "Content-Type: application/json" \
  -d '{
    "lead_name": "Riley Stone",
    "company_name": "PaperTrail Cafe",
    "company_domain": "papertrail-cafe.example"
  }'
printf '\n'
