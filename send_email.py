"""
Email sender — professional newsletter template inspired by codeflair style.
White background, red accent, article thumbnails, clean card sections.
"""

import base64
import os
import re
import smtplib
import json
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

CONFIG_FILE = Path(__file__).parent / "config.json"
_LOGO_FILE  = Path(__file__).parent / "bsm_logo.png"

# ── Colour palette ─────────────────────────────────────────
_RED       = "#d63c2f"
_WHITE     = "#ffffff"
_BG        = "#f4f4f4"
_BORDER    = "#e8e8e8"
_DIVIDER   = "#f0f0f0"
_TEXT_HEAD = "#1a1a1a"
_TEXT_BODY = "#444444"
_TEXT_META = "#888888"

# Section → accent colour (used only on the label dot)
_SECTION_COLORS = {
    "what's hot today":  _RED,
    "claude insider":    "#6b4fa0",
    "ai tool landscape": "#c47e1a",
    "bsm must try":      "#c47e1a",
    "bsm sales angle":   "#2a7d4f",
    "what i'm testing":  "#2563eb",
    "industry watch":    "#2a7d6e",
    "priority reading":  "#b5386e",
    "2-minute read":     "#555555",
}


def _esc(t: str) -> str:
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _refs_to_links(text: str, articles: list[dict]) -> str:
    def replace(m):
        idx = int(m.group(1)) - 1
        if 0 <= idx < len(articles):
            url   = _esc(articles[idx].get("url", "#"))
            title = _esc(articles[idx].get("title", m.group(0)))
            return (f'<a href="{url}" style="color:{_RED};text-decoration:none;font-weight:600;" '
                    f'target="_blank">{title}</a>')
        return m.group(0)
    return re.sub(r"\[(\d+)\]", replace, text)


def _get_section_color(line: str):
    lower = line.lower()
    for key, color in _SECTION_COLORS.items():
        if key in lower:
            return color
    return None


def _logo_tag(height: int = 44) -> str:
    if _LOGO_FILE.exists():
        b64 = base64.b64encode(_LOGO_FILE.read_bytes()).decode()
        return f'<img src="data:image/png;base64,{b64}" height="{height}" alt="BSM" style="display:block;">'
    return f'<span style="color:{_RED};font-size:26px;font-weight:900;letter-spacing:1px;">BSM</span>'


def _img_tag(url: str, alt: str = "", width: int = 200) -> str:
    if not url:
        return ""
    safe_url = _esc(url)
    safe_alt = _esc(alt[:40])
    return (
        f'<img src="{safe_url}" alt="{safe_alt}" width="{width}" '
        f'style="width:{width}px;height:130px;object-fit:cover;border-radius:8px;'
        f'display:block;border:0;" />'
    )


# ── HTML builder ───────────────────────────────────────────

def _build_html(brief_text: str, articles: list[dict],
                display_date: str, first_name: str, from_name: str) -> str:

    article_count = len(articles)
    articles_with_img = [a for a in articles if a.get("image")]
    # Pick up to 3 hero article images for the top strip
    hero_articles = articles_with_img[:3]

    lines = brief_text.split("\n")

    # ── Wrapper & header ───────────────────────────────────
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
</head>
<body style="margin:0;padding:0;background:{_BG};font-family:Arial,Helvetica,sans-serif;">
<div style="max-width:640px;margin:0 auto;">

  <!-- ── TOP NAV BAR ── -->
  <div style="background:{_WHITE};padding:16px 28px;border-bottom:1px solid {_BORDER};">
    <table width="100%" cellpadding="0" cellspacing="0">
      <tr>
        <td style="vertical-align:middle;">{_logo_tag(44)}</td>
        <td style="vertical-align:middle;text-align:right;">
          <span style="font-size:11px;color:{_TEXT_META};letter-spacing:0.5px;">AI Intelligence Briefing</span>
        </td>
      </tr>
    </table>
  </div>

  <!-- ── RED HERO BANNER ── -->
  <div style="background:{_RED};padding:32px 28px 28px;">
    <p style="margin:0 0 6px;font-size:11px;color:rgba(255,255,255,0.7);letter-spacing:2px;text-transform:uppercase;">Boulder SEO Marketing</p>
    <h1 style="margin:0 0 10px;font-size:26px;font-weight:900;color:{_WHITE};line-height:1.2;letter-spacing:0.5px;">SEAN'S DAILY<br>AI UPDATES</h1>
    <p style="margin:0;font-size:13px;color:rgba(255,255,255,0.85);">{display_date}</p>
  </div>

  <!-- ── STATS BAR ── -->
  <div style="background:{_WHITE};border-bottom:3px solid {_RED};">
    <table width="100%" cellpadding="0" cellspacing="0">
      <tr>
        <td style="width:33%;padding:18px 0;text-align:center;border-right:1px solid {_BORDER};">
          <p style="margin:0;font-size:22px;font-weight:800;color:{_RED};">{article_count}</p>
          <p style="margin:4px 0 0;font-size:10px;color:{_TEXT_META};text-transform:uppercase;letter-spacing:1px;">Sources Reviewed</p>
        </td>
        <td style="width:33%;padding:18px 0;text-align:center;border-right:1px solid {_BORDER};">
          <p style="margin:0;font-size:22px;font-weight:800;color:{_RED};">9</p>
          <p style="margin:4px 0 0;font-size:10px;color:{_TEXT_META};text-transform:uppercase;letter-spacing:1px;">Brief Sections</p>
        </td>
        <td style="width:33%;padding:18px 0;text-align:center;">
          <p style="margin:0;font-size:22px;font-weight:800;color:{_RED};">Daily</p>
          <p style="margin:4px 0 0;font-size:10px;color:{_TEXT_META};text-transform:uppercase;letter-spacing:1px;">AI Intelligence</p>
        </td>
      </tr>
    </table>
  </div>

  <!-- ── GREETING ── -->
  <div style="background:{_WHITE};padding:24px 28px 0;">
    <p style="margin:0;font-size:15px;color:{_TEXT_BODY};line-height:1.6;">
      Hey <strong style="color:{_TEXT_HEAD};">{first_name}</strong>, here's your AI intelligence briefing for today 👇
    </p>
  </div>
"""

    # ── Hero image strip (if we have article images) ────────
    if hero_articles:
        cols = len(hero_articles)
        col_width = 186 if cols == 3 else (290 if cols == 2 else 584)
        html += f'\n  <!-- ── ARTICLE IMAGE STRIP ── -->\n'
        html += f'  <div style="background:{_WHITE};padding:20px 28px;">\n'
        html += f'  <table width="100%" cellpadding="0" cellspacing="0"><tr>\n'
        for i, a in enumerate(hero_articles):
            pad = "padding-left:8px;" if i > 0 else ""
            html += (
                f'    <td style="width:{col_width}px;vertical-align:top;{pad}">'
                f'<a href="{_esc(a["url"])}" target="_blank" style="text-decoration:none;">'
                f'{_img_tag(a["image"], a["title"], col_width)}'
                f'<p style="margin:8px 0 0;font-size:12px;font-weight:600;color:{_TEXT_HEAD};line-height:1.4;">'
                f'{_esc(a["title"][:60])}{"…" if len(a["title"])>60 else ""}</p>'
                f'<p style="margin:4px 0 0;font-size:11px;color:{_TEXT_META};">{_esc(a["source"])}</p>'
                f'</a></td>\n'
            )
        html += '  </tr></table>\n  </div>\n'

    # ── Section rendering ──────────────────────────────────
    cur_color    = None
    section_html = ""
    in_list      = False
    in_table     = False
    is_table_sec = False
    is_cards_sec = False
    is_footer_sec = False
    item_idx     = 0   # tracks article index for inline thumbnails

    def close_section():
        nonlocal html, section_html, in_list, in_table, cur_color
        if cur_color is None:
            return
        if in_list:  section_html += "</table>"
        if in_table: section_html += "</table>"
        html += section_html + "\n  </div>\n"
        section_html = ""
        cur_color = None

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if "sean's daily ai updates" in stripped.lower():
            continue

        color = _get_section_color(stripped)
        if color:
            close_section()
            cur_color    = color
            in_list      = False
            in_table     = False
            item_idx     = 0
            hdr          = re.sub(r"^#+\s*", "", stripped)
            is_table_sec  = "tool landscape" in hdr.lower()
            is_cards_sec  = "priority reading" in hdr.lower()
            is_footer_sec = "minute read" in hdr.lower()

            # Section card open
            html += (
                f'\n  <!-- {hdr} -->\n'
                f'  <div style="background:{_WHITE};margin-top:2px;padding:24px 28px;">\n'
            )
            # Section header row
            section_html = (
                f'<table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:16px;">'
                f'<tr>'
                f'<td><p style="margin:0;font-size:12px;font-weight:700;color:{_TEXT_META};'
                f'text-transform:uppercase;letter-spacing:1.5px;">'
                f'<span style="display:inline-block;width:8px;height:8px;border-radius:50%;'
                f'background:{color};margin-right:7px;vertical-align:middle;"></span>'
                f'{_esc(hdr)}</p></td>'
                f'</tr></table>'
                f'<hr style="border:none;border-top:1px solid {_BORDER};margin:0 0 16px;">'
            )
            continue

        if cur_color is None:
            continue

        content = re.sub(r"^-\s*", "", stripped)
        linked  = _refs_to_links(_esc(content), articles)

        # ── Table section (AI Tool Landscape) ──────────────
        if is_table_sec:
            colon = content.find(":")
            if colon > 0:
                label = _esc(content[:colon].strip())
                value = _refs_to_links(_esc(content[colon+1:].strip()), articles)
                if not in_table:
                    section_html += (
                        f'<table width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;">'
                        f'<tr style="background:{_BG};">'
                        f'<th style="padding:9px 12px;font-size:10px;color:{_TEXT_META};font-weight:700;'
                        f'text-align:left;border-bottom:2px solid {_RED};width:26%;text-transform:uppercase;letter-spacing:1px;">Category</th>'
                        f'<th style="padding:9px 12px;font-size:10px;color:{_TEXT_META};font-weight:700;'
                        f'text-align:left;border-bottom:2px solid {_RED};text-transform:uppercase;letter-spacing:1px;">Leader &amp; Notes</th>'
                        f'</tr>'
                    )
                    in_table = True
                row_bg = _WHITE if (section_html.count("<tr") % 2 == 0) else _BG
                section_html += (
                    f'<tr style="background:{row_bg};">'
                    f'<td style="padding:10px 12px;font-size:13px;color:{_TEXT_HEAD};font-weight:600;'
                    f'border-bottom:1px solid {_DIVIDER};vertical-align:top;">{label}</td>'
                    f'<td style="padding:10px 12px;font-size:14px;color:{_TEXT_BODY};'
                    f'border-bottom:1px solid {_DIVIDER};line-height:1.5;">{value}</td>'
                    f'</tr>'
                )
            continue

        # ── Cards section (Priority Reading) ───────────────
        if is_cards_sec:
            section_html += (
                f'<div style="border:1px solid {_BORDER};border-radius:8px;padding:14px 16px;'
                f'margin-bottom:10px;font-size:14px;line-height:1.65;color:{_TEXT_BODY};">'
                f'{linked}</div>'
            )
            continue

        # ── Footer section (2-minute read) ─────────────────
        if is_footer_sec:
            section_html += (
                f'<p style="margin:10px 0 0;font-size:15px;color:{_TEXT_BODY};'
                f'line-height:1.65;font-style:italic;">{linked}</p>'
            )
            continue

        # ── Standard article list with inline thumbnails ───
        if not in_list:
            section_html += '<table width="100%" cellpadding="0" cellspacing="0">'
            in_list = True

        # Try to attach a thumbnail from the matching article
        thumb_html = ""
        for a in articles:
            if a.get("image") and (
                _esc(a.get("title",""))[:30].lower() in linked.lower()
                or any(f"[{i+1}]" in line for i, x in enumerate(articles) if x is a)
            ):
                thumb_html = _img_tag(a["image"], a.get("title",""), 100)
                break

        # Row: thumbnail (if available) + text
        if thumb_html:
            section_html += (
                f'<tr><td style="padding:0 0 14px;">'
                f'<table width="100%" cellpadding="0" cellspacing="0"><tr>'
                f'<td style="width:108px;vertical-align:top;padding-right:14px;">{thumb_html}</td>'
                f'<td style="vertical-align:top;font-size:14px;line-height:1.65;color:{_TEXT_BODY};">{linked}</td>'
                f'</tr></table>'
                f'<hr style="border:none;border-top:1px solid {_DIVIDER};margin:0;">'
                f'</td></tr>'
            )
        else:
            section_html += (
                f'<tr><td style="padding:11px 0;border-bottom:1px solid {_DIVIDER};'
                f'font-size:14px;line-height:1.65;color:{_TEXT_BODY};">'
                f'{linked}</td></tr>'
            )
        item_idx += 1

    close_section()

    # ── Sign-off ───────────────────────────────────────────
    html += f"""
  <!-- ── SIGN-OFF ── -->
  <div style="background:{_RED};padding:28px 28px 24px;">
    <p style="margin:0 0 6px;font-size:15px;color:{_WHITE};line-height:1.6;">
      If you're building in SEO, AI, or automation — this is your edge.
    </p>
    <p style="margin:0;font-size:16px;font-weight:700;color:{_WHITE};">– {from_name}</p>
  </div>

  <!-- ── FOOTER ── -->
  <div style="background:#2a2a2a;padding:20px 28px;">
    <table width="100%" cellpadding="0" cellspacing="0">
      <tr>
        <td style="vertical-align:top;width:50%;">
          <p style="margin:0 0 4px;font-size:13px;font-weight:700;color:{_WHITE};">Boulder SEO Marketing</p>
          <p style="margin:0;font-size:12px;color:#aaaaaa;">boulderseomarketing.com</p>
        </td>
        <td style="vertical-align:top;text-align:right;">
          <p style="margin:0;font-size:11px;color:#888888;">Generated from {article_count} articles</p>
          <p style="margin:4px 0 0;font-size:11px;color:#666666;">AI Intelligence Officer</p>
        </td>
      </tr>
    </table>
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


def send_newsletter(subject: str, brief_text: str,
                    articles: list[dict], display_date: str) -> None:
    config    = json.loads(CONFIG_FILE.read_text())
    email_cfg = config["email"]
    smtp_user = os.environ["SMTP_USER"]
    smtp_pass = os.environ["SMTP_PASSWORD"]
    from_name = email_cfg.get("from_name", "Sean")

    for recipient in email_cfg["recipients"]:
        first_name = recipient.get("first_name", "there")

        msg = MIMEMultipart("alternative")
        msg["Subject"]  = subject
        msg["From"]     = f"{from_name} <{email_cfg['from_address']}>"
        msg["To"]       = recipient["email"]
        msg["Reply-To"] = email_cfg.get("reply_to", email_cfg["from_address"])

        plain = _build_plain(brief_text, first_name, from_name)
        html  = _build_html(brief_text, articles, display_date, first_name, from_name)

        msg.attach(MIMEText(plain, "plain"))
        msg.attach(MIMEText(html,  "html"))

        with smtplib.SMTP(email_cfg["smtp_host"], email_cfg["smtp_port"]) as server:
            server.ehlo()
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.sendmail(email_cfg["from_address"], recipient["email"], msg.as_string())

        print(f"  ✓ Sent to {recipient['email']}")
