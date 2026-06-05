"""POST /api/subscribe - validate email and write subscriber via Supabase REST."""
from http.server import BaseHTTPRequestHandler
import datetime
import json
import os
import re
import secrets
import sys
import urllib.error

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from newsletter.backend_utils import (  # noqa: E402
    classify_supabase_error,
    normalize_supabase_url,
    quote_filter,
    read_error_body,
    rest_get,
    rest_patch,
    rest_post,
)


def _is_valid_email(email: str) -> bool:
    return bool(re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]{2,}$", email.strip()))


def _now_utc() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")


class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.end_headers()

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(length) if length > 0 else b"{}"
            body = json.loads(raw.decode("utf-8")) if raw else {}
        except Exception:
            self._json({"ok": False, "error": "Invalid request body."}, 400)
            return

        email_raw = body.get("email", "")
        source = str(body.get("source", "web") or "web")[:64]
        if not isinstance(email_raw, str) or not _is_valid_email(email_raw):
            self._json({"ok": False, "error": "Please enter a valid email address."}, 400)
            return

        email = email_raw.strip().lower()
        sb_url = normalize_supabase_url(os.environ.get("SUPABASE_URL", ""))
        sb_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()
        if not sb_url or not sb_key:
            self._json({"ok": False, "error": "Subscription service is not configured."}, 503)
            return

        try:
            query = f"select=id,email,status&email=eq.{quote_filter(email)}&limit=1"
            existing = rest_get(sb_url, sb_key, "subscribers", query)
            now = _now_utc()

            if existing:
                row = existing[0]
                if row.get("status") == "active":
                    self._json({"ok": True, "status": "already_subscribed", "email": email})
                    return

                rest_patch(
                    sb_url,
                    sb_key,
                    "subscribers",
                    f"id=eq.{row['id']}",
                    {
                        "status": "active",
                        "source": source,
                        "updated_at": now,
                        "unsubscribed_at": None,
                        "unsubscribe_token": secrets.token_urlsafe(32),
                    },
                )
                self._json({"ok": True, "status": "subscribed", "email": email})
                return

            rest_post(
                sb_url,
                sb_key,
                "subscribers",
                {
                    "email": email,
                    "status": "active",
                    "source": source,
                    "created_at": now,
                    "updated_at": now,
                    "unsubscribed_at": None,
                    "unsubscribe_token": secrets.token_urlsafe(32),
                },
            )
            self._json({"ok": True, "status": "subscribed", "email": email})
        except urllib.error.HTTPError as exc:
            detail = read_error_body(exc, 500)
            lower = detail.lower()
            if "42p01" in lower or "does not exist" in lower or "schema cache" in lower:
                self._json({"ok": False, "error": "Subscribers table is missing. Run supabase/schema.sql."}, 503)
            elif "23505" in lower or "duplicate" in lower:
                self._json({"ok": True, "status": "already_subscribed", "email": email})
            else:
                self._json({"ok": False, "error": classify_supabase_error(exc, "Subscribers table")}, 503)
        except Exception as exc:
            self._json({"ok": False, "error": classify_supabase_error(exc, "Subscribers table")}, 503)

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")

    def _json(self, body, status=200):
        payload = json.dumps(body).encode("utf-8")
        self.send_response(status)
        self._cors()
        self.send_header("Cache-Control", "no-store, no-cache, max-age=0, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *args):
        pass


app = handler
application = handler
