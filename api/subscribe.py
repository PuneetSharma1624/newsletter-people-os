"""POST /api/subscribe — validate email, upsert subscriber via Supabase client.
Vercel Python serverless: handler must be BaseHTTPRequestHandler.
Uses same supabase-py client pattern as newsletter/subscribers.py (known to work).
NEVER expose SUPABASE_SERVICE_ROLE_KEY to frontend.
"""
from http.server import BaseHTTPRequestHandler
import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def _is_valid_email(email: str) -> bool:
    return bool(re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]{2,}$', email.strip()))


def _normalize(email: str) -> str:
    return email.strip().lower()


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
        source = str(body.get('source', 'web') or 'web')[:64]

        if not email_raw or not isinstance(email_raw, str):
            self._json({'ok': False, 'error': 'Please enter a valid email address.'}, 400)
            return

        email = _normalize(email_raw)
        if not _is_valid_email(email):
            self._json({'ok': False, 'error': 'Please enter a valid email address.'}, 400)
            return

        # Validate Supabase config
        sb_url = os.environ.get('SUPABASE_URL', '').strip()
        sb_key = os.environ.get('SUPABASE_SERVICE_ROLE_KEY', '').strip()
        if not sb_url or not sb_key:
            self._json({
                'ok': False,
                'error': 'Subscription service is not configured. Missing Supabase environment variables.',
            }, 503)
            return

        try:
            import secrets
            from supabase import create_client

            client = create_client(sb_url, sb_key)

            # Check existing subscriber
            result = (
                client.table('subscribers')
                .select('id, email, status')
                .eq('email', email)
                .limit(1)
                .execute()
            )
            existing = result.data

            if existing:
                row = existing[0]
                if row.get('status') == 'active':
                    self._json({'ok': True, 'message': 'You are already subscribed.'})
                    return
                # Reactivate unsubscribed
                token = secrets.token_urlsafe(32)
                client.table('subscribers').update({
                    'status': 'active',
                    'unsubscribe_token': token,
                    'unsubscribed_at': None,
                }).eq('id', row['id']).execute()
                self._json({'ok': True, 'message': 'Subscribed successfully.'})
                return

            # Insert new subscriber
            token = secrets.token_urlsafe(32)
            try:
                client.table('subscribers').insert({
                    'email': email,
                    'status': 'active',
                    'source': source,
                    'unsubscribe_token': token,
                }).execute()
                self._json({'ok': True, 'message': 'Subscribed successfully.'})
            except Exception as insert_exc:
                err = str(insert_exc).lower()
                if 'duplicate' in err or 'unique' in err or '23505' in err:
                    self._json({'ok': True, 'message': 'You are already subscribed.'})
                else:
                    self._json({
                        'ok': False,
                        'error': f'Database insert failed: {str(insert_exc)[:200]}',
                    }, 500)

        except Exception as exc:
            err = str(exc)
            err_lower = err.lower()
            if 'does not exist' in err_lower or 'relation' in err_lower or '42p01' in err_lower:
                self._json({
                    'ok': False,
                    'error': 'Subscriber table not found. Run supabase/schema.sql in Supabase SQL editor.',
                }, 503)
            elif 'invalid api key' in err_lower or 'jwt' in err_lower or '401' in err_lower:
                self._json({
                    'ok': False,
                    'error': 'Supabase authentication failed. Check SUPABASE_SERVICE_ROLE_KEY.',
                }, 503)
            elif 'connection' in err_lower or 'timeout' in err_lower or 'network' in err_lower:
                self._json({
                    'ok': False,
                    'error': 'Cannot reach database. Check SUPABASE_URL.',
                }, 503)
            else:
                self._json({
                    'ok': False,
                    'error': f'Subscription error: {err[:300]}',
                }, 500)

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
