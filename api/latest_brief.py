"""GET /api/latest-brief — returns latest saved issue."""
from __future__ import annotations
import json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from newsletter.logger import log

_CORS = {"Access-Control-Allow-Origin": "*", "Content-Type": "application/json"}


def _json(body: dict, status: int = 200):
    return {"statusCode": status, "headers": _CORS, "body": json.dumps(body, default=str)}


def handler(request, response=None):
    method = getattr(request, "method", "GET")
    if method == "OPTIONS":
        return _json({}, 200)

    try:
        from newsletter import config
        config.validate_config(["SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY"])
        from newsletter.archive import get_latest_issue
        issue = get_latest_issue()
        if not issue:
            return _json({"ok": False, "issue": None, "message": "No issues published yet."}, 404)
        return _json({"ok": True, "issue": issue})
    except EnvironmentError:
        log.warning("No Supabase config — returning demo issue")
        from api.demo_data import get_demo_issue
        return _json({"ok": True, "issue": get_demo_issue(), "_demo": True})
    except Exception as exc:
        log.error(f"latest-brief error: {exc}")
        return _json({"ok": False, "message": "Server error."}, 500)


app = handler
application = handler
