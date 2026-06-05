"""POST /api/admin/action-log — write an action log entry to Supabase.
Called by frontend after any admin button click.
"""
from http.server import BaseHTTPRequestHandler
import json, os, urllib.request, datetime


def _sb_headers(key):
    return {
        'apikey': key,
        'Authorization': f'Bearer {key}',
        'Content-Type': 'application/json',
    }


class handler(BaseHTTPRequestHandler):

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.end_headers()

    def do_POST(self):
        try:
            length = int(self.headers.get('Content-Length') or 0)
            raw = self.rfile.read(length) if length > 0 else b''
            body = json.loads(raw) if raw else {}
        except Exception:
            self._json({'ok': False, 'error': 'Invalid body.'}, 400)
            return

        action_name = str(body.get('action_name', 'unknown'))[:200]
        action_type = str(body.get('action_type', ''))[:100]
        status      = str(body.get('status', 'unknown'))[:50]
        error_msg   = str(body.get('error_message', '') or '')[:500]

        # Strip any secret-looking values from payloads
        req_payload  = body.get('request_payload') or {}
        resp_payload = body.get('response_payload') or {}
        if isinstance(req_payload, dict):
            req_payload = {k: v for k, v in req_payload.items()
                          if not any(s in k.lower() for s in ('key', 'token', 'secret', 'password'))}

        sb_url = os.environ.get('SUPABASE_URL', '').rstrip('/')
        sb_key = os.environ.get('SUPABASE_SERVICE_ROLE_KEY', '')

        if not sb_url or not sb_key:
            self._json({'ok': True, 'note': 'log_unavailable'})
            return

        try:
            row = {
                'action_name':    action_name,
                'action_type':    action_type,
                'status':         status,
                'request_payload':  req_payload,
                'response_payload': resp_payload,
                'error_message':  error_msg or None,
            }
            url  = f"{sb_url}/rest/v1/action_logs"
            data = json.dumps(row).encode()
            req  = urllib.request.Request(
                url, data=data,
                headers={**_sb_headers(sb_key), 'Prefer': 'return=minimal'},
                method='POST',
            )
            with urllib.request.urlopen(req, timeout=5):
                pass
            self._json({'ok': True})
        except Exception as exc:
            # Log failure should never break the UI
            self._json({'ok': True, 'note': 'log_failed', 'detail': str(exc)[:200]})

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


app = handler
application = handler
