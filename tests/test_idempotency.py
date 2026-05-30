"""Tests: idempotency, section model, demo data, static publisher."""
import sys, os, json, tempfile, shutil
from pathlib import Path
from unittest.mock import MagicMock

for mod in ["supabase", "resend", "anthropic", "tavily", "groq"]:
    sys.modules.setdefault(mod, MagicMock())

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from newsletter.utils import normalize_email, is_valid_email


class TestIdempotencyHelpers:
    def test_normalize_idempotent(self):
        e = normalize_email("  USER@Example.COM  ")
        assert normalize_email(e) == e == "user@example.com"

    def test_already_active(self):
        r = {"subscriber_id": "x", "is_new": False, "was_reactivated": False, "already_active": True}
        assert r["already_active"] and not r["is_new"]

    def test_reactivation(self):
        r = {"subscriber_id": "x", "is_new": False, "was_reactivated": True, "already_active": False}
        assert r["was_reactivated"]

    def test_invalid_emails(self):
        for e in ["notanemail", "x@", "@d.com", ""]:
            assert not is_valid_email(e)

    def test_test_mode_no_db_log(self):
        import newsletter.subscribers as sm
        import newsletter.sender as send_mod
        import newsletter.renderer as ren
        import newsletter.config as cfg

        ml = MagicMock(); ms = MagicMock(return_value=False); me = MagicMock(return_value={"ok": True, "message_id": "x", "error": ""})
        mh = MagicMock(return_value="<html/>"); mt = MagicMock(return_value="txt"); mb = MagicMock(return_value="https://x.com")

        sm.log_send, sm.already_sent = ml, ms
        send_mod.send_email, cfg.base_url = me, mb
        ren.render_html_email, ren.render_text_email = mh, mt
        send_mod.render_html_email, send_mod.render_text_email = mh, mt

        sub = {"id": "s1", "email": "t@t.com", "unsubscribe_token": "tok"}
        issue = {"issue_date": "2026-05-30", "subject": "T", "html": "", "text": "", "preheader": "", "sections": []}
        send_mod.send_to_subscriber(sub, issue, "i1", is_test=True)
        ml.assert_not_called()


class TestSectionModel:
    def test_exactly_12(self):
        from newsletter.sections import SECTIONS
        assert len(SECTIONS) == 12

    def test_exact_ids_in_order(self):
        from newsletter.sections import SECTION_IDS
        assert SECTION_IDS == [
            "india_stock_market", "us_stock_market", "global_markets",
            "ai_news", "ai_research_papers", "trending_topics",
            "hr_news_india", "global_hr_news", "hr_research_papers",
            "macroeconomics", "microeconomics", "major_updates",
        ]

    def test_exact_codes(self):
        from newsletter.sections import SECTIONS
        assert [s["code"] for s in SECTIONS] == [f"S{i}" for i in range(1, 13)]

    def test_queries_per_section(self):
        from newsletter.sections import SECTIONS
        for s in SECTIONS:
            assert len(s["queries"]) >= 3

    def test_dashboard_email_counts(self):
        from newsletter.sections import SECTIONS
        for s in SECTIONS:
            assert s["dashboard_items"] == 6
            assert s["email_items"] == 2

    def test_lookup_by_id(self):
        from newsletter.sections import get_section
        s = get_section("india_stock_market")
        assert s["code"] == "S1" and s["name"] == "India Stock Market"

    def test_lookup_by_code(self):
        from newsletter.sections import get_section_by_code
        s = get_section_by_code("S12")
        assert s["id"] == "major_updates"


class TestDemoData:
    def test_3_dates(self):
        from api.demo_data import get_demo_dates
        assert len(get_demo_dates()) == 3

    def test_12_sections(self):
        from api.demo_data import get_demo_issue
        assert len(get_demo_issue()["sections"]) == 12

    def test_6_items_per_section(self):
        from api.demo_data import get_demo_issue
        for s in get_demo_issue()["sections"]:
            assert len(s["items"]) == 6, f"{s['code']} has {len(s['items'])} items"

    def test_216_total_items(self):
        from api.demo_data import get_demo_dates, get_demo_issue
        total = sum(
            len(s["items"])
            for d in get_demo_dates()
            for s in get_demo_issue(d)["sections"]
        )
        assert total >= 216, f"Only {total} items"

    def test_section_ids_match_taxonomy(self):
        from api.demo_data import get_demo_issue
        from newsletter.sections import SECTION_IDS
        assert [s["section_id"] for s in get_demo_issue()["sections"]] == SECTION_IDS


class TestStaticPublisher:
    """Test static publisher with a temp directory."""

    def setup_method(self):
        self._tmpdir = tempfile.mkdtemp()
        # Monkey-patch the data dir
        import newsletter.static_publisher as sp
        self._orig_data = sp._DATA_DIR
        self._orig_issues = sp._ISSUES_DIR
        sp._DATA_DIR = Path(self._tmpdir) / "data"
        sp._ISSUES_DIR = sp._DATA_DIR / "issues"
        sp._DATA_DIR.mkdir(parents=True, exist_ok=True)
        sp._ISSUES_DIR.mkdir(parents=True, exist_ok=True)

    def teardown_method(self):
        import newsletter.static_publisher as sp
        sp._DATA_DIR = self._orig_data
        sp._ISSUES_DIR = self._orig_issues
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def _make_issue(self, date: str) -> dict:
        return {
            "issue_date": date,
            "title": f"PeopleOS Brief — {date}",
            "subject": "Test",
            "preheader": "Test",
            "executive_summary": "Test summary.",
            "total_sections": 12,
            "total_dashboard_items": 72,
            "total_email_items": 24,
            "sections": [],
        }

    def test_save_and_load(self):
        from newsletter.static_publisher import save_issue, load_issue
        issue = self._make_issue("2026-05-30")
        save_issue(issue)
        loaded = load_issue("2026-05-30")
        assert loaded["issue_date"] == "2026-05-30"

    def test_issue_exists(self):
        from newsletter.static_publisher import save_issue, issue_exists
        assert not issue_exists("2026-05-30")
        save_issue(self._make_issue("2026-05-30"))
        assert issue_exists("2026-05-30")

    def test_status_lifecycle(self):
        from newsletter.static_publisher import set_status, get_status, is_today_complete
        set_status("running", current_date="2026-05-30")
        assert get_status()["status"] == "running"
        set_status("complete", current_date="2026-05-30")
        assert is_today_complete("2026-05-30")
        assert not is_today_complete("2026-05-29")

    def test_dates_index_updated(self):
        from newsletter.static_publisher import save_issue, get_dates
        save_issue(self._make_issue("2026-05-30"))
        save_issue(self._make_issue("2026-05-29"))
        dates = get_dates()
        assert "2026-05-30" in dates
        assert "2026-05-29" in dates

    def test_partial_save_and_load(self):
        from newsletter.static_publisher import save_partial, load_partial, delete_partial
        secs = [{"code": "S1", "section_id": "india_stock_market", "items": []}]
        save_partial("2026-05-30", secs)
        loaded = load_partial("2026-05-30")
        assert len(loaded) == 1
        delete_partial("2026-05-30")
        assert load_partial("2026-05-30") == []

    def test_prune_archive(self):
        from newsletter.static_publisher import save_issue, prune_archive, get_dates
        import datetime
        old_date = (datetime.date.today() - datetime.timedelta(days=200)).isoformat()
        recent_date = datetime.date.today().isoformat()
        save_issue(self._make_issue(old_date))
        save_issue(self._make_issue(recent_date))
        deleted = prune_archive(retention_days=180)
        assert old_date in deleted
        assert recent_date not in deleted
        remaining = get_dates()
        assert recent_date in remaining
        assert old_date not in remaining
