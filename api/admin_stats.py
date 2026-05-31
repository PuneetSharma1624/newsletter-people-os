"""GET /api/admin/stats — admin-only aggregate stats.
Requires Authorization: Bearer <ADMIN_TRIGGER_TOKEN>.
"""
from http.server import BaseHTTPRequestHandler
import json, os, urllib.request, datetime


def _sb_headers(key):
    return {'apikey': key, 'Authorization': f'Bearer {key}'}


def _sb_count(sb_url, sb_key, table, qs=''):
    url = f"{sb_url}/rest/v1/{table}?select=id{('&' + qs) if qs else ''}"
    req = urllib.request.Request(
        url, headers={**_sb_headers(sb_key), 'Prefer': 'count=exact'},
    )
    with urllib.request.urlopen(req, timeout=6) as r:
        cr = r.headers.get('Content-Range', '')
        return int(cr.split('/')[-1]) if '/' in cr else 0


def _sb_get(sb_url, sb_key, table, qs=''):
    url = f"{sb_url}/rest/v1/{table}{'?' + qs if qs else ''}"
    req = urllib.request.Request(
        url, headers={**_sb_headers(sb_key), 'Accept': 'application/json'},
    )
    with urllib.request.urlopen(req, timeout=6) as r:
        return json.loads(r.read())


class handler(BaseHTTPRequestHandler):

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.end_headers()

    def do_GET(self):
        if not self._validate_auth():
            self._json({'ok': False, 'message': 'Unauthorized'}, 401)
            return

        sb_url = os.environ.get('SUPABASE_URL', '').rstrip('/')
        sb_key = os.environ.get('SUPABASE_SERVICE_ROLE_KEY', '')
        if not sb_url or not sb_key:
            self._json({'ok': False, 'message': 'Supabase not configured'}, 503)
            return

        try:
            today = datetime.date.today().isoformat()
            today_dt = f"{today}T00:00:00"

            total_visits      = _sb_count(sb_url, sb_key, 'site_analytics', 'event_type=eq.visit')
            today_visits      = _sb_count(sb_url, sb_key, 'site_analytics', f'event_type=eq.visit&created_at=gte.{today_dt}')
            total_subscribers = _sb_count(sb_url, sb_key, 'subscribers', 'status=eq.active')
            new_today         = _sb_count(sb_url, sb_key, 'subscribers', f'created_at=gte.{today_dt}')

            # Last subscriber added
            latest = _sb_get(sb_url, sb_key, 'subscribers',
                             'select=email,created_at&order=created_at.desc&limit=1')
            last_subscriber = latest[0] if latest else None

            self._json({
                'ok': True,
                'total_visits': total_visits,
                'today_visits': today_visits,
                'total_subscribers': total_subscribers,
                'new_today': new_today,
                'last_subscriber': last_subscriber,
            })
        except Exception as exc:
            self._json({'ok': False, 'message': str(exc)}, 500)

    def _validate_auth(self):
        expected = os.environ.get('ADMIN_TRIGGER_TOKEN', '').strip().strip('"').strip("'")
        if not expected:
            return False
        auth = self.headers.get('Authorization', '')
        return auth.startswith('Bearer ') and auth[7:].strip() == expected

    def _cors(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')

    def _json(self, body, status=200):
        payload = json.dumps(body, default=str).encode()
        self.send_response(status)
        self._cors()
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *args):
        pass
