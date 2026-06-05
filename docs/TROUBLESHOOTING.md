# PeopleOS Brief — Troubleshooting

## Subscribe Button Fails

**Symptom:** Clicking subscribe shows error or no response.

**Diagnose:**
```bash
curl -i -X POST "$BASE_URL/api/subscribe" \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","source":"test"}'
```

**Causes:**
- Missing `SUPABASE_URL` or `SUPABASE_SERVICE_ROLE_KEY` in Vercel env vars → returns 503
- `subscribers` table not created → run `supabase/schema.sql` in Supabase SQL editor
- Invalid Supabase key → check dashboard → Settings → API

## Spinner Stuck

`subscribe.js` uses `finally { if (!succeeded) setLoading(false) }` — spinner always stops unless subscription succeeded. If spinner is stuck after success, that's intentional (button becomes "Subscribed"). Check browser console for JS errors.

## Supabase PGRST Errors

`PGRST116` = relation not found → run `supabase/schema.sql`  
`PGRST301` = JWT expired → regenerate service role key  
`401` = invalid API key → check `SUPABASE_SERVICE_ROLE_KEY`

## Dashboard Not Updating

1. Check `landing/data/status.json` — `generation_status` should be `complete`
2. Check `landing/data/dates.json` — today's date should be first entry
3. Check GitHub Actions — did `generate-brief-0700` run and push?
4. Check Vercel deployment log — did redeploy trigger after push?

**If dates.json is stale:**
```bash
python newsletter/main.py --refresh-index
git add landing/data/ && git commit -m "fix index" && git push
```

## Workflow Did Not Run

- Check GitHub → Actions → is workflow enabled?
- Check cron timezone: `30 1 * * *` = 07:00 IST, `45 1 * * *` = 07:15 IST, `0 2 * * *` = 07:30 IST
- GitHub Actions cron can be 15-30 min late during high load
- Ensure no conflicting workflows: `daily-brief.yml.disabled` and `newsletter.yml.disabled` must NOT be enabled

## Vercel Did Not Redeploy

- Vercel redeploys on every push to the connected branch
- Check Vercel dashboard → Deployments
- If push shows in git log but Vercel did not redeploy: check GitHub integration in Vercel project settings

## Email Did Not Send

1. `status.json` → `last_email_status` should be `sent`
2. If `skipped_issue_not_deployed`: production issue URL returned non-200 at send time — wait and manually trigger send workflow
3. If `failed`: check workflow logs for Resend error
4. Test email first: `python newsletter/main.py --test-email your@email.com`

## Duplicate Send Prevention

`send_log` table has unique constraint on `(subscriber_id, issue_date, send_type)`. If you need to resend, delete the send_log row for that subscriber+date.

## Article Links Opening Homepages

Old issue data may contain homepage URLs from before the source_id mapping was enforced. Run:
```bash
python newsletter/main.py --audit-links
```
New generations use `source_id → source_url` mapping and will not contain homepage URLs.

## Admin Trigger Not Working

Required env vars in Vercel:
- `ADMIN_TRIGGER_TOKEN`
- `GITHUB_OWNER`
- `GITHUB_REPO`
- `GITHUB_WORKFLOW_FILE`
- `GITHUB_PAT_FOR_WORKFLOW_DISPATCH`

The PAT needs `workflow` scope. Generate at GitHub → Settings → Developer settings → Personal access tokens.

## Missing Env Vars

Run preflight check:
```bash
python newsletter/main.py --preflight
```

This checks all required vars and shows MISSING / WARN / OK status.
