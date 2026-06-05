"""GET /api/stats - real page-view and subscriber counts from Supabase."""
from http.server import BaseHTTPRequestHandler
import datetime
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from newsletter.backend_utils import (  # noqa: E402
    classify_supabase_error,
    normalize_supabase_url,
    rest_count,
    rest_get,
)

IST = datetime.timezone(datetime.timedelta(hours=5, minutes=30))


def _today_ist_utc_range() -> tuple[str, str]:
    today = datetime.datetime.now(IST).date()
    start_ist = datetime.datetime.combine(today, datetime.time.min, tzinfo=IST)
    end_ist = start_ist + datetime.timedelta(days=1)
    start_utc = start_ist.astimezone(datetime.timezone.utc).isoformat().replace("+00:00", "Z")
    end_utc = end_ist.astimezone(datetime.timezone.utc).isoformat().replace("+00:00", "Z")
    return start_utc, end_utc


def _load_stats(sb_url: str, sb_key: str) -> dict:
    total_page_views = rest_count(sb_url, sb_key, "site_analytics", "event_type=eq.page_view")
    total_subscribers = rest_count(sb_url, sb_key, "subscribers", "status=eq.active")

    start, end = _today_ist_utc_range()
    rows = rest_get(
        sb_url,
        sb_key,
        "site_analytics",
        f"select=visitor_hash&event_type=eq.page_view&visitor_hash=not.is.null&created_at=gte.{start}&created_at=lt.{end}",
    )
    unique_visitors_today = len({r.get("visitor_hash") for r in rows if r.get("visitor_hash")})

    return {
        "ok": True,
        "total_page_views": total_page_views,
        "total_visits": total_page_views,
        "unique_visitors_today": unique_visitors_today,
        "total_subscribers": total_subscribers,
    }


class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.end_headers()

    def do_GET(self):
        sb_url = normalize_supabase_url(os.environ.get("SUPABASE_URL", ""))
        sb_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()

        if not sb_url or not sb_key:
            self._json({"ok": False, "error": "Stats service is not configured."}, 503)
            return

        try:
            self._json(_load_stats(sb_url, sb_key))
        except Exception as exc:
            message = classify_supabase_error(exc, "Stats tables")
            if "missing" in message.lower():
                message = "Stats tables are missing. Run supabase/schema.sql."
            self._json({"ok": False, "error": message}, 503)

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")

    def _nocache(self):
        self.send_header("Cache-Control", "no-store, no-cache, max-age=0, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")

    def _json(self, body, status=200):
        payload = json.dumps(body).encode("utf-8")
        self.send_response(status)
        self._cors()
        self._nocache()
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *args):
        pass


app = handler
application = handler
