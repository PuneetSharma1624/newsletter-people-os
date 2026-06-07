"""
PeopleOS Brief — Newsletter CLI

Commands:
  --dry-run                  Search + generate section-by-section. Print. No save, no email.
  --dry-run --force          Force dry-run even if today's issue exists.
  --generate-today           Generate today's issue, save static files.
  --generate-today --force   Force regeneration even if complete.
  --test EMAIL               Generate + send to one test email only.
  --send-live                Send to all active subscribers. LIVE. Protected.
  --backfill-initial         Generate last 3 days if archive is empty (first-time setup).
  --prune-archive            Delete issues older than ARCHIVE_RETENTION_DAYS.
  --seed-demo                Seed demo data into landing/data/ if no issues exist.
  --refresh-index            Rebuild archive.json and dates.json from issue files.

Live send NEVER happens by default. Must pass --send-live explicitly.
"""
from __future__ import annotations

import argparse
import datetime
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _today() -> str:
    """IST date (UTC+5:30) — what today means in India."""
    ist = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
    return datetime.datetime.now(ist).date().isoformat()


def _fmt_date(iso: str) -> str:
    try:
        return datetime.date.fromisoformat(iso).strftime("%B %d, %Y")
    except Exception:
        return iso


# ─── CORE GENERATION ─────────────────────────────────────────────────────────

def _generate_issue(
    date: str,
    dry_run: bool = False,
    force: bool = False,
    save: bool = True,
) -> dict | None:
    """
    Generate one issue section-by-section.
    Each section = one Groq call (fixes 413 token limit error).
    Returns assembled issue dict or None on critical failure.
    """
    from newsletter import config
    from newsletter.logger import log
    from newsletter.sections import SECTIONS
    from newsletter.searcher import search_section
    from newsletter.generator import generate_section, generate_executive_summary
    from newsletter.static_publisher import (
        is_today_complete, is_running_recently, set_status,
        save_partial, load_partial, save_issue, issue_exists,
    )

    log.info(f"=== Generating issue for {date} ===")

    if not dry_run and not force:
        if is_today_complete(date):
            log.info(f"Issue for {date} already complete. Use --force to regenerate.")
            from newsletter.static_publisher import load_issue
            return load_issue(date)
        if is_running_recently(date):
            log.warning(f"Issue for {date} already running. Skipping duplicate run.")
            return None

    if not dry_run:
        set_status("running", current_date=date)

    try:
        # Load partial progress (resume support)
        done_sections = {}
        if not force and not dry_run:
            partial = load_partial(date)
            for s in partial:
                done_sections[s.get("section_id", s.get("code", ""))] = s
            if done_sections:
                log.info(f"Resuming: {len(done_sections)} sections already done")

        search_delay = config.section_search_delay()
        section_delay = config.groq_section_delay()
        generated_sections = []

        for i, section in enumerate(SECTIONS):
            sid = section["id"]

            # Skip already-done sections when resuming
            if sid in done_sections:
                log.info(f"{section['code']} {section['name']} — loaded from partial")
                generated_sections.append(done_sections[sid])
                continue

            # Search
            log.info(f"{section['code']} {section['name']} — searching sources...")
            try:
                sources = search_section(section)
            except Exception as exc:
                log.error(f"{section['code']} search failed: {exc}")
                sources = []

            if i > 0 and search_delay > 0:
                time.sleep(search_delay)

            # Generate
            log.info(f"{section['code']} {section['name']} — generating with Groq...")
            sec_result = generate_section(section, sources, date)
            generated_sections.append(sec_result)

            # Save partial progress
            if not dry_run:
                save_partial(date, generated_sections)
                set_status("running", current_date=date, sections_complete=len(generated_sections))

            # Wait before next section (rate limit safety)
            if i < len(SECTIONS) - 1 and section_delay > 0:
                log.info(f"Waiting {section_delay:.0f}s before next section...")
                time.sleep(section_delay)

        # Generate executive summary from assembled sections
        log.info("Generating executive summary...")
        exec_summary = generate_executive_summary(generated_sections, date)

        # Assemble full issue
        total_items = sum(len(s.get("items", [])) for s in generated_sections)
        email_items = sum(min(len(s.get("items", [])), 2) for s in generated_sections)

        issue = {
            "issue_date": date,
            "title": f"PeopleOS Brief — {date}",
            "subject": f"PeopleOS Brief — {_fmt_date(date)} Intelligence",
            "preheader": "12-section daily executive intelligence across markets, AI, HR, and economics.",
            "executive_summary": exec_summary,
            "total_sections": len(generated_sections),
            "total_dashboard_items": total_items,
            "total_email_items": email_items,
            "sections": generated_sections,
            "sources": [],
        }

        if save and not dry_run:
            save_issue(issue)
            set_status("complete", current_date=date, sections_complete=len(generated_sections))
            log.info(f"Issue complete: {total_items} dashboard items, {email_items} email items")

        return issue

    except Exception as exc:
        if not dry_run:
            log.error(f"Generation failed with exception: {exc}")
            set_status("failed", current_date=date, error=str(exc))
        raise


# ─── COMMANDS ────────────────────────────────────────────────────────────────

def _run_dry(force: bool = False) -> None:
    from newsletter import config
    from newsletter.logger import log, log_mode

    log_mode("dry-run")
    config.validate_config(["GROQ_API_KEY_1", "TAVILY_API_KEY"])

    date = _today()
    issue = _generate_issue(date, dry_run=True, force=force, save=False)

    if not issue:
        print("ERROR: Generation failed")
        sys.exit(1)

    print(f"\n{'='*60}")
    print(f"PeopleOS Brief — {date}")
    print(f"Subject: {issue.get('subject','')}")
    print(f"Preheader: {issue.get('preheader','')}")
    print(f"\nExecutive Summary:\n{issue.get('executive_summary','')}")
    print(f"\n{'='*60}\n")

    total_dash = 0
    total_email = 0
    for section in issue.get("sections", []):
        code = section.get("code", "")
        name = section.get("section_name", "")
        items = section.get("items", [])
        total_dash += len(items)
        total_email += min(len(items), 2)
        print(f"{code}: {name}")
        for item in items:
            print(f"  {item.get('rank','')}. {item.get('headline','')}")
        print()

    print(f"{'='*60}")
    print(f"Dashboard items: {total_dash}")
    print(f"Email items:     {total_email}")
    print(f"No emails sent.")
    print(f"No files published.")


def _run_generate_today(force: bool = False) -> None:
    from newsletter import config
    from newsletter.logger import log, log_mode

    log_mode("generate-today")
    config.validate_config(["GROQ_API_KEY_1", "TAVILY_API_KEY"])

    date = _today()

    from newsletter.static_publisher import issue_exists, is_today_complete
    if not force and issue_exists(date):
        if is_today_complete(date):
            log.info(f"Issue for {date} already exists and is complete. Skipping. Use --force to override.")
            return

    issue = _generate_issue(date, dry_run=False, force=force, save=True)
    if issue:
        total   = issue.get("total_dashboard_items", 0)
        secs    = issue.get("total_sections", 0)
        email_i = issue.get("total_email_items", 0)
        log.info(f"Generated and saved: {date} ({total} dashboard items)")
        # Machine-parseable line for workflow summary parsing
        print(f"STATS: sections={secs} dashboard_items={total} email_items={email_i} issue_date={date}")
    else:
        log.error("Generation failed")
        sys.exit(1)


def _run_test(test_email: str) -> None:
    from newsletter import config
    from newsletter.logger import log, log_mode
    from newsletter.sender import send_test_email
    from newsletter.static_publisher import load_issue, issue_exists
    from newsletter.utils import is_valid_email

    if not is_valid_email(test_email):
        print(f"ERROR: Invalid email: {test_email}", file=sys.stderr)
        sys.exit(1)

    log_mode("test")
    config.validate_config(["GROQ_API_KEY_1", "TAVILY_API_KEY", "RESEND_API_KEY",
                             "NEWSLETTER_FROM_EMAIL", "BASE_URL"])
    date = _today()

    # Load existing issue or generate fresh
    if issue_exists(date):
        log.info(f"Loading existing issue for {date}")
        issue = load_issue(date)
    else:
        log.info(f"No issue for {date} — generating for test send")
        issue = _generate_issue(date, dry_run=False, force=False, save=True)

    if not issue:
        log.error("No issue available for test send")
        sys.exit(1)

    log.info(f"Sending test email to {test_email}...")
    result = send_test_email(test_email, issue)

    if result["ok"]:
        log.info(f"Test email sent OK to {test_email}")
        print(f"Subject: {issue.get('subject','')}")
        print(f"Dashboard items: {issue.get('total_dashboard_items',0)} | Email items: {issue.get('total_email_items',0)}")
    else:
        log.error(f"Test email FAILED: {result['error']}")
        sys.exit(1)


def _supabase_preflight() -> list:
    """Validate Supabase connection and return active subscribers. Clean error on failure."""
    from newsletter import config
    from newsletter.logger import log

    url = config.supabase_url()
    key = config.supabase_service_key()

    if not url or url == "your-supabase-url":
        print("ERROR: SUPABASE_URL is not configured. Set it in .env and run supabase/schema.sql.")
        raise SystemExit(1)
    if not key or key == "your-service-role-key":
        print("ERROR: SUPABASE_SERVICE_ROLE_KEY is not configured. Set it in .env.")
        raise SystemExit(1)

    try:
        from supabase import create_client
        client = create_client(url, key)
        result = client.table("subscribers").select("id").limit(1).execute()
        log.info("Supabase preflight OK — subscribers table reachable.")
    except Exception as exc:
        err = str(exc)
        print(f"\nERROR: Supabase subscribers table is not reachable.")
        print(f"Detail: {err}")
        print(f"\nFix:")
        print(f"  1. Verify SUPABASE_URL in .env")
        print(f"  2. Verify SUPABASE_SERVICE_ROLE_KEY in .env")
        print(f"  3. Run supabase/schema.sql in your Supabase SQL editor")
        print(f"  4. Confirm 'subscribers' table exists")
        print(f"\nLive send aborted. No emails sent.")
        raise SystemExit(1)

    from newsletter.subscribers import get_active_subscribers
    try:
        return get_active_subscribers()
    except Exception as exc:
        print(f"\nERROR: Failed to fetch active subscribers: {exc}")
        print(f"Live send aborted. No emails sent.")
        raise SystemExit(1)


def _run_live() -> None:
    from newsletter import config
    from newsletter.logger import log, log_mode, log_subscribers, log_summary
    from newsletter.sender import send_to_subscriber
    from newsletter.static_publisher import load_issue, issue_exists
    from newsletter.archive import mark_sent

    log_mode("live")
    config.validate_config()

    date = _today()
    subscribers = _supabase_preflight()
    log_subscribers(len(subscribers))
    if not subscribers:
        log.warning("No active subscribers. Exiting.")
        return

    if not issue_exists(date):
        log.error(f"No issue for {date}. Run --generate-today first.")
        sys.exit(1)

    issue = load_issue(date)
    if not issue:
        log.error("Failed to load issue")
        sys.exit(1)

    # Get real UUID from DB — required for send_log (UUID column)
    from newsletter import archive as arc
    from newsletter.renderer import render_html_email, render_text_email
    base_url = config.base_url()
    placeholder = f"{base_url}/api/unsubscribe?token=PLACEHOLDER"
    html = render_html_email(issue, placeholder, base_url)
    text = render_text_email(issue, placeholder, base_url)
    try:
        issue_id = arc.ensure_newsletter_issue(issue, html, text)
    except Exception as exc:
        log.error(f"Cannot get DB issue UUID for {date}: {exc}")
        log.error("send_log requires real UUID. Aborting.")
        sys.exit(1)

    sent = failed = skipped = 0
    for sub in subscribers:
        result = send_to_subscriber(sub, issue, issue_id, is_test=False)
        if result.get("skipped"):
            skipped += 1
        elif result["ok"]:
            sent += 1
        else:
            failed += 1

    log_summary(sent, failed, skipped)
    if sent > 0 or skipped > 0:
        try:
            mark_sent(issue_id)
        except Exception:
            pass

    if failed > 0 and sent == 0 and skipped == 0:
        log.error("All sends failed.")
        sys.exit(1)


def _run_backfill_initial(force: bool = False) -> None:
    from newsletter import config
    from newsletter.logger import log
    from newsletter.static_publisher import get_dates, issue_exists

    config.validate_config(["GROQ_API_KEY_1", "TAVILY_API_KEY"])

    existing_dates = get_dates()
    if existing_dates and not force:
        log.info(f"Archive has {len(existing_dates)} issues. Backfill skipped (use --force to override).")
        return

    today = datetime.date.today()
    dates_to_generate = [
        (today - datetime.timedelta(days=i)).isoformat()
        for i in range(3)
    ]

    log.info(f"Backfill: generating {dates_to_generate}")
    for date in dates_to_generate:
        if issue_exists(date) and not force:
            log.info(f"Skipping {date} — already exists")
            continue
        log.info(f"Generating {date}...")
        issue = _generate_issue(date, dry_run=False, force=force, save=True)
        if issue:
            log.info(f"Backfilled {date}")
        else:
            log.error(f"Backfill failed for {date}")
        # Wait between dates
        if date != dates_to_generate[-1]:
            log.info("Waiting 30s before next date...")
            time.sleep(30)

    log.info("Backfill complete")


def _run_prune_archive() -> None:
    from newsletter.logger import log
    from newsletter.static_publisher import prune_archive
    from newsletter import config

    days = config.archive_retention_days()
    log.info(f"Pruning issues older than {days} days...")
    deleted = prune_archive(days)
    if deleted:
        print(f"Deleted {len(deleted)} issues: {deleted}")
    else:
        print(f"Nothing to prune (retention: {days} days)")


def _run_seed_demo() -> None:
    from newsletter.logger import log
    from newsletter.static_publisher import seed_demo_data
    log.info("Seeding demo data...")
    seed_demo_data()


def _run_refresh_index() -> None:
    from newsletter.logger import log
    from newsletter.static_publisher import refresh_indices
    log.info("Refreshing archive index...")
    refresh_indices()
    log.info("Done")


def _run_audit_links() -> None:
    """Scan all issue JSON files and report homepage/missing source URLs."""
    import glob
    import json
    from newsletter.utils import validate_article_url
    import pathlib
    ISSUES_DIR = pathlib.Path("landing/data/issues")

    issue_files = sorted(glob.glob(str(ISSUES_DIR / "*.json")))
    if not issue_files:
        print("No issue files found under landing/data/issues/")
        return

    total = 0
    bad: list[dict] = []

    for path in issue_files:
        with open(path, encoding="utf-8") as f:
            try:
                issue = json.load(f)
            except Exception as exc:
                print(f"  Could not parse {path}: {exc}")
                continue

        for section in issue.get("sections", []):
            sec_code = section.get("code", "?")
            sec_name = section.get("section_name", "?")
            for item in section.get("items", []):
                total += 1
                url = item.get("source_url", "")
                result = validate_article_url(url)
                if not result["is_valid_article_url"]:
                    bad.append({
                        "date": issue.get("issue_date", "?"),
                        "section": f"{sec_code} {sec_name}",
                        "headline": item.get("headline", "?"),
                        "url": url or "(empty)",
                        "reason": result["reason"],
                    })

    print(f"Checked {total} source links across {len(issue_files)} issue files.")
    if not bad:
        print("All article links look valid.")
        return

    print(f"\nHomepage or invalid links found: {len(bad)}\n")
    for entry in bad:
        print(f"[{entry['date']}] {entry['section']}")
        print(f"  - {entry['headline']}")
        print(f"    {entry['url']}")
        print(f"    reason: {entry['reason']}")
        print()


# ─── NEW RELIABILITY COMMANDS ────────────────────────────────────────────────

def _run_check_today() -> None:
    from newsletter.static_publisher import validate_issue_complete
    from newsletter.logger import log

    date = _today()
    print(f"=== Check Today: {date} ===")
    result = validate_issue_complete(date)

    print(f"  exists           : {result['exists']}")
    print(f"  valid_json       : {result.get('valid_json', False)}")
    print(f"  sections         : {result['sections']}")
    print(f"  dashboard_items  : {result['dashboard_items']}")
    print(f"  email_items      : {result['email_items']}")
    print(f"  in_dates_json    : {result['in_dates_json']}")
    print(f"  in_archive_json  : {result['in_archive_json']}")
    print(f"  status_complete  : {result['status_complete']}")

    if result["errors"]:
        print(f"\n  ERRORS ({len(result['errors'])}):")
        for e in result["errors"]:
            print(f"    - {e}")

    if result["ok"]:
        print(f"\n[OK] Today's issue ({date}) is COMPLETE.")
        sys.exit(0)
    else:
        print(f"\n[FAIL] Today's issue ({date}) is INCOMPLETE.")
        sys.exit(1)


def _run_ensure_today(admin_force: bool = False) -> None:
    from newsletter import config
    from newsletter.logger import log
    from newsletter.static_publisher import validate_issue_complete, get_status, set_status

    config.validate_config(["GROQ_API_KEY_1", "TAVILY_API_KEY"])
    date = _today()
    print(f"=== Ensure Today: {date} ===")

    # Check if complete
    result = validate_issue_complete(date)
    if result["ok"]:
        print(f"Today's issue already complete. Skipping generation.")
        set_status("skipped_already_complete", current_date=date)
        sys.exit(0)

    # Files valid but status.json is the only error — fix status, skip generation
    non_status_errors = [e for e in result["errors"] if "status.json" not in e]
    if not non_status_errors and result["exists"] and result["valid_json"] and result["sections"] >= 12:
        print(f"Today's issue files are complete. Correcting status.json and skipping generation.")
        set_status("complete", current_date=date)
        sys.exit(0)

    # Check if in_progress and fresh (< 30 min) — don't double-generate
    # Exit 1 (not 0) so calling workflows know issue is NOT ready.
    s = get_status()
    if not admin_force and s.get("generation_status") in ("in_progress", "running"):
        started = s.get("generation_started_at_utc") or s.get("last_started_at")
        if started:
            try:
                import datetime as dt_mod
                start_dt = dt_mod.datetime.fromisoformat(started.rstrip("Z")).replace(
                    tzinfo=dt_mod.timezone.utc
                )
                age_min = (dt_mod.datetime.now(dt_mod.timezone.utc) - start_dt).total_seconds() / 60
                if age_min < 30:
                    print(f"Generation is in_progress (started {age_min:.1f}m ago). Issue not yet complete.")
                    print("Use --force to bypass, or wait for generation to finish.")
                    sys.exit(1)
                elif age_min < 45:
                    print(f"Generation in_progress but {age_min:.1f}m ago — issue still not complete.")
                    sys.exit(1)
                else:
                    print(f"Generation in_progress but stale ({age_min:.1f}m ago). Forcing retry.")
            except Exception:
                pass

    # Mark attempt
    attempt = "retry_0715" if os.getenv("GENERATION_ATTEMPT") == "retry_0715" else "ensure"
    set_status("retrying", current_date=date, attempt=attempt)

    # Run generation
    issue = _generate_issue(date, dry_run=False, force=True, save=True)
    if not issue:
        log.error("Generation failed in --ensure-today")
        set_status("failed", current_date=date, error="Generation returned None")
        sys.exit(1)

    # Validate again
    result2 = validate_issue_complete(date)
    if result2["ok"]:
        print(f"[OK] Today's issue ({date}) generated and validated successfully.")
        sys.exit(0)
    else:
        print(f"[FAIL] Issue generated but validation failed:")
        for e in result2["errors"]:
            print(f"  - {e}")
        sys.exit(1)


def _mask_email(email: str) -> str:
    if not email or "@" not in email:
        return "***"
    local, domain = email.split("@", 1)
    return f"{local[0]}***@{domain}"


def _safe_base_url() -> str:
    from newsletter import config as cfg
    base_url = cfg.base_url()
    if not base_url:
        raise RuntimeError("BASE_URL is not configured")
    if "localhost" in base_url or "127.0.0.1" in base_url:
        raise RuntimeError(f"BASE_URL is localhost — not valid for production: {base_url}")
    if "vercel.app" in base_url and ("git-" in base_url or "-pr-" in base_url):
        raise RuntimeError(f"BASE_URL appears to be a Vercel preview URL: {base_url}")
    return base_url


def _run_wait_production_today() -> None:
    """Poll BASE_URL/data/issues/YYYY-MM-DD.json until ready. Up to 15 min."""
    from newsletter.static_publisher import check_production_issue_available

    date = _today()
    try:
        base_url = _safe_base_url()
    except RuntimeError as exc:
        print(f"[FAIL] {exc}")
        sys.exit(1)

    url = f"{base_url}/data/issues/{date}.json"
    print(f"=== Wait Production Today: {date} ===")
    print(f"Polling: {url}")

    for i in range(1, 16):
        print(f"  Attempt {i}/15 ...")
        result = check_production_issue_available(date)
        if result["ok"]:
            print(f"[OK] Production ready — {result.get('sections',0)} sections, {result.get('dashboard_items',0)} dashboard items")
            sys.exit(0)
        print(f"  Not ready: {result['errors']}")
        if i < 15:
            print("  Waiting 60 seconds...")
            time.sleep(60)

    print(f"[FAIL] Production issue not available after 15 attempts.")
    sys.exit(1)


def _run_debug_subscribers() -> None:
    """Connect to Supabase, count active subscribers, print masked sample. No email sent."""
    from newsletter import config as cfg
    from newsletter.subscribers import get_active_subscribers

    print("=== Debug Subscribers ===")
    url = os.getenv("SUPABASE_URL", "")
    print(f"  SUPABASE_URL configured   : {'yes' if url else 'NO — missing'}")
    print(f"  SUPABASE_SERVICE_ROLE_KEY : {'yes' if os.getenv('SUPABASE_SERVICE_ROLE_KEY') else 'NO — missing'}")

    try:
        subs = get_active_subscribers()
    except Exception as exc:
        print(f"[FAIL] Subscriber fetch failed: {exc}")
        sys.exit(1)

    print(f"  Active subscriber count   : {len(subs)}")
    for sub in subs[:3]:
        print(f"    {_mask_email(sub.get('email', ''))}")

    if not subs:
        print("[FAIL] No active subscribers found.")
        sys.exit(1)

    print("[OK] Subscribers reachable.")


def _run_send_live_today(force_resend: bool = False) -> None:
    from newsletter import config
    from newsletter.logger import log, log_mode, log_subscribers, log_summary
    from newsletter.sender import send_to_subscriber
    from newsletter.static_publisher import (
        load_issue, validate_issue_complete, set_status,
        check_production_issue_available,
    )
    from newsletter.archive import mark_sent
    from newsletter.subscribers import already_sent_today

    log_mode("send-live-today")
    config.validate_config()

    date = _today()
    print(f"=== Send Live Today: {date} ===")
    print(f"  force_resend              : {force_resend}")

    # Print safe config summary
    base_url_raw = os.getenv("BASE_URL", "")
    from_email = os.getenv("NEWSLETTER_FROM_EMAIL", "")
    from_domain = from_email.split("@")[-1] if "@" in from_email else "(not set)"
    print(f"  BASE_URL configured       : {'yes — ' + base_url_raw if base_url_raw else 'NO'}")
    print(f"  SUPABASE_URL configured   : {'yes' if os.getenv('SUPABASE_URL') else 'NO'}")
    print(f"  RESEND_API_KEY configured : {'yes' if os.getenv('RESEND_API_KEY') else 'NO'}")
    print(f"  FROM_EMAIL domain         : {from_domain}")

    # Validate BASE_URL
    try:
        base_url = _safe_base_url()
    except RuntimeError as exc:
        print(f"[FAIL] {exc}")
        sys.exit(1)

    dashboard_url = f"{base_url}/"
    issue_url = f"{base_url}/brief?date={date}"
    print(f"  Dashboard URL             : {dashboard_url}")
    print(f"  Issue URL                 : {issue_url}")

    # Validate local issue completeness
    result = validate_issue_complete(date)
    print(f"  Local issue complete      : {'yes' if result['ok'] else 'NO'}")
    if not result["ok"]:
        print(f"[FAIL] Today's issue ({date}) is NOT complete. Aborting send.")
        for e in result["errors"]:
            print(f"  - {e}")
        set_status("complete", email_status="skipped_issue_missing")
        sys.exit(1)

    # Check production availability (with retries)
    max_retries = 3
    wait_seconds = 60
    prod_ok = False
    for attempt in range(1, max_retries + 1):
        prod = check_production_issue_available(date)
        if prod["ok"]:
            prod_ok = True
            print(f"  Production URL ready      : yes — {prod['url']}")
            break
        print(f"  Production check {attempt}/{max_retries} failed: {prod['errors']}")
        if attempt < max_retries:
            print(f"  Waiting {wait_seconds}s before retry...")
            time.sleep(wait_seconds)

    if not prod_ok:
        print(f"[FAIL] Production issue not available after {max_retries} attempts. Aborting send.")
        set_status("complete", email_status="skipped_issue_not_deployed")
        sys.exit(1)

    # Duplicate send guard
    if not force_resend and already_sent_today(date):
        print(f"[SKIP] Today's newsletter already sent (found in send_log). Use --force-resend to override.")
        sys.exit(0)
    if force_resend:
        print(f"  force_resend=True — bypassing duplicate-send guard.")

    # Fetch subscribers
    subscribers = _supabase_preflight()
    log_subscribers(len(subscribers))
    print(f"  Subscriber count          : {len(subscribers)}")
    for sub in subscribers[:3]:
        print(f"    {_mask_email(sub.get('email', ''))}")

    if not subscribers:
        print("[FAIL] No active subscribers found. Live newsletter was not sent.")
        set_status("complete", email_status="failed_no_subscribers")
        sys.exit(1)

    issue = load_issue(date)
    if not issue:
        log.error("Failed to load issue")
        sys.exit(1)

    if issue.get("issue_date") != date:
        log.error(f"Issue date mismatch: issue has {issue.get('issue_date')}, expected {date}. Aborting.")
        sys.exit(1)

    # Get real UUID from DB — required for send_log (UUID column)
    from newsletter import archive as arc
    from newsletter.renderer import render_html_email, render_text_email
    placeholder = f"{base_url}/api/unsubscribe?token=PLACEHOLDER"
    html = render_html_email(issue, placeholder, base_url)
    text = render_text_email(issue, placeholder, base_url)

    issue_slug = f"static-{date}"
    try:
        db_issue_id = arc.ensure_newsletter_issue(issue, html, text)
    except Exception as exc:
        print(f"[FAIL] Cannot get DB issue UUID for {date}: {exc}")
        print(f"  send_log requires real UUID — cannot use {issue_slug}. Aborting.")
        sys.exit(1)

    print(f"  Issue date                : {date}")
    print(f"  Static issue slug         : {issue_slug}")
    print(f"  DB issue UUID             : {db_issue_id}")
    print(f"  Duplicate check uses UUID : yes")

    issue_id = db_issue_id  # always a real UUID from here

    # Pre-flight: verify send_log is reachable before starting batch
    from newsletter.subscribers import probe_send_log
    try:
        probe_send_log()
        print(f"  send_log reachable        : yes")
    except Exception as exc:
        print(f"[FAIL] send_log table not reachable: {exc}")
        print(f"  Cannot safely check for duplicates — aborting to prevent spam.")
        sys.exit(1)

    set_status("complete", email_date=date, email_status="sending")

    sent = failed = skipped = db_logged_count = 0
    utc_now = datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")

    for i, sub in enumerate(subscribers, 1):
        masked = _mask_email(sub.get("email", ""))
        print(f"  [{i}/{len(subscribers)}] Sending to: {masked}")
        result2 = send_to_subscriber(sub, issue, issue_id, is_test=False)
        if result2.get("skipped"):
            skipped += 1
            print(f"    Duplicate check: already sent — skipped")
        elif result2["ok"]:
            sent += 1
            msg_id = result2.get("message_id", "")
            print(f"    Resend accepted: {msg_id or '(no id)'}")
            if result2.get("db_logged"):
                db_logged_count += 1
                print(f"    DB send log: ok")
            else:
                print(f"    DB send log: [WARN] not logged")
        else:
            failed += 1
            print(f"    [WARN] Send failed: {result2.get('error','')[:120]}")

    attempted = len(subscribers)
    log_summary(sent, failed, skipped)
    print(f"\nFinal send summary:")
    print(f"  attempted         : {attempted}")
    print(f"  accepted_by_resend: {sent}")
    print(f"  db_logged         : {db_logged_count}")
    print(f"  skipped           : {skipped}")
    print(f"  failed            : {failed}")

    # Determine result status
    if attempted == 0:
        send_result = "no_subscribers"
    elif sent == 0:
        send_result = "failed"
    elif failed > 0:
        send_result = "partial"
    else:
        send_result = "success"

    # Machine-parseable lines for workflow summary parsing
    print(f"STATS: subscribers={attempted} accepted={sent} db_logged={db_logged_count} skipped={skipped} failed={failed}")
    print(f"SEND_RESULT={send_result}")

    # Only mark issue as sent in Supabase if at least one email was accepted
    if sent > 0:
        try:
            mark_sent(issue_id)
        except Exception:
            pass
        set_status(
            "complete",
            email_date=date,
            email_status="sent" if send_result == "success" else "partial",
            email_sent_at_utc=utc_now,
        )
        log.info(f"Newsletter send complete. result={send_result} accepted={sent} failed={failed} skipped={skipped}")
    else:
        set_status("complete", email_date=date, email_status="failed")
        log.error(f"Newsletter not delivered. result={send_result} attempted={attempted} failed={failed} skipped={skipped}")

    # Exit logic: only exit 0 if at least one email was accepted by Resend
    if send_result in ("success", "partial"):
        sys.exit(0)
    else:
        sys.exit(1)


def _run_mark_generation_started() -> None:
    from newsletter.static_publisher import set_status
    date = _today()
    run_id = os.getenv("GITHUB_RUN_ID", "")
    attempt = os.getenv("GENERATION_ATTEMPT", "scheduled_0700")
    set_status("running", current_date=date, run_id=run_id or None, attempt=attempt)
    print(f"Marked generation started for {date} (run_id={run_id}, attempt={attempt})")


def _run_mark_generation_failed(error: str = "") -> None:
    from newsletter.static_publisher import set_status
    date = _today()
    set_status("failed", current_date=date, error=error or "Marked failed via CLI")
    print(f"Marked generation failed for {date}")


def _run_preflight() -> None:
    """Check required env vars and folder structure. Exit 0=ok, 1=fail."""
    import pathlib

    gen_vars = ["GROQ_API_KEY_1", "TAVILY_API_KEY"]
    send_vars = [
        "SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY",
        "RESEND_API_KEY", "NEWSLETTER_FROM_EMAIL", "BASE_URL",
    ]
    required_dirs = [pathlib.Path("landing/data/issues"), pathlib.Path("newsletter")]

    print("=== Preflight Check ===")
    ok = True

    for v in gen_vars:
        val = os.getenv(v, "").strip()
        status = "OK" if val else "MISSING"
        if not val:
            ok = False
        print(f"  {status:7s} {v}")

    for v in send_vars:
        val = os.getenv(v, "").strip()
        status = "OK" if val else "WARN"
        print(f"  {status:7s} {v}")

    for d in required_dirs:
        exists = d.exists()
        status = "OK" if exists else "MISSING"
        if not exists:
            ok = False
        print(f"  {status:7s} {d}")

    groq_keys = sum(1 for i in (1, 2, 3) if os.getenv(f"GROQ_API_KEY_{i}", "").strip())
    print(f"  INFO    {groq_keys} Groq key(s) active")

    if ok:
        print("\n[OK] Preflight passed.")
        sys.exit(0)
    else:
        print("\n[FAIL] Preflight failed.")
        sys.exit(1)


def _run_test_email(email: str) -> None:
    """Canonical --test-email alias — same as --test."""
    _run_test(email)


def _run_test_welcome_email(email: str, dry_run: bool = False) -> None:
    """Send one welcome email to the supplied address. No DB write.
    With dry_run=True: validates config and prints what would be sent, but does NOT call Resend.
    """
    from newsletter.sender import send_welcome_email
    from newsletter.utils import is_valid_email
    import os as _os

    if not is_valid_email(email):
        print(f"ERROR: Invalid email: {email}", file=sys.stderr)
        sys.exit(1)

    masked = _mask_email(email)

    # Print env config status before attempting send
    resend_key     = _os.environ.get("RESEND_API_KEY", "").strip()
    from_email_val = _os.environ.get("NEWSLETTER_FROM_EMAIL", "").strip()
    reply_to_val   = _os.environ.get("NEWSLETTER_REPLY_TO", "").strip()
    raw_base       = _os.environ.get("BASE_URL", "").strip()
    base_is_local  = bool(raw_base and ("localhost" in raw_base or "127.0.0.1" in raw_base))

    print(f"=== Welcome Email Config ===")
    print(f"  recipient            : {masked}")
    print(f"  has_api_key          : {bool(resend_key)}")
    print(f"  has_from_email       : {bool(from_email_val)}")
    print(f"  has_reply_to         : {bool(reply_to_val)}")
    print(f"  base_url             : {'localhost' if base_is_local else (raw_base or '(not set)')}")
    print(f"  base_is_localhost    : {base_is_local}")
    print(f"  dry_run              : {dry_run}")
    print(f"===========================")

    if dry_run:
        result = send_welcome_email(email, dry_run=True)
        if result["ok"]:
            print(f"[DRY RUN OK] Config valid. Would send welcome email to {masked}")
        else:
            print(f"[FAIL] code={result.get('error_code','unknown')}")
            print(f"       reason={result.get('error_message','')}")
            sys.exit(1)
        return

    print(f"Sending welcome email to {masked} ...")
    result = send_welcome_email(email)
    if result["ok"]:
        resend_id = result.get("resend_id") or ""
        print(f"[OK] Welcome email accepted by Resend")
        print(f"     recipient={masked}")
        print(f"     resend_id={resend_id}")
    else:
        print(f"[FAIL] Welcome email failed")
        print(f"       code={result.get('error_code','unknown')}")
        print(f"       reason={result.get('error_message','')}")
        sys.exit(1)


# ─── ARGPARSE ────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="PeopleOS Brief CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--dry-run", action="store_true", help="Search + generate + print. No save, no email.")
    group.add_argument("--generate-today", action="store_true", help="Generate today's issue, save static files.")
    group.add_argument("--test", metavar="EMAIL", help="Generate + send to one test email.")
    group.add_argument("--send-live", action="store_true", help="Send to all active subscribers. LIVE.")
    group.add_argument("--backfill-initial", action="store_true", help="Generate last 3 days if archive is empty.")
    group.add_argument("--prune-archive", action="store_true", help="Delete issues older than ARCHIVE_RETENTION_DAYS.")
    group.add_argument("--seed-demo", action="store_true", help="Seed demo data if no issues exist.")
    group.add_argument("--refresh-index", action="store_true", help="Rebuild archive.json and dates.json.")
    group.add_argument("--audit-links", action="store_true", help="Scan all issue JSON files for homepage/missing source URLs.")
    # ── Reliability commands ──
    group.add_argument("--check-today", action="store_true", help="Validate today's issue completeness. Exit 0=ok, 1=fail.")
    group.add_argument("--ensure-today", action="store_true", help="Generate today's issue only if missing/incomplete.")
    group.add_argument("--send-live-today", action="store_true", help="Send today's newsletter only if issue is complete.")
    group.add_argument("--mark-generation-started", action="store_true", help="Write in_progress to status.json.")
    group.add_argument("--mark-generation-failed", action="store_true", help="Write failed to status.json.")
    group.add_argument("--preflight", action="store_true", help="Check env vars and folder structure.")
    group.add_argument("--test-email", metavar="EMAIL", help="Send test email (alias for --test).")
    group.add_argument("--wait-production-today", action="store_true", help="Poll BASE_URL until today's issue JSON is live. Exit 0=ready, 1=timeout.")
    group.add_argument("--debug-subscribers", action="store_true", help="Count active subscribers and print masked sample. No email sent.")
    group.add_argument("--test-welcome-email", metavar="EMAIL", help="Send one welcome email to EMAIL. No DB write. For testing only.")

    parser.add_argument("--force", action="store_true", help="Force operation even if issue already exists.")
    parser.add_argument("--admin-force", action="store_true", help="Skip in_progress guard in --ensure-today.")
    parser.add_argument("--error-msg", metavar="MSG", default="", help="Error message for --mark-generation-failed.")
    parser.add_argument("--force-resend", action="store_true", help="Bypass duplicate-send guard in --send-live-today.")
    parser.add_argument("--validate-only", action="store_true", help="With --test-welcome-email: validate config only, do NOT call Resend.")

    args = parser.parse_args()

    if args.dry_run:
        _run_dry(force=args.force)
    elif args.generate_today:
        _run_generate_today(force=args.force)
    elif args.test:
        _run_test(args.test)
    elif args.send_live:
        _run_live()
    elif args.backfill_initial:
        _run_backfill_initial(force=args.force)
    elif args.prune_archive:
        _run_prune_archive()
    elif args.seed_demo:
        _run_seed_demo()
    elif args.refresh_index:
        _run_refresh_index()
    elif args.audit_links:
        _run_audit_links()
    elif args.check_today:
        _run_check_today()
    elif args.ensure_today:
        _run_ensure_today(admin_force=args.admin_force or args.force)
    elif args.send_live_today:
        _run_send_live_today(force_resend=args.force_resend)
    elif args.wait_production_today:
        _run_wait_production_today()
    elif args.debug_subscribers:
        _run_debug_subscribers()
    elif args.mark_generation_started:
        _run_mark_generation_started()
    elif args.mark_generation_failed:
        _run_mark_generation_failed(error=args.error_msg)
    elif args.preflight:
        _run_preflight()
    elif args.test_email:
        _run_test_email(args.test_email)
    elif args.test_welcome_email:
        _run_test_welcome_email(args.test_welcome_email, dry_run=args.validate_only)


if __name__ == "__main__":
    main()
