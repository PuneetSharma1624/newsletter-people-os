"""
POST /api/admin/login
Validates ADMIN_TRIGGER_TOKEN. Returns session on success.
Checks multiple key variants so frontend key mismatches never cause silent 500s.
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

    # CORS preflight
    if method == "OPTIONS":
        return _json({}, 200)

    if method != "POST":
        return _json({"ok": False, "success": False, "message": "Method not allowed"}, 405)

    # Parse body — handle bytes, str, or missing body gracefully
    try:
        body_raw = getattr(request, "body", b"") or b""
        if isinstance(body_raw, str):
            body_raw = body_raw.encode("utf-8")
        body = json.loads(body_raw) if body_raw.strip() else {}
    except Exception as exc:
        return _json({"ok": False, "success": False, "message": f"Invalid JSON body: {exc}"}, 400)

    # Accept token under any common key variant
    token = (
        body.get("token")
        or body.get("password")
        or body.get("adminToken")
        or ""
    )
    if isinstance(token, str):
        token = token.strip()

    if not token:
        return _json({"ok": False, "success": False, "message": "Token is required."}, 400)

    # Validate against env var — explicit 500 if not configured
    expected = os.environ.get("ADMIN_TRIGGER_TOKEN", "")
    if not expected:
        return _json({
            "ok": False,
            "success": False,
            "message": "ADMIN_TRIGGER_TOKEN is not set on the server. Add it in Vercel environment variables.",
        }, 500)

    if token != expected:
        return _json({"ok": False, "success": False, "message": "Invalid token. Access denied."}, 401)

    # Success — return both ok and success keys for frontend compatibility
    return _json({"ok": True, "success": True, "session": token, "message": "Authenticated."})


app = handler
application = handler
