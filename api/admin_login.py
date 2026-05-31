"""
POST /api/admin/login
Validates admin token against ADMIN_TRIGGER_TOKEN env var OR fallback password.
IMPORTANT: Remove FALLBACK_PASSWORD and rotate token once env var is confirmed working.
"""
from __future__ import annotations
import json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# TODO: Remove this fallback once ADMIN_TRIGGER_TOKEN env var is confirmed working on Vercel.
_FALLBACK_PASSWORD = "PuneetAdmin1234"

_CORS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, Authorization",
    "Content-Type": "application/json",
}


def _resp(body: dict, status: int = 200) -> dict:
    return {"statusCode": status, "headers": _CORS, "body": json.dumps(body)}


def handler(request, response=None):
    try:
        method = getattr(request, "method", "POST")

        if method == "OPTIONS":
            return _resp({}, 200)

        if method != "POST":
            return _resp({"success": False, "error": "Method not allowed"}, 405)

        # Parse body — handle bytes, str, or absent body
        body_raw = getattr(request, "body", b"") or b""
        if isinstance(body_raw, str):
            body_raw = body_raw.encode("utf-8")
        body_data = json.loads(body_raw) if body_raw.strip() else {}

        # Extract token — accept any of these key variants
        token = (
            body_data.get("token")
            or body_data.get("password")
            or body_data.get("adminToken")
            or ""
        )
        if isinstance(token, str):
            token = token.strip()

        if not token:
            return _resp({"success": False, "error": "Token is required."}, 400)

        # Auth: match fallback OR env var (strip env var to handle hidden quotes)
        env_token = (os.environ.get("ADMIN_TRIGGER_TOKEN") or "").strip().strip('"').strip("'")
        authenticated = (token == _FALLBACK_PASSWORD) or (env_token and token == env_token)

        if not authenticated:
            return _resp({"success": False, "error": "Invalid access token or password."}, 401)

        session = env_token if env_token else token
        return _resp({"success": True, "ok": True, "message": "Authenticated.", "session": session})

    except Exception as exc:
        return _resp({"success": False, "ok": False, "error": str(exc)}, 500)


app = handler
application = handler
