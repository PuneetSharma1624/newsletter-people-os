# PeopleOS Brief — Operations Guide

## Daily Automation Pipeline

| Time (IST) | Workflow | File | What it does |
|---|---|---|---|
| 07:00 | Generate Brief | `generate-brief-0700.yml` | Generates today's 12-section issue, commits `landing/data/`, pushes to GitHub → Vercel redeploys |
| 07:15 | Check & Retry | `check-and-retry-0715.yml` | Validates issue completeness, retries if missing or incomplete, commits+pushes if changed |
| 07:30 | Send Newsletter | `send-newsletter-0730.yml` | Polls production URL, confirms issue live, sends email digest to active subscribers |

Concurrency group `peopleos-brief-daily-${{ github.ref }}` prevents workflows from running in parallel (later run waits for earlier).

## Verify Today's Issue

```bash
# Check local
python newsletter/main.py --check-today

# Check audit links
python newsletter/main.py --audit-links

# Check production
./scripts/smoke_production.sh https://your-project.vercel.app
```

## Manual Recovery

**If 07:00 workflow failed:**
```bash
# GitHub → Actions → "1. Generate Brief" → Run workflow → force=true
# OR locally:
python newsletter/main.py --generate-today --force
git add landing/data/ && git commit -m "manual regen $(date +%Y-%m-%d)" && git push
```

**If 07:15 retry did not help:**
```bash
python newsletter/main.py --ensure-today --force
```

**If newsletter was not sent:**
```bash
# Check status
cat landing/data/status.json

# Test email first
python newsletter/main.py --test-email heyypuneet@gmail.com

# Send live (requires BASE_URL in env)
python newsletter/main.py --send-live-today
```

## Verify Email Send

Check `status.json`:
```json
{
  "last_email_status": "sent",
  "last_email_sent_date": "YYYY-MM-DD"
}
```

Or query Supabase `send_log` table for today's date.

## Checking Workflow Logs

GitHub → Actions → select workflow run → expand steps. All steps log to stdout.

## Archive & Index

After manual generation, rebuild:
```bash
python newsletter/main.py --refresh-index
```

## Prune Old Issues

Runs automatically on schedule. Manual:
```bash
python newsletter/main.py --prune-archive
```
