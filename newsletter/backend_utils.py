"""Backend helpers for Supabase REST calls.

Public API functions use these helpers so SUPABASE_URL can be pasted as either
the project root or the REST endpoint without producing malformed paths.
"""
from __future__ import annotations

import json
import urllib.parse
import urllib.request
import urllib.error
from typing import Any


def normalize_supabase_url(raw_url: str) -> str:
    if not raw_url:
        return ""
    url = raw_url.strip().rstrip("/")
    if url.endswith("/rest/v1"):
        url = url[: -len("/rest/v1")]
    return url.rstrip("/")


def supabase_headers(service_role_key: str, content_type: bool = True) -> dict[str, str]:
    headers = {
        "apikey": service_role_key,
        "Authorization": f"Bearer {service_role_key}",
        "Accept": "application/json",
    }
    if content_type:
        headers["Content-Type"] = "application/json"
    return headers


def rest_url(sb_url: str, table: str, query: str = "") -> str:
    base = normalize_supabase_url(sb_url)
    url = f"{base}/rest/v1/{table}"
    if query:
        url += "?" + query.lstrip("?")
    return url


def quote_filter(value: str) -> str:
    return urllib.parse.quote(value, safe="")


def read_error_body(exc: BaseException, limit: int = 300) -> str:
    if isinstance(exc, urllib.error.HTTPError):
        try:
            return exc.read().decode("utf-8", errors="replace")[:limit]
        except Exception:
            return str(exc)[:limit]
    return str(exc)[:limit]


def classify_supabase_error(exc: BaseException, table_label: str = "tables") -> str:
    err = (read_error_body(exc, 600) or str(exc)).lower()
    if "pgrst125" in err or "invalid path" in err:
        return "Supabase URL is misconfigured. Use the project URL, not a REST path."
    if "42p01" in err or "does not exist" in err or "schema cache" in err:
        return f"{table_label} are missing. Run supabase/schema.sql."
    if "jwt" in err or "invalid api key" in err or "401" in err:
        return "Supabase authentication failed. Check SUPABASE_SERVICE_ROLE_KEY."
    return "Supabase request failed."


def rest_get(sb_url: str, sb_key: str, table: str, query: str = "", timeout: int = 8) -> Any:
    req = urllib.request.Request(
        rest_url(sb_url, table, query),
        headers=supabase_headers(sb_key, content_type=False),
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read().decode("utf-8")
        return json.loads(body) if body else []


def rest_count(sb_url: str, sb_key: str, table: str, query: str = "", timeout: int = 8) -> int:
    q = "select=id"
    if query:
        q += "&" + query.lstrip("?")
    req = urllib.request.Request(
        rest_url(sb_url, table, q),
        headers={**supabase_headers(sb_key, content_type=False), "Prefer": "count=exact"},
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        cr = resp.headers.get("Content-Range", "")
        return int(cr.split("/")[-1]) if "/" in cr and cr.split("/")[-1].isdigit() else 0


def rest_post(
    sb_url: str,
    sb_key: str,
    table: str,
    body: dict[str, Any] | list[dict[str, Any]],
    prefer: str = "return=representation",
    timeout: int = 8,
) -> Any:
    req = urllib.request.Request(
        rest_url(sb_url, table),
        data=json.dumps(body).encode("utf-8"),
        headers={**supabase_headers(sb_key), "Prefer": prefer},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        payload = resp.read().decode("utf-8")
        return json.loads(payload) if payload else []


def rest_patch(
    sb_url: str,
    sb_key: str,
    table: str,
    query: str,
    body: dict[str, Any],
    prefer: str = "return=representation",
    timeout: int = 8,
) -> Any:
    req = urllib.request.Request(
        rest_url(sb_url, table, query),
        data=json.dumps(body).encode("utf-8"),
        headers={**supabase_headers(sb_key), "Prefer": prefer},
        method="PATCH",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        payload = resp.read().decode("utf-8")
        return json.loads(payload) if payload else []
