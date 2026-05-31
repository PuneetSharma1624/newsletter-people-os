"""POST /api/admin/notifications/mark-seen — reset new-subscriber notification badge.
Sets last_seen_subscriber_at to now() in admin_notification_state.
Requires Authorization: Bearer <ADMIN_TRIGGER_TOKEN>.
"""
from http.server import BaseHTTPRequestHandler
import json, os, urllib.request, datetime


def _sb_headers(key):
    return {
        'apikey': key,
        'Authorization': f'Bearer {key}',
        'Content-Type': 'application/json',
    }


def _sb_upsert(sb_url, sb_key, table, body):
    url = f"{sb_url}/rest/v1/{table}"
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        url, data=data,
        headers={**_sb_headers(sb_key), 'Prefer': 'resolution=merge-duplicates,return=minimal'},
        method='POST',
    )
    with urllib.request.urlopen(req, timeout=6) as r:
        return r.status


class handler(BaseHTTPRequestHandler):

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.end_headers()

    def do_POST(self):
        if not self._validate_auth():
            self._json({'ok': False, 'message': 'Unauthorized'}, 401)
            return

        sb_url = os.environ.get('SUPABASE_URL', '').rstrip('/')
        sb_key = os.environ.get('SUPABASE_SERVICE_ROLE_KEY', '')
        if not sb_url or not sb_key:
            self._json({'ok': False, 'message': 'Supabase not configured'}, 503)
            return

        try:
            now = datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
            _sb_upsert(sb_url, sb_key, 'admin_notification_state', {
                'id': 'default',
                'last_seen_subscriber_at': now,
                'updated_at': now,
            })
            self._json({'ok': True, 'marked_at': now})
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
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')

    def _json(self, body, status=200):
        payload = json.dumps(body).encode()
        self.send_response(status)
        self._cors()
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *args):
        pass
