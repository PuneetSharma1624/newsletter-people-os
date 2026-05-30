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
from pathlib import Path
from typing import Any

from newsletter.logger import log

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
    return _read_json(_DATA_DIR / "status.json", {
        "current_date": None, "status": "not_started",
        "last_started_at": None, "last_completed_at": None,
        "last_error": None, "sections_complete": 0,
    })


def set_status(
    status: str,
    current_date: str | None = None,
    error: str | None = None,
    sections_complete: int | None = None,
) -> None:
    existing = get_status()
    now = datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00","Z")
    existing["status"] = status
    if current_date:
        existing["current_date"] = current_date
    if status == "running" and not existing.get("last_started_at"):
        existing["last_started_at"] = now
    if status in ("complete", "failed"):
        existing["last_completed_at"] = now
    if error is not None:
        existing["last_error"] = error
    if status == "running":
        existing["last_error"] = None
    if status == "complete":
        existing["last_started_at"] = None  # reset for next run
    if sections_complete is not None:
        existing["sections_complete"] = sections_complete
    _write_json(_DATA_DIR / "status.json", existing)


def is_today_complete(date: str) -> bool:
    s = get_status()
    return s.get("current_date") == date and s.get("status") == "complete"


def is_running_recently(date: str, stale_minutes: int = 60) -> bool:
    """True if a run is in progress and not stale."""
    s = get_status()
    if s.get("current_date") != date or s.get("status") != "running":
        return False
    started = s.get("last_started_at")
    if not started:
        return False
    try:
        dt = datetime.datetime.fromisoformat(started.rstrip("Z"))
        age = (datetime.datetime.utcnow() - dt).total_seconds() / 60
        return age < stale_minutes
    except Exception:
        return False


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
