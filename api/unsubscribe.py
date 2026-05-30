"""
Vercel serverless function — GET /api/unsubscribe?token=<token>
One-click unsubscribe. Returns HTML confirmation page.
"""
from __future__ import annotations

import os
import sys
import urllib.parse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from newsletter.logger import log


_HTML_SUCCESS = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Unsubscribed — PeopleOS Brief</title>
<style>
  body{margin:0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
       background:#0f0f0f;color:#e8e8e8;display:flex;align-items:center;
       justify-content:center;min-height:100vh;}
  .box{text-align:center;max-width:480px;padding:48px 32px;}
  h1{font-size:1.5rem;font-weight:600;margin-bottom:12px;color:#fff;}
  p{color:#999;line-height:1.6;font-size:0.95rem;}
  a{color:#7c6af7;text-decoration:none;}
</style>
</head>
<body>
<div class="box">
  <h1>You have been unsubscribed.</h1>
  <p>You have been unsubscribed from <strong>PeopleOS Brief</strong>.<br>
     We're sorry to see you go. Changed your mind?
     <a href="/">Subscribe again</a>.</p>
</div>
</body>
</html>"""

_HTML_INVALID = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Invalid Link — PeopleOS Brief</title>
<style>
  body{margin:0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
       background:#0f0f0f;color:#e8e8e8;display:flex;align-items:center;
       justify-content:center;min-height:100vh;}
  .box{text-align:center;max-width:480px;padding:48px 32px;}
  h1{font-size:1.5rem;font-weight:600;margin-bottom:12px;color:#fff;}
  p{color:#999;line-height:1.6;font-size:0.95rem;}
</style>
</head>
<body>
<div class="box">
  <h1>Invalid link.</h1>
  <p>This unsubscribe link is invalid or has already been used.</p>
</div>
</body>
</html>"""


def _html_response(html: str, status: int = 200):
    return {
        "statusCode": status,
        "headers": {"Content-Type": "text/html; charset=utf-8"},
        "body": html,
    }


def handler(request, response=None):
    """Vercel Python handler."""
    method = getattr(request, "method", "GET")
    if method not in ("GET", "HEAD"):
        return _html_response("<p>Method not allowed.</p>", 405)

    # Extract token from query string
    query_raw = getattr(request, "query", {}) or {}
    if isinstance(query_raw, str):
        parsed = urllib.parse.parse_qs(query_raw)
        token = parsed.get("token", [""])[0]
    else:
        token = query_raw.get("token", "")

    if not token or not isinstance(token, str) or len(token) < 8:
        return _html_response(_HTML_INVALID, 400)

    try:
        from newsletter import config
        config.validate_config(["SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY"])
        from newsletter.subscribers import unsubscribe_by_token
        updated = unsubscribe_by_token(token)
    except EnvironmentError as exc:
        log.error(f"Config error in unsubscribe API: {exc}")
        return _html_response(_HTML_INVALID, 500)
    except Exception as exc:
        log.error(f"Unsubscribe error: {exc}")
        return _html_response(_HTML_INVALID, 500)

    if updated:
        return _html_response(_HTML_SUCCESS, 200)
    else:
        return _html_response(_HTML_INVALID, 400)
