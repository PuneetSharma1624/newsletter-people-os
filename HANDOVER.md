# PeopleOS Brief — Project Handover

---

## ⚠️ Known Production Issues (as of June 1, 2026)

### 1. Dashboard does not update automatically
- **Symptom:** Production dashboard shows old issue date. `/?date=2026-06-01` returns nothing or shows fallback.
- **Root cause:** `landing/data/issues/YYYY-MM-DD.json` was generated locally but **never committed and pushed** to GitHub. Vercel only serves files that are in the repo. The 7:00 AM GitHub Actions workflow (`generate-brief-0700.yml`) must commit and push `landing/data/` after generation.
- **Status:** Workflow exists and is configured correctly. Manual trigger needed to confirm end-to-end. The scheduled cron (`30 1 * * *`) has not been verified live yet.
- **Manual fix:**
  ```bash
  python newsletter/main.py --generate-today --force
  python newsletter/main.py --check-today
  git add landing/data/
  git commit -m "Generate PeopleOS Brief for YYYY-MM-DD"
  git push origin main
  ```
  After push, Vercel redeploys in ~1-2 min. Then `/?date=YYYY-MM-DD` works.

### 2. Subscribe button not working
- **Symptom:** Spinner shows, then error message: "Something went wrong. Please try again." or "Subscription error: ...". Spinner may stay visible after error.
- **Root cause A — backend:** `api/subscribe.py` was originally written with old Vercel function-handler format (`def handler(request, response=None)`) which is incompatible with the current runtime. Rewritten as `BaseHTTPRequestHandler` using `supabase-py` client. Now returns descriptive errors.
- **Root cause B — spinner CSS:** `.loader { display: inline-block }` in `style.css` overrides the HTML `hidden` attribute. Fixed by switching to `element.style.display` instead of `element.hidden` in `subscribe.js`.
- **Status:** Both fixes committed and pushed (`fd5a899`). Needs production verification.
- **If still failing after deploy:** The actual error text will now appear in the UI. Common causes:
  - `SUPABASE_URL` or `SUPABASE_SERVICE_ROLE_KEY` not set in Vercel env vars → shows "not configured"
  - `subscribers` table not created → shows "table not found. Run supabase/schema.sql"
  - Invalid API key → shows "authentication failed"
- **Verification:**
  ```bash
  curl -i -X POST https://YOUR_DOMAIN/api/subscribe \
    -H "Content-Type: application/json" \
    -d '{"email":"test@example.com","source":"dashboard"}'
  ```

---

## 1. Product Overview

**PeopleOS Brief** is a dashboard-first daily executive intelligence product.

12-section daily intelligence dashboard across markets, AI, HR, research, economics, and major updates.

Two layers:
1. **Public Dashboard** — full 12-section daily intelligence experience at `/`
2. **Email Digest** — top 2 items from each section (24 items) sent via Resend

Dashboard is the main product. Subscription is a supporting CTA block.

---

## 2. Dashboard-First Principle

**Correct flow:**
```
Visitor opens site
→ sees full dashboard immediately
→ reads 12 sections × 6 items = 72 cards
→ browses archive
→ subscribes if useful
```

**Wrong flow (do not revert to this):**
```
Visitor opens site
→ sees only subscribe form
→ dashboard hidden or behind paywall
```

`/` must always be the dashboard first.

---

## 3. Architecture

```
GitHub Actions at 7:00 AM IST (cron: 30 1 * * *)
→ Search sources section-by-section (Tavily)
→ Generate S1–S12 one-by-one (Groq)
→ Save landing/data/issues/YYYY-MM-DD.json
→ Update landing/data/archive.json and dates.json
→ Commit + push to GitHub
→ Vercel redeploys automatically
→ Guests read static JSON (no API calls)
→ Email digest sent to Supabase subscribers via Resend
```

Public visitors: **only read static JSON**. Never trigger Tavily, Groq, Resend, or Supabase.

---

## 4. Section Taxonomy (exactly 12)

| Code | Section            |
|------|--------------------|
| S1   | India Stock Market |
| S2   | US Stock Market    |
| S3   | Global Markets     |
| S4   | AI News            |
| S5   | AI Research Papers |
| S6   | Trending Topics    |
| S7   | HR News India      |
| S8   | Global HR News     |
| S9   | HR Research Papers |
| S10  | Macroeconomics     |
| S11  | Microeconomics     |
| S12  | Major Updates      |

- Dashboard: 12 × 6 = **72 items**
- Email digest: 12 × 2 = **24 items**

---

## 5. Static Data Model

```
landing/data/
├── archive.json       ← list of all issues with metadata
├── dates.json         ← { "dates": ["2026-05-30", "2026-05-29", ...] }
├── status.json        ← generation status
└── issues/
    ├── 2026-05-30.json
    ├── 2026-05-29.json
    └── 2026-05-28.json
```

Issue JSON structure:
```json
{
  "issue_date": "2026-05-30",
  "title": "PeopleOS Brief — 2026-05-30",
  "subject": "PeopleOS Brief — Markets, AI, HR & Economy Intelligence",
  "preheader": "...",
  "executive_summary": "...",
  "total_sections": 12,
  "total_dashboard_items": 72,
  "total_email_items": 24,
  "sections": [
    {
      "code": "S1",
      "section_id": "india_stock_market",
      "section_name": "India Stock Market",
      "section_summary": "...",
      "items": [ ...6 items... ]
    }
  ]
}
```

---

## 5b. Section Filtering & Navigation

Dashboard supports URL-based section filtering:

```
/?section=ai_research_papers
/?section=hr_news_india
/?section=ai_news
/?section=global_hr_news
/?section=macroeconomics
/?date=2026-05-30&section=ai_research_papers
```

**Behavior (updated May 2026):**
- Section Command Center (12 bento-grid cards) renders between issue header and article feed
- Clicking a section card → filters to that section, updates URL `?section=`, **scrolls directly to that section's feed**
- Selected Section Banner appears between command center and article panel showing: section code, name, description, category, update count, and "← All Sections" button
- "All Sections" button (command center or banner) → shows all 12 sections, removes `?section=` from URL, hides banner
- Slim filter bar below date bar also works as secondary navigation (also triggers scroll)
- On page load with `?section=`, after data loads and renders, auto-scrolls to selected section
- Unknown section IDs gracefully fall back to all-sections mode
- Each article panel `div` has `id="section-{section_id}"` for direct anchor targeting
- `scroll-margin-top: 170px` on `.section-card` accounts for sticky nav + date bar + filter bar

**Section IDs → category colors:**
| Section ID | Code | Category | Color |
|---|---|---|---|
| india_stock_market | S1 | markets | blue |
| us_stock_market | S2 | markets | blue |
| global_markets | S3 | markets | blue |
| ai_news | S4 | ai | purple |
| ai_research_papers | S5 | ai | purple |
| trending_topics | S6 | trending | amber |
| hr_news_india | S7 | hr | green |
| global_hr_news | S8 | hr | green |
| hr_research_papers | S9 | hr | green |
| macroeconomics | S10 | econ | orange |
| microeconomics | S11 | econ | orange |
| major_updates | S12 | major | red |

**Troubleshooting — section filter not working:**
- Check `dashboard.js` loaded (no 404 in browser network tab)
- Check `sectionCommand` div exists in `index.html`
- Check issue JSON has `section_id` fields matching the IDs above
- If section command center empty, issue JSON may have 0 items

---

## 5c. Admin Access

**Admin login:** `http://localhost:5124/admin/` (local) or `/admin/` (production)

**Admin dashboard:** `http://localhost:5124/admin/dashboard/` (local) or `/admin/dashboard/` (production)

Admin link visible in: top nav (dim text, between Archive and Subscribe) and footer.

**Manual generation buttons (admin dashboard):**
- Generate Today's Brief
- Force Regenerate
- Send Test Email
- Trigger Live Send (requires confirm)
- Backfill 3 Days
- Dry Run
- Refresh Archive Index

**Admin trigger flow:** Admin button → `POST /api/admin/trigger` → GitHub Actions `workflow_dispatch` → generation runs in Actions (not browser, avoids Vercel timeout).

**Required env vars for admin:**
```
ADMIN_TRIGGER_TOKEN=
GITHUB_OWNER=
GITHUB_REPO=
GITHUB_WORKFLOW_FILE=
GITHUB_PAT_FOR_WORKFLOW_DISPATCH=
```

If GitHub dispatch not configured, admin dashboard shows: "GitHub workflow dispatch is not configured. Add GITHUB_PAT_FOR_WORKFLOW_DISPATCH, GITHUB_OWNER, GITHUB_REPO, and GITHUB_WORKFLOW_FILE."

**Troubleshooting — admin login not appearing:**
- Check `landing/admin/index.html` exists (not `landing/admin.html`)
- Use trailing slash locally: `http://localhost:5124/admin/`
- Check Vercel route `/admin/?` maps to `landing/admin/index.html`

---

## 6. Folder Structure

```
landing/
├── index.html              ← MAIN DASHBOARD (dashboard-first)
├── style.css
├── brief.css
├── archive.css
├── dashboard.js            ← loads static JSON, renders 12 sections
├── subscribe.js            ← subscribe form handler
├── archive.js              ← archive page JS
├── admin.js                ← admin panel JS
├── data/
│   ├── archive.json
│   ├── dates.json
│   ├── status.json
│   └── issues/
│       └── YYYY-MM-DD.json
├── brief/
│   └── index.html          ← dashboard alias (same UI as /)
├── archive/
│   └── index.html          ← archive page
└── admin/
    ├── index.html          ← admin login
    └── dashboard/
        └── index.html      ← admin control panel
```

---

## 7. Local Preview

```bash
python -m http.server 5124 --directory landing
```

Open (use trailing slash for folder routes):
```
http://localhost:5124/              ← full dashboard
http://localhost:5124/brief/        ← dashboard alias
http://localhost:5124/archive/      ← archive
http://localhost:5124/admin/        ← admin login
http://localhost:5124/data/dates.json
```

**Note:** Python http.server requires trailing slash for folder routes. `/brief` returns 404 locally; `/brief/` works. Vercel handles both.

---

## 8. Generation Commands

```bash
# Standard
python newsletter/main.py --dry-run
python newsletter/main.py --generate-today
python newsletter/main.py --generate-today --force
python newsletter/main.py --backfill-initial
python newsletter/main.py --seed-demo
python newsletter/main.py --refresh-index
python newsletter/main.py --prune-archive

# Reliability commands (used by automation)
python newsletter/main.py --check-today           # validate completeness, exit 0=ok 1=fail
python newsletter/main.py --ensure-today          # generate only if missing/incomplete
python newsletter/main.py --send-live-today        # send today's issue with all safety checks
python newsletter/main.py --mark-generation-started
python newsletter/main.py --mark-generation-failed --error-msg "reason"
```

**Reliability command details:**

| Command | Behaviour |
|---|---|
| `--check-today` | Uses IST date. Validates issue: exists, 12 sections, 72 items, 24 email items, all fields, in dates/archive/status. Exit 0=ok, 1=fail. |
| `--ensure-today` | Checks if complete. If yes, skips. If in_progress <30m, waits. If stale >45m, forces. Runs `--generate-today --force` if needed. |
| `--send-live-today` | Checks completeness → checks production URL (5 retries × 2min) → checks Supabase duplicate send → sends. Never sends stale issue. |
| `--mark-generation-started` | Writes `in_progress` to status.json with timestamp. |
| `--mark-generation-failed` | Writes `failed` to status.json with error message. |

---

## 9. Email Commands

```bash
# Test email (no live send)
python newsletter/main.py --test heyypuneet@gmail.com

# Legacy live send (no production availability check)
python newsletter/main.py --send-live

# Safe live send for today only (recommended — used by automation)
python newsletter/main.py --send-live-today
```

`--send-live-today` is the production command used by the 7:30 workflow. It:
1. Validates today's issue completeness
2. Checks production URL is live (5 retries × 2 min)
3. Checks Supabase for duplicate sends
4. Sends only today's issue (never yesterday)

---

## 10. GitHub Actions (Three-Stage Automation)

### Schedule

| Time (IST) | UTC Cron | Workflow File | Purpose |
|---|---|---|---|
| 7:00 AM | `30 1 * * *` | `generate-brief-0700.yml` | Generate + publish today's brief |
| 7:15 AM | `45 1 * * *` | `check-and-retry-0715.yml` | Verify + retry if missing/incomplete |
| 7:30 AM | `0 2 * * *` | `send-newsletter-0730.yml` | Send newsletter (today only) |

### Concurrency

All three workflows share concurrency group `peopleos-brief-daily-${{ github.ref }}` with `cancel-in-progress: false`. This prevents 7:00 and 7:15 from running generation simultaneously. If 7:00 is still running when 7:15 triggers, 7:15 will queue and wait.

### Duplicate Generation Prevention

- `--ensure-today` checks `status.json` before generating
- If `generation_status=in_progress` and started <30 min ago → skip
- If `generation_status=in_progress` and started >45 min ago → treat as stale, retry
- GitHub Actions concurrency group prevents parallel runs

### Duplicate Email Prevention

- `send_log` table tracks `issue_date` + `send_type` per subscriber
- `--send-live-today` calls `already_sent_today(date)` before sending
- If any successful live send exists for today → skip entire batch

### Retry Logic (7:15)

- If `--check-today` passes → print "No retry needed", exit
- If `--check-today` fails → run `--ensure-today` with `GENERATION_ATTEMPT=retry_0715`
- Commit + push if files changed
- status.json `last_generation_attempt` set to `retry_0715`

### Production Availability Check (7:30)

Before sending, `--send-live-today` hits `{BASE_URL}/data/issues/YYYY-MM-DD.json`:
- Validates HTTP 200, valid JSON, correct date, 12 sections, 72 items
- Retries 5 times with 2-minute waits (covers Vercel deploy time)
- If still unavailable → sets `email_status=skipped_issue_not_deployed`, exits

### Manual Recovery

If today's issue does not appear:
```bash
python newsletter/main.py --ensure-today
python newsletter/main.py --check-today
git add landing/data/
git commit -m "Generate PeopleOS Brief for YYYY-MM-DD"
git push origin main
```

If issue exists but email did not go out:
```bash
python newsletter/main.py --check-today
python newsletter/main.py --send-live-today
```

### Legacy workflows

`daily-brief.yml` and `newsletter.yml` still exist for manual one-off use. The three new workflows replace their scheduled behaviour.

---

## 11. Vercel Deployment

1. Push repo root to GitHub (not just `landing/`)
2. Vercel → New Project → import repo root
3. Add all environment variables
4. Deploy
5. Confirm routes: `/`, `/brief`, `/archive`, `/admin`, `/admin/dashboard`

Routes configured in `vercel.json`. Both `/brief` and `/brief/` work in production.

---

## 12. Supabase Setup

Supabase used for: subscribers, unsubscribe records, send logs.

Public dashboard does NOT depend on Supabase.

**Before `--send-live`:**
1. Run `supabase/schema.sql` in Supabase SQL editor
2. Verify `SUPABASE_URL` in `.env`
3. Verify `SUPABASE_SERVICE_ROLE_KEY` in `.env`
4. Test: `python newsletter/main.py --send-live` (preflight runs automatically)

**Known error (now handled cleanly):**
```
PGRST125 Invalid path specified in request URL
```
Now shows actionable error instead of traceback.

---

## 13. Admin Dashboard

URLs:
- `/admin/` — login (token-based)
- `/admin/dashboard/` — control panel

Admin triggers GitHub Actions `workflow_dispatch`. Generation runs in Actions, not in Vercel (avoids timeout).

Requires: `GITHUB_OWNER`, `GITHUB_REPO`, `GITHUB_PAT_FOR_WORKFLOW_DISPATCH`, `ADMIN_TRIGGER_TOKEN` in env.

---

## 14. Environment Variables

```env
GROQ_API_KEY_1=
GROQ_API_KEY_2=
GROQ_API_KEY_3=
TAVILY_API_KEY=
RESEND_API_KEY=
SUPABASE_URL=
SUPABASE_ANON_KEY=
SUPABASE_SERVICE_ROLE_KEY=
NEWSLETTER_FROM_EMAIL=
NEWSLETTER_REPLY_TO=
BASE_URL=
ADMIN_EMAIL=
ADMIN_PASSWORD_HASH=
ADMIN_SESSION_SECRET=
ADMIN_TRIGGER_TOKEN=
GITHUB_OWNER=
GITHUB_REPO=
GITHUB_WORKFLOW_FILE=
GITHUB_PAT_FOR_WORKFLOW_DISPATCH=
ARCHIVE_RETENTION_DAYS=180
SECTION_SEARCH_DELAY_SECONDS=3
GROQ_SECTION_DELAY_SECONDS=15
GROQ_RETRY_DELAY_SECONDS=20
GROQ_KEY_COOLDOWN_SECONDS=20
```

Never expose secrets in frontend JavaScript.

---

## 15. Archive Retention

Default: 180 days (180 × 72 = 12,960 archived cards)

```bash
python newsletter/main.py --prune-archive
```

Options: 90 days (lightweight MVP), 180 days (recommended), 365 days (deep archive).

---

## 15b. Source Link Integrity

Every article card links to the **exact article URL** from the Tavily search result — never the publisher homepage.

**How it works:**
1. `searcher.py` assigns each candidate a `source_id` (e.g. `S1-003`) and stores the exact `source_url`
2. `generator.py` passes only `source_id` to Groq — never asks Groq for a URL
3. After Groq responds, Python maps `source_id` → original `source_url` from the candidate list
4. Static JSON stores the exact URL; dashboard renders `item.source_url` as the `<a href>`

**Groq never writes URLs.** This prevents hallucinated homepage links.

**Audit command:**
```bash
python newsletter/main.py --audit-links
```
Scans all `landing/data/issues/*.json` and reports any homepage or missing URLs.

**URL validation functions** in `newsletter/utils.py`:
- `is_probably_homepage_url(url)` — flags bare domains and single-segment paths
- `validate_article_url(url)` — returns `{"is_valid_article_url": bool, "reason": str}`

**Tests:** `tests/test_source_links.py` — 24 tests covering URL validation, demo data integrity, dashboard.js uses `source_url`, renderer.py uses `source_url`.

---

## 15c. Vercel Python Entrypoint

All files in `api/` that Vercel invokes as serverless functions must expose a top-level `handler`, `app`, or `application` name.

Every handler file ends with:
```python
app = handler
application = handler
```

**Files patched:**
- `api/subscribe.py`
- `api/unsubscribe.py`
- `api/admin_login.py`
- `api/admin_status.py`
- `api/admin_trigger.py`
- `api/archive_list.py`
- `api/dates.py`
- `api/issue.py`
- `api/latest_brief.py`

`api/demo_data.py` is a data module — not a serverless function, no handler needed.

---

## 16. Troubleshooting

**`/brief` returns 404 locally**
Python http.server needs trailing slash. Use `http://localhost:5124/brief/`. Vercel handles both.

**`/` shows subscribe page instead of dashboard**
`landing/index.html` was reverted. It must be the dashboard. Do not replace with subscribe-only page.

**Dashboard empty**
```bash
python newsletter/main.py --seed-demo
python newsletter/main.py --refresh-index
```
Then check `landing/data/issues/` contains at least 3 files.

**Groq 413 token error**
Sections sent as one prompt. Fix: generate one section at a time (already implemented).

**Live send fails with PGRST125**
Supabase misconfigured. Run schema.sql, verify URL/key, rerun `--send-live`.

**Dashboard shows 0 sections**
`dashboard.js` failed to load `/data/dates.json`. Check file exists and server is running from `landing/` directory.

---

## 17. Known Limitations

1. Live send requires Supabase schema and credentials to be correct.
2. Resend requires verified sender domain for production deliverability.
3. Admin GitHub Actions trigger requires GitHub PAT and workflow configuration.
4. Local Python server requires trailing slash for folder routes.
5. Public dashboard updates after generation + commit + Vercel redeploy (not real-time).
6. Real-time updates intentionally avoided for MVP stability.

---

## 18c. Analytics & Subscriber Layer (May 2026)

### Architecture
Visitor and subscriber counts stored in Supabase (stateless Vercel functions can't use memory).
Public dashboard remains 100% static JSON — API calls are non-blocking and fail gracefully.

### Public API endpoints
| Endpoint | Method | Auth | Purpose |
|---|---|---|---|
| `/api/analytics/visit` | POST | None | Record visit, return aggregate counts |
| `/api/public/stats` | GET | None | Total visits + subscribers only |

Both return `{ ok, total_visits, total_subscribers }`. Never return emails or PII.

### Admin API endpoints
| Endpoint | Method | Auth | Purpose |
|---|---|---|---|
| `/api/admin/stats` | GET | Bearer token | Detailed visitor + subscriber stats |
| `/api/admin/notifications` | GET | Bearer token | New subscribers since last admin view |
| `/api/admin/notifications/mark-seen` | POST | Bearer token | Reset notification badge |
| `/api/admin/subscribers` | GET | Bearer token | Paginated subscriber list |

Query params for `/api/admin/subscribers`: `status=active|unsubscribed|all`, `since=YYYY-MM-DD`, `limit=200`

All admin endpoints return 401 if missing/wrong token. Return 503 if Supabase not configured.

### Privacy
- Raw IP addresses never stored
- Visitor hash = `sha256(user_agent + coarse_date)[:16]` — server-side only
- Public endpoints return only aggregate counts

### Supabase schema additions (schema.sql v3)
Run the new migration block in Supabase SQL Editor:
```sql
-- New tables:
-- site_analytics   (visit events, no PII)
-- admin_notification_state  (single-row bell badge state, id='default')

-- New column on subscribers:
-- last_email_sent_at TIMESTAMPTZ
```

Migration is fully idempotent (`CREATE TABLE IF NOT EXISTS`, `ADD COLUMN IF NOT EXISTS`).

### Frontend behavior
**Dashboard (`dashboard.js`):**
- On load, `POST /api/analytics/visit` — non-blocking
- Updates `#kpiVisitorsVal` and `#kpiSubscribersVal` KPI cards
- Dashboard renders even if API fails (shows `—`)

**Subscribe module (`subscribe.js`):**
- On load, `GET /api/public/stats` → updates `#readerCountLine`
- Copy: `"Join N readers getting the executive cut every morning."`
- After successful subscribe, re-fetches count

**Admin dashboard (`admin.js`):**
- On load: `loadAdminStats()`, `loadNotifications()`, `loadStatus()`
- Notification bell shows badge count of new subscribers since last mark-seen
- Click bell → dropdown with subscriber emails + timestamps
- "Mark as seen" → `POST /api/admin/notifications/mark-seen` → badge clears
- Subscribers tab → table with status/source/date filters
- Tab switching: Overview | Subscribers

### Admin notification state
`admin_notification_state` table has one row `id='default'`.
`last_seen_subscriber_at` is updated each time admin clicks "Mark as seen".
New subscribers = those with `created_at > last_seen_subscriber_at`.

### Local testing
```bash
# Static UI only (no API):
python -m http.server 5124 --directory landing

# Full API testing:
vercel dev

# Test endpoints:
curl -X POST http://localhost:3000/api/analytics/visit
curl http://localhost:3000/api/public/stats
curl -H "Authorization: Bearer YOUR_TOKEN" http://localhost:3000/api/admin/stats
curl -H "Authorization: Bearer YOUR_TOKEN" http://localhost:3000/api/admin/subscribers
curl -H "Authorization: Bearer YOUR_TOKEN" http://localhost:3000/api/admin/notifications
curl -X POST -H "Authorization: Bearer YOUR_TOKEN" http://localhost:3000/api/admin/notifications/mark-seen
```

### Deployment checklist
1. Run schema migration v3 in Supabase SQL Editor
2. Confirm `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` are in Vercel env vars
3. Push to GitHub → Vercel redeploys
4. Visit `/` → check visitor KPI card increments
5. Subscribe → check reader count updates
6. Visit `/admin/dashboard/` → check analytics KPI strip
7. Check notification bell shows new subscriber count
8. Open Subscribers tab → confirm table loads

## 18b. Design System (May 2026 Premium Redesign)

**Direction:** Linear-inspired premium AI command center. Vercel/Geist-level typography. Dark SaaS, executive, boardroom-ready.

**CSS files:**
- `style.css` — design system tokens (CSS variables), shared nav, buttons, subscribe form, footer
- `brief.css` — dashboard-specific: date bar, section command, section panels, article cards, banners
- `archive.css` — archive page styles

**Key CSS variables:**
```css
--bg-base: #080c15        /* deepest background */
--bg-elevated: #141b2d    /* cards, panels */
--accent: #6366f1         /* indigo primary */
--border-subtle: rgba(255,255,255,0.05)
--border-default: rgba(255,255,255,0.09)
```

**Category color system:**
- Markets (S1–S3): `#3b82f6` blue
- AI (S4–S5): `#a855f7` purple
- Trending (S6): `#f59e0b` amber
- HR (S7–S9): `#10b981` emerald
- Economics (S10–S11): `#f97316` orange
- Major Updates (S12): `#ef4444` red

**Button system:** `.btn-primary`, `.btn-secondary`, `.btn-ghost`, `.btn-danger` — consistent across all pages.

**Body background:** radial indigo gradient glow from top (`background-attachment: fixed`).

**Nav:** glass morphism (`backdrop-filter: blur(20px)`, `rgba(8,12,21,0.88)`), height 54px, sticky z-index 300.

**Article cards:** structured insight rows with `.insight-tag.why/lens/action` labels, credibility dot, premium source pill.

**Section command center:** bento grid `repeat(auto-fill, minmax(175px, 1fr))`, category-colored top border per card, active card gets category-colored ring.

**Selected Section Banner (`.selected-section-banner`):** appears between command center and article feed when section active. Shows section code, name, description, category, count, and All Sections button.

**Admin pages:**
- Login: glass card `var(--bg-elevated)` with accent glow dot, indigo button system
- Dashboard: control-room style, inline status grid, action buttons, log panel

**Acceptance checklist (verified design direction):**
- [x] `/` loads premium dark dashboard
- [x] Clicking section card scrolls directly to that section's feed
- [x] `?section=` URL param auto-scrolls on load
- [x] All Sections restores full view
- [x] Selected section banner shows with correct metadata
- [x] Archive loads with premium issue cards
- [x] Admin login is a glass card (no raw HTML feel)
- [x] Admin dashboard is control-room style
- [x] Subscribe form follows design system
- [x] No secrets in frontend JS
- [x] Mobile-friendly (768px and 480px breakpoints)

## 18. Exact Next Steps

1. Run local server: `python -m http.server 5124 --directory landing`
2. Open `http://localhost:5124/` — confirm dashboard shows 12 sections and 72 cards
3. Open `http://localhost:5124/brief/` — same dashboard
4. Open `http://localhost:5124/archive/` — archive page
5. Open `http://localhost:5124/admin/` — admin login
6. Push to GitHub → Vercel deploys automatically
7. Configure Supabase: run schema.sql, set env vars
8. Test live send: `python newsletter/main.py --send-live` (preflight will validate)
9. Configure GitHub Actions secrets for daily automation
