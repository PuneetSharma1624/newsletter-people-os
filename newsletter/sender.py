"""Resend-powered email sender for PeopleOS Brief."""
from __future__ import annotations

from typing import Any

from newsletter import config
from newsletter.logger import log, log_send_success, log_send_failure, log_send_skipped
from newsletter.renderer import render_html_email, render_text_email


def send_email(
    to_email: str,
    subject: str,
    html: str,
    text: str,
    unsubscribe_url: str,
    preheader: str = "",
) -> dict[str, Any]:
    """Send single email via Resend. Never raises."""
    config.validate_config(["RESEND_API_KEY", "NEWSLETTER_FROM_EMAIL"])
    import resend
    resend.api_key = config.resend_key()

    # Preheader invisible text (email preview line)
    if preheader:
        pre = (
            f'<div style="display:none;max-height:0;overflow:hidden;mso-hide:all;">'
            f'{preheader}&nbsp;‌&zwnj;&nbsp;‌&zwnj;&nbsp;‌&zwnj;</div>'
        )
        html = pre + html

    from_name = config.newsletter_name()
    params: dict[str, Any] = {
        "from": f"{from_name} <{config.from_email()}>",
        "to": [to_email],
        "subject": subject,
        "html": html,
        "text": text,
        "headers": {
            "List-Unsubscribe": f"<{unsubscribe_url}>",
            "List-Unsubscribe-Post": "List-Unsubscribe=One-Click",
        },
    }
    rt = config.reply_to()
    if rt:
        params["reply_to"] = rt

    try:
        email = resend.Emails.send(params)
        msg_id = getattr(email, "id", "") or (email.get("id", "") if isinstance(email, dict) else "")
        log_send_success(to_email, msg_id)
        return {"ok": True, "message_id": msg_id, "error": ""}
    except Exception as exc:
        error = str(exc)[:300]
        log_send_failure(to_email, error)
        return {"ok": False, "message_id": "", "error": error}


def send_to_subscriber(
    subscriber: dict,
    issue: dict,
    issue_id: str,
    is_test: bool = False,
) -> dict[str, Any]:
    """Send to one subscriber. Checks duplicates. Logs result."""
    from newsletter.subscribers import already_sent, log_send

    subscriber_id = subscriber.get("id", "")
    email = subscriber.get("email", "")
    token = subscriber.get("unsubscribe_token", "test-token")

    unsubscribe_url = f"{config.base_url()}/api/unsubscribe?token={token}"
    base_url = config.base_url()

    if not is_test and already_sent(issue_id, subscriber_id):
        log_send_skipped(email)
        return {"ok": True, "skipped": True, "message_id": "", "error": ""}

    # Build per-subscriber email (unsubscribe URL is unique per subscriber)
    html = render_html_email(issue, unsubscribe_url, base_url)
    text = render_text_email(issue, unsubscribe_url, base_url)

    result = send_email(
        to_email=email,
        subject=issue.get("subject", "PeopleOS Brief"),
        html=html,
        text=text,
        unsubscribe_url=unsubscribe_url,
        preheader=issue.get("preheader", ""),
    )

    db_logged = False
    if not is_test and subscriber_id:
        status = "sent" if result["ok"] else "failed"
        db_logged = log_send(
            issue_id=issue_id,
            subscriber_id=subscriber_id,
            email=email,
            status=status,
            resend_message_id=result.get("message_id", ""),
            error_message=result.get("error", ""),
            issue_date=issue.get("issue_date", ""),
            send_type="live",
        )

    result["skipped"] = False
    result["db_logged"] = db_logged
    return result


def send_welcome_email(email: str, base_url: str = "", dry_run: bool = False) -> dict[str, Any]:
    """
    Send welcome email to a new/reactivated subscriber. Never raises.
    Returns structured dict:
      success: {"ok": True, "status": "sent", "resend_id": "re_...", "error_code": None, "error_message": None}
      failure: {"ok": False, "status": "failed", "resend_id": None, "error_code": "<code>", "error_message": "<msg>"}

    base_url source: passed as argument (CLI), or os.environ BASE_URL via config.base_url().
    dry_run=True: validates config and prints what would be sent, but does NOT call Resend.
    """
    import os as _os

    masked = _mask_email_local(email)

    # ── env validation ───────────────────────────────────────────────────────
    resend_key = _os.environ.get("RESEND_API_KEY", "").strip()
    from_email_val = _os.environ.get("NEWSLETTER_FROM_EMAIL", "").strip()
    has_reply_to = bool(_os.environ.get("NEWSLETTER_REPLY_TO", "").strip())
    raw_base = base_url or _os.environ.get("BASE_URL", "").strip()
    base_is_localhost = bool(raw_base and ("localhost" in raw_base or "127.0.0.1" in raw_base))
    base_log = "localhost" if base_is_localhost else (raw_base or "(not set)")

    def _fail(code: str, msg: str) -> dict[str, Any]:
        log.warning(
            f"Welcome email failed for {masked} | code={code} | reason={msg} | "
            f"has_api_key={bool(resend_key)} | has_from_email={bool(from_email_val)} | "
            f"has_reply_to={has_reply_to} | base_url={base_log} | base_is_localhost={base_is_localhost}"
        )
        return {"ok": False, "status": "failed", "resend_id": None, "error_code": code, "error_message": msg}

    if not resend_key:
        return _fail("missing_env_RESEND_API_KEY", "RESEND_API_KEY is not configured")
    if not from_email_val:
        return _fail("missing_env_NEWSLETTER_FROM_EMAIL", "NEWSLETTER_FROM_EMAIL is not configured")
    if not raw_base:
        return _fail("missing_env_BASE_URL", "BASE_URL is not configured")
    if base_is_localhost:
        return _fail("invalid_BASE_URL_localhost",
                     "BASE_URL is localhost — set BASE_URL to your production Vercel URL")

    effective_base = base_url or config.base_url()

    if dry_run:
        log.info(
            f"[DRY RUN] Would send welcome email | recipient={masked} | "
            f"from={from_email_val} | base_url={effective_base} | has_api_key=True"
        )
        return {"ok": True, "status": "dry_run", "resend_id": None, "error_code": None, "error_message": None}

    html = f"""<h1>Welcome to PeopleOS Brief</h1>
<p>You're now subscribed to PeopleOS Brief — your daily executive intelligence briefing across markets, AI, HR, economics, and major updates.</p>
<p>Every morning, you'll receive a concise digest designed to help you catch the signal without scanning the noise.</p>
<p><a href="{effective_base}">Open PeopleOS Brief</a></p>
<p style="color:#666;font-size:12px;">You are receiving this because you subscribed to PeopleOS Brief.</p>"""

    text = f"""Welcome to PeopleOS Brief.

You're now subscribed to PeopleOS Brief — your daily executive intelligence briefing across markets, AI, HR, economics, and major updates.

Open PeopleOS Brief:
{effective_base}

You are receiving this because you subscribed to PeopleOS Brief."""

    raw = send_email(
        to_email=email,
        subject="Welcome to PeopleOS Brief",
        html=html,
        text=text,
        unsubscribe_url=f"{effective_base}/api/unsubscribe",
    )
    # send_email returns {"ok": bool, "message_id": str, "error": str}
    if raw["ok"]:
        resend_id = raw.get("message_id", "")
        log.info(f"Welcome email sent | recipient={masked} | resend_id={resend_id}")
        return {"ok": True, "status": "sent", "resend_id": resend_id, "error_code": None, "error_message": None}
    else:
        err = raw.get("error", "unknown")
        code = "resend_error"
        # Try to extract HTTP status code if present in error string
        import re as _re
        m = _re.search(r"(\d{3})", err)
        if m:
            code = f"resend_{m.group(1)}"
        log.warning(
            f"Welcome email failed for {masked} | code={code} | error={err[:120]} | "
            f"has_api_key=True | from={from_email_val} | base_url={effective_base}"
        )
        return {"ok": False, "status": "failed", "resend_id": None, "error_code": code, "error_message": err}


def _mask_email_local(email: str) -> str:
    """Local email masker for sender.py (avoids circular import from logger)."""
    if not email or "@" not in email:
        return "***"
    local, domain = email.split("@", 1)
    return f"{local[0]}***@{domain}"


def send_test_email(test_email: str, issue: dict) -> dict[str, Any]:
    """Test mode: single email, placeholder token, no DB log."""
    log.info(f"TEST MODE — sending to {test_email}")
    base_url = config.base_url()
    unsubscribe_url = f"{base_url}/api/unsubscribe?token=TEST-TOKEN"
    html = render_html_email(issue, unsubscribe_url, base_url)
    text = render_text_email(issue, unsubscribe_url, base_url)
    return send_email(
        to_email=test_email,
        subject=f"[TEST] {issue.get('subject', 'PeopleOS Brief')}",
        html=html,
        text=text,
        unsubscribe_url=unsubscribe_url,
        preheader=issue.get("preheader", ""),
    )
