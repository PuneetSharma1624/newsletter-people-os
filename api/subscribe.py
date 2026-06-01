"""POST /api/subscribe — validate email, upsert subscriber.
Vercel Python serverless: handler must be BaseHTTPRequestHandler.
NEVER expose SUPABASE_SERVICE_ROLE_KEY to frontend.
"""
from http.server import BaseHTTPRequestHandler
import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def _is_valid_email(email: str) -> bool:
    return bool(re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', email.strip()))


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _sb_headers(key: str) -> dict:
    return {
        'apikey': key,
        'Authorization': f'Bearer {key}',
        'Content-Type': 'application/json',
        'Prefer': 'return=representation',
    }


class handler(BaseHTTPRequestHandler):

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.end_headers()

    def do_POST(self):
        # Parse body
        try:
            length = int(self.headers.get('Content-Length') or 0)
            raw = self.rfile.read(length) if length > 0 else b''
            body = json.loads(raw) if raw else {}
        except Exception:
            self._json({'ok': False, 'error': 'Invalid request body.'}, 400)
            return

        email_raw = body.get('email', '')
        source = body.get('source', 'web') or 'web'

        if not email_raw or not isinstance(email_raw, str):
            self._json({'ok': False, 'error': 'Please enter a valid email address.'}, 400)
            return

        email = _normalize_email(email_raw)
        if not _is_valid_email(email):
            self._json({'ok': False, 'error': 'Please enter a valid email address.'}, 400)
            return

        # Check Supabase config
        sb_url = os.environ.get('SUPABASE_URL', '').strip().rstrip('/')
        sb_key = os.environ.get('SUPABASE_SERVICE_ROLE_KEY', '').strip()
        if not sb_url or not sb_key:
            self._json({
                'ok': False,
                'error': 'Subscription service is not configured. Missing Supabase environment variables.',
            }, 503)
            return

        try:
            import urllib.request, urllib.error, secrets

            # Check if subscriber exists
            import urllib.parse
            check_url = (
                f"{sb_url}/rest/v1/subscribers"
                f"?select=id,email,status"
                f"&email=eq.{urllib.parse.quote(email)}"
                f"&limit=1"
            )
            req = urllib.request.Request(
                check_url,
                headers={**_sb_headers(sb_key), 'Accept': 'application/json'},
            )
            with urllib.request.urlopen(req, timeout=8) as resp:
                existing = json.loads(resp.read())

            if existing:
                row = existing[0]
                if row.get('status') == 'active':
                    self._json({'ok': True, 'message': 'You are already subscribed.'})
                    return
                # Reactivate unsubscribed
                token = secrets.token_urlsafe(32)
                patch_url = f"{sb_url}/rest/v1/subscribers?id=eq.{row['id']}"
                patch_req = urllib.request.Request(
                    patch_url,
                    data=json.dumps({'status': 'active', 'unsubscribe_token': token}).encode(),
                    headers={**_sb_headers(sb_key), 'Prefer': 'return=minimal'},
                    method='PATCH',
                )
                with urllib.request.urlopen(patch_req, timeout=8):
                    pass
                self._json({'ok': True, 'message': 'Subscribed successfully.'})
                return

            # Insert new subscriber
            token = secrets.token_urlsafe(32)
            insert_url = f"{sb_url}/rest/v1/subscribers"
            insert_req = urllib.request.Request(
                insert_url,
                data=json.dumps({
                    'email': email,
                    'status': 'active',
                    'source': str(source)[:64],
                    'unsubscribe_token': token,
                }).encode(),
                headers={**_sb_headers(sb_key), 'Prefer': 'return=minimal'},
                method='POST',
            )
            try:
                with urllib.request.urlopen(insert_req, timeout=8):
                    pass
                self._json({'ok': True, 'message': 'Subscribed successfully.'})
            except urllib.error.HTTPError as exc:
                err_body = exc.read().decode('utf-8', errors='replace')
                if exc.code == 409 or 'duplicate' in err_body.lower() or 'unique' in err_body.lower():
                    self._json({'ok': True, 'message': 'You are already subscribed.'})
                elif 'does not exist' in err_body.lower() or 'relation' in err_body.lower():
                    self._json({
                        'ok': False,
                        'error': 'Subscriber table not found. Run supabase/schema.sql first.',
                    }, 503)
                else:
                    self._json({'ok': False, 'error': f'Database error ({exc.code}).'}, 500)

        except Exception as exc:
            err = str(exc)
            if 'does not exist' in err.lower() or 'relation' in err.lower():
                self._json({
                    'ok': False,
                    'error': 'Subscriber table not found. Run supabase/schema.sql first.',
                }, 503)
            elif 'name or service not known' in err.lower() or 'connection' in err.lower():
                self._json({'ok': False, 'error': 'Cannot reach database. Check SUPABASE_URL.'}, 503)
            else:
                self._json({'ok': False, 'error': 'Something went wrong. Please try again.'}, 500)

    def _cors(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
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
