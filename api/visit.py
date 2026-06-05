"""POST /api/visit - record one page_view and return live stats."""
from http.server import BaseHTTPRequestHandler
import datetime
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from newsletter.backend_utils import (  # noqa: E402
    classify_supabase_error,
    normalize_supabase_url,
    rest_post,
)
from api.stats import _load_stats  # noqa: E402

IST = datetime.timezone(datetime.timedelta(hours=5, minutes=30))


def _today_ist() -> str:
    return datetime.datetime.now(IST).date().isoformat()


def _hash(value: str, length: int = 24) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:length]


class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.end_headers()

    def do_POST(self):
        sb_url = normalize_supabase_url(os.environ.get("SUPABASE_URL", ""))
        sb_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()
        if not sb_url or not sb_key:
            self._json({"ok": False, "recorded": False, "error": "Visit service is not configured."}, 503)
            return

        body = {}
        try:
            length = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(length) if length > 0 else b"{}"
            body = json.loads(raw.decode("utf-8")) if raw else {}
        except Exception:
            body = {}

        ua = self.headers.get("User-Agent", "") or ""
        forwarded = self.headers.get("X-Forwarded-For", "") or self.client_address[0] or ""
        ip_coarse = forwarded.split(",")[0].strip()
        visitor_hash = _hash(f"{ip_coarse}|{ua}|{_today_ist()}")
        user_agent_hash = _hash(ua, 24)
        path = str(body.get("path") or self.headers.get("Referer") or "/")[:500]
        referrer = str(body.get("referrer") or self.headers.get("Referer") or "")[:500]

        row = {
            "event_type": "page_view",
            "visitor_hash": visitor_hash,
            "user_agent_hash": user_agent_hash,
            "path": path,
            "page_path": path,
            "referrer": referrer,
        }

        try:
            attempts = [
                row,
                {k: v for k, v in row.items() if k != "page_path"},
                {k: v for k, v in row.items() if k != "path"},
            ]
            last_exc = None
            for payload in attempts:
                try:
                    rest_post(sb_url, sb_key, "site_analytics", payload, prefer="return=minimal")
                    last_exc = None
                    break
                except Exception as exc:
                    last_exc = exc
            if last_exc:
                raise last_exc

            stats = _load_stats(sb_url, sb_key)
            stats["recorded"] = True
            self._json(stats)
        except Exception as exc:
            message = classify_supabase_error(exc, "Stats tables")
            if "missing" in message.lower():
                message = "Stats tables are missing. Run supabase/schema.sql."
            self._json({"ok": False, "recorded": False, "error": message}, 503)

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")

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
