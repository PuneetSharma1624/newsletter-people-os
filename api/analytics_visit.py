"""POST /api/analytics/visit — record a dashboard visit, return aggregate counts.
No raw IPs stored. Visitor hash = sha256(user_agent + coarse_date)[:16].
Fails gracefully if Supabase not configured.
"""
from http.server import BaseHTTPRequestHandler
import json, os, urllib.request, urllib.error, hashlib, datetime


def _sb_headers(key):
    return {
        'apikey': key,
        'Authorization': f'Bearer {key}',
        'Content-Type': 'application/json',
    }


def _sb_insert(sb_url, sb_key, table, body):
    url = f"{sb_url}/rest/v1/{table}"
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        url, data=data,
        headers={**_sb_headers(sb_key), 'Prefer': 'return=minimal'},
        method='POST',
    )
    with urllib.request.urlopen(req, timeout=5) as r:
        return r.status


def _sb_count(sb_url, sb_key, table, qs=''):
    url = f"{sb_url}/rest/v1/{table}?select=id{('&' + qs) if qs else ''}"
    req = urllib.request.Request(
        url,
        headers={**_sb_headers(sb_key), 'Prefer': 'count=exact'},
    )
    with urllib.request.urlopen(req, timeout=5) as r:
        cr = r.headers.get('Content-Range', '')
        return int(cr.split('/')[-1]) if '/' in cr else 0


class handler(BaseHTTPRequestHandler):

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.end_headers()

    def do_POST(self):
        sb_url = os.environ.get('SUPABASE_URL', '').rstrip('/')
        sb_key = os.environ.get('SUPABASE_SERVICE_ROLE_KEY', '')

        if not sb_url or not sb_key:
            self._json({'ok': True, 'total_visits': 0, 'total_subscribers': 0,
                        'note': 'analytics_unavailable'})
            return

        # Build privacy-safe visitor hash
        try:
            ua = self.headers.get('User-Agent', '') or ''
            date_coarse = datetime.date.today().isoformat()
            visitor_hash = hashlib.sha256(f"{ua}{date_coarse}".encode()).hexdigest()[:16]
            _sb_insert(sb_url, sb_key, 'site_analytics', {
                'event_type': 'visit',
                'page_path': '/',
                'visitor_hash': visitor_hash,
            })
        except Exception:
            pass  # never block on insert failure

        try:
            total_visits      = _sb_count(sb_url, sb_key, 'site_analytics', 'event_type=eq.visit')
            total_subscribers = _sb_count(sb_url, sb_key, 'subscribers',    'status=eq.active')
        except Exception:
            total_visits, total_subscribers = 0, 0

        self._json({'ok': True, 'total_visits': total_visits, 'total_subscribers': total_subscribers})

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
