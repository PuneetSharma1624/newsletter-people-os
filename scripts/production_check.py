"""PeopleOS Brief production diagnostics.

Env:
  BASE_URL required
  TEST_SUBSCRIBE_EMAIL optional
"""
import json
import os
import sys
import urllib.error
import urllib.request

BASE_URL = os.getenv("BASE_URL", "").rstrip("/")


def _print(ok, label, detail=""):
    icon = "OK" if ok else "FAIL"
    print(f"{icon} {label}" + (f": {detail}" if detail else ""))
    return ok


def _json_response(req):
    with urllib.request.urlopen(req, timeout=12) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
        return resp.status, json.loads(raw) if raw else {}


def _get(path):
    req = urllib.request.Request(f"{BASE_URL}{path}", headers={"User-Agent": "PeopleOS-ProductionCheck/1.0"})
    return _json_response(req)


def _post(path, body=None):
    data = json.dumps(body or {}).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE_URL}{path}",
        data=data,
        headers={"Content-Type": "application/json", "User-Agent": "PeopleOS-ProductionCheck/1.0"},
        method="POST",
    )
    return _json_response(req)


def _safe_call(fn, label):
    try:
        return fn()
    except urllib.error.HTTPError as exc:
        try:
            body = exc.read().decode("utf-8", errors="replace")[:300]
        except Exception:
            body = str(exc)
        _print(False, label, f"HTTP {exc.code} {body}")
    except Exception as exc:
        _print(False, label, str(exc)[:300])
    return None


def main():
    if not BASE_URL:
        print("FAIL BASE_URL missing")
        sys.exit(1)

    all_ok = True
    print(f"BASE_URL={BASE_URL}")

    result = _safe_call(lambda: _get("/data/dates.json"), "/data/dates.json reachable")
    dates = []
    if result:
        _, data = result
        dates = data.get("dates", [])
        all_ok &= _print(bool(dates), "/data/dates.json reachable", f"latest={dates[0] if dates else 'none'}")
    else:
        all_ok = False

    latest = dates[0] if dates else ""
    if latest:
        result = _safe_call(lambda: _get(f"/data/issues/{latest}.json"), "latest issue reachable")
        if result:
            _, issue = result
            sections = len(issue.get("sections", []))
            items = issue.get("total_dashboard_items", 0)
            all_ok &= _print(sections == 12 and items == 72, f"latest issue reachable: {latest}", f"sections={sections} items={items}")
        else:
            all_ok = False

    result = _safe_call(lambda: _get("/api/health"), "/api/health reachable")
    if result:
        _, data = result
        all_ok &= _print(bool(data.get("ok")), "/api/health reachable", str(data)[:120])
    else:
        all_ok = False

    before_views = None
    result = _safe_call(lambda: _get("/api/stats?t=before"), "/api/stats reachable")
    if result:
        _, stats = result
        before_views = stats.get("total_page_views")
        all_ok &= _print(bool(stats.get("ok")), "/api/stats reachable", f"total_subscribers={stats.get('total_subscribers')} total_page_views={before_views}")
    else:
        all_ok = False

    result = _safe_call(lambda: _post("/api/visit", {"path": "/production-check"}), "/api/visit records page view")
    if result:
        _, visit = result
        after_views = visit.get("total_page_views")
        incremented = before_views is None or (isinstance(after_views, int) and after_views >= before_views)
        all_ok &= _print(bool(visit.get("ok")) and bool(visit.get("recorded")) and incremented, "/api/visit increments page views", f"before={before_views} after={after_views}")
    else:
        all_ok = False

    email = os.getenv("TEST_SUBSCRIBE_EMAIL", "").strip()
    if email:
        result = _safe_call(lambda: _post("/api/subscribe", {"email": email, "source": "production_check"}), "/api/subscribe test")
        if result:
            _, sub = result
            all_ok &= _print(bool(sub.get("ok")), "/api/subscribe test", sub.get("status") or sub.get("error", ""))
    else:
        print("SKIP /api/subscribe test: set TEST_SUBSCRIBE_EMAIL")

    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
