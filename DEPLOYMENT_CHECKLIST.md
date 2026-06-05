# PeopleOS Brief — Deployment Checklist

## ⚠️ Critical Rules
- **Use your production/custom domain** — NOT `xxx.vercel.app` preview URLs as `BASE_URL`
- **Remove `?date=2026-06-01`** from browser when testing latest issue
- **GitHub Secrets and Vercel Env Vars are separate** — must be added to both

---

## 1. Supabase Setup
- [ ] Open Supabase Dashboard → SQL Editor → New Query
- [ ] Paste entire contents of `supabase/schema.sql`
- [ ] Click Run
- [ ] Verify tables exist: `subscribers`, `site_analytics`, `action_logs`, `newsletter_issues`, `send_log`

## 2. Vercel Env Vars
Go to Vercel → Project → Settings → Environment Variables. Add:
```
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJ...
GROQ_API_KEY_1=gsk_...
TAVILY_API_KEY=tvly-...
RESEND_API_KEY=re_...
NEWSLETTER_FROM_EMAIL=brief@yourdomain.com
NEWSLETTER_REPLY_TO=reply@yourdomain.com
BASE_URL=https://yourdomain.com
ADMIN_TRIGGER_TOKEN=<generate: python -c "import secrets; print(secrets.token_urlsafe(32))">
GITHUB_OWNER=<your-github-username>
GITHUB_REPO=<your-repo-name>
GITHUB_WORKFLOW_FILE=generate-brief-0700.yml
GITHUB_PAT_FOR_WORKFLOW_DISPATCH=ghp_...
```

## 3. GitHub Secrets
Go to GitHub → Repo → Settings → Secrets → Actions. Add same list as Vercel Env Vars above.

## 4. Deploy from repo root
- Vercel must deploy from **repo root**, not `landing/` subdirectory
- Check: Vercel → Project → Settings → General → Root Directory should be empty or `/`

## 5. First manual generation run
After all secrets are set:
- GitHub → Actions → "1. Generate Brief — 7:00 AM IST" → Run workflow
- Set `force = true`
- Wait ~15 minutes for generation to complete
- Check Actions tab for success/failure

## 5b. Confirm function count (Hobby plan safety check)
After deploy, go to Vercel → Project → Functions tab.
Must show **≤ 6 functions**:
- `api/admin`
- `api/health`
- `api/stats`
- `api/subscribe`
- `api/unsubscribe`
- `api/visit`

If more appear, check for stray `.py` files under `/api`.

## 6. Verify production data
After workflow runs:
```
https://yourdomain.com/data/dates.json              → should include today's date
https://yourdomain.com/data/issues/YYYY-MM-DD.json  → today's issue
https://yourdomain.com/api/stats                    → GET public stats
https://yourdomain.com/api/subscribe                → POST subscribe
https://yourdomain.com/api/visit                    → POST page view
https://yourdomain.com/api/health                   → GET health check
https://yourdomain.com/api/admin?action=status      → GET admin status (requires auth)
```

## 7. Test subscribe button
```bash
curl -i -X POST https://yourdomain.com/api/subscribe \
  -H "Content-Type: application/json" \
  -d '{"email":"heyypuneet@gmail.com","source":"admin_test"}'
```
Expected: `{"ok":true,"message":"Subscribed successfully."}`
OR: `{"ok":true,"message":"You are already subscribed."}`

## 8. Test analytics
```bash
curl -i https://yourdomain.com/api/public/stats
curl -i -X POST https://yourdomain.com/api/analytics/visit
```
Refreshing page multiple times should increment `total_page_views`.

## 9. Test date fallback
```
https://yourdomain.com/                    → loads latest issue
https://yourdomain.com/?date=2026-06-01   → shows warning if unavailable, falls back to latest
https://yourdomain.com/?date=2099-01-01   → shows warning, falls back to latest
```

## 10. Test admin dashboard
```
https://yourdomain.com/admin/             → login with ADMIN_TRIGGER_TOKEN
https://yourdomain.com/admin/dashboard/   → see action buttons
Click "Test Subscribe heyypuneet@gmail.com"
Click "Refresh Public Stats"
Click "Check Today's Issue"
```

## 11. Run production check script
```bash
BASE_URL=https://yourdomain.com TEST_SUBSCRIBE_EMAIL=heyypuneet@gmail.com python scripts/production_check.py
```

## 12. Verify automation schedule
GitHub Actions run at:
- `01:30 UTC` = 7:00 AM IST — generate
- `01:45 UTC` = 7:15 AM IST — check/retry
- `02:00 UTC` = 7:30 AM IST — send

To verify: check GitHub Actions tab → "1. Generate Brief" → should have run today.

---

## Common Issues

| Problem | Cause | Fix |
|---------|-------|-----|
| Dashboard shows old date | Secrets missing in GitHub → generation fails | Add all secrets, trigger manually |
| Subscribe spinner stays | Supabase env vars missing in Vercel | Add to Vercel env vars |
| Stats show 0 | `site_analytics` table missing | Run schema.sql in Supabase |
| Action logs empty | `action_logs` table missing | Run schema.sql migration v5 |
| Admin trigger fails | `GITHUB_PAT_FOR_WORKFLOW_DISPATCH` missing | Generate PAT with `workflow` scope |
