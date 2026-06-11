#!/usr/bin/env bash
set -euo pipefail

WEBHOOK_URL="${WEBHOOK_URL:-http://localhost:8000/webhook/sms}"

curl -X POST "$WEBHOOK_URL" \
  -H "Content-Type: application/json" \
  -d '{
    "from": "+1234567890",
    "text": "Test SMS from local curl",
    "sentStamp": "2026-06-11T12:00:00Z",
    "receivedStamp": "2026-06-11T12:00:05Z",
    "sim": "SIM2"
  }'
