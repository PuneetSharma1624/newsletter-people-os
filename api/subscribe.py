"""
Vercel serverless function — POST /api/subscribe
Accepts JSON: {"email": "..."} — validates, normalizes, upserts subscriber.
NEVER expose SUPABASE_SERVICE_ROLE_KEY to frontend. This file is server-side only.
"""
from __future__ import annotations

import json
import os
import sys

# Allow imports from repo root when running locally
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from newsletter.utils import normalize_email, is_valid_email, generate_token
from newsletter.logger import log


def _cors_headers() -> dict:
    return {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
        "Content-Type": "application/json",
    }


def _json(body: dict, status: int = 200):
    return {"statusCode": status, "headers": _cors_headers(), "body": json.dumps(body)}


def handler(request, response=None):
    """Vercel Python handler."""
    method = getattr(request, "method", "POST")

    # Handle CORS preflight
    if method == "OPTIONS":
        return _json({}, 200)

    if method != "POST":
        return _json({"ok": False, "message": "Method not allowed."}, 405)

    # Parse body
    try:
        body_raw = getattr(request, "body", b"") or b""
        if isinstance(body_raw, str):
            body_raw = body_raw.encode()
        body = json.loads(body_raw) if body_raw else {}
    except (json.JSONDecodeError, ValueError):
        return _json({"ok": False, "message": "Invalid request body."}, 400)

    email_raw = body.get("email", "")
    if not email_raw or not isinstance(email_raw, str):
        return _json({"ok": False, "message": "Please enter a valid email address."}, 400)

    email = normalize_email(email_raw)
    if not is_valid_email(email):
        return _json({"ok": False, "message": "Please enter a valid email address."}, 400)

    # Upsert via subscribers module
    try:
        from newsletter import config
        config.validate_config(["SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY"])
        from newsletter.subscribers import upsert_subscriber
        result = upsert_subscriber(email, source="web")
    except EnvironmentError as exc:
        log.error(f"Config error in subscribe API: {exc}")
        return _json({"ok": False, "message": "Service configuration error. Please try again later."}, 500)
    except Exception as exc:
        log.error(f"Subscribe error for {email}: {exc}")
        return _json({"ok": False, "message": "Something went wrong. Please try again."}, 500)

    if result.get("already_active"):
        return _json({"ok": True, "message": "You're already subscribed to PeopleOS Brief."})

    return _json({"ok": True, "message": "You're subscribed to PeopleOS Brief."})
