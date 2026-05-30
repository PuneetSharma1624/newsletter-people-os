"""
PeopleOS Brief — Section-by-section Groq generator.

CRITICAL: One Groq call per section. Never 12 sections in one request.
Root cause of previous 413: 21,604 tokens sent in one request vs 12,000 TPM limit.
Fix: each section = separate Groq call with compact prompt (~2-3K tokens).
Key rotation: round-robin per section call, not per 12-section issue.
"""
from __future__ import annotations

import json
import re
import time
from typing import Any

from newsletter import config
from newsletter.logger import log
from newsletter.sections import SECTIONS

GROQ_MODEL = "llama-3.3-70b-versatile"

# Compact system prompt — single section only
SECTION_SYSTEM_PROMPT = """You are the editor of PeopleOS Brief, a premium daily intelligence dashboard.

Generate exactly 6 intelligence items for the given section using ONLY provided sources.
If sources are weak, generate 3-4 strong items rather than 6 weak/fabricated ones.

Rules:
- No fabricated facts, stats, quotes, or URLs
- Use the exact source_id from the provided sources list — do NOT invent source_ids
- headline: sharp executive headline, under 12 words
- summary: 1-2 sentences, what happened
- why_it_matters: 1 sentence for senior leaders
- peopleos_lens: 1 sentence on business/people/market implication
- action: 1 concrete action or question for this week
- credibility_score: integer 1-10
- DO NOT include source_url, source_domain, or source_name — Python will add these from source_id

Output ONLY valid raw JSON (no markdown, no code fences):
{"section_summary": "one line of what mattered today", "items": [{"rank": 1, "source_id": "S1-000", "headline": "...", "summary": "...", "why_it_matters": "...", "peopleos_lens": "...", "action": "...", "credibility_score": 8}]}"""


class GroqKeyRotator:
    """Round-robin key rotation per section call. Never spams same payload."""

    def __init__(self, keys: list[str]) -> None:
        self.keys = keys
        self._idx = 0
        self._skip_until: dict[int, float] = {}

    def next_key(self) -> tuple[int, str]:
        now = time.time()
        for _ in range(len(self.keys)):
            idx = self._idx % len(self.keys)
            self._idx += 1
            if now >= self._skip_until.get(idx, 0):
                return idx, self.keys[idx]
        # All on cooldown — wait for earliest
        earliest = min(self._skip_until, key=self._skip_until.get)
        wait = self._skip_until[earliest] - now
        log.warning(f"All Groq keys cooling. Waiting {wait:.1f}s...")
        time.sleep(max(wait, 0) + 1)
        return earliest, self.keys[earliest]

    def mark_rate_limited(self, idx: int, retry_after: float | None = None) -> None:
        cooldown = retry_after or config.groq_key_cooldown()
        self._skip_until[idx] = time.time() + cooldown
        log.warning(f"Groq key {idx+1} rate-limited. Cooldown {cooldown:.0f}s.")


_rotator: GroqKeyRotator | None = None


def _get_rotator() -> GroqKeyRotator:
    global _rotator
    if _rotator is None:
        _rotator = GroqKeyRotator(config.groq_keys())
    return _rotator


def _build_section_sources(sources: list[dict]) -> str:
    """Compact source block — source_id, title, domain, name, date, snippet.
    URL intentionally excluded — Python enriches from source_id after generation.
    """
    max_snip = config.max_snippet_chars()
    lines = []
    for s in sources:
        sid = s.get("source_id", "")
        title = s.get("title", "Untitled")[:120]
        domain = s.get("source_domain") or s.get("source", "")
        sname = s.get("source_name", domain)
        date = s.get("published_date", "unknown")
        snip = (s.get("summary") or s.get("snippet") or "")[:max_snip]
        cred = s.get("credibility_score", 5)
        lines.append(
            f'source_id:{sid} | "{title}" | {domain} | {sname} | {date} | cred:{cred}/10\n'
            f'   {snip}'
        )
    return "\n".join(lines)


def _build_source_map(sources: list[dict]) -> dict[str, dict]:
    """Map source_id → full source record for URL enrichment after generation."""
    return {s["source_id"]: s for s in sources if s.get("source_id")}


def _parse_section_response(raw: str) -> dict[str, Any]:
    cleaned = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.MULTILINE)
    cleaned = re.sub(r"\s*```$", "", cleaned.strip(), flags=re.MULTILINE)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{[\s\S]*\}", cleaned)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
    return {}


def _fallback_section(section: dict) -> dict[str, Any]:
    """Safe fallback when all retries fail."""
    return {
        "section_summary": "This section could not be updated due to API limits. Will retry next run.",
        "items": [],
        "generation_status": "fallback",
    }


def generate_section(
    section: dict,
    sources: list[dict],
    issue_date: str,
) -> dict[str, Any]:
    """
    Generate ONE section via ONE Groq call.
    Compact prompt ~2-3K tokens — well within 12K TPM limit.
    Key rotation per section, not per full issue.
    """
    from groq import Groq, RateLimitError

    candidates = sources[:config.max_candidates_per_section()]
    source_block = _build_section_sources(candidates) if candidates else "No sources available."
    source_map = _build_source_map(candidates)
    max_retries = config.max_groq_retries_per_section()

    user_prompt = (
        f"Section: {section['code']} — {section['name']}\n"
        f"Description: {section['description']}\n"
        f"Date: {issue_date}\n\n"
        f"Sources ({len(candidates)} candidates — use only these):\n"
        f"{source_block}\n\n"
        f"Generate {section['dashboard_items']} items. Output raw JSON only."
    )

    rotator = _get_rotator()

    for attempt in range(max_retries):
        key_idx, api_key = rotator.next_key()
        log.info(f"{section['code']} {section['name']} — Groq key {key_idx+1} attempt {attempt+1}/{max_retries}")
        client = Groq(api_key=api_key)

        try:
            response = client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[
                    {"role": "system", "content": SECTION_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.65,
                max_tokens=2000,
            )
            raw = response.choices[0].message.content or ""
            result = _parse_section_response(raw)

            if not result or not isinstance(result.get("items"), list):
                log.warning(f"{section['code']}: malformed response attempt {attempt+1}")
                time.sleep(config.groq_retry_delay())
                continue

            # Enrich items: map source_id → exact source URL (prevents Groq URL hallucination)
            items = result["items"]
            for rank, item in enumerate(items, 1):
                item.setdefault("rank", rank)
                item.setdefault("credibility_score", 5)
                sid = item.get("source_id", "")
                src = source_map.get(sid, {})
                # Always use exact URL from original search result, never Groq's output
                item["source_url"] = src.get("source_url") or src.get("url") or item.get("source_url", "#")
                item["source_domain"] = src.get("source_domain") or src.get("source", "") or item.get("source_domain", "")
                item["source_name"] = src.get("source_name") or item.get("source_name") or item["source_domain"]
                item["published_date"] = src.get("published_date") or item.get("published_date", "unknown")
                item["credibility_score"] = src.get("credibility_score") or item.get("credibility_score", 5)

            return {
                "code": section["code"],
                "section_id": section["id"],
                "section_name": section["name"],
                "section_summary": result.get("section_summary", ""),
                "items": items,
                "generation_status": "ok",
            }

        except RateLimitError as exc:
            retry_after = None
            m = re.search(r"(\d+(?:\.\d+)?)\s*s", str(exc))
            if m:
                retry_after = float(m.group(1)) + 2
            rotator.mark_rate_limited(key_idx, retry_after)
            time.sleep(config.groq_retry_delay())
            continue

        except Exception as exc:
            log.error(f"{section['code']} error attempt {attempt+1}: {exc}")
            time.sleep(config.groq_retry_delay())
            continue

    log.error(f"{section['code']}: all {max_retries} attempts failed — using fallback")
    fb = _fallback_section(section)
    fb["code"] = section["code"]
    fb["section_id"] = section["id"]
    fb["section_name"] = section["name"]
    return fb


def generate_executive_summary(sections: list[dict], issue_date: str) -> str:
    """
    Generate a 3-4 sentence executive summary from assembled sections.
    Single compact Groq call using only section summaries (not full items).
    """
    try:
        from groq import Groq
        rotator = _get_rotator()
        key_idx, api_key = rotator.next_key()
        client = Groq(api_key=api_key)

        # Compact: only section code, name, summary
        section_lines = "\n".join(
            f"{s['code']} {s['section_name']}: {s.get('section_summary', 'No update')}"
            for s in sections
        )
        prompt = (
            f"Date: {issue_date}\n\n"
            f"Section summaries:\n{section_lines}\n\n"
            "Write a 3-4 sentence executive summary of today's PeopleOS Brief covering "
            "the most important signals. Be specific, not generic. Output plain text only."
        )
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": "You are the editor of PeopleOS Brief. Write concise executive summaries."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.6,
            max_tokens=300,
        )
        return response.choices[0].message.content.strip()
    except Exception as exc:
        log.error(f"Executive summary failed: {exc}")
        return "Today's brief covers 12 intelligence sections across markets, AI, HR, and economics."
