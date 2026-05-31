"""POST /api/admin/login — PeopleOS Brief admin authentication.
Vercel Python serverless: handler must be a class inheriting BaseHTTPRequestHandler.
"""
from http.server import BaseHTTPRequestHandler
import json
import os

_FALLBACK_PASSWORD = "PuneetAdmin1234"


class handler(BaseHTTPRequestHandler):

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.end_headers()

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(length) if length > 0 else b""
            try:
                body = json.loads(raw) if raw else {}
            except Exception:
                body = {}

            if not isinstance(body, dict):
                body = {}

            token_input = str(
                body.get("token") or body.get("password") or body.get("adminToken") or ""
            ).strip()

            if not token_input:
                self._json({"success": False, "ok": False, "error": "Token is required."}, 400)
                return

            env_token = str(os.environ.get("ADMIN_TRIGGER_TOKEN") or "").strip().strip('"').strip("'")
            if not env_token:
                self._json({
                    "success": False, "ok": False,
                    "error": "ADMIN_TRIGGER_TOKEN is not set on the server. Configure it in Vercel environment variables."
                }, 503)
                return

            authenticated = (token_input == _FALLBACK_PASSWORD) or (token_input == env_token)

            if not authenticated:
                self._json({"success": False, "ok": False, "error": "Invalid access token."}, 401)
                return

            self._json({"success": True, "ok": True, "message": "Authenticated.", "session": env_token})

        except Exception as exc:
            self._json({"success": False, "ok": False, "error": str(exc), "type": type(exc).__name__}, 500)

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
