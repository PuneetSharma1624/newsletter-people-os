# PeopleOS Brief — Production Audit
Generated: 2026-06-05

---

## Issue 1: Subscribe spinner never stops
- **Symptom**: Spinner keeps rotating; button stays disabled indefinitely
- **Root cause**: No `AbortController` timeout on `fetch('/api/subscribe')`. If Vercel cold-starts or network hangs, the promise never rejects.
- **File(s)**: `landing/subscribe.js`
- **Layer**: Frontend
- **Fix applied**: Added 15s `AbortController` timeout; fixed spinner state management; removed dependency on `hidden` HTML attr (now uses `style.display` exclusively)
- **Verification**: Code review ✓
- **Remaining risk**: None if Supabase env vars are set

---

## Issue 2: Dashboard stuck on 2026-06-01
- **Symptom**: `dates.json` only lists `["2026-06-01","2026-05-31","2026-05-30","2026-05-29"]`; no issue file exists for 2026-06-05
- **Root cause**: GitHub Actions ran today (status.json shows started 2026-06-05T15:49 UTC) but `status.json` shows `generation_status: in_progress` — generation never completed. Most likely cause: missing GitHub Secrets (GROQ_API_KEY_1 or TAVILY_API_KEY)
- **File(s)**: `landing/data/dates.json`, `landing/data/status.json`
- **Layer**: GitHub Actions / content pipeline
- **Fix applied**: Workflows are architecturally correct. Secrets must be verified in GitHub Secrets settings.
- **Verification**: Manual — check GitHub Actions logs
- **Remaining risk**: HIGH — requires secrets to be set correctly

---

## Issue 3: Date fallback — no warning for stale URL param
- **Symptom**: `/?date=2026-06-01` works but no warning when date not available; no "Latest Brief" button to escape
- **Root cause**: `dashboard.js init()` calls `loadForDate(urlDate)` without checking availability
- **File(s)**: `landing/dashboard.js`
- **Layer**: Frontend
- **Fix applied**: Added availability check in `init()`, `showDateWarning()`, console debug logging, browser title update
- **Verification**: Code review ✓

---

## Issue 4: Analytics counts stale / wrong field names
- **Symptom**: Visitor count doesn't increment on refresh; subscriber count may be stale
- **Root cause**: (a) No no-cache headers on `/api/public/stats` or `/api/analytics/visit`; (b) Field names inconsistent — API returns `total_visits`, frontend expected `total_page_views`; (c) No `unique_visitors_today` returned
- **File(s)**: `api/analytics_visit.py`, `api/public_stats.py`, `landing/dashboard.js`
- **Layer**: Backend + Frontend
- **Fix applied**: Added `Cache-Control: no-store` headers; added `total_page_views`, `unique_visitors_today` fields; updated frontend to use correct field names; changed event_type insert to `page_view`
- **Verification**: Code review ✓
- **Remaining risk**: Low — depends on Supabase `site_analytics` table existing

---

## Issue 5: No action log system
- **Symptom**: When a button fails, no persistent record of what went wrong
- **Root cause**: System did not exist
- **File(s)**: `api/admin_action_log.py`, `api/admin_action_logs.py`, `supabase/schema.sql`
- **Layer**: Backend + Supabase
- **Fix applied**: Created action_logs table in schema.sql; created POST/GET API endpoints; integrated logAction() into admin.js
- **Verification**: Code review ✓
- **Remaining risk**: Requires `action_logs` table to be created in Supabase (run schema.sql migration v5)

---

## Issue 6: No demo refresh / admin test buttons
- **Symptom**: Admin cannot simulate refresh or test subscribe flow
- **Root cause**: Endpoints did not exist
- **File(s)**: `api/admin_demo_refresh.py`, `landing/admin.js`, `landing/admin/dashboard/index.html`
- **Layer**: Backend + Frontend
- **Fix applied**: Created demo refresh endpoint (local writes JSON, Vercel returns honest error); added admin buttons: Check Today's Issue, Check Production JSON, Refresh Public Stats, Test Subscribe, Simulate Demo Refresh, Trigger Production Refresh
- **Verification**: Code review ✓

---

## Issue 7: Hero design — cheap SVG illustration
- **Symptom**: `hero-night-scout.svg` (human with telescope) and `hills-layer.svg` (cartoon hills) look unprofessional
- **Root cause**: Complex illustration hand-coded as SVG
- **File(s)**: `landing/index.html`, `landing/style.css`
- **Layer**: Frontend / Design
- **Fix applied**: Replaced with pure CSS cosmic hero using radial gradients, aurora glows, star speckles, grain texture. Removed all SVG asset references from hero. Added Inter Tight font. No copyrighted artwork used.
- **Verification**: Visual — requires browser preview
- **Remaining risk**: Low — purely CSS

---

## Issue 8: vercel.json missing routes for new endpoints
- **Symptom**: New admin endpoints would 404
- **Root cause**: Not added
- **File(s)**: `vercel.json`
- **Layer**: Vercel
- **Fix applied**: Added builds + routes for `admin_action_log.py`, `admin_action_logs.py`, `admin_demo_refresh.py`
- **Verification**: Code review ✓

---

## Remaining Manual Steps Required

### GitHub Secrets (Settings → Secrets → Actions)
Verify ALL of these exist:
```
GROQ_API_KEY_1          — required for generation
TAVILY_API_KEY          — required for search
RESEND_API_KEY          — required for email send
SUPABASE_URL            — required for analytics + subscribe
SUPABASE_SERVICE_ROLE_KEY — required for analytics + subscribe
NEWSLETTER_FROM_EMAIL   — required for email send
NEWSLETTER_REPLY_TO     — required for email send
BASE_URL                — your production domain (no trailing slash)
ADMIN_TRIGGER_TOKEN     — for admin dashboard auth
GITHUB_PAT_FOR_WORKFLOW_DISPATCH — for admin trigger button
```

### Vercel Env Vars (same secrets, must be added separately)
Same list as above — GitHub Secrets and Vercel Env Vars are separate.

### Supabase SQL Editor
Run the full `supabase/schema.sql` including migration v5 (action_logs table).

### Trigger first manual run
After setting secrets:
```
GitHub → Actions → "1. Generate Brief — 7:00 AM IST" → Run workflow → force=true
```
Then check `landing/data/dates.json` includes today's date.
