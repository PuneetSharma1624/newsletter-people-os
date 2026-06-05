"""POST/GET /api/admin?action=<action> — consolidated admin endpoint.
Requires Authorization: Bearer <ADMIN_TRIGGER_TOKEN> for most actions.
action=log does not require auth (but scrubs secrets).

Actions:
  GET  status          — generation status + today's issue info
  GET  stats           — admin analytics (visits, subs, new today)
  GET  subscribers     — list subscribers
  GET  logs            — recent action logs
  GET  check_today     — validate today's issue files
  POST trigger         — dispatch GitHub Actions workflow_dispatch
  POST log             — write action log entry (no auth required)
  POST demo_refresh    — write demo JSON locally (honest error on Vercel)
  POST check_json      — check production JSON availability
"""
from http.server import BaseHTTPRequestHandler
import json, os, urllib.request, urllib.error, hashlib, datetime, pathlib, sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from newsletter.backend_utils import normalize_supabase_url


# ── helpers ──────────────────────────────────────────────────────────────────

def _today_ist():
    ist = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
    return datetime.datetime.now(ist).date().isoformat()


def _sb_headers(key):
    return {'apikey': key, 'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'}


def _sb_count(sb_url, sb_key, table, qs=''):
    url = f"{sb_url}/rest/v1/{table}?select=id{('&' + qs) if qs else ''}"
    req = urllib.request.Request(url, headers={**_sb_headers(sb_key), 'Prefer': 'count=exact'})
    with urllib.request.urlopen(req, timeout=6) as r:
        cr = r.headers.get('Content-Range', '')
        return int(cr.split('/')[-1]) if '/' in cr else 0


def _sb_get(sb_url, sb_key, table, qs=''):
    url = f"{sb_url}/rest/v1/{table}{'?' + qs if qs else ''}"
    req = urllib.request.Request(url, headers={**_sb_headers(sb_key), 'Accept': 'application/json'})
    with urllib.request.urlopen(req, timeout=6) as r:
        return json.loads(r.read())


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


def _validate_auth(headers):
    expected = os.environ.get('ADMIN_TRIGGER_TOKEN', '').strip().strip('"').strip("'")
    if not expected:
        return False
    auth = headers.get('Authorization', '')
    return auth.startswith('Bearer ') and auth[7:].strip() == expected


def _trigger_github(mode, force=False):
    owner = os.getenv('GITHUB_OWNER', '')
    repo  = os.getenv('GITHUB_REPO', '')
    pat   = os.getenv('GITHUB_PAT_FOR_WORKFLOW_DISPATCH', '')
    branch = os.getenv('GITHUB_DEFAULT_BRANCH', 'main')

    if not all([owner, repo, pat]):
        return False, 'GitHub dispatch not configured (missing GITHUB_OWNER/REPO/PAT)'

    if mode in ('check_today', 'ensure_today', 'check_production'):
        workflow = 'check-and-retry-0715.yml'
    elif mode == 'send_live_today':
        workflow = 'send-newsletter-0730.yml'
    else:
        workflow = os.getenv('GITHUB_WORKFLOW_FILE', 'generate-brief-0700.yml')

    if workflow == 'generate-brief-0700.yml':
        inputs = {'force': 'true' if force else 'false'}
    elif workflow == 'send-newsletter-0730.yml':
        inputs = {'send_live': 'true' if mode == 'send_live_today' else 'false'}
    else:
        inputs = {}

    url = f"https://api.github.com/repos/{owner}/{repo}/actions/workflows/{workflow}/dispatches"
    payload = json.dumps({'ref': branch, 'inputs': inputs}).encode()
    req = urllib.request.Request(
        url, data=payload,
        headers={
            'Authorization': f'Bearer {pat}',
            'Accept': 'application/vnd.github+json',
            'Content-Type': 'application/json',
            'X-GitHub-Api-Version': '2022-11-28',
        },
        method='POST',
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return True, f'Workflow dispatched (HTTP {resp.status})'
    except urllib.error.HTTPError as exc:
        body = exc.read().decode('utf-8', errors='replace')[:200]
        return False, f'GitHub API error {exc.code}: {body}'
    except Exception as exc:
        return False, f'Network error: {exc}'


def _scrub(d):
    """Remove secret-looking keys from dict."""
    if not isinstance(d, dict):
        return d
    return {k: v for k, v in d.items()
            if not any(s in k.lower() for s in ('key', 'token', 'secret', 'password', 'pat'))}


# ── action handlers ───────────────────────────────────────────────────────────

def _action_status():
    today = _today_ist()
    try:
        import sys
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
        from newsletter.static_publisher import get_status, get_dates, issue_exists, load_issue
        status = get_status()
        dates  = get_dates()
        today_exists = issue_exists(today)
        today_info = {}
        if today_exists:
            issue = load_issue(today)
            if issue:
                today_info = {
                    'total_sections': issue.get('total_sections', 0),
                    'total_dashboard_items': issue.get('total_dashboard_items', 0),
                    'subject': issue.get('subject', ''),
                }
        return {
            'ok': True, 'today': today, 'today_exists': today_exists,
            'today_info': today_info, 'latest_date': dates[0] if dates else None,
            'total_archived': len(dates), 'generation_status': status,
            'github_configured': bool(os.getenv('GITHUB_PAT_FOR_WORKFLOW_DISPATCH')),
        }
    except Exception as exc:
        return {'ok': False, 'message': str(exc)}


def _action_admin_stats():
    sb_url = normalize_supabase_url(os.environ.get('SUPABASE_URL', ''))
    sb_key = os.environ.get('SUPABASE_SERVICE_ROLE_KEY', '')
    if not sb_url or not sb_key:
        return {'ok': False, 'message': 'Supabase not configured'}
    try:
        today = datetime.date.today().isoformat()
        today_dt = f"{today}T00:00:00"
        total_visits      = _sb_count(sb_url, sb_key, 'site_analytics')
        today_visits      = _sb_count(sb_url, sb_key, 'site_analytics', f'created_at=gte.{today_dt}')
        total_subscribers = _sb_count(sb_url, sb_key, 'subscribers', 'status=eq.active')
        new_today         = _sb_count(sb_url, sb_key, 'subscribers', f'created_at=gte.{today_dt}')
        latest = _sb_get(sb_url, sb_key, 'subscribers',
                         'select=email,created_at&order=created_at.desc&limit=1')
        return {
            'ok': True, 'total_visits': total_visits, 'today_visits': today_visits,
            'total_subscribers': total_subscribers, 'new_today': new_today,
            'last_subscriber': latest[0] if latest else None,
        }
    except Exception as exc:
        return {'ok': False, 'message': str(exc)}


def _action_subscribers(limit=100):
    sb_url = normalize_supabase_url(os.environ.get('SUPABASE_URL', ''))
    sb_key = os.environ.get('SUPABASE_SERVICE_ROLE_KEY', '')
    if not sb_url or not sb_key:
        return {'ok': False, 'message': 'Supabase not configured'}
    try:
        rows = _sb_get(sb_url, sb_key, 'subscribers',
                       f'select=email,status,source,created_at,last_email_sent_at,unsubscribed_at&order=created_at.desc&limit={limit}')
        return {'ok': True, 'subscribers': rows}
    except Exception as exc:
        return {'ok': False, 'message': str(exc)}


def _action_logs(limit=50):
    sb_url = normalize_supabase_url(os.environ.get('SUPABASE_URL', ''))
    sb_key = os.environ.get('SUPABASE_SERVICE_ROLE_KEY', '')
    if not sb_url or not sb_key:
        return {'ok': True, 'logs': [], 'note': 'unavailable'}
    try:
        rows = _sb_get(sb_url, sb_key, 'action_logs',
                       f'select=id,action_name,action_type,status,error_message,created_at&order=created_at.desc&limit={limit}')
        return {'ok': True, 'logs': rows}
    except Exception as exc:
        return {'ok': False, 'error': str(exc)[:200]}


def _action_log_write(body):
    action_name = str(body.get('action_name', 'unknown'))[:200]
    status      = str(body.get('status', 'unknown'))[:50]
    action_type = str(body.get('action_type', body.get('details', {}).get('type', '')))[:100]
    error_msg   = str(body.get('error_message', '') or body.get('details', {}).get('error', '') or '')[:500]
    req_payload  = _scrub(body.get('request_payload') or body.get('details', {}).get('request') or {})
    resp_payload = _scrub(body.get('response_payload') or body.get('details', {}).get('response') or {})

    sb_url = normalize_supabase_url(os.environ.get('SUPABASE_URL', ''))
    sb_key = os.environ.get('SUPABASE_SERVICE_ROLE_KEY', '')
    if not sb_url or not sb_key:
        return {'ok': True, 'note': 'log_unavailable'}
    try:
        _sb_insert(sb_url, sb_key, 'action_logs', {
            'action_name': action_name,
            'action_type': action_type,
            'status': status,
            'request_payload': req_payload or None,
            'response_payload': resp_payload or None,
            'error_message': error_msg or None,
        })
        return {'ok': True}
    except Exception as exc:
        return {'ok': True, 'note': 'log_failed', 'detail': str(exc)[:200]}


def _action_check_today():
    today = _today_ist()
    try:
        import sys
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
        from newsletter.static_publisher import validate_issue_complete
        result = validate_issue_complete(today)
        return {'ok': result['ok'], 'date': today, 'result': result}
    except Exception as exc:
        return {'ok': False, 'error': str(exc)}


def _action_demo_refresh():
    if os.environ.get('VERCEL') or os.environ.get('VERCEL_ENV'):
        return {
            'ok': False, 'mode': 'production',
            'error': 'Demo refresh cannot persist files on Vercel. Use Trigger Production Refresh.',
        }
    today = _today_ist()
    issues_dir = pathlib.Path('landing/data/issues')
    dates_file = pathlib.Path('landing/data/dates.json')
    try:
        issues_dir.mkdir(parents=True, exist_ok=True)
        SECTIONS = [
            ("india_stock_market","India Stock Market","S1"),
            ("us_stock_market","US Stock Market","S2"),
            ("global_markets","Global Markets","S3"),
            ("ai_news","AI News","S4"),
            ("ai_research_papers","AI Research Papers","S5"),
            ("trending_topics","Trending Topics","S6"),
            ("hr_news_india","HR News India","S7"),
            ("global_hr_news","Global HR News","S8"),
            ("hr_research_papers","HR Research Papers","S9"),
            ("macroeconomics","Macroeconomics","S10"),
            ("microeconomics","Microeconomics","S11"),
            ("major_updates","Major Updates","S12"),
        ]
        sections = []
        for sid, sname, code in SECTIONS:
            items = [{'rank': i, 'headline': f'Demo headline {i} for {sname}',
                      'summary': f'Demo summary {i}.', 'source_name': 'Demo',
                      'source_url': f'https://example.com/{sid}/{i}',
                      'credibility_score': 7} for i in range(1, 7)]
            sections.append({'section_id': sid, 'section_name': sname, 'code': code,
                             'section_summary': f'Demo: {sname}.', 'items': items})
        issue = {
            'issue_date': today, 'title': f'PeopleOS Brief — {today} (DEMO)',
            'subject': f'PeopleOS Brief — {today} (DEMO)',
            'executive_summary': 'Demo issue from admin simulate refresh.',
            'total_sections': 12, 'total_dashboard_items': 72, 'total_email_items': 24,
            'sections': sections, '_demo': True,
        }
        (issues_dir / f'{today}.json').write_text(json.dumps(issue, indent=2))
        existing = []
        if dates_file.exists():
            try: existing = json.loads(dates_file.read_text())['dates']
            except: pass
        if today not in existing:
            existing = [today] + existing
        dates_file.write_text(json.dumps({'dates': existing}, indent=2))
        return {'ok': True, 'mode': 'local', 'date': today,
                'message': f'Demo issue created for {today}. Reload / to see it.'}
    except Exception as exc:
        return {'ok': False, 'error': str(exc)[:300]}


# ── handler ───────────────────────────────────────────────────────────────────

class handler(BaseHTTPRequestHandler):

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.end_headers()

    def do_GET(self):
        action = self._qs_action()
        authed = _validate_auth(self.headers)

        if not authed:
            self._json({'ok': False, 'error': 'Unauthorized'}, 401)
            return

        if action == 'status':
            self._json(_action_status())
        elif action == 'stats':
            self._json(_action_admin_stats())
        elif action == 'subscribers':
            self._json(_action_subscribers())
        elif action == 'logs':
            self._json(_action_logs())
        elif action == 'check_today':
            self._json(_action_check_today())
        else:
            self._json({'ok': False, 'error': f'Unknown GET action: {action}'}, 400)

    def do_POST(self):
        length = int(self.headers.get('Content-Length') or 0)
        raw = self.rfile.read(length) if length > 0 else b''
        try:
            body = json.loads(raw) if raw else {}
        except Exception:
            body = {}

        action = self._qs_action() or str(body.get('action', ''))

        # log action does not require auth
        if action == 'log':
            self._json(_action_log_write(body))
            return

        authed = _validate_auth(self.headers)
        if not authed:
            self._json({'ok': False, 'error': 'Unauthorized'}, 401)
            return

        if action == 'trigger':
            mode  = str(body.get('mode', 'ensure_today'))
            force = bool(body.get('force', False))
            ok, msg = _trigger_github(mode, force)
            if ok:
                self._json({'ok': True, 'message': msg, 'mode': mode})
            else:
                self._json({
                    'ok': False, 'message': msg,
                    'fallback': ('GitHub not configured. Trigger manually: '
                                 'GitHub → Actions → Generate Brief → Run workflow'),
                }, 503 if 'not configured' in msg else 502)
        elif action == 'demo_refresh':
            self._json(_action_demo_refresh())
        elif action == 'check_today':
            self._json(_action_check_today())
        elif action == 'check_json':
            self._json(self._check_production_json(body))
        elif action == 'status':
            self._json(_action_status())
        elif action == 'stats':
            self._json(_action_admin_stats())
        elif action == 'subscribers':
            self._json(_action_subscribers())
        elif action == 'logs':
            self._json(_action_logs())
        else:
            self._json({'ok': False, 'error': f'Unknown action: {action}'}, 400)

    def _qs_action(self):
        path = self.path or ''
        if '?' in path:
            qs = path.split('?', 1)[1]
            for part in qs.split('&'):
                if part.startswith('action='):
                    return part[7:]
        return ''

    def _check_production_json(self, body):
        base_url = os.environ.get('BASE_URL', '').rstrip('/')
        if not base_url:
            return {'ok': False, 'error': 'BASE_URL not configured'}
        today = _today_ist()
        url = f"{base_url}/data/issues/{today}.json"
        try:
            with urllib.request.urlopen(url, timeout=10) as r:
                data = json.loads(r.read())
                return {
                    'ok': True, 'url': url, 'date': today,
                    'sections': data.get('total_sections', 0),
                    'items': data.get('total_dashboard_items', 0),
                }
        except urllib.error.HTTPError as exc:
            return {'ok': False, 'url': url, 'error': f'HTTP {exc.code}'}
        except Exception as exc:
            return {'ok': False, 'url': url, 'error': str(exc)[:200]}

    def _cors(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')

    def _json(self, body, status=200):
        payload = json.dumps(body, default=str).encode()
        self.send_response(status)
        self._cors()
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *args):
        pass


app = handler
application = handler
