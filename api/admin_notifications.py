"""GET /api/admin/notifications — new subscribers since last admin check.
Requires Authorization: Bearer <ADMIN_TRIGGER_TOKEN>.
"""
from http.server import BaseHTTPRequestHandler
import json, os, urllib.request


def _sb_headers(key):
    return {'apikey': key, 'Authorization': f'Bearer {key}', 'Accept': 'application/json'}


def _sb_get(sb_url, sb_key, table, qs=''):
    url = f"{sb_url}/rest/v1/{table}{'?' + qs if qs else ''}"
    req = urllib.request.Request(url, headers=_sb_headers(sb_key))
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
            # Get last-seen timestamp
            state_rows = _sb_get(sb_url, sb_key, 'admin_notification_state', 'id=eq.default')
            last_seen = state_rows[0]['last_seen_subscriber_at'] if state_rows else '1970-01-01T00:00:00'
            if not last_seen:
                last_seen = '1970-01-01T00:00:00'

            # New subscribers since last seen
            new_subs = _sb_get(
                sb_url, sb_key, 'subscribers',
                f'select=id,email,created_at,source&created_at=gt.{last_seen}&order=created_at.desc&limit=20',
            )

            self._json({
                'ok': True,
                'new_subscriber_count': len(new_subs),
                'last_seen_at': last_seen,
                'latest_subscribers': [
                    {
                        'email': s.get('email', ''),
                        'subscribed_at': s.get('created_at', ''),
                        'source': s.get('source') or 'dashboard',
                    }
                    for s in new_subs
                ],
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
