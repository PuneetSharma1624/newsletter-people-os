"""GET /api/admin/action-logs — return recent action log entries.
Requires Authorization: Bearer <ADMIN_TRIGGER_TOKEN>.
"""
from http.server import BaseHTTPRequestHandler
import json, os, urllib.request


def _sb_headers(key):
    return {'apikey': key, 'Authorization': f'Bearer {key}'}


class handler(BaseHTTPRequestHandler):

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.end_headers()

    def do_GET(self):
        # Light auth check
        auth = self.headers.get('Authorization', '')
        expected = os.environ.get('ADMIN_TRIGGER_TOKEN', '')
        if expected and auth != f'Bearer {expected}':
            self._json({'ok': False, 'error': 'Unauthorized.'}, 401)
            return

        sb_url = os.environ.get('SUPABASE_URL', '').rstrip('/')
        sb_key = os.environ.get('SUPABASE_SERVICE_ROLE_KEY', '')

        if not sb_url or not sb_key:
            self._json({'ok': True, 'logs': [], 'note': 'unavailable'})
            return

        try:
            url = (f"{sb_url}/rest/v1/action_logs"
                   f"?select=id,action_name,action_type,status,error_message,created_at"
                   f"&order=created_at.desc&limit=50")
            req = urllib.request.Request(url, headers=_sb_headers(sb_key))
            with urllib.request.urlopen(req, timeout=8) as r:
                logs = json.loads(r.read())
            self._json({'ok': True, 'logs': logs})
        except Exception as exc:
            self._json({'ok': False, 'error': str(exc)[:200]}, 500)

    def _cors(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')

    def _json(self, body, status=200):
        payload = json.dumps(body).encode()
        self.send_response(status)
        self._cors()
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *args):
        pass


app = handler
application = handler
