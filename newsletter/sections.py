"""PeopleOS Brief — exact 12-section taxonomy. Single source of truth."""
from __future__ import annotations

SECTIONS = [
    {
        "id": "india_stock_market",
        "code": "S1",
        "name": "India Stock Market",
        "description": "Nifty, Sensex, Indian equities, sectors, earnings, flows, and key market-moving updates.",
        "dashboard_items": 6,
        "email_items": 2,
        "queries": [
            "India stock market today Nifty Sensex market update",
            "Nifty Sensex top market news today sectors earnings",
            "India equities FII DII flows market today",
        ],
    },
    {
        "id": "us_stock_market",
        "code": "S2",
        "name": "US Stock Market",
        "description": "S&P 500, Nasdaq, Dow, big tech, earnings, Fed-sensitive moves, and US equity market signals.",
        "dashboard_items": 6,
        "email_items": 2,
        "queries": [
            "US stock market today S&P 500 Nasdaq Dow update",
            "US equities market news today big tech earnings",
            "Wall Street market update today Federal Reserve stocks",
        ],
    },
    {
        "id": "global_markets",
        "code": "S3",
        "name": "Global Markets",
        "description": "Europe, Asia, commodities, currencies, bonds, geopolitics, and global risk sentiment.",
        "dashboard_items": 6,
        "email_items": 2,
        "queries": [
            "global markets today Asia Europe commodities currencies bonds",
            "global market update today geopolitics oil dollar yields",
            "world markets today risk sentiment equities bonds commodities",
        ],
    },
    {
        "id": "ai_news",
        "code": "S4",
        "name": "AI News",
        "description": "Major AI product launches, company moves, regulation, model releases, and enterprise AI adoption.",
        "dashboard_items": 6,
        "email_items": 2,
        "queries": [
            "latest AI news today OpenAI Google Anthropic Microsoft",
            "enterprise AI news today model release regulation",
            "AI startup funding product launch today",
        ],
    },
    {
        "id": "ai_research_papers",
        "code": "S5",
        "name": "AI Research Papers",
        "description": "Important AI/ML papers, model architecture, benchmarks, agents, safety, and applied research.",
        "dashboard_items": 6,
        "email_items": 2,
        "queries": [
            "latest AI research papers arxiv machine learning agents",
            "new AI paper arxiv LLM benchmark reasoning agents",
            "AI research papers this week large language models",
        ],
    },
    {
        "id": "trending_topics",
        "code": "S6",
        "name": "Trending Topics",
        "description": "High-signal trending stories across technology, business, society, and internet culture.",
        "dashboard_items": 6,
        "email_items": 2,
        "queries": [
            "top trending business technology topics today",
            "trending news today technology business India global",
            "viral business tech trend today",
        ],
    },
    {
        "id": "hr_news_india",
        "code": "S7",
        "name": "HR News India",
        "description": "India-specific HR, hiring, compensation, layoffs, workplace policy, labor market, and people updates.",
        "dashboard_items": 6,
        "email_items": 2,
        "queries": [
            "India HR news today hiring layoffs compensation workplace",
            "India employment news HR policy labor market today",
            "India workplace trends HR technology hiring today",
        ],
    },
    {
        "id": "global_hr_news",
        "code": "S8",
        "name": "Global HR News",
        "description": "Global HR, people strategy, workforce transformation, employee experience, and workplace updates.",
        "dashboard_items": 6,
        "email_items": 2,
        "queries": [
            "global HR news today workplace workforce layoffs hiring",
            "global talent management employee experience HR technology today",
            "future of work HR news global today",
        ],
    },
    {
        "id": "hr_research_papers",
        "code": "S9",
        "name": "HR Research Papers",
        "description": "Research on work, organizations, leadership, people analytics, talent, culture, and workforce behavior.",
        "dashboard_items": 6,
        "email_items": 2,
        "queries": [
            "HR research papers work organization leadership employee behavior",
            "people analytics research paper workforce organizational behavior",
            "latest research workplace culture leadership talent management",
        ],
    },
    {
        "id": "macroeconomics",
        "code": "S10",
        "name": "Macroeconomics",
        "description": "Inflation, rates, GDP, central banks, fiscal policy, employment, currencies, and macro indicators.",
        "dashboard_items": 6,
        "email_items": 2,
        "queries": [
            "macroeconomics news today inflation GDP central bank rates",
            "global macroeconomic update today inflation interest rates",
            "India US macroeconomics news today economy data",
        ],
    },
    {
        "id": "microeconomics",
        "code": "S11",
        "name": "Microeconomics",
        "description": "Firm behavior, consumer demand, pricing, competition, labor markets, incentives, and sector-level economics.",
        "dashboard_items": 6,
        "email_items": 2,
        "queries": [
            "microeconomics news today pricing demand competition labor market",
            "consumer demand pricing competition industry economics today",
            "firm behavior market competition economic analysis today",
        ],
    },
    {
        "id": "major_updates",
        "code": "S12",
        "name": "Major Updates",
        "description": "Important breaking or high-impact updates that do not fit neatly into the other sections.",
        "dashboard_items": 6,
        "email_items": 2,
        "queries": [
            "major breaking news business technology economy today",
            "major global updates today business markets technology",
            "important news today India world business technology economy",
        ],
    },
]

SECTION_IDS = [s["id"] for s in SECTIONS]
SECTION_MAP = {s["id"]: s for s in SECTIONS}
SECTION_CODE_MAP = {s["code"]: s for s in SECTIONS}


def get_section(section_id: str) -> dict:
    return SECTION_MAP.get(section_id, {})


def get_section_by_code(code: str) -> dict:
    return SECTION_CODE_MAP.get(code, {})
