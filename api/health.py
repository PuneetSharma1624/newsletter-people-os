"""GET /api/health — liveness check."""
from http.server import BaseHTTPRequestHandler
import json
import datetime


class handler(BaseHTTPRequestHandler):

    def do_GET(self):
        payload = json.dumps({
            "ok": True,
            "service": "peopleos-brief",
            "time": datetime.datetime.utcnow().isoformat() + "Z",
        }).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *args):
        pass


app = handler
application = handler
