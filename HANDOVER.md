# PeopleOS Brief — Project Handover

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

## 5b. Section Filtering

Dashboard supports URL-based section filtering:

```
/?section=ai_research_papers
/?section=hr_news_india
/?section=ai_news
/?section=global_hr_news
/?section=macroeconomics
/?date=2026-05-30&section=ai_research_papers
```

**Behavior:**
- Section Command Center (12 large clickable cards) renders between issue header and article feed
- Clicking a section card → filters to that section only, updates URL `?section=`
- "All Sections" button → shows all 12 sections, removes `?section=` from URL
- Slim filter bar below date bar also works as secondary navigation
- Active section card is highlighted with its category color

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
python newsletter/main.py --dry-run
python newsletter/main.py --dry-run --force
python newsletter/main.py --generate-today
python newsletter/main.py --generate-today --force
python newsletter/main.py --backfill-initial
python newsletter/main.py --seed-demo
python newsletter/main.py --refresh-index
python newsletter/main.py --prune-archive
```

- `--dry-run`: Search + generate S1–S12 section by section. Print 72/24 items. No save, no email.
- `--generate-today`: Generate and save today's issue. Skip if already complete unless `--force`.
- `--backfill-initial`: Generate last 3 days if archive is empty.
- `--seed-demo`: Seed demo issue data.
- `--refresh-index`: Rebuild archive.json and dates.json from issue files.
- `--prune-archive`: Delete issues older than ARCHIVE_RETENTION_DAYS.

---

## 9. Email Commands

```bash
# Test email (no live send)
python newsletter/main.py --test heyypuneet@gmail.com

# Live send to all active subscribers (requires Supabase preflight to pass)
python newsletter/main.py --send-live
```

`--send-live` runs Supabase preflight first. If Supabase URL/key/table not configured, it exits cleanly with instructions.

---

## 10. GitHub Actions

File: `.github/workflows/daily-brief.yml`

Cron: `30 1 * * *` = 1:30 AM UTC = 7:00 AM IST

Manual dispatch inputs: `dry_run`, `generate_today`, `test_email`, `send_live`, `backfill_initial`, `prune_archive`

Manual trigger must **not** accidentally send live emails. `send_live` input requires explicit `true`.

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
