"""Newsletter archive — store and retrieve structured issues from Supabase."""
from __future__ import annotations

import datetime
from typing import Any

from supabase import create_client

from newsletter import config
from newsletter.logger import log


def _client():
    return create_client(config.supabase_url(), config.supabase_service_key())


def get_issue_by_date(date: str) -> dict[str, Any] | None:
    """Return existing issue for date (YYYY-MM-DD) or None."""
    client = _client()
    result = (
        client.table("newsletter_issues")
        .select("*")
        .eq("issue_date", date)
        .execute()
    )
    data = result.data
    return data[0] if data else None


def get_latest_issue() -> dict[str, Any] | None:
    """Return most recent published issue."""
    client = _client()
    result = (
        client.table("newsletter_issues")
        .select("*")
        .order("issue_date", desc=True)
        .limit(1)
        .execute()
    )
    data = result.data
    return data[0] if data else None


def list_issues(limit: int = 60) -> list[dict[str, Any]]:
    """Return archive list. Selects only columns that exist in minimal schema."""
    client = _client()
    # sections column may not exist — select only safe columns
    try:
        result = (
            client.table("newsletter_issues")
            .select("id, issue_date, subject, preheader, created_at, sent_at")
            .order("issue_date", desc=True)
            .limit(limit)
            .execute()
        )
        return result.data or []
    except Exception as exc:
        log.warning(f"list_issues full select failed: {exc} — trying minimal")
        result = (
            client.table("newsletter_issues")
            .select("id, issue_date")
            .order("issue_date", desc=True)
            .limit(limit)
            .execute()
        )
        return result.data or []


def list_available_dates() -> list[str]:
    """Return list of YYYY-MM-DD strings with published issues."""
    client = _client()
    result = (
        client.table("newsletter_issues")
        .select("issue_date")
        .order("issue_date", desc=True)
        .limit(90)
        .execute()
    )
    return [row["issue_date"] for row in (result.data or [])]


def save_issue(issue: dict[str, Any], html: str, text: str) -> dict[str, Any]:
    """
    Save structured issue to DB. Includes sections JSONB, html, text.
    Raises on duplicate issue_date (unique constraint).
    Does NOT include executive_summary — column not in newsletter_issues schema.
    """
    client = _client()
    payload = {
        "issue_date": issue["issue_date"],
        "subject": issue["subject"],
        "preheader": issue.get("preheader", ""),
        "html": html,
        "text": text,
        "sections": issue.get("sections", []),
        "sources": _extract_sources(issue),
    }
    result = client.table("newsletter_issues").insert(payload).execute()
    data = result.data
    if data:
        log.info(f"Issue saved for {issue['issue_date']}")
        return data[0]
    raise RuntimeError(f"Failed to save issue for {issue['issue_date']}")


def _fetch_issue_uuid(issue_date: str) -> str | None:
    """
    Try to find existing newsletter_issues row for date.
    Tolerates schema variations (issue_date vs date column).
    Returns UUID string or None.
    """
    client = _client()

    # Try issue_date column (preferred)
    try:
        result = client.table("newsletter_issues").select("id").eq("issue_date", issue_date).limit(1).execute()
        if result.data:
            return result.data[0]["id"]
    except Exception as exc:
        log.warning(f"fetch by issue_date failed: {exc}")

    # Try date column (fallback)
    try:
        result = client.table("newsletter_issues").select("id").eq("date", issue_date).limit(1).execute()
        if result.data:
            return result.data[0]["id"]
    except Exception:
        pass

    return None


def _try_insert_issue(client, payload: dict) -> str | None:
    """Attempt insert. Returns UUID string on success, None on failure."""
    try:
        result = client.table("newsletter_issues").insert(payload).execute()
        if result.data and result.data[0].get("id"):
            return result.data[0]["id"]
    except Exception as exc:
        log.warning(f"Insert attempt failed ({list(payload.keys())}): {str(exc)[:120]}")
    return None


def ensure_newsletter_issue(issue: dict[str, Any], html: str = "", text: str = "") -> str:
    """
    Get or create newsletter_issues row for send identity.
    Always returns a real UUID string.
    Uses minimal payload with fallback variants — never inserts sections/sources/html/text
    unless they succeed. Never aborts due to missing optional columns.
    """
    issue_date = issue["issue_date"]
    subject = issue.get("subject", f"PeopleOS Brief — {issue_date}")
    preheader = issue.get("preheader", "")
    title = f"PeopleOS Brief — {issue_date}"
    slug = f"static-{issue_date}"

    # Step 1: fetch existing row
    existing_id = _fetch_issue_uuid(issue_date)
    if existing_id:
        log.info(f"DB issue row found: {existing_id}")
        return existing_id

    client = _client()

    # Step 2: try insert with progressively smaller payloads
    # Never include: sections, sources, executive_summary, dashboard_items, email_items
    insert_attempts = [
        # A: richest safe payload with html/text
        {"issue_date": issue_date, "subject": subject, "preheader": preheader, "html": html, "text": text},
        # B: no html/text (large blobs may cause issues)
        {"issue_date": issue_date, "subject": subject, "preheader": preheader},
        # C: minimal with issue_date
        {"issue_date": issue_date, "subject": subject},
        # D: bare minimum with issue_date
        {"issue_date": issue_date},
        # E: try date column instead
        {"date": issue_date, "subject": subject},
        # F: try date column bare
        {"date": issue_date},
    ]

    for payload in insert_attempts:
        uid = _try_insert_issue(client, payload)
        if uid:
            log.info(f"DB issue row created (fields: {list(payload.keys())}): {uid}")
            return uid
        # After each failed insert, try fetch again (duplicate race condition)
        existing_id = _fetch_issue_uuid(issue_date)
        if existing_id:
            log.info(f"DB issue row found after insert retry: {existing_id}")
            return existing_id

    raise RuntimeError(
        f"Could not get or create newsletter_issues row for {issue_date}. "
        f"Tried fetch + {len(insert_attempts)} insert variants. "
        f"Check newsletter_issues schema in Supabase."
    )


def _extract_sources(issue: dict) -> list[dict]:
    """Flatten all source URLs from sections for top-level sources field."""
    sources = []
    for section in issue.get("sections", []):
        for item in section.get("items", []):
            if item.get("source_url"):
                sources.append({
                    "title": item.get("headline", ""),
                    "url": item["source_url"],
                    "source_name": item.get("source_name", ""),
                    "section": section.get("section_name", ""),
                })
    return sources


def mark_sent(issue_id: str) -> None:
    try:
        client = _client()
        client.table("newsletter_issues").update(
            {"sent_at": datetime.datetime.utcnow().isoformat()}
        ).eq("id", issue_id).execute()
        log.info(f"Issue {issue_id} marked sent")
    except Exception as exc:
        log.warning(f"mark_sent failed for {issue_id}: {exc} — non-fatal, continuing")


def get_or_create_issue(
    issue_date: str,
    generator_fn,
    renderer_fn,
    force_regenerate: bool = False,
) -> dict[str, Any]:
    """
    Return existing DB issue or generate+save new one.
    generator_fn() → structured issue dict
    renderer_fn(issue) → (html, text) tuple
    """
    if not force_regenerate:
        existing = get_issue_by_date(issue_date)
        if existing:
            log.info(f"Loaded existing issue for {issue_date}")
            return existing

    log.info(f"Generating new issue for {issue_date}")
    issue = generator_fn()
    html, text = renderer_fn(issue)
    return save_issue(issue, html, text)
