"""
POST /api/admin/trigger
Validates admin token then triggers GitHub Actions workflow_dispatch.
Never exposes GITHUB_PAT or API keys to frontend.
"""
from __future__ import annotations
import json, os, sys, urllib.request, urllib.error
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from newsletter.logger import log

_CORS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, Authorization",
    "Content-Type": "application/json",
}


def _json(body: dict, status: int = 200):
    return {"statusCode": status, "headers": _CORS, "body": json.dumps(body)}


def _validate_auth(request) -> bool:
    expected = os.getenv("ADMIN_TRIGGER_TOKEN", "")
    if not expected:
        return False
    # Check Authorization: Bearer <token>
    auth = ""
    headers = getattr(request, "headers", {}) or {}
    if isinstance(headers, dict):
        auth = headers.get("Authorization", headers.get("authorization", ""))
    if auth.startswith("Bearer "):
        return auth[7:].strip() == expected
    return False


def _trigger_github_workflow(mode: str, test_email: str = "", force: bool = False) -> tuple[bool, str]:
    """Call GitHub Actions workflow_dispatch API."""
    owner = os.getenv("GITHUB_OWNER", "")
    repo = os.getenv("GITHUB_REPO", "")
    workflow = os.getenv("GITHUB_WORKFLOW_FILE", "daily-brief.yml")
    pat = os.getenv("GITHUB_PAT_FOR_WORKFLOW_DISPATCH", "")
    branch = os.getenv("GITHUB_DEFAULT_BRANCH", "main")

    if not all([owner, repo, pat]):
        return False, "GitHub dispatch not configured (GITHUB_OWNER, GITHUB_REPO, GITHUB_PAT_FOR_WORKFLOW_DISPATCH missing)"

    url = f"https://api.github.com/repos/{owner}/{repo}/actions/workflows/{workflow}/dispatches"
    payload = {
        "ref": branch,
        "inputs": {
            "mode": mode,
            "test_email": test_email,
            "force": "true" if force else "false",
        },
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
            # 204 = success (no content)
            return True, f"Workflow dispatched (HTTP {resp.status})"
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")[:200]
        return False, f"GitHub API error {exc.code}: {body}"
    except Exception as exc:
        return False, f"Network error: {exc}"


def handler(request, response=None):
    method = getattr(request, "method", "POST")
    if method == "OPTIONS":
        return _json({}, 200)
    if method != "POST":
        return _json({"ok": False, "message": "Method not allowed"}, 405)

    if not _validate_auth(request):
        return _json({"ok": False, "message": "Unauthorized"}, 401)

    try:
        body_raw = getattr(request, "body", b"") or b""
        if isinstance(body_raw, str):
            body_raw = body_raw.encode()
        body = json.loads(body_raw) if body_raw else {}
    except Exception:
        return _json({"ok": False, "message": "Invalid request body"}, 400)

    mode = body.get("mode", "generate_today")
    test_email = body.get("test_email", "")
    force = bool(body.get("force", False))

    VALID_MODES = {"generate_today", "dry_run", "test_email", "send_live", "backfill_initial"}
    if mode not in VALID_MODES:
        return _json({"ok": False, "message": f"Invalid mode. Use: {', '.join(VALID_MODES)}"}, 400)

    # Safety: send_live requires explicit confirmation
    if mode == "send_live" and not body.get("confirm_live_send"):
        return _json({"ok": False, "message": "Live send requires confirm_live_send=true"}, 400)

    log.info(f"Admin trigger: mode={mode}, force={force}")
    ok, message = _trigger_github_workflow(mode, test_email, force)

    if not ok:
        # Graceful degradation: if GitHub dispatch not configured, show instructions
        return _json({
            "ok": False,
            "message": message,
            "fallback": (
                "GitHub dispatch not configured. To trigger manually: "
                "Go to GitHub → Actions → PeopleOS Brief Daily Brief → Run workflow. "
                "Set mode to 'generate_today'. Click Run."
            ),
        }, 503 if "not configured" in message else 502)

    return _json({"ok": True, "message": message, "mode": mode})


app = handler
application = handler
