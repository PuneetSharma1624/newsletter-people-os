"""GET /api/dates — available issue dates for calendar."""
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
        from newsletter.archive import list_available_dates
        dates = list_available_dates()
        return _json({"ok": True, "dates": dates})
    except EnvironmentError:
        from api.demo_data import get_demo_dates
        return _json({"ok": True, "dates": get_demo_dates(), "_demo": True})
    except Exception as exc:
        log.error(f"dates error: {exc}")
        return _json({"ok": False, "dates": [], "message": "Server error."}, 500)
