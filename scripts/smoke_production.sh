#!/usr/bin/env bash
# Production smoke test — accepts BASE_URL as first arg or env var
# Usage: ./scripts/smoke_production.sh https://your-project.vercel.app
set -e

BASE="${1:-${BASE_URL:-}}"
if [ -z "$BASE" ]; then
  echo "ERROR: provide BASE_URL as arg or env var"
  exit 1
fi
BASE="${BASE%/}"  # strip trailing slash

TODAY=$(TZ='Asia/Kolkata' date '+%Y-%m-%d' 2>/dev/null || date '+%Y-%m-%d')
FAIL=0

check() {
  local label="$1"; local url="$2"; local extra="$3"
  echo -n "--- $label ... "
  STATUS=$(curl -s -o /tmp/smoke_body.txt -w "%{http_code}" "$url")
  if [ "$STATUS" = "200" ]; then
    echo "HTTP $STATUS OK"
    [ -n "$extra" ] && eval "$extra"
  else
    echo "FAIL (HTTP $STATUS)"
    FAIL=1
  fi
}

echo "=== Production Smoke: $BASE ==="
echo "    IST date: $TODAY"

check "GET /"                      "$BASE/"
check "GET /data/dates.json"       "$BASE/data/dates.json" \
  "python3 -c \"import json; d=json.load(open('/tmp/smoke_body.txt')); print('  dates:', len(d.get('dates',[])))\" || true"
check "GET /data/status.json"      "$BASE/data/status.json"
check "GET /data/archive.json"     "$BASE/data/archive.json"
check "GET /api/health"            "$BASE/api/health" \
  "python3 -c \"import json; d=json.load(open('/tmp/smoke_body.txt')); print('  ok:', d.get('ok'))\" || true"
check "GET /api/public/stats"      "$BASE/api/public/stats" \
  "python3 -c \"import json; d=json.load(open('/tmp/smoke_body.txt')); print('  ok:', d.get('ok'), 'subs:', d.get('total_subscribers'))\" || true"
check "GET /data/issues/$TODAY.json" "$BASE/data/issues/$TODAY.json" \
  "python3 -c \"import json; d=json.load(open('/tmp/smoke_body.txt')); print('  sections:', d.get('total_sections'), 'items:', d.get('total_dashboard_items'))\" || true"

echo "--- POST /api/subscribe ---"
SUBR=$(curl -s -X POST "$BASE/api/subscribe" \
  -H "Content-Type: application/json" \
  -d '{"email":"production-smoke@example.com","source":"production_smoke"}')
echo "  response: $SUBR"
echo "$SUBR" | python3 -c "import json,sys; d=json.load(sys.stdin); exit(0 if d.get('ok') else 1)" || FAIL=1

if [ $FAIL -eq 0 ]; then
  echo ""
  echo "[PASS] All production smoke tests passed."
else
  echo ""
  echo "[FAIL] One or more smoke tests failed."
  exit 1
fi
