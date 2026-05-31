"""
POST /api/admin/login — PeopleOS Brief admin authentication.
Vercel Python serverless. Zero non-stdlib imports at module level.
TODO: Remove _FALLBACK_PASSWORD once ADMIN_TRIGGER_TOKEN env var is confirmed working.
"""
import json
import os

_FALLBACK_PASSWORD = "PuneetAdmin1234"

_CORS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type, Authorization",
    "Access-Control-Allow-Methods": "POST, OPTIONS",
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

        # ── Defensive body extraction — try every known Vercel request shape ──
        body_data = {}
        try:
            if hasattr(request, "get_json") and callable(request.get_json):
                body_data = request.get_json() or {}
            elif hasattr(request, "json") and callable(request.json):
                body_data = request.json() or {}
            elif hasattr(request, "body"):
                raw = request.body
                if raw:
                    if isinstance(raw, (bytes, bytearray)):
                        raw = raw.decode("utf-8", errors="replace")
                    body_data = json.loads(raw) if isinstance(raw, str) and raw.strip() else {}
            elif hasattr(request, "data"):
                raw = request.data
                if isinstance(raw, (bytes, bytearray)):
                    raw = raw.decode("utf-8", errors="replace")
                body_data = json.loads(raw) if raw and raw.strip() else {}
            elif hasattr(request, "read") and callable(request.read):
                raw = request.read()
                if isinstance(raw, (bytes, bytearray)):
                    raw = raw.decode("utf-8", errors="replace")
                body_data = json.loads(raw) if raw and raw.strip() else {}
        except Exception:
            body_data = {}

        if not isinstance(body_data, dict):
            body_data = {}

        # ── Token extraction — accept any key variant ──
        user_input = str(
            body_data.get("token")
            or body_data.get("password")
            or body_data.get("adminToken")
            or ""
        ).strip()

        if not user_input:
            return _resp({"success": False, "error": "Token is required."}, 400)

        # ── Auth check: fallback OR env var (strip hidden quotes from env) ──
        env_token = str(os.environ.get("ADMIN_TRIGGER_TOKEN") or "").strip().strip('"').strip("'")
        authenticated = (user_input == _FALLBACK_PASSWORD) or (env_token and user_input == env_token)

        if not authenticated:
            return _resp({"success": False, "ok": False, "error": "Invalid access token or password."}, 401)

        session = env_token if env_token else user_input
        return _resp({"success": True, "ok": True, "message": "Authenticated.", "session": session})

    except Exception as exc:
        return _resp({"success": False, "ok": False, "error": str(exc), "type": type(exc).__name__}, 500)


app = handler
application = handler
