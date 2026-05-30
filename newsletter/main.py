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
    return datetime.date.today().isoformat()


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
        total = issue.get("total_dashboard_items", 0)
        log.info(f"Generated and saved: {date} ({total} dashboard items)")
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

    # Also try to get/create DB issue for send log
    try:
        from newsletter import archive as arc
        from newsletter.renderer import render_html_email, render_text_email
        base_url = config.base_url()
        placeholder = f"{base_url}/api/unsubscribe?token=PLACEHOLDER"
        html = render_html_email(issue, placeholder, base_url)
        text = render_text_email(issue, placeholder, base_url)
        db_issue = arc.save_issue(issue, html, text)
        issue_id = db_issue["id"]
    except Exception as exc:
        log.warning(f"DB save skipped (no Supabase?): {exc}")
        issue_id = f"static-{date}"

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

    parser.add_argument("--force", action="store_true", help="Force operation even if issue already exists.")

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


if __name__ == "__main__":
    main()
