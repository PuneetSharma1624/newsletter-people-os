"""Subscriber data layer — all Supabase interactions for subscribers."""
from __future__ import annotations

import uuid
from uuid import UUID
from typing import Any


def _assert_uuid(value: str, field: str = "issue_id") -> None:
    """Fail fast with a clear local error before Postgres throws 22P02."""
    try:
        UUID(str(value))
    except Exception:
        raise ValueError(f"{field} must be a valid UUID, got: {value!r}")

from supabase import create_client, Client

from newsletter import config
from newsletter.logger import log
from newsletter.utils import generate_token, normalize_email


def _client() -> Client:
    return create_client(config.supabase_url(), config.supabase_service_key())


def upsert_subscriber(email: str, source: str = "web") -> dict[str, Any]:
    """
    Insert new subscriber or reactivate unsubscribed one.
    Returns dict with keys: subscriber_id, is_new, was_reactivated, already_active.
    """
    email = normalize_email(email)
    token = generate_token()
    client = _client()

    result = (
        client.rpc("upsert_subscriber", {"p_email": email, "p_token": token, "p_source": source})
        .execute()
    )
    data = result.data
    if data:
        row = data[0]
        return {
            "subscriber_id": row["subscriber_id"],
            "is_new": row["is_new"],
            "was_reactivated": row["was_reactivated"],
            "already_active": row["already_active"],
        }
    raise RuntimeError(f"upsert_subscriber returned no data for {email}")


def get_active_subscribers() -> list[dict[str, Any]]:
    """Return all active subscribers."""
    client = _client()
    result = (
        client.table("subscribers")
        .select("id, email, unsubscribe_token")
        .eq("status", "active")
        .execute()
    )
    return result.data or []


def get_by_token(token: str) -> dict[str, Any] | None:
    """Fetch subscriber by unsubscribe token."""
    client = _client()
    result = (
        client.table("subscribers")
        .select("id, email, status")
        .eq("unsubscribe_token", token)
        .execute()
    )
    data = result.data
    return data[0] if data else None


def unsubscribe_by_token(token: str) -> bool:
    """Mark subscriber as unsubscribed. Returns True if found and updated."""
    import datetime
    client = _client()
    result = (
        client.table("subscribers")
        .update({"status": "unsubscribed", "unsubscribed_at": datetime.datetime.utcnow().isoformat(), "updated_at": datetime.datetime.utcnow().isoformat()})
        .eq("unsubscribe_token", token)
        .eq("status", "active")
        .execute()
    )
    return bool(result.data)


def probe_send_log() -> None:
    """Verify send_log table is reachable. Raises if not. Used as pre-flight before batch send."""
    client = _client()
    client.table("send_log").select("id").limit(1).execute()


def already_sent(issue_id: str, subscriber_id: str) -> bool:
    """Check if issue already sent to subscriber (application-level guard)."""
    _assert_uuid(issue_id, "issue_id")
    _assert_uuid(subscriber_id, "subscriber_id")
    client = _client()
    result = (
        client.table("send_log")
        .select("id")
        .eq("issue_id", issue_id)
        .eq("subscriber_id", subscriber_id)
        .eq("status", "sent")
        .execute()
    )
    return bool(result.data)


def already_sent_today(issue_date: str) -> bool:
    """Check if a successful live send already went out for issue_date (any subscriber)."""
    try:
        client = _client()
        result = (
            client.table("send_log")
            .select("id")
            .eq("issue_date", issue_date)
            .eq("send_type", "live")
            .eq("status", "sent")
            .limit(1)
            .execute()
        )
        return bool(result.data)
    except Exception:
        return False


def _mask_email(email: str) -> str:
    if not email or "@" not in email:
        return "***"
    local, domain = email.split("@", 1)
    return f"{local[0]}***@{domain}"


def log_send(
    issue_id: str,
    subscriber_id: str,
    email: str,
    status: str,
    resend_message_id: str = "",
    error_message: str = "",
    issue_date: str = "",
    send_type: str = "live",
) -> bool:
    """Write send result to send_log. Returns True if logged successfully."""
    _assert_uuid(issue_id, "issue_id")
    client = _client()
    payload: dict[str, Any] = {
        "issue_id": issue_id,
        "subscriber_id": subscriber_id,
        "email": email,
        "status": status,
        "send_type": send_type,
    }
    if issue_date:
        payload["issue_date"] = issue_date
    if resend_message_id:
        payload["resend_message_id"] = resend_message_id
    if error_message:
        payload["error_message"] = error_message[:500]

    try:
        client.table("send_log").insert(payload).execute()
        return True
    except Exception as exc:
        err = str(exc)
        # If full payload fails due to missing optional columns, retry with minimal payload
        if any(k in err.lower() for k in ("schema cache", "does not exist", "column", "42703")):
            minimal: dict[str, Any] = {
                "issue_id": issue_id,
                "subscriber_id": subscriber_id,
                "status": status,
            }
            try:
                client.table("send_log").insert(minimal).execute()
                log.warning(f"log_send used minimal payload for {_mask_email(email)} (schema mismatch: {err[:120]})")
                return True
            except Exception as exc2:
                log.warning(f"log_send failed (minimal) for {_mask_email(email)}: {exc2}")
                return False
        # Uniqueness violation = already logged. Safe to ignore.
        log.warning(f"log_send conflict or error for {_mask_email(email)}: {err[:120]}")
        return False
