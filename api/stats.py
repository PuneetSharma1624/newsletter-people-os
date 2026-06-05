"""GET /api/stats — aggregate page views + subscriber counts. No-cache always."""
from http.server import BaseHTTPRequestHandler
import json, os, urllib.request, datetime


def _sb_headers(key):
    return {'apikey': key, 'Authorization': f'Bearer {key}'}


def _sb_count(sb_url, sb_key, table, qs=''):
    url = f"{sb_url}/rest/v1/{table}?select=id{('&' + qs) if qs else ''}"
    req = urllib.request.Request(
        url, headers={**_sb_headers(sb_key), 'Prefer': 'count=exact'},
    )
    with urllib.request.urlopen(req, timeout=5) as r:
        cr = r.headers.get('Content-Range', '')
        return int(cr.split('/')[-1]) if '/' in cr else 0


def _today_range():
    today = datetime.date.today().isoformat()
    return f"{today}T00:00:00Z", f"{today}T23:59:59Z"


class handler(BaseHTTPRequestHandler):

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.end_headers()

    def do_GET(self):
        sb_url = os.environ.get('SUPABASE_URL', '').rstrip('/')
        sb_key = os.environ.get('SUPABASE_SERVICE_ROLE_KEY', '')

        if not sb_url or not sb_key:
            self._json({'ok': True, 'total_page_views': 0, 'total_visits': 0,
                        'unique_visitors_today': 0, 'total_subscribers': 0,
                        'note': 'analytics_unavailable'})
            return

        try:
            total_page_views = _sb_count(sb_url, sb_key, 'site_analytics')
            start, end = _today_range()
            unique_visitors_today = _sb_count(
                sb_url, sb_key, 'site_analytics',
                f'visitor_hash=neq.null&created_at=gte.{start}&created_at=lte.{end}'
            )
            total_subscribers = _sb_count(sb_url, sb_key, 'subscribers', 'status=eq.active')
            self._json({
                'ok': True,
                'total_page_views': total_page_views,
                'total_visits': total_page_views,
                'unique_visitors_today': unique_visitors_today,
                'total_subscribers': total_subscribers,
            })
        except Exception:
            self._json({'ok': False, 'error': 'Analytics service error.'}, 500)

    def _cors(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')

    def _nocache(self):
        self.send_header('Cache-Control', 'no-store, no-cache, max-age=0, must-revalidate')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Expires', '0')

    def _json(self, body, status=200):
        payload = json.dumps(body).encode()
        self.send_response(status)
        self._cors()
        self._nocache()
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *args):
        pass


app = handler
application = handler
