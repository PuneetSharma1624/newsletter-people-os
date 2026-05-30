"""Section-by-section Tavily search for PeopleOS Brief — 12 sections."""
from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

from newsletter import config
from newsletter.logger import log
from newsletter.sections import SECTIONS

HIGH_CRED_DOMAINS = {
    "reuters.com", "bloomberg.com", "ft.com", "wsj.com", "cnbc.com",
    "marketwatch.com", "economictimes.indiatimes.com", "moneycontrol.com",
    "livemint.com", "business-standard.com", "financialexpress.com",
    "rbi.org.in", "federalreserve.gov", "imf.org", "worldbank.org",
    "openai.com", "anthropic.com", "deepmind.google", "ai.meta.com",
    "research.google", "microsoft.com", "huggingface.co", "arxiv.org",
    "paperswithcode.com", "venturebeat.com", "techcrunch.com",
    "the-decoder.com", "nvidia.com",
    "shrm.org", "hrdive.com", "peoplemattersglobal.com", "ethrworld.com",
    "hbr.org", "mckinsey.com", "deloitte.com", "bcg.com", "gartner.com",
    "nber.org", "ssrn.com",
    "bbc.com", "theguardian.com", "economist.com", "fortune.com",
    "businessinsider.com", "wired.com", "fastcompany.com", "forbes.com",
}

LOW_CRED_DOMAINS = {
    "medium.com", "buzzfeed.com", "listverse.com", "makeuseof.com",
    "lifehacker.com", "quora.com", "reddit.com",
}


def _domain(url: str) -> str:
    try:
        return urlparse(url).netloc.replace("www.", "")
    except Exception:
        return url


def _score(item: dict) -> int:
    d = _domain(item.get("url", ""))
    score = 5
    if d in HIGH_CRED_DOMAINS or any(h in d for h in HIGH_CRED_DOMAINS):
        score = 9
    elif d in LOW_CRED_DOMAINS:
        score = 2
    if not item.get("published_date"):
        score -= 1
    return max(1, min(10, score))


def _normalize(raw: dict, section: dict, idx: int = 0) -> dict[str, Any]:
    exact_url = raw.get("url", "")
    d = _domain(exact_url)
    return {
        "source_id": f"{section['code']}-{idx:03d}",
        "title": (raw.get("title") or "Untitled")[:200],
        "url": exact_url,
        "source_url": exact_url,          # exact article URL — never collapsed to domain
        "source_domain": d,
        "source_name": d,
        "summary": (raw.get("content") or raw.get("snippet") or "")[:config.max_snippet_chars()],
        "published_date": raw.get("published_date", ""),
        "source": d,
        "section_id": section["id"],
        "section_code": section["code"],
        "credibility_score": _score(raw),
    }


def search_section(section: dict) -> list[dict[str, Any]]:
    """
    Search one section's queries. Returns scored, deduped candidates.
    Called per section during generation pipeline.
    """
    config.validate_config(["TAVILY_API_KEY"])
    try:
        from tavily import TavilyClient
        client = TavilyClient(api_key=config.tavily_key())
    except Exception as exc:
        log.error(f"Tavily init: {exc}")
        return []

    seen: set[str] = set()
    results: list[dict] = []
    max_per_section = config.max_candidates_per_section() + 4  # search more, trim later

    for query in section["queries"]:
        if len(results) >= max_per_section:
            break
        try:
            resp = client.search(
                query=query,
                search_depth="basic",
                max_results=4,
                include_answer=False,
            )
            for item in resp.get("results", []):
                url = item.get("url", "")
                if not url or url in seen:
                    continue
                seen.add(url)
                results.append(_normalize(item, section, idx=len(results)))
        except Exception as exc:
            log.warning(f"Search fail [{section['code']}] q={query!r}: {exc}")

    results.sort(key=lambda x: x["credibility_score"], reverse=True)
    final = results[:config.max_candidates_per_section()]
    log.info(f"{section['code']} {section['name']}: {len(final)} candidates")
    return final


def search_all_sections() -> dict[str, list[dict[str, Any]]]:
    """Search all 12 sections. Returns dict: section_id → [sources]."""
    import time
    delay = config.section_search_delay()
    out: dict[str, list] = {}
    for i, section in enumerate(SECTIONS):
        out[section["id"]] = search_section(section)
        if i < len(SECTIONS) - 1 and delay > 0:
            time.sleep(delay)
    total = sum(len(v) for v in out.values())
    log.info(f"Total search candidates: {total}")
    return out
