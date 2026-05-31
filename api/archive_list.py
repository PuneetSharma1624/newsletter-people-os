"""GET /api/archive — archive list."""
from __future__ import annotations
import json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from newsletter.logger import log

_CORS = {"Access-Control-Allow-Origin": "*", "Content-Type": "application/json"}


def _enrich(row: dict) -> dict:
    secs = row.get("sections") or []
    sec_count = len(secs) if isinstance(secs, list) else 0
    item_count = sum(len(s.get("items", [])) for s in secs) if isinstance(secs, list) else 0
    return {
        "id": row.get("id"),
        "issue_date": row.get("issue_date"),
        "subject": row.get("subject", ""),
        "preheader": row.get("preheader", ""),
        "executive_summary": row.get("executive_summary", ""),
        "section_count": sec_count,
        "item_count": item_count,
        "sent_at": row.get("sent_at"),
    }


def _json(body: dict, status: int = 200):
    return {"statusCode": status, "headers": _CORS, "body": json.dumps(body, default=str)}


def handler(request, response=None):
    method = getattr(request, "method", "GET")
    if method == "OPTIONS":
        return _json({}, 200)

    try:
        from newsletter import config
        config.validate_config(["SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY"])
        from newsletter.archive import list_issues
        issues = list_issues(limit=90)
        archive = [_enrich(row) for row in issues]
        return _json({"ok": True, "archive": archive, "count": len(archive)})
    except EnvironmentError:
        from api.demo_data import get_demo_archive
        archive = get_demo_archive()
        return _json({"ok": True, "archive": archive, "count": len(archive), "_demo": True})
    except Exception as exc:
        log.error(f"archive error: {exc}")
        return _json({"ok": False, "archive": [], "message": "Server error."}, 500)


app = handler
application = handler
