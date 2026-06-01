"""POST /api/admin/trigger — triggers GitHub Actions workflow_dispatch.
Vercel Python serverless: handler must be a class inheriting BaseHTTPRequestHandler.
Never exposes GITHUB_PAT or API keys to frontend.
"""
from http.server import BaseHTTPRequestHandler
import json
import os
import urllib.request
import urllib.error

VALID_MODES = {
    "generate_today", "dry_run", "test_email", "send_live", "backfill_initial",
    "check_today", "ensure_today", "send_live_today", "check_production",
}


class handler(BaseHTTPRequestHandler):

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.end_headers()

    def do_POST(self):
        if not self._validate_auth():
            self._json({"ok": False, "message": "Unauthorized"}, 401)
            return

        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length > 0 else b""
        try:
            body = json.loads(raw) if raw else {}
        except Exception:
            self._json({"ok": False, "message": "Invalid request body"}, 400)
            return

        mode = body.get("mode", "generate_today")
        test_email = body.get("test_email", "")
        force = bool(body.get("force", False))

        if mode not in VALID_MODES:
            self._json({"ok": False, "message": f"Invalid mode. Use: {', '.join(VALID_MODES)}"}, 400)
            return

        if mode == "send_live" and not body.get("confirm_live_send"):
            self._json({"ok": False, "message": "Live send requires confirm_live_send=true"}, 400)
            return

        ok, message = self._trigger_github_workflow(mode, test_email, force)

        if not ok:
            self._json({
                "ok": False,
                "message": message,
                "fallback": (
                    "GitHub dispatch not configured. To trigger manually: "
                    "Go to GitHub → Actions → PeopleOS Brief Daily Brief → Run workflow. "
                    "Set mode to 'generate_today'. Click Run."
                ),
            }, 503 if "not configured" in message else 502)
            return

        self._json({"ok": True, "message": message, "mode": mode})

    def _validate_auth(self):
        expected = os.getenv("ADMIN_TRIGGER_TOKEN", "").strip().strip('"').strip("'")
        if not expected:
            return False
        auth = self.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            return auth[7:].strip() == expected
        return False

    def _trigger_github_workflow(self, mode, test_email="", force=False):
        owner = os.getenv("GITHUB_OWNER", "")
        repo = os.getenv("GITHUB_REPO", "")
        pat = os.getenv("GITHUB_PAT_FOR_WORKFLOW_DISPATCH", "")
        branch = os.getenv("GITHUB_DEFAULT_BRANCH", "main")

        if not all([owner, repo, pat]):
            return False, "GitHub dispatch not configured (GITHUB_OWNER, GITHUB_REPO, GITHUB_PAT_FOR_WORKFLOW_DISPATCH missing)"

        # Route to correct workflow file based on mode
        if mode in ("check_today", "ensure_today", "check_production"):
            workflow = "check-and-retry-0715.yml"
        elif mode == "send_live_today":
            workflow = "send-newsletter-0730.yml"
        else:
            workflow = os.getenv("GITHUB_WORKFLOW_FILE", "generate-brief-0700.yml")

        url = f"https://api.github.com/repos/{owner}/{repo}/actions/workflows/{workflow}/dispatches"

        # Build inputs per workflow
        if workflow == "generate-brief-0700.yml":
            inputs = {"force": "true" if force else "false"}
        elif workflow == "send-newsletter-0730.yml":
            inputs = {"send_live": "true" if mode == "send_live_today" else "false"}
        else:
            inputs = {}

        payload = {
            "ref": branch,
            "inputs": inputs,
        }
        data = json.dumps(payload).encode()
        req = urllib.request.Request(
            url, data=data,
            headers={
                "Authorization": f"Bearer {pat}",
                "Accept": "application/vnd.github+json",
                "Content-Type": "application/json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                return True, f"Workflow dispatched (HTTP {resp.status})"
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")[:200]
            return False, f"GitHub API error {exc.code}: {body}"
        except Exception as exc:
            return False, f"Network error: {exc}"

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")

    def _json(self, body, status=200):
        payload = json.dumps(body).encode()
        self.send_response(status)
        self._cors()
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *args):
        pass
