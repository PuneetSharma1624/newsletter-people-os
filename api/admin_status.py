"""GET /api/admin/status — returns generation status and latest issue info. Requires auth."""
from __future__ import annotations
import json, os, sys, datetime
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

_CORS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type, Authorization",
    "Content-Type": "application/json",
}


def _json(body: dict, status: int = 200):
    return {"statusCode": status, "headers": _CORS, "body": json.dumps(body, default=str)}


def _validate_auth(request) -> bool:
    expected = os.getenv("ADMIN_TRIGGER_TOKEN", "")
    if not expected:
        return False
    headers = getattr(request, "headers", {}) or {}
    auth = ""
    if isinstance(headers, dict):
        auth = headers.get("Authorization", headers.get("authorization", ""))
    if auth.startswith("Bearer "):
        return auth[7:].strip() == expected
    return False


def handler(request, response=None):
    method = getattr(request, "method", "GET")
    if method == "OPTIONS":
        return _json({}, 200)

    if not _validate_auth(request):
        return _json({"ok": False, "message": "Unauthorized"}, 401)

    today = datetime.date.today().isoformat()

    try:
        from newsletter.static_publisher import (
            get_status, get_dates, issue_exists, load_issue
        )
        status = get_status()
        dates = get_dates()
        latest_date = dates[0] if dates else None
        today_exists = issue_exists(today)

        today_info = {}
        if today_exists:
            issue = load_issue(today)
            if issue:
                today_info = {
                    "total_sections": issue.get("total_sections", 0),
                    "total_dashboard_items": issue.get("total_dashboard_items", 0),
                    "subject": issue.get("subject", ""),
                }

        return _json({
            "ok": True,
            "today": today,
            "today_exists": today_exists,
            "today_info": today_info,
            "latest_date": latest_date,
            "total_archived": len(dates),
            "generation_status": status,
            "github_configured": bool(os.getenv("GITHUB_PAT_FOR_WORKFLOW_DISPATCH")),
        })
    except Exception as exc:
        return _json({"ok": False, "message": f"Error: {exc}"}, 500)


app = handler
application = handler
