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
    """Return archive list (date, subject, preheader, section count) desc."""
    client = _client()
    result = (
        client.table("newsletter_issues")
        .select("id, issue_date, subject, preheader, sections, created_at, sent_at")
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


def ensure_newsletter_issue(issue: dict[str, Any], html: str, text: str) -> str:
    """
    Get or create newsletter_issues row. Always returns a real UUID string.
    Handles duplicate issue_date gracefully (select-then-insert pattern).
    Raises RuntimeError only if UUID cannot be obtained after all attempts.
    """
    issue_date = issue["issue_date"]

    existing = get_issue_by_date(issue_date)
    if existing:
        log.info(f"DB issue row found: {existing['id']}")
        return existing["id"]

    client = _client()
    payload = {
        "issue_date": issue_date,
        "subject": issue.get("subject", ""),
        "preheader": issue.get("preheader", ""),
        "html": html,
        "text": text,
        "sections": issue.get("sections", []),
        "sources": _extract_sources(issue),
    }
    try:
        result = client.table("newsletter_issues").insert(payload).execute()
        data = result.data
        if data:
            log.info(f"DB issue row created: {data[0]['id']}")
            return data[0]["id"]
    except Exception as exc:
        log.warning(f"DB insert failed for {issue_date}: {exc} — retrying fetch")
        existing = get_issue_by_date(issue_date)
        if existing:
            log.info(f"DB issue row found after retry: {existing['id']}")
            return existing["id"]

    raise RuntimeError(f"Could not get or create newsletter_issues row for {issue_date}")


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
    client = _client()
    client.table("newsletter_issues").update(
        {"sent_at": datetime.datetime.utcnow().isoformat()}
    ).eq("id", issue_id).execute()
    log.info(f"Issue {issue_id} marked sent")


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
