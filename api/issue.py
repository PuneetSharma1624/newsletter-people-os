"""GET /api/issue?date=YYYY-MM-DD — returns saved issue for that date."""
from __future__ import annotations
import json, os, sys, re, urllib.parse
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from newsletter.logger import log

_CORS = {"Access-Control-Allow-Origin": "*", "Content-Type": "application/json"}
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _json(body: dict, status: int = 200):
    return {"statusCode": status, "headers": _CORS, "body": json.dumps(body, default=str)}


def _get_param(request, key: str) -> str:
    query = getattr(request, "query", {}) or {}
    if isinstance(query, str):
        parsed = urllib.parse.parse_qs(query)
        return parsed.get(key, [""])[0]
    return query.get(key, "")


def handler(request, response=None):
    method = getattr(request, "method", "GET")
    if method == "OPTIONS":
        return _json({}, 200)

    date = _get_param(request, "date").strip()
    if not date or not _DATE_RE.match(date):
        return _json({"ok": False, "message": "Missing or invalid date. Use YYYY-MM-DD."}, 400)

    try:
        from newsletter import config
        config.validate_config(["SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY"])
        from newsletter.archive import get_issue_by_date
        issue = get_issue_by_date(date)
        if not issue:
            return _json({"ok": False, "issue": None, "message": f"No brief for {date}."}, 404)
        return _json({"ok": True, "issue": issue})
    except EnvironmentError:
        from api.demo_data import get_demo_issue, get_demo_dates
        demo_dates = get_demo_dates()
        if date in demo_dates:
            return _json({"ok": True, "issue": get_demo_issue(date), "_demo": True})
        return _json({"ok": False, "issue": None, "message": f"No brief for {date}."}, 404)
    except Exception as exc:
        log.error(f"issue API error: {exc}")
        return _json({"ok": False, "message": "Server error."}, 500)
