"""
Email sender — clean BSM-branded professional HTML template.
Light theme matching Boulder SEO Marketing brand style.
"""

import os
import re
import smtplib
import json
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

CONFIG_FILE = Path(__file__).parent / "config.json"

# ── BSM exact colour palette (extracted from brand screenshot) ──
_BSM_RED       = "#d63c2f"   # BSM logo red
_BSM_BLUE      = "#4472c4"   # section icon blue (search/research)
_BSM_GREEN     = "#3d8f5e"   # link / positive accent green
_BSM_AMBER     = "#c47e1a"   # warm amber for tools/try
_BSM_PURPLE    = "#6b4fa0"   # claude/AI purple
_BSM_TEAL      = "#2a7d6e"   # industry/watch teal
_BSM_PINK      = "#b5386e"   # priority reading pink
_BSM_GRAY      = "#6b6b6b"   # neutral/footer

# Page & card colours
_PAGE_BG       = "#ede9e2"   # warm cream page background
_CARD_BG       = "#ffffff"   # white card surface
_CARD_BORDER   = "#e4dfd6"   # soft warm border
_DIVIDER       = "#ebe5dd"   # row divider
_TEXT_PRIMARY  = "#1a1a1a"   # headings
_TEXT_BODY     = "#333333"   # body copy
_TEXT_LABEL    = "#8c8c8c"   # small uppercase labels
_TEXT_LINK     = _BSM_GREEN  # hyperlinks

# Section header keyword → accent colour
_SECTION_COLORS = {
    "what's hot today":  _BSM_RED,
    "claude insider":    _BSM_PURPLE,
    "ai tool landscape": _BSM_AMBER,
    "bsm must try":      _BSM_AMBER,
    "bsm sales angle":   _BSM_GREEN,
    "what i'm testing":  _BSM_BLUE,
    "industry watch":    _BSM_TEAL,
    "priority reading":  _BSM_PINK,
    "2-minute read":     _BSM_GRAY,
}


def _esc(t: str) -> str:
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _refs_to_links(text: str, articles: list[dict]) -> str:
    def replace(m):
        idx = int(m.group(1)) - 1
        if 0 <= idx < len(articles):
            url = _esc(articles[idx].get("url", "#"))
            title = _esc(articles[idx].get("title", m.group(0)))
            return f'<a href="{url}" style="color:{_TEXT_LINK};text-decoration:none;border-bottom:1px solid #b8ddc8;" target="_blank">{title}</a>'
        return m.group(0)
    return re.sub(r"\[(\d+)\]", replace, text)


def _get_section_color(line: str) -> str | None:
    lower = line.lower()
    for key, color in _SECTION_COLORS.items():
        if key in lower:
            return color
    return None


# BSM logo built entirely in HTML/CSS — matches brand screenshot exactly
_BSM_LOGO = f"""
<table cellpadding="0" cellspacing="0" border="0">
  <tr>
    <td style="padding-right:10px;vertical-align:middle;">
      <div style="width:38px;height:38px;background:{_BSM_RED};border-radius:8px;text-align:center;line-height:38px;">
        <span style="color:#fff;font-size:18px;font-weight:900;">&#x2197;</span>
      </div>
    </td>
    <td style="vertical-align:middle;">
      <span style="color:{_BSM_RED};font-size:28px;font-weight:900;letter-spacing:1.5px;font-family:Arial,sans-serif;">BSM</span>
    </td>
  </tr>
</table>
"""


def _build_html(brief_text: str, articles: list[dict], display_date: str,
                first_name: str, from_name: str) -> str:

    lines = brief_text.split("\n")

    # ── Outer wrapper ──────────────────────────────────────────
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
</head>
<body style="margin:0;padding:0;background:{_PAGE_BG};font-family:Arial,Helvetica,sans-serif;">
<div style="max-width:640px;margin:0 auto;background:{_PAGE_BG};padding:24px 16px;">

  <!-- BSM Header Card -->
  <div style="background:{_CARD_BG};border-radius:10px;padding:18px 24px;margin-bottom:10px;border:1px solid {_CARD_BORDER};">
    <table width="100%" cellpadding="0" cellspacing="0">
      <tr>
        <td>{_BSM_LOGO}</td>
      </tr>
    </table>
  </div>

  <!-- Title Card -->
  <div style="background:{_CARD_BG};border-radius:10px;padding:22px 26px;margin-bottom:10px;border:1px solid {_CARD_BORDER};">
    <p style="margin:0 0 4px;font-size:10px;letter-spacing:2px;color:{_TEXT_LABEL};text-transform:uppercase;font-weight:600;">Boulder SEO Marketing</p>
    <h1 style="margin:6px 0 8px;font-size:20px;font-weight:800;color:{_TEXT_PRIMARY};letter-spacing:0.5px;">SEAN'S DAILY AI UPDATES</h1>
    <p style="margin:0;font-size:13px;color:{_TEXT_LABEL};">{display_date} &nbsp;&nbsp;|&nbsp;&nbsp; AI Intelligence Briefing</p>
  </div>

  <!-- Greeting -->
  <div style="padding:4px 4px 10px;">
    <p style="margin:0;font-size:14px;color:{_TEXT_BODY};">Hey <strong style="color:{_TEXT_PRIMARY};">{first_name}</strong>, here's your AI intelligence briefing for today 👇</p>
  </div>

  <!-- Sections -->
"""

    # ── Section rendering ──────────────────────────────────────
    cur_color = None
    section_html = ""
    in_list = False
    in_table = False

    def close_section():
        nonlocal html, section_html, in_list, in_table, cur_color
        if cur_color is None:
            return
        if in_list:
            section_html += "</ul>"
            in_list = False
        if in_table:
            section_html += "</table>"
            in_table = False
        html += section_html + "</div>\n"
        section_html = ""
        cur_color = None

    section_num = 0
    is_table_section = False
    is_cards_section = False

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if "sean's daily ai updates" in stripped.lower():
            continue

        color = _get_section_color(stripped)
        if color:
            close_section()
            section_num += 1
            cur_color = color
            in_list = False
            in_table = False
            hdr = re.sub(r"^#+\s*", "", stripped)
            is_table_section = "tool landscape" in hdr.lower()
            is_cards_section = "priority reading" in hdr.lower()
            is_footer = "2-minute read" in hdr.lower() or "minute read" in hdr.lower()

            if is_footer:
                section_html = f'<div style="background:{_CARD_BG};border-radius:10px;padding:18px 24px;margin-bottom:10px;border:1px solid {_CARD_BORDER};border-top:3px solid {color};">'
                section_html += f'<p style="margin:0;font-size:11px;font-weight:700;color:{color};text-transform:uppercase;letter-spacing:1.5px;">{_esc(hdr)}</p>'
            else:
                section_html = f'<div style="background:{_CARD_BG};border-radius:10px;padding:18px 24px;margin-bottom:10px;border:1px solid {_CARD_BORDER};border-left:4px solid {color};">'
                section_html += f'<p style="margin:0 0 12px;font-size:11px;font-weight:700;color:{color};text-transform:uppercase;letter-spacing:1.5px;">{_esc(hdr)}</p>'
            continue

        if cur_color is None:
            continue

        content = re.sub(r"^-\s*", "", stripped)
        linked = _refs_to_links(_esc(content), articles)

        # Table section (AI Tool Landscape)
        if is_table_section:
            colon = content.find(":")
            if colon > 0:
                label = _esc(content[:colon].strip())
                value = _refs_to_links(_esc(content[colon+1:].strip()), articles)
                if not in_table:
                    section_html += (
                        '<table width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;">'
                        f'<tr style="background:{_PAGE_BG};">'
                        f'<th style="padding:8px 12px;font-size:10px;color:{_TEXT_LABEL};font-weight:700;text-align:left;border-bottom:1px solid {_DIVIDER};width:28%;letter-spacing:1px;text-transform:uppercase;">CATEGORY</th>'
                        f'<th style="padding:8px 12px;font-size:10px;color:{_TEXT_LABEL};font-weight:700;text-align:left;border-bottom:1px solid {_DIVIDER};letter-spacing:1px;text-transform:uppercase;">LEADER &amp; NOTES</th>'
                        '</tr>'
                    )
                    in_table = True
                row_bg = _CARD_BG if (section_html.count('<tr') % 2 == 0) else _PAGE_BG
                section_html += (
                    f'<tr style="background:{row_bg};">'
                    f'<td style="padding:9px 12px;font-size:12px;color:{_TEXT_PRIMARY};font-weight:600;border-bottom:1px solid {_DIVIDER};vertical-align:top;">{label}</td>'
                    f'<td style="padding:9px 12px;font-size:13px;color:{_TEXT_BODY};border-bottom:1px solid {_DIVIDER};">{value}</td>'
                    f'</tr>'
                )
            continue

        # Cards section (Priority Reading)
        if is_cards_section:
            section_html += (
                f'<div style="background:{_PAGE_BG};border:1px solid {_CARD_BORDER};border-radius:8px;'
                f'padding:12px 16px;margin-bottom:8px;font-size:13px;line-height:1.65;color:{_TEXT_BODY};">'
                f'{linked}</div>'
            )
            continue

        # Footer section (2-minute read)
        if is_footer:
            section_html += f'<p style="margin:10px 0 0;font-size:14px;color:{_TEXT_BODY};line-height:1.6;">{linked}</p>'
            continue

        # Standard list
        if not in_list:
            section_html += '<ul style="margin:0;padding-left:0;list-style:none;">'
            in_list = True
        section_html += (
            f'<li style="padding:9px 0;border-bottom:1px solid {_DIVIDER};font-size:13px;'
            f'line-height:1.6;color:{_TEXT_BODY};display:flex;gap:8px;">'
            f'<span style="color:{_TEXT_LABEL};flex-shrink:0;font-size:11px;padding-top:2px;">●</span>'
            f'<span>{linked}</span></li>'
        )

    close_section()

    # ── Sign-off card ──────────────────────────────────────────
    article_count = len(articles)
    html += f"""
  <!-- Sign-off -->
  <div style="background:{_CARD_BG};border-radius:10px;padding:20px 24px;margin-bottom:10px;border:1px solid {_CARD_BORDER};">
    <p style="margin:0 0 8px;font-size:14px;color:{_TEXT_BODY};line-height:1.6;">If you're building in SEO, AI, or automation — this is your edge.</p>
    <p style="margin:0;font-size:14px;color:{_TEXT_PRIMARY};font-weight:700;">– {from_name}</p>
  </div>

  <!-- Footer -->
  <div style="text-align:center;padding:12px 0 8px;">
    <p style="margin:0;font-size:11px;color:{_TEXT_LABEL};">Generated from {article_count} articles &nbsp;·&nbsp; Boulder SEO Marketing</p>
  </div>

</div>
</body>
</html>"""

    return html


def _build_plain(brief_text: str, first_name: str, from_name: str) -> str:
    return f"""Hey {first_name},

Here's your AI intelligence briefing for today:

---

{brief_text}

---

If you're building in SEO, AI, or automation — this is your edge.

– {from_name}
Boulder SEO Marketing"""


def send_newsletter(subject: str, brief_text: str, articles: list[dict], display_date: str) -> None:
    config = json.loads(CONFIG_FILE.read_text())
    email_cfg = config["email"]

    smtp_user = os.environ["SMTP_USER"]
    smtp_password = os.environ["SMTP_PASSWORD"]
    from_name = email_cfg.get("from_name", "Sean")

    for recipient in email_cfg["recipients"]:
        first_name = recipient.get("first_name", "there")

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{from_name} <{email_cfg['from_address']}>"
        msg["To"] = recipient["email"]
        msg["Reply-To"] = email_cfg.get("reply_to", email_cfg["from_address"])

        plain = _build_plain(brief_text, first_name, from_name)
        html  = _build_html(brief_text, articles, display_date, first_name, from_name)

        msg.attach(MIMEText(plain, "plain"))
        msg.attach(MIMEText(html,  "html"))

        with smtplib.SMTP(email_cfg["smtp_host"], email_cfg["smtp_port"]) as server:
            server.ehlo()
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.sendmail(email_cfg["from_address"], recipient["email"], msg.as_string())

        print(f"  ✓ Sent to {recipient['email']}")
