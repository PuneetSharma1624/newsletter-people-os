"""Demo data helpers for tests and local dev.
Not a serverless function — lives under newsletter/ not api/.
"""
import datetime

DEMO_SECTIONS = [
    ("india_stock_market",  "India Stock Market",  "S1"),
    ("us_stock_market",     "US Stock Market",     "S2"),
    ("global_markets",      "Global Markets",      "S3"),
    ("ai_news",             "AI News",             "S4"),
    ("ai_research_papers",  "AI Research Papers",  "S5"),
    ("trending_topics",     "Trending Topics",     "S6"),
    ("hr_news_india",       "HR News India",       "S7"),
    ("global_hr_news",      "Global HR News",      "S8"),
    ("hr_research_papers",  "HR Research Papers",  "S9"),
    ("macroeconomics",      "Macroeconomics",      "S10"),
    ("microeconomics",      "Microeconomics",      "S11"),
    ("major_updates",       "Major Updates",       "S12"),
]


def get_demo_dates(n=3):
    today = datetime.date.today()
    return [(today - datetime.timedelta(days=i)).isoformat() for i in range(n)]


def get_demo_issue(date=None):
    if date is None:
        date = datetime.date.today().isoformat()
    sections = []
    for sid, sname, code in DEMO_SECTIONS:
        items = [
            {
                "rank": i,
                "headline": f"Demo headline {i} for {sname}",
                "summary": f"Demo summary {i}.",
                "source_name": "Demo Source",
                "source_url": f"https://example.com/{sid}/{i}",
                "credibility_score": 7,
                "why_it_matters": f"Demo insight {i}.",
                "peopleos_lens": "Executive perspective placeholder.",
            }
            for i in range(1, 7)
        ]
        sections.append({
            "section_id": sid,
            "section_name": sname,
            "code": code,
            "section_summary": f"Demo section summary for {sname}.",
            "items": items,
        })
    return {
        "issue_date": date,
        "title": f"PeopleOS Brief — {date} (DEMO)",
        "subject": f"PeopleOS Brief — {date} Intelligence (DEMO)",
        "executive_summary": "This is a demo issue.",
        "total_sections": len(sections),
        "total_dashboard_items": sum(len(s["items"]) for s in sections),
        "total_email_items": len(sections) * 2,
        "sections": sections,
        "_demo": True,
    }
