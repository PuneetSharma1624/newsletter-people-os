"""
POST /api/admin/login
MVP auth: validates ADMIN_TRIGGER_TOKEN.
Returns session token (same token for simplicity — admin stores in sessionStorage).
Admin secrets never exposed to frontend.
"""
from __future__ import annotations
import json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

_CORS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, Authorization",
    "Content-Type": "application/json",
}


def _json(body: dict, status: int = 200):
    return {"statusCode": status, "headers": _CORS, "body": json.dumps(body)}


def handler(request, response=None):
    method = getattr(request, "method", "POST")
    if method == "OPTIONS":
        return _json({}, 200)
    if method != "POST":
        return _json({"ok": False, "message": "Method not allowed"}, 405)

    try:
        body_raw = getattr(request, "body", b"") or b""
        if isinstance(body_raw, str):
            body_raw = body_raw.encode()
        body = json.loads(body_raw) if body_raw else {}
    except Exception:
        return _json({"ok": False, "message": "Invalid request"}, 400)

    token = body.get("token", "").strip()
    if not token:
        return _json({"ok": False, "message": "Token required"}, 400)

    expected = os.getenv("ADMIN_TRIGGER_TOKEN", "")
    if not expected:
        return _json({"ok": False, "message": "Admin not configured on server"}, 503)

    if token != expected:
        return _json({"ok": False, "message": "Invalid token"}, 401)

    # Return the token as session — admin stores in sessionStorage and sends as Bearer
    return _json({"ok": True, "session": token, "message": "Authenticated"})


# Vercel Python runtime needs a top-level 'app', 'application', or 'handler'.
app = handler
application = handler
