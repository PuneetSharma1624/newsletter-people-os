"""
Static publishing model for PeopleOS Brief.
Generated content saved to landing/data/ as static JSON files.
Public dashboard reads these files — no API calls for guests.

Structure:
  landing/data/
    status.json          — generation status/lock
    dates.json           — available issue dates
    archive.json         — archive metadata list
    issues/
      YYYY-MM-DD.json    — complete issue
      YYYY-MM-DD.partial.json — in-progress (not public)
"""
from __future__ import annotations

import datetime
import json
import os
import urllib.request
import urllib.error
from pathlib import Path
from typing import Any

from newsletter.logger import log

IST = datetime.timezone(datetime.timedelta(hours=5, minutes=30))


def get_ist_now() -> datetime.datetime:
    return datetime.datetime.now(IST)


def get_ist_date() -> str:
    return get_ist_now().date().isoformat()


def _utc_now_str() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")


def _ist_now_str() -> str:
    return get_ist_now().isoformat()

# Path resolution: this file is newsletter/static_publisher.py
# landing/data/ is ../landing/data/ from here
_DATA_DIR = Path(__file__).parent.parent / "landing" / "data"
_ISSUES_DIR = _DATA_DIR / "issues"


def _ensure_dirs() -> None:
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    _ISSUES_DIR.mkdir(parents=True, exist_ok=True)


def _read_json(path: Path, default: Any = None) -> Any:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        log.warning(f"Failed to read {path}: {exc}")
    return default


def _write_json(path: Path, data: Any) -> None:
    _ensure_dirs()
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


# ─── STATUS ──────────────────────────────────────────────────────────────────

def get_status() -> dict:
    defaults = {
        "latest_issue_date": None,
        "latest_complete_issue_date": None,
        "generation_status": "not_started",
        "generation_started_at_utc": None,
        "generation_completed_at_utc": None,
        "generation_started_at_ist": None,
        "generation_completed_at_ist": None,
        "last_generation_run_id": None,
        "last_generation_attempt": None,
        "last_generation_error": None,
        "sections_complete": 0,
        "last_email_sent_date": None,
        "last_email_sent_at_utc": None,
        "last_email_status": "not_sent",
        # legacy compat fields
        "current_date": None,
        "status": "not_started",
        "last_started_at": None,
        "last_completed_at": None,
        "last_error": None,
    }
    stored = _read_json(_DATA_DIR / "status.json", {})
    defaults.update(stored)
    return defaults


def set_status(
    status: str,
    current_date: str | None = None,
    error: str | None = None,
    sections_complete: int | None = None,
    attempt: str | None = None,
    run_id: str | None = None,
    email_date: str | None = None,
    email_status: str | None = None,
    email_sent_at_utc: str | None = None,
) -> None:
    existing = get_status()
    utc_now = _utc_now_str()
    ist_now = _ist_now_str()

    # Map old "running"/"complete"/"failed" to new schema names
    gen_status_map = {
        "running": "in_progress",
        "complete": "complete",
        "failed": "failed",
        "not_started": "not_started",
        "retrying": "retrying",
        "skipped_already_complete": "skipped_already_complete",
    }
    gen_status = gen_status_map.get(status, status)

    existing["generation_status"] = gen_status
    # legacy compat
    existing["status"] = status

    if current_date:
        existing["current_date"] = current_date
        existing["latest_issue_date"] = current_date

    if gen_status == "in_progress":
        if not existing.get("generation_started_at_utc"):
            existing["generation_started_at_utc"] = utc_now
            existing["generation_started_at_ist"] = ist_now
            existing["last_started_at"] = utc_now
        existing["last_generation_error"] = None
        existing["last_error"] = None

    if gen_status in ("complete", "failed"):
        existing["generation_completed_at_utc"] = utc_now
        existing["generation_completed_at_ist"] = ist_now
        existing["last_completed_at"] = utc_now

    if gen_status == "complete" and current_date:
        existing["latest_complete_issue_date"] = current_date
        existing["generation_started_at_utc"] = None
        existing["generation_started_at_ist"] = None
        existing["last_started_at"] = None

    if error is not None:
        existing["last_generation_error"] = error
        existing["last_error"] = error

    if sections_complete is not None:
        existing["sections_complete"] = sections_complete

    if attempt is not None:
        existing["last_generation_attempt"] = attempt

    if run_id is not None:
        existing["last_generation_run_id"] = run_id

    if email_date is not None:
        existing["last_email_sent_date"] = email_date
    if email_status is not None:
        existing["last_email_status"] = email_status
    if email_sent_at_utc is not None:
        existing["last_email_sent_at_utc"] = email_sent_at_utc

    _write_json(_DATA_DIR / "status.json", existing)


def is_today_complete(date: str) -> bool:
    s = get_status()
    return s.get("latest_complete_issue_date") == date and s.get("generation_status") == "complete"


def is_running_recently(date: str, stale_minutes: int = 60) -> bool:
    """True if a run is in progress and not stale."""
    s = get_status()
    if s.get("latest_issue_date") != date and s.get("current_date") != date:
        return False
    if s.get("generation_status") not in ("in_progress", "running"):
        return False
    started = s.get("generation_started_at_utc") or s.get("last_started_at")
    if not started:
        return False
    try:
        dt = datetime.datetime.fromisoformat(started.rstrip("Z")).replace(tzinfo=datetime.timezone.utc)
        age = (datetime.datetime.now(datetime.timezone.utc) - dt).total_seconds() / 60
        return age < stale_minutes
    except Exception:
        return False


REQUIRED_ITEM_FIELDS = ["headline", "summary", "source_name", "source_url", "why_it_matters", "peopleos_lens", "action"]
REQUIRED_SECTIONS = 12
ITEMS_PER_SECTION = 6
EXPECTED_DASHBOARD_ITEMS = 72
EXPECTED_EMAIL_ITEMS = 24


def validate_issue_complete(issue_date: str) -> dict:
    """
    Check issue completeness. Returns structured result dict.
    ok=True only if ALL checks pass.
    """
    errors: list[str] = []
    result: dict = {
        "ok": False,
        "issue_date": issue_date,
        "exists": False,
        "valid_json": False,
        "date_matches": False,
        "sections": 0,
        "dashboard_items": 0,
        "email_items": 0,
        "in_dates_json": False,
        "in_archive_json": False,
        "status_complete": False,
        "errors": errors,
    }

    path = _ISSUES_DIR / f"{issue_date}.json"
    if not path.exists():
        errors.append("Issue file missing")
        return result
    result["exists"] = True

    try:
        issue = json.loads(path.read_text(encoding="utf-8"))
        result["valid_json"] = True
    except Exception as exc:
        errors.append(f"Invalid JSON: {exc}")
        return result

    if issue.get("issue_date") != issue_date:
        errors.append(f"issue_date mismatch: got {issue.get('issue_date')!r}")
    else:
        result["date_matches"] = True

    sections = issue.get("sections")
    if not isinstance(sections, list):
        errors.append("sections field missing or not a list")
        return result

    result["sections"] = len(sections)
    if len(sections) != REQUIRED_SECTIONS:
        errors.append(f"Expected {REQUIRED_SECTIONS} sections, got {len(sections)}")

    dash_items = 0
    email_items = 0
    for sec in sections:
        items = sec.get("items", [])
        if len(items) != ITEMS_PER_SECTION:
            errors.append(f"Section {sec.get('code','?')}: expected {ITEMS_PER_SECTION} items, got {len(items)}")
        for item in items:
            dash_items += 1
            missing = [f for f in REQUIRED_ITEM_FIELDS if not item.get(f)]
            if missing:
                errors.append(f"Item missing fields: {missing} in section {sec.get('code','?')}")
        email_items += min(len(items), 2)

    result["dashboard_items"] = dash_items
    result["email_items"] = email_items

    if dash_items != EXPECTED_DASHBOARD_ITEMS:
        errors.append(f"Expected {EXPECTED_DASHBOARD_ITEMS} dashboard items, got {dash_items}")
    if email_items != EXPECTED_EMAIL_ITEMS:
        errors.append(f"Expected {EXPECTED_EMAIL_ITEMS} email items, got {email_items}")

    dates = get_dates()
    result["in_dates_json"] = issue_date in dates
    if not result["in_dates_json"]:
        errors.append(f"{issue_date} not in dates.json")

    archive = get_archive()
    result["in_archive_json"] = any(a.get("issue_date") == issue_date for a in archive)
    if not result["in_archive_json"]:
        errors.append(f"{issue_date} not in archive.json")

    s = get_status()
    result["status_complete"] = (
        s.get("generation_status") == "complete"
        and s.get("latest_complete_issue_date") == issue_date
    )
    if not result["status_complete"]:
        errors.append("status.json does not mark today as complete")

    result["ok"] = len(errors) == 0
    return result


def check_production_issue_available(issue_date: str) -> dict:
    """
    Hit BASE_URL/data/issues/YYYY-MM-DD.json and validate.
    Returns dict with ok, status_code, errors.
    """
    from newsletter import config as cfg
    base_url = (cfg.base_url() or "").rstrip("/")
    url = f"{base_url}/data/issues/{issue_date}.json"
    errors: list[str] = []
    result = {"ok": False, "url": url, "status_code": None, "errors": errors}

    if not base_url:
        errors.append("BASE_URL not configured")
        return result

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "PeopleOS-Brief-Checker/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            result["status_code"] = resp.status
            if resp.status != 200:
                errors.append(f"HTTP {resp.status}")
                return result
            try:
                issue = json.loads(resp.read().decode("utf-8"))
            except Exception as exc:
                errors.append(f"Invalid JSON from production: {exc}")
                return result
    except urllib.error.HTTPError as exc:
        result["status_code"] = exc.code
        errors.append(f"HTTP error {exc.code}")
        return result
    except Exception as exc:
        errors.append(f"Network error: {exc}")
        return result

    if issue.get("issue_date") != issue_date:
        errors.append(f"issue_date mismatch on production: got {issue.get('issue_date')!r}")

    sections = issue.get("sections", [])
    if len(sections) != REQUIRED_SECTIONS:
        errors.append(f"Production: expected {REQUIRED_SECTIONS} sections, got {len(sections)}")

    dash_items = sum(len(s.get("items", [])) for s in sections)
    if dash_items != EXPECTED_DASHBOARD_ITEMS:
        errors.append(f"Production: expected {EXPECTED_DASHBOARD_ITEMS} dashboard items, got {dash_items}")

    result["ok"] = len(errors) == 0
    result["sections"] = len(sections)
    result["dashboard_items"] = dash_items
    return result


# ─── PARTIAL PROGRESS ────────────────────────────────────────────────────────

def save_partial(date: str, sections_so_far: list[dict]) -> None:
    """Save partial progress after each section."""
    path = _ISSUES_DIR / f"{date}.partial.json"
    _write_json(path, {"issue_date": date, "sections": sections_so_far, "_partial": True})


def load_partial(date: str) -> list[dict]:
    """Load already-generated sections for resuming a failed run."""
    path = _ISSUES_DIR / f"{date}.partial.json"
    data = _read_json(path, {})
    return data.get("sections", [])


def delete_partial(date: str) -> None:
    path = _ISSUES_DIR / f"{date}.partial.json"
    if path.exists():
        path.unlink()


# ─── ISSUE ───────────────────────────────────────────────────────────────────

def issue_exists(date: str) -> bool:
    return (_ISSUES_DIR / f"{date}.json").exists()


def save_issue(issue: dict) -> None:
    """Save complete issue JSON. Updates archive and dates indices."""
    date = issue["issue_date"]
    path = _ISSUES_DIR / f"{date}.json"
    _write_json(path, issue)
    log.info(f"Issue saved: landing/data/issues/{date}.json")
    delete_partial(date)
    _update_indices()


def load_issue(date: str) -> dict | None:
    path = _ISSUES_DIR / f"{date}.json"
    return _read_json(path)


def load_latest_issue() -> dict | None:
    dates = get_dates()
    if not dates:
        return None
    return load_issue(dates[0])


# ─── INDICES ─────────────────────────────────────────────────────────────────

def get_dates() -> list[str]:
    data = _read_json(_DATA_DIR / "dates.json", {"dates": []})
    return data.get("dates", [])


def get_archive() -> list[dict]:
    data = _read_json(_DATA_DIR / "archive.json", {"issues": []})
    return data.get("issues", [])


def _update_indices() -> None:
    """Rebuild dates.json and archive.json from all issue files."""
    _ensure_dirs()
    issue_files = sorted(_ISSUES_DIR.glob("????-??-??.json"), reverse=True)
    dates = []
    archive_entries = []

    for f in issue_files:
        date = f.stem
        dates.append(date)
        issue = _read_json(f, {})
        if issue:
            sections = issue.get("sections", [])
            item_count = sum(len(s.get("items", [])) for s in sections)
            archive_entries.append({
                "issue_date": date,
                "title": issue.get("title", f"PeopleOS Brief — {date}"),
                "subject": issue.get("subject", ""),
                "preheader": issue.get("preheader", ""),
                "executive_summary": (issue.get("executive_summary") or "")[:200],
                "section_count": len(sections),
                "item_count": item_count,
                "sent_at": issue.get("sent_at"),
            })

    _write_json(_DATA_DIR / "dates.json", {"dates": dates})
    _write_json(_DATA_DIR / "archive.json", {"issues": archive_entries})
    log.info(f"Indices updated: {len(dates)} dates")


def refresh_indices() -> None:
    """Public API to force-rebuild indices."""
    _update_indices()


# ─── ARCHIVE PRUNING ─────────────────────────────────────────────────────────

def prune_archive(retention_days: int | None = None) -> list[str]:
    """
    Delete issue files older than retention_days.
    Never deletes today's issue.
    Returns list of deleted dates.
    """
    from newsletter import config as cfg
    days = retention_days or cfg.archive_retention_days()
    today = datetime.date.today()
    cutoff = today - datetime.timedelta(days=days)
    deleted = []

    for f in sorted(_ISSUES_DIR.glob("????-??-??.json")):
        date_str = f.stem
        try:
            d = datetime.date.fromisoformat(date_str)
        except ValueError:
            continue
        if d < cutoff and d != today:
            f.unlink()
            deleted.append(date_str)
            log.info(f"Pruned: {date_str}")

    if deleted:
        _update_indices()
        log.info(f"Pruned {len(deleted)} issues older than {days} days")
    else:
        log.info(f"No issues older than {days} days to prune")
    return deleted


# ─── DEMO SEED ───────────────────────────────────────────────────────────────

def seed_demo_data() -> None:
    """
    Seed landing/data/ with demo issues if no issues exist.
    Called on first setup so dashboard works without Supabase.
    """
    if get_dates():
        log.info("Demo seed skipped — issues already exist")
        return

    log.info("Seeding demo data...")
    try:
        from api.demo_data import get_demo_dates, get_demo_issue
        dates = get_demo_dates()
        for date in dates:
            issue = get_demo_issue(date)
            # Add required aggregate fields
            sections = issue.get("sections", [])
            total_items = sum(len(s.get("items", [])) for s in sections)
            issue["total_sections"] = len(sections)
            issue["total_dashboard_items"] = total_items
            issue["total_email_items"] = sum(min(len(s.get("items", [])), 2) for s in sections)
            save_issue(issue)
        # Set status to not_started (demo, not real generation)
        set_status("not_started")
        log.info(f"Demo data seeded: {len(dates)} dates")
    except Exception as exc:
        log.error(f"Demo seed failed: {exc}")
