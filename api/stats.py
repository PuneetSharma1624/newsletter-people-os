"""GET /api/stats - real page-view and subscriber counts from Supabase."""
from http.server import BaseHTTPRequestHandler
import datetime
import json
import os
import urllib.error
import urllib.request

IST = datetime.timezone(datetime.timedelta(hours=5, minutes=30))


def _normalize_url(raw: str) -> str:
    url = raw.strip().rstrip("/")
    if url.endswith("/rest/v1"):
        url = url[: -len("/rest/v1")]
    return url.rstrip("/")


def _headers(key: str) -> dict:
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Accept": "application/json",
    }


def _rest_count(sb_url: str, sb_key: str, table: str, query: str = "") -> int:
    q = "select=id"
    if query:
        q += "&" + query.lstrip("?")
    url = f"{sb_url}/rest/v1/{table}?{q}"
    req = urllib.request.Request(
        url,
        headers={**_headers(sb_key), "Prefer": "count=exact"},
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=8) as resp:
        cr = resp.headers.get("Content-Range", "")
        return int(cr.split("/")[-1]) if "/" in cr and cr.split("/")[-1].isdigit() else 0


def _rest_get(sb_url: str, sb_key: str, table: str, query: str = "") -> list:
    url = f"{sb_url}/rest/v1/{table}" + (f"?{query.lstrip('?')}" if query else "")
    req = urllib.request.Request(url, headers=_headers(sb_key), method="GET")
    with urllib.request.urlopen(req, timeout=8) as resp:
        body = resp.read().decode("utf-8")
        return json.loads(body) if body else []


def _classify_error(exc: BaseException) -> str:
    try:
        err = (exc.read().decode("utf-8", errors="replace")[:600] if isinstance(exc, urllib.error.HTTPError) else str(exc)).lower()
    except Exception:
        err = str(exc).lower()
    if "42p01" in err or "does not exist" in err:
        return "Stats tables are missing. Run supabase/schema.sql."
    if "jwt" in err or "invalid api key" in err:
        return "Supabase authentication failed. Check SUPABASE_SERVICE_ROLE_KEY."
    if "pgrst125" in err or "invalid path" in err:
        return "Supabase URL is misconfigured."
    return "Supabase request failed."


def _today_ist_utc_range() -> tuple:
    today = datetime.datetime.now(IST).date()
    start_ist = datetime.datetime.combine(today, datetime.time.min, tzinfo=IST)
    end_ist = start_ist + datetime.timedelta(days=1)
    start_utc = start_ist.astimezone(datetime.timezone.utc).isoformat().replace("+00:00", "Z")
    end_utc = end_ist.astimezone(datetime.timezone.utc).isoformat().replace("+00:00", "Z")
    return start_utc, end_utc


def _load_stats(sb_url: str, sb_key: str) -> dict:
    total_page_views = _rest_count(sb_url, sb_key, "site_analytics", "event_type=eq.page_view")
    total_subscribers = _rest_count(sb_url, sb_key, "subscribers", "status=eq.active")

    start, end = _today_ist_utc_range()
    new_today = _rest_count(sb_url, sb_key, "subscribers", f"created_at=gte.{start}&created_at=lt.{end}")
    rows = _rest_get(
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
        "new_today": new_today,
    }


class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.end_headers()

    def do_GET(self):
        sb_url = _normalize_url(os.environ.get("SUPABASE_URL", ""))
        sb_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()

        if not sb_url or not sb_key:
            self._json({"ok": False, "error": "Stats service is not configured."}, 503)
            return

        try:
            self._json(_load_stats(sb_url, sb_key))
        except Exception as exc:
            self._json({"ok": False, "error": _classify_error(exc)}, 503)

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
