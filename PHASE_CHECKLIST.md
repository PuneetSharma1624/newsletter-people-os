# PeopleOS Brief — Phase Checklist

---

## Phase 0: Repository Inspection and Planning
**Status:** ✅ COMPLETE

- Inspected repo: fresh (only .claude/settings.local.json existed)
- No existing useful files to preserve
- Directory structure created
- Implementation plan written

---

## Phase 1: Project Skeleton and Configuration
**Status:** ✅ COMPLETE

**Completed**
- `requirements.txt` — all 6 dependencies
- `.env.example` — 11 env vars documented
- `.gitignore` — secrets, pyc, venv, logs excluded
- `newsletter/__init__.py`
- `newsletter/config.py` — validate_config(), fail-fast on missing vars, accessors
- `newsletter/logger.py` — structured logging, no secrets logged
- `newsletter/utils.py` — normalize_email(), is_valid_email(), generate_token()

**Checked**
- `python -m compileall newsletter` → PASS
- Secrets excluded from Git via .gitignore ✓
- Config fails fast with helpful error when vars missing ✓

**Fixed**
- Nothing required

---

## Phase 2: Supabase Schema and Data Layer
**Status:** ✅ COMPLETE

**Completed**
- `supabase/schema.sql` — subscribers, newsletter_issues, send_log tables
- Uniqueness constraints: email, unsubscribe_token, (issue_id, subscriber_id)
- `upsert_subscriber()` SQL function — handles new/reactivation/already_active
- CHECK constraints: status IN ('active','unsubscribed')
- Indexes on all required columns
- RLS notes documented in SQL comments
- `newsletter/subscribers.py` — upsert, get_active, get_by_token, unsubscribe_by_token, already_sent, log_send
- `newsletter/archive.py` — get_issue_by_date, save_issue, mark_sent, get_or_create_issue

**Checked**
- All 3 tables present ✓
- UNIQUE(issue_id, subscriber_id) on send_log ✓
- Unsubscribed users excluded via status='active' filter ✓
- Application-level already_sent() guard ✓
- `python -m compileall newsletter` → PASS

---

## Phase 3: Subscribe and Unsubscribe APIs
**Status:** ✅ COMPLETE

**Completed**
- `api/subscribe.py` — POST only, JSON parse, validate, normalize, upsert, CORS headers
- `api/unsubscribe.py` — GET with token, HTML confirmation, no row deletion
- Invalid emails → 400 JSON error
- Duplicate active → 200 "already subscribed"
- Unsubscribed user re-subscribing → reactivated
- Invalid unsubscribe token → HTML error page (no stack trace exposed)

**Checked**
- POST-only enforced ✓
- GET-only for unsubscribe ✓
- No internal errors exposed to users ✓
- Secrets server-side only ✓
- `python -m compileall api newsletter` → PASS

---

## Phase 4: Landing Page and Vercel Routing
**Status:** ✅ COMPLETE

**Completed**
- `landing/index.html` — PeopleOS Brief branding, hero, form, topics, quote, footer
- `landing/style.css` — premium dark theme, Inter font, mobile responsive
- `landing/subscribe.js` — loading/success/error states, calls /api/subscribe
- `vercel.json` — correct routing: root→HTML, /api/*→Python, static assets

**Checked**
- Branding consistent ✓
- Form posts to /api/subscribe ✓
- Loading, success, error states ✓
- Mobile responsive via media query ✓
- Vercel routes root (not just landing/) ✓
- README must warn: deploy repo root not landing/ ✓ (documented)

---

## Phase 5: Search and Generation Pipeline
**Status:** ✅ COMPLETE

**Completed**
- `newsletter/searcher.py` — 8 Tavily queries, dedup by URL, graceful per-query failure
- `newsletter/generator.py` — Claude generation with system prompt, JSON parse, fallback parser
- Hallucination mitigation: system prompt instructs Claude to use only provided sources
- Handles empty sources gracefully (continues with warning)
- Handles malformed Claude output with fallback parse

**Checked**
- Sources deduplicated ✓
- Per-query failures don't crash pipeline ✓
- Claude output parsed with fallback ✓
- Editorial tone aligned with PeopleOS Brief ✓
- `python -m compileall newsletter` → PASS

---

## Phase 6: Email Sender and Newsletter CLI
**Status:** ✅ COMPLETE

**Completed**
- `newsletter/sender.py` — Resend send, unsubscribe link injection, preheader, List-Unsubscribe header
- `newsletter/main.py` — `--dry-run` / `--test EMAIL` / `--send-live` CLI
- Live mode: active subscribers only, skip already-sent, log per-subscriber result, continue on failure
- Test mode: single email, placeholder token, no DB log
- Dry run: no email, no DB write, print preview

**Checked**
- `--send-live` required explicitly ✓
- Test mode does not log to send_log ✓
- Live mode skips unsubscribed ✓
- Duplicate sends skipped at app level + DB constraint ✓
- Per-subscriber failure doesn't stop batch ✓
- CLI fails clearly on missing env vars ✓
- `python newsletter/main.py` (no args) → correct error ✓

---

## Phase 7: GitHub Actions Automation
**Status:** ✅ COMPLETE

**Completed**
- `.github/workflows/newsletter.yml`
- Cron: `30 1 * * *` = 01:30 UTC = 07:00 IST ✓
- `workflow_dispatch` with optional `test_email` input
- Manual + test_email → test mode ✓
- Manual + no email → dry-run ✓
- Scheduled cron → live mode ✓
- Environment validation step before send ✓
- Python 3.11 specified ✓
- All 10 secrets referenced ✓

**Checked**
- Cron UTC correct for 7:00 AM IST ✓
- No accidental live blast from manual trigger ✓
- Fail-fast env validation step ✓

---

## Phase 8: Tests
**Status:** ✅ COMPLETE

**Completed**
- `tests/test_email_validation.py` — 13 tests: valid emails, invalid emails, normalization
- `tests/test_unsubscribe_token.py` — 6 tests: length, alphanumeric, uniqueness, entropy
- `tests/test_idempotency.py` — 8 tests: normalize idempotent, upsert states, already_sent guard, test-mode no DB log

**Checked**
- `pytest tests/ -v` → 27 passed, 0 failed ✓
- No API keys required ✓
- External deps stubbed with MagicMock ✓

**Fixed**
- Initial 3 failures: patch target couldn't resolve module because supabase not installed → fixed by stubbing deps at module level before import

---

## Phase 9: README and Operational Documentation
**Status:** ✅ COMPLETE

**Completed**
- Product overview + brand positioning
- Architecture diagram
- File structure
- YOUR NEXT STEPS flow (user-friendly 8-step)
- Environment variable setup with security notes
- Supabase SQL setup instructions
- Vercel repo-root deployment warning (prominent)
- GitHub Secrets setup
- Local dry-run, test-send, live-send commands
- GitHub Actions schedule explanation
- Unsubscribe flow documentation
- Duplicate-send protection explanation
- Email deliverability notes
- Cost estimates (framed as approximate)
- Security notes
- Troubleshooting section
- Known limitations

---

## Phase 10: Final Validation Audit
**Status:** ✅ COMPLETE

**Commands run**
```
python -m compileall .    → PASS (all files)
pytest tests/ -v          → 27 passed, 0 failed
python newsletter/main.py → PASS (correct error: requires --dry-run|--test|--send-live)
```

**Security audit**
- SUPABASE_SERVICE_ROLE_KEY: server-side only ✓
- No secrets logged ✓
- Live send requires explicit --send-live ✓
- Unsubscribe tokens: secrets.choice (cryptographically secure) ✓
- Invalid emails rejected before DB ✓
- Unsubscribed users excluded at query level ✓

**Duplicate-send audit**
- Application guard: already_sent() before each send ✓
- DB constraint: UNIQUE(issue_id, subscriber_id) on send_log ✓
- Test mode: skips DB log entirely ✓

**Deployment audit**
- vercel.json routes repo root correctly ✓
- README warns about repo root deployment ✓
- Python API routes in /api/ not /landing/ ✓

**What could NOT be tested (API keys required)**
- Tavily search (TAVILY_API_KEY)
- Claude generation (ANTHROPIC_API_KEY)
- Resend email delivery (RESEND_API_KEY)
- Supabase read/write (SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY)
- Full --dry-run end-to-end (requires Tavily + Anthropic)
- Full --test end-to-end (requires all of above + Resend)
- Full --send-live end-to-end (requires all of above)

**Known limitations**
- No admin dashboard
- No bounce handling / auto-unsubscribe on hard bounces
- No email open/click tracking
- RLS disabled for MVP (documented)
- Live integrations untested without real API keys

---

## Final Status: HARDENED MVP ✅

All phases complete. All local checks pass. Live integrations require real API keys.
First command: `python newsletter/main.py --dry-run` (after filling .env)
