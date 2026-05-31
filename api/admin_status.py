"""GET /api/admin/status — returns generation status and latest issue info.
Vercel Python serverless: handler must be a class inheriting BaseHTTPRequestHandler.
"""
from http.server import BaseHTTPRequestHandler
import json
import os
import datetime


class handler(BaseHTTPRequestHandler):

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.end_headers()

    def do_GET(self):
        if not self._validate_auth():
            self._json({"ok": False, "message": "Unauthorized"}, 401)
            return

        today = datetime.date.today().isoformat()

        try:
            import sys
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
            from newsletter.static_publisher import get_status, get_dates, issue_exists, load_issue

            status = get_status()
            dates = get_dates()
            latest_date = dates[0] if dates else None
            today_exists = issue_exists(today)

            today_info = {}
            if today_exists:
                issue = load_issue(today)
                if issue:
                    today_info = {
                        "total_sections": issue.get("total_sections", 0),
                        "total_dashboard_items": issue.get("total_dashboard_items", 0),
                        "subject": issue.get("subject", ""),
                    }

            self._json({
                "ok": True,
                "today": today,
                "today_exists": today_exists,
                "today_info": today_info,
                "latest_date": latest_date,
                "total_archived": len(dates),
                "generation_status": status,
                "github_configured": bool(os.getenv("GITHUB_PAT_FOR_WORKFLOW_DISPATCH")),
            })
        except Exception as exc:
            self._json({"ok": False, "message": f"Error: {exc}"}, 500)

    def _validate_auth(self):
        expected = os.getenv("ADMIN_TRIGGER_TOKEN", "").strip().strip('"').strip("'")
        if not expected:
            return False
        auth = self.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            return auth[7:].strip() == expected
        return False

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")

    def _json(self, body, status=200):
        payload = json.dumps(body, default=str).encode()
        self.send_response(status)
        self._cors()
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *args):
        pass
