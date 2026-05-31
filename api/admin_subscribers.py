"""GET /api/admin/subscribers — paginated subscriber list with filters.
Query params: status=active|unsubscribed|all, since=YYYY-MM-DD, limit=100
Requires Authorization: Bearer <ADMIN_TRIGGER_TOKEN>.
Never called by public frontend.
"""
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import json, os, urllib.request


def _sb_headers(key):
    return {'apikey': key, 'Authorization': f'Bearer {key}', 'Accept': 'application/json'}


def _sb_get(sb_url, sb_key, table, qs=''):
    url = f"{sb_url}/rest/v1/{table}{'?' + qs if qs else ''}"
    req = urllib.request.Request(url, headers=_sb_headers(sb_key))
    with urllib.request.urlopen(req, timeout=8) as r:
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

        # Parse query params
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        status = params.get('status', ['all'])[0]
        since  = params.get('since',  [''])[0]
        limit  = min(int(params.get('limit', ['200'])[0]), 500)

        # Build Supabase filter string
        select = 'id,email,status,source,created_at,updated_at,unsubscribed_at,last_email_sent_at'
        filters = [f'select={select}', f'order=created_at.desc', f'limit={limit}']
        if status in ('active', 'unsubscribed'):
            filters.append(f'status=eq.{status}')
        if since:
            filters.append(f'created_at=gte.{since}T00:00:00')

        try:
            rows = _sb_get(sb_url, sb_key, 'subscribers', '&'.join(filters))
            self._json({
                'ok': True,
                'count': len(rows),
                'subscribers': rows,
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
