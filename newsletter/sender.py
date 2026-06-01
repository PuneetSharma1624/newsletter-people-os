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

    if not is_test and subscriber_id:
        status = "sent" if result["ok"] else "failed"
        log_send(
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
    return result


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
