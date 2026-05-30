import re
import secrets
import string
from urllib.parse import urlparse


def normalize_email(email: str) -> str:
    """Lowercase + strip whitespace."""
    return email.strip().lower()


def is_valid_email(email: str) -> bool:
    """Basic RFC-compliant email check."""
    pattern = r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email.strip()))


def generate_token(length: int = 48) -> str:
    """Cryptographically secure URL-safe token."""
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def truncate(text: str, max_chars: int = 200) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rstrip() + "..."


def is_probably_homepage_url(url: str) -> bool:
    """
    Return True if URL looks like a publisher homepage or top-level section page,
    not a specific article/paper/report.

    Flags:
      - Empty or None URL
      - Path is empty, '/', or only one non-empty segment (e.g. /markets, /blog)
      - Known bare homepages (x.com, twitter.com with no path)

    Allows:
      - arxiv.org/abs/XXXX  (has meaningful path)
      - moneycontrol.com/news/business/markets/article-slug.html
      - reuters.com/markets/asia/india-gdp-2026-05-30
    """
    if not url:
        return True
    try:
        parsed = urlparse(url)
        path = parsed.path.strip("/")
        # Empty path = homepage
        if not path:
            return True
        # Single top-level segment = section/category page, not article
        segments = [s for s in path.split("/") if s]
        if len(segments) <= 1:
            return True
        return False
    except Exception:
        return True


def validate_article_url(url: str, source_domain: str = "") -> dict:
    """
    Validate that a URL points to a specific article, not a homepage.
    Returns {"is_valid_article_url": bool, "reason": str}
    """
    if not url or url == "#":
        return {"is_valid_article_url": False, "reason": "missing_url"}
    if is_probably_homepage_url(url):
        return {"is_valid_article_url": False, "reason": "homepage_url"}
    return {"is_valid_article_url": True, "reason": "ok"}
