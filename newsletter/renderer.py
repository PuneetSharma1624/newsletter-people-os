"""Premium compact email renderer for PeopleOS Brief — 12 sections × 2 items each.
Gmail-safe inline CSS. Dark header, compact section cards, TOC, mobile-readable.
"""
from __future__ import annotations

import datetime
from typing import Any

from newsletter.sections import SECTIONS


def _fmt_date(iso: str) -> str:
    try:
        return datetime.date.fromisoformat(iso).strftime("%B %d, %Y")
    except Exception:
        return iso


def _toc_html(sections: list[dict]) -> str:
    """Compact table of contents — S1 to S12 inline pills."""
    pills = ""
    for s in sections:
        code = s.get("code", "")
        name = s.get("section_name", "")
        pills += (
            f'<span style="display:inline-block;background:#1a1030;color:#9585ff;'
            f'font-size:11px;font-weight:600;padding:3px 10px;border-radius:999px;'
            f'border:1px solid #2d2b55;margin:3px 3px 3px 0;white-space:nowrap;">'
            f'{code} {name}</span>'
        )
    return (
        f'<p style="margin:0 0 8px;font-size:11px;font-weight:700;color:#555;'
        f'text-transform:uppercase;letter-spacing:0.08em;">In This Brief</p>'
        f'<div style="line-height:2;">{pills}</div>'
    )


def _section_email_html(section: dict) -> str:
    """Compact email block for one section — top 2 items only."""
    items = section.get("items", [])[:2]
    if not items:
        return ""

    code = section.get("code", "")
    name = section.get("section_name", "")
    # Section injection comment for Python template system
    comment = f"<!-- {code}: {name} -->"

    items_html = ""
    for item in items:
        src_name = item.get("source_name") or item.get("source_domain", "")
        src_url = item.get("source_url", "#")
        items_html += f"""
<tr>
  <td style="padding:10px 20px 10px;">
    <table width="100%" cellpadding="0" cellspacing="0" border="0">
      <tr>
        <td style="padding-bottom:4px;">
          <span style="font-size:10px;font-weight:700;color:#7c6af7;
                       text-transform:uppercase;letter-spacing:0.05em;">#{item.get('rank','')} &nbsp;</span>
          <a href="{src_url}" style="font-size:14px;font-weight:700;color:#ffffff;
                                      text-decoration:none;line-height:1.3;"
             target="_blank">{item.get('headline','').strip()}</a>
        </td>
      </tr>
      <tr>
        <td style="padding-bottom:3px;">
          <span style="font-size:12px;color:#a0a0b0;line-height:1.5;">{item.get('summary','').strip()}</span>
        </td>
      </tr>
      <tr>
        <td style="padding-bottom:6px;">
          <span style="font-size:11px;color:#7c6af7;font-weight:600;">Why: </span>
          <span style="font-size:11px;color:#888;">{item.get('why_it_matters','').strip()}</span>
        </td>
      </tr>
      <tr>
        <td>
          <a href="{src_url}" style="font-size:11px;color:#555;text-decoration:none;
                                      border:1px solid #222;border-radius:4px;padding:2px 8px;"
             target="_blank">↗ {src_name}</a>
        </td>
      </tr>
    </table>
  </td>
</tr>
"""

    return f"""{comment}
<tr>
  <td style="padding:4px 0 4px;">
    <table width="100%" cellpadding="0" cellspacing="0" border="0"
           style="background:#0f0f18;border-radius:8px;border:1px solid #1a1a2e;overflow:hidden;">
      <tr>
        <td style="padding:10px 20px 8px;border-bottom:1px solid #1a1a2e;">
          <span style="font-size:10px;font-weight:800;color:#555;
                       text-transform:uppercase;letter-spacing:0.1em;">{code}</span>
          <span style="font-size:13px;font-weight:700;color:#e0e0f0;margin-left:8px;">{name}</span>
          <span style="font-size:11px;color:#444;margin-left:8px;">{section.get('section_summary','').strip()[:80]}</span>
        </td>
      </tr>
      {items_html}
    </table>
  </td>
</tr>
<tr><td style="height:6px;"></td></tr>
"""


def render_html_email(issue: dict, unsubscribe_url: str, base_url: str) -> str:
    """Build full premium compact HTML email — 12 sections × 2 items."""
    issue_date = issue.get("issue_date", "")
    date_display = _fmt_date(issue_date)
    subject = issue.get("subject", "PeopleOS Brief")
    executive_summary = issue.get("executive_summary", "")
    sections = issue.get("sections", [])
    dashboard_url = f"{base_url}/brief?date={issue_date}"

    toc = _toc_html(sections)
    section_blocks = "".join(_section_email_html(s) for s in sections)

    return f"""<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
<meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>{subject}</title>
</head>
<body style="margin:0;padding:0;background:#0a0a0f;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#0a0a0f;">
  <tr><td align="center" style="padding:24px 16px;">
    <table width="640" cellpadding="0" cellspacing="0" border="0" style="max-width:640px;width:100%;">

      <!-- HEADER -->
      <tr>
        <td style="background:#0d0d1a;border-radius:10px 10px 0 0;padding:24px 28px 18px;
                   border:1px solid #1a1a2e;border-bottom:none;">
          <table width="100%" cellpadding="0" cellspacing="0" border="0">
            <tr>
              <td>
                <p style="margin:0 0 4px;font-size:11px;font-weight:800;color:#7c6af7;
                           text-transform:uppercase;letter-spacing:0.12em;">PeopleOS Brief</p>
                <p style="margin:0;font-size:22px;font-weight:800;color:#fff;letter-spacing:-0.02em;">
                  Daily Executive Intelligence</p>
                <p style="margin:2px 0 0;font-size:12px;color:#555;">Markets · AI · HR · Economics</p>
              </td>
              <td align="right" valign="top">
                <span style="display:inline-block;background:#13102a;color:#9585ff;
                             font-size:11px;font-weight:700;padding:5px 12px;
                             border-radius:999px;border:1px solid #2d2b55;white-space:nowrap;">
                  {date_display}
                </span>
              </td>
            </tr>
          </table>
        </td>
      </tr>

      <!-- EXECUTIVE SUMMARY -->
      <tr>
        <td style="background:#0b0b18;padding:16px 28px;border-left:1px solid #1a1a2e;border-right:1px solid #1a1a2e;">
          <p style="margin:0 0 6px;font-size:10px;font-weight:700;color:#555;
                     text-transform:uppercase;letter-spacing:0.08em;">Today's Signals</p>
          <p style="margin:0;font-size:13px;color:#b0b0c0;line-height:1.65;">{executive_summary}</p>
        </td>
      </tr>

      <!-- TOC -->
      <tr>
        <td style="background:#0b0b18;padding:12px 28px 16px;border-left:1px solid #1a1a2e;border-right:1px solid #1a1a2e;border-bottom:1px solid #1a1a2e;">
          {toc}
        </td>
      </tr>

      <!-- SECTION BLOCKS S1-S12 -->
      <!-- Template injection format: {{S1_CONTENT}} through {{S12_CONTENT}} -->
      <tr>
        <td style="background:#0b0b18;padding:16px 28px;border-left:1px solid #1a1a2e;border-right:1px solid #1a1a2e;">
          <table width="100%" cellpadding="0" cellspacing="0" border="0">
            {section_blocks}
          </table>
        </td>
      </tr>

      <!-- CTA -->
      <tr>
        <td style="background:#0b0b18;padding:8px 28px 24px;border-left:1px solid #1a1a2e;border-right:1px solid #1a1a2e;">
          <table width="100%" cellpadding="0" cellspacing="0" border="0">
            <tr><td style="padding-bottom:14px;"><div style="border-top:1px solid #1a1a2e;"></div></td></tr>
            <tr>
              <td align="center">
                <a href="{dashboard_url}"
                   style="display:inline-block;background:#7c6af7;color:#fff;
                          font-size:13px;font-weight:700;text-decoration:none;
                          padding:12px 28px;border-radius:7px;">
                  Read Full Dashboard — 72 Stories →
                </a>
              </td>
            </tr>
            <tr>
              <td align="center" style="padding-top:10px;">
                <a href="{base_url}/archive"
                   style="font-size:12px;color:#444;text-decoration:none;margin-right:16px;">Archive</a>
                <a href="{base_url}"
                   style="font-size:12px;color:#444;text-decoration:none;">Subscribe / Share</a>
              </td>
            </tr>
          </table>
        </td>
      </tr>

      <!-- FOOTER -->
      <tr>
        <td style="background:#07070f;padding:18px 28px;border:1px solid #1a1a2e;
                   border-top:none;border-radius:0 0 10px 10px;">
          <p style="margin:0 0 4px;font-size:11px;color:#333;line-height:1.6;">
            <strong style="color:#444;">PeopleOS Brief</strong> by Puneet Sharma ·
            Where people strategy meets AI-native execution.
          </p>
          <p style="margin:0;font-size:11px;color:#2a2a3a;">
            No spam. No noise. ·
            <a href="{unsubscribe_url}" style="color:#333;text-decoration:none;">Unsubscribe</a>
          </p>
        </td>
      </tr>

    </table>
  </td></tr>
</table>
</body>
</html>"""


def render_text_email(issue: dict, unsubscribe_url: str, base_url: str) -> str:
    """Build plain-text email — compact, 12 sections × 2 items."""
    issue_date = issue.get("issue_date", "")
    date_display = _fmt_date(issue_date)
    dashboard_url = f"{base_url}/brief?date={issue_date}"
    lines = [
        "PEOPLEOS BRIEF — Daily Executive Intelligence",
        f"Markets · AI · HR · Economics — {date_display}",
        "=" * 60,
        "",
        issue.get("executive_summary", ""),
        "",
        "IN THIS BRIEF: " + " | ".join(f"{s.get('code','')} {s.get('section_name','')}" for s in issue.get("sections", [])),
        "",
        "=" * 60,
        "",
    ]

    for section in issue.get("sections", []):
        code = section.get("code", "")
        name = section.get("section_name", "")
        lines.append(f"{code} · {name.upper()}")
        lines.append(section.get("section_summary", ""))
        for item in section.get("items", [])[:2]:
            lines.append(f"  #{item.get('rank','')} {item.get('headline','')}")
            lines.append(f"  {item.get('summary','')}")
            lines.append(f"  Why: {item.get('why_it_matters','')}")
            lines.append(f"  Source: {item.get('source_name','')} — {item.get('source_url','')}")
            lines.append("")
        lines.append("-" * 40)
        lines.append("")

    lines += [
        f"Read Full Dashboard (72 stories): {dashboard_url}",
        f"Archive: {base_url}/archive",
        "",
        "---",
        "PeopleOS Brief by Puneet Sharma · No spam. No noise.",
        f"Unsubscribe: {unsubscribe_url}",
    ]
    return "\n".join(lines)
