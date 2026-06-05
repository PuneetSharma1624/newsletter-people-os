#!/usr/bin/env bash
# Local smoke test — run from repo root
set -e

echo "=== PeopleOS Brief — Local Smoke Test ==="

echo "--- 1. pytest ---"
pytest tests/ -v

echo "--- 2. Preflight ---"
python newsletter/main.py --preflight || echo "WARN: preflight failed (expected without full .env)"

echo "--- 3. Seed demo ---"
python newsletter/main.py --seed-demo

echo "--- 4. Refresh index ---"
python newsletter/main.py --refresh-index

echo "--- 5. Audit links ---"
python newsletter/main.py --audit-links || echo "WARN: link audit found issues (expected in demo data)"

echo "--- 6. Check today (demo) ---"
python newsletter/main.py --check-today || echo "INFO: today not generated yet (expected in local dev)"

echo "=== Local smoke complete ==="
