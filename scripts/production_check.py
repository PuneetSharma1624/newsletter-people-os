"""
PeopleOS Brief — Production Diagnostics
Checks all public endpoints and data files from BASE_URL.

Usage:
  python scripts/production_check.py

Set env vars:
  BASE_URL              required
  TEST_SUBSCRIBE_EMAIL  optional — if set, tests subscribe endpoint
"""
import os, sys, json, datetime, urllib.request, urllib.error

BASE_URL = os.getenv('BASE_URL', '').rstrip('/')

def _ist_today():
    ist = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
    return datetime.datetime.now(ist).date().isoformat()

def _get(url, label):
    try:
        with urllib.request.urlopen(url, timeout=10) as r:
            body = r.read().decode()
            data = json.loads(body) if body else {}
            return True, data
    except urllib.error.HTTPError as e:
        return False, {'http_status': e.code}
    except Exception as exc:
        return False, {'error': str(exc)[:200]}

def check(ok, label, detail=''):
    icon = '✅' if ok else '❌'
    print(f"{icon} {label}" + (f": {detail}" if detail else ''))
    return ok

def main():
    if not BASE_URL:
        print("❌ BASE_URL env var is not set. Set it to your production domain, e.g.:")
        print("   BASE_URL=https://your-domain.vercel.app python scripts/production_check.py")
        sys.exit(1)

    print(f"=== PeopleOS Brief — Production Check ===")
    print(f"BASE_URL : {BASE_URL}")
    print(f"IST date : {_ist_today()}")
    print()

    all_ok = True

    # 1. dates.json
    ok, data = _get(f"{BASE_URL}/data/dates.json", "dates.json")
    dates = data.get('dates', []) if ok else []
    all_ok &= check(ok and bool(dates), "dates.json reachable",
                    f"latest={dates[0] if dates else 'EMPTY'}" if ok else str(data))

    # 2. Latest issue
    today = _ist_today()
    latest = dates[0] if dates else today
    ok2, issue = _get(f"{BASE_URL}/data/issues/{latest}.json", f"latest issue {latest}")
    sections = len(issue.get('sections', [])) if ok2 else 0
    items = issue.get('total_dashboard_items', 0) if ok2 else 0
    all_ok &= check(ok2, f"latest issue reachable: {latest}",
                    f"sections={sections} items={items}" if ok2 else str(issue))
    if ok2 and (sections < 12 or items < 60):
        check(False, f"issue completeness", f"sections={sections}/12 items={items}/72")
        all_ok = False

    # 3. Today issue (IST)
    if today != latest:
        ok3, issue3 = _get(f"{BASE_URL}/data/issues/{today}.json", f"today issue {today}")
        all_ok &= check(ok3, f"today's issue available ({today})",
                        "MISSING — generation may not have run" if not ok3 else
                        f"sections={len(issue3.get('sections',[]))} items={issue3.get('total_dashboard_items',0)}")

    # 4. Public stats
    ok4, stats = _get(f"{BASE_URL}/api/stats?t=check", "public stats")
    if ok4 and stats.get('ok'):
        pv = stats.get('total_page_views', stats.get('total_visits', '?'))
        sb = stats.get('total_subscribers', '?')
        all_ok &= check(True, f"public stats reachable", f"total_page_views={pv} total_subscribers={sb}")
    else:
        all_ok &= check(False, "public stats reachable", str(stats))

    # 5. Analytics visit
    try:
        req = urllib.request.Request(f"{BASE_URL}/api/visit", data=b'{}',
                                     headers={'Content-Type': 'application/json'}, method='POST')
        with urllib.request.urlopen(req, timeout=10) as r:
            d = json.loads(r.read())
        all_ok &= check(d.get('ok', False), "analytics/visit endpoint", str(d)[:120])
    except Exception as exc:
        all_ok &= check(False, "analytics/visit endpoint", str(exc)[:120])

    # 6. Subscribe endpoint (test email only if TEST_SUBSCRIBE_EMAIL set)
    test_email = os.getenv('TEST_SUBSCRIBE_EMAIL', '')
    if test_email:
        try:
            payload = json.dumps({'email': test_email, 'source': 'production_check'}).encode()
            req = urllib.request.Request(
                f"{BASE_URL}/api/subscribe", data=payload,
                headers={'Content-Type': 'application/json'}, method='POST')
            with urllib.request.urlopen(req, timeout=10) as r:
                d = json.loads(r.read())
            sub_ok = d.get('ok', False)
            all_ok &= check(sub_ok, f"subscribe endpoint ({test_email})",
                            d.get('message') or d.get('status') or d.get('error', ''))
        except Exception as exc:
            all_ok &= check(False, f"subscribe endpoint", str(exc)[:120])
    else:
        print(f"ℹ️  subscribe endpoint: skipped (set TEST_SUBSCRIBE_EMAIL to test)")

    print()
    if all_ok:
        print("[OK] All checks passed.")
        sys.exit(0)
    else:
        print("[FAIL] Some checks failed. See above.")
        sys.exit(1)

if __name__ == '__main__':
    main()
