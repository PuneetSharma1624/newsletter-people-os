#!/usr/bin/env bash
# Vercel dev smoke test — requires `vercel dev` running on localhost:3000
set -e

BASE="${1:-http://localhost:3000}"
echo "=== Vercel Dev Smoke Test: $BASE ==="

echo "--- GET / ---"
curl -sI "$BASE/" | head -2

echo "--- GET /data/dates.json ---"
curl -sf "$BASE/data/dates.json" | python3 -c "import json,sys; d=json.load(sys.stdin); print('dates:', len(d.get('dates',[])))"

echo "--- GET /api/health ---"
curl -sf "$BASE/api/health" | python3 -c "import json,sys; d=json.load(sys.stdin); print('health ok:', d.get('ok'))"

echo "--- GET /api/public/stats ---"
curl -sf "$BASE/api/public/stats" | python3 -c "import json,sys; d=json.load(sys.stdin); print('stats ok:', d.get('ok'), 'subscribers:', d.get('total_subscribers'))"

echo "--- POST /api/subscribe ---"
curl -sf -X POST "$BASE/api/subscribe" \
  -H "Content-Type: application/json" \
  -d '{"email":"smoke-test@example.com","source":"local_smoke"}' \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print('subscribe ok:', d.get('ok'), d.get('message',''))"

echo "=== Vercel dev smoke complete ==="
