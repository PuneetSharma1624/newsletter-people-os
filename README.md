# PeopleOS Brief

**One sharp daily briefing on AI, work, leadership, and people systems — built for operators who do not have time for noise.**

By Puneet Sharma · *Where people strategy meets AI-native execution.*

---

## Product Overview

PeopleOS Brief is a daily newsletter that curates high-signal insights on:

- AI agents at work
- HR technology shifts
- Leadership and management systems
- Productivity workflows
- Human-agent operating models
- Workforce strategy and business transformation
- Future of work signals

**Brand:** Premium, modern, sharp, executive-friendly, AI-native, practical — not theoretical.

---

## Architecture Overview

```
Landing page (Vercel static)
    ↓ POST /api/subscribe
Subscribe API (Vercel Python serverless)
    ↓ Supabase (subscribers table)

GitHub Actions cron (daily 7:00 AM IST)
    ↓ Tavily search → Claude generation → Resend email
    ↓ Supabase (newsletter_issues + send_log tables)
```

**Status: Hardened MVP.** All code is production-grade. Live integrations require real API keys — see setup below.

---

## File Structure

```
peopleos-brief/
├── .github/workflows/newsletter.yml   # Daily cron + manual trigger
├── newsletter/
│   ├── main.py          # CLI: --dry-run / --test / --send-live
│   ├── config.py        # Env var validation and accessors
│   ├── searcher.py      # Tavily news search
│   ├── generator.py     # Claude newsletter generation
│   ├── sender.py        # Resend email sending
│   ├── subscribers.py   # Supabase subscriber data layer
│   ├── archive.py       # Supabase newsletter archive
│   ├── logger.py        # Structured logging (no secrets)
│   └── utils.py         # Email validation, token generation
├── api/
│   ├── subscribe.py     # POST /api/subscribe (Vercel serverless)
│   └── unsubscribe.py   # GET /api/unsubscribe?token=... (Vercel serverless)
├── landing/
│   ├── index.html       # Landing page
│   ├── style.css        # Premium dark theme
│   └── subscribe.js     # Form handler (calls /api/subscribe)
├── supabase/schema.sql  # Full DB schema with indexes + RLS notes
├── tests/               # Pytest tests (no API keys required)
├── requirements.txt
├── .env.example
├── vercel.json          # Routing: root → landing, /api/* → Python
└── README.md
```

---

## YOUR NEXT STEPS

```
1. GET API KEYS:
   - Groq (3 keys): console.groq.com
   - Tavily: tavily.com
   - Resend: resend.com
   - Supabase: supabase.com

2. FILL IN .env:
   Copy from .env.example.

3. RUN SUPABASE SQL:
   Run supabase/schema.sql in your Supabase dashboard.

4. TEST LOCALLY:
   python newsletter/main.py --dry-run
   python newsletter/main.py --test your@email.com

5. DEPLOY LANDING PAGE AND API:
   Push to GitHub.
   Go to Vercel.
   Import the repo ROOT (not the landing folder).
   Deploy.

6. ADD GITHUB SECRETS:
   Add all required secrets in GitHub repository settings.

7. FIRST LIVE TEST:
   GitHub Actions → PeopleOS Brief → Run workflow.
   Enter your email in test_email.
   Confirm test email delivery.

8. GO LIVE:
   Confirm domain, sender, unsubscribe, and test email.
   The cron runs automatically every day at 7:00 AM IST.
   Share your Vercel URL.
```

---

## Environment Variable Setup

Copy `.env.example` to `.env` and fill in all values:

```env
GROQ_API_KEY_1=            # From console.groq.com — primary key
GROQ_API_KEY_2=            # Second key (optional but recommended for rotation)
GROQ_API_KEY_3=            # Third key (optional but recommended for rotation)
TAVILY_API_KEY=            # From tavily.com
RESEND_API_KEY=            # From resend.com
SUPABASE_URL=              # From Supabase project settings
SUPABASE_ANON_KEY=         # From Supabase project settings (public)
SUPABASE_SERVICE_ROLE_KEY= # From Supabase project settings (SECRET — never expose to frontend)
NEWSLETTER_FROM_EMAIL=     # Verified sender email (must be verified in Resend)
NEWSLETTER_REPLY_TO=       # Reply-to address (can match from email)
BASE_URL=                  # Your Vercel URL e.g. https://peopleos-brief.vercel.app
ADMIN_TEST_EMAIL=          # Your personal email for test sends
NEWSLETTER_NAME=PeopleOS Brief
```

**Security rule:** `SUPABASE_SERVICE_ROLE_KEY` is a server-side secret. It must never appear in frontend JavaScript or be committed to Git.

---

## Supabase Setup

1. Create a new Supabase project at supabase.com
2. Go to **SQL Editor → New Query**
3. Paste the full contents of `supabase/schema.sql`
4. Run the query
5. Verify three tables exist: `subscribers`, `newsletter_issues`, `send_log`
6. Copy your **Project URL** and **anon key** and **service role key** from Project Settings → API

**RLS:** For this MVP, RLS is disabled. Server-side Python code uses the service role key which bypasses RLS. Frontend never talks directly to Supabase — it goes through `/api/subscribe`. This is safe as long as you never expose the service role key to the frontend.

---

## Vercel Deployment

> **IMPORTANT: Import the repo ROOT into Vercel, not just the `landing/` folder.**
>
> Deploying only the landing folder will cause `/api/subscribe` and `/api/unsubscribe` to return 404 errors, breaking the subscribe form.

Steps:
1. Push this repo to GitHub
2. Go to vercel.com → Add New Project
3. Import the GitHub repository
4. **Root Directory: leave blank (repo root)**
5. Framework Preset: Other
6. Add all environment variables (same as `.env`)
7. Deploy

The `vercel.json` handles all routing:
- `/` → `landing/index.html`
- `/style.css` → `landing/style.css`
- `/subscribe.js` → `landing/subscribe.js`
- `/api/subscribe` → `api/subscribe.py`
- `/api/unsubscribe` → `api/unsubscribe.py`

---

## GitHub Secrets Setup

Add these in: **GitHub repo → Settings → Secrets and variables → Actions → New repository secret**

```
GROQ_API_KEY_1
GROQ_API_KEY_2
GROQ_API_KEY_3
TAVILY_API_KEY
RESEND_API_KEY
SUPABASE_URL
SUPABASE_ANON_KEY
SUPABASE_SERVICE_ROLE_KEY
NEWSLETTER_FROM_EMAIL
NEWSLETTER_REPLY_TO
BASE_URL
ADMIN_TEST_EMAIL
```

---

## Local Testing

Install dependencies:
```bash
pip install -r requirements.txt
```

Check syntax:
```bash
python -m compileall .
```

Run tests (no API keys required):
```bash
pytest
```

---

## Dry-Run Mode

Searches sources and generates newsletter. Prints output. **No emails sent. No DB writes.**

```bash
python newsletter/main.py --dry-run
```

Use this to validate your API keys and see what the newsletter will look like.

---

## Test-Send Mode

Generates newsletter and sends to **one test email only**. Does not write to live send_log.

```bash
python newsletter/main.py --test your@email.com
```

---

## Live-Send Mode

**Sends to all active subscribers.** Requires explicit `--send-live` flag. Never runs by default.

```bash
python newsletter/main.py --send-live
```

Safe to retry — already-sent subscribers are skipped (enforced at both application and database level).

---

## GitHub Actions Schedule

The workflow runs automatically at **7:00 AM IST (01:30 UTC)** every day.

Manual trigger options:
- **With `test_email`:** Runs test mode — sends to that email only
- **Without `test_email`:** Runs dry-run mode — no emails sent

**A manual workflow_dispatch never triggers live mass email.** Only the scheduled cron runs live mode.

---

## Unsubscribe Flow

Every email includes a unique unsubscribe link:
```
https://your-domain.vercel.app/api/unsubscribe?token=<unique_token>
```

- Token is 48-character cryptographically secure random string
- One-click — no confirmation page required beyond the success HTML
- Sets `status = 'unsubscribed'` and `unsubscribed_at` — row is never deleted
- If user re-subscribes, they are reactivated with a new token
- Unsubscribed users are always excluded from live sends

---

## Duplicate-Send Protection

Two layers:

1. **Application level:** `already_sent(issue_id, subscriber_id)` checked before each send
2. **Database level:** `UNIQUE(issue_id, subscriber_id)` constraint on `send_log` table

If workflow is retried, already-sent subscribers are automatically skipped. Failed sends can be safely retried.

---

## Email Deliverability Notes

Before sending to real subscribers:
- Verify your sender domain in Resend (DNS records)
- Configure SPF, DKIM, and DMARC records for your domain
- Use a verified sender email address
- Test with your own email first
- Avoid spammy subject lines
- Do not mass-send until domain verification is complete

When subscriber volume exceeds Resend's free tier, a paid plan may be required.

---

## Cost Assumptions

```
Estimated MVP costs (approximate):

Tavily searches:   ~$0.04/day
Groq API:          Free tier (generous limits; 3-key rotation extends headroom)
Resend:            Free up to 3,000 emails/month (plan limits apply)
Supabase:          Free tier for MVP usage
GitHub Actions:    Free tier for MVP usage
Vercel:            Free tier for MVP usage

Total:             ~$0.12/day · ~₹10/day · ~₹300/month (low-volume MVP)

These are estimates. Actual costs vary with subscriber volume, retries, model
choice, and provider pricing changes.
```

---

## Security Notes

- `SUPABASE_SERVICE_ROLE_KEY` is never exposed to frontend
- Frontend only calls `/api/subscribe` — never writes to Supabase directly
- No secrets are logged
- Live email sending requires explicit `--send-live` flag
- Unsubscribe tokens are cryptographically secure (secrets module)
- Invalid emails are rejected before reaching the database
- Unsubscribed users are permanently excluded from live sends
- Users are never deleted — soft-delete via status field only

---

## Troubleshooting

**Subscribe form returns 404**
→ You deployed the `landing/` folder instead of the repo root. Redeploy from repo root.

**`EnvironmentError: Missing required environment variables`**
→ Copy `.env.example` to `.env` and fill in all values. For GitHub Actions, add secrets.

**Dry-run generates no sources**
→ Check your `TAVILY_API_KEY`. The workflow continues without sources but quality will be low.

**Emails not arriving**
→ Check sender domain verification in Resend. Check spam folder. Check `NEWSLETTER_FROM_EMAIL`.

**Supabase permission denied**
→ Ensure you are using `SUPABASE_SERVICE_ROLE_KEY` (not anon key) in server-side code.

**Duplicate email error on subscribe**
→ This is handled — duplicate active subscribers return "already subscribed" without error.

**GitHub Actions run succeeds but no email received**
→ Check Resend dashboard for delivery status. Check `BASE_URL` is set correctly for unsubscribe links.

---

## Known Limitations

- No admin dashboard — manage subscribers directly in Supabase
- No email bounce handling — failed sends are logged but not auto-unsubscribed
- No A/B subject line testing
- Claude model and Tavily search quality affect newsletter content significantly
- Resend free tier limits may apply at scale
- Live integrations (Tavily, Claude, Resend, Supabase) not tested in this build — API keys required

---

*PeopleOS Brief — Hardened MVP · Built with Python, Groq (llama-3.3-70b, 3-key rotation), Tavily, Resend, Supabase, Vercel, and GitHub Actions.*
