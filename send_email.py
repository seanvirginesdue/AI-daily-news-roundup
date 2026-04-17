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

# Section header keyword → accent colour
_SECTION_COLORS = {
    "what's hot today":  "#e03c2f",
    "claude insider":    "#7c3aed",
    "ai tool landscape": "#d97706",
    "bsm must try":      "#d97706",
    "bsm sales angle":   "#059669",
    "what i'm testing":  "#2563eb",
    "industry watch":    "#7c3aed",
    "priority reading":  "#db2777",
    "2-minute read":     "#6b7280",
}


def _esc(t: str) -> str:
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _refs_to_links(text: str, articles: list[dict]) -> str:
    def replace(m):
        idx = int(m.group(1)) - 1
        if 0 <= idx < len(articles):
            url = _esc(articles[idx].get("url", "#"))
            title = _esc(articles[idx].get("title", m.group(0)))
            return f'<a href="{url}" style="color:#2563eb;text-decoration:none;border-bottom:1px solid #bfdbfe;" target="_blank">{title}</a>'
        return m.group(0)
    return re.sub(r"\[(\d+)\]", replace, text)


def _get_section_color(line: str) -> str | None:
    lower = line.lower()
    for key, color in _SECTION_COLORS.items():
        if key in lower:
            return color
    return None


# BSM logo built entirely in HTML/CSS — no image needed
_BSM_LOGO = """
<table cellpadding="0" cellspacing="0" border="0">
  <tr>
    <td style="padding-right:10px;vertical-align:middle;">
      <div style="width:36px;height:36px;background:#e03c2f;border-radius:7px;text-align:center;line-height:36px;">
        <span style="color:#fff;font-size:14px;font-weight:900;letter-spacing:-0.5px;">&#x2197;</span>
      </div>
    </td>
    <td style="vertical-align:middle;">
      <span style="color:#e03c2f;font-size:26px;font-weight:900;letter-spacing:1px;font-family:Arial,sans-serif;">BSM</span>
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
<body style="margin:0;padding:0;background:#f0ede8;font-family:Arial,Helvetica,sans-serif;">
<div style="max-width:640px;margin:0 auto;background:#f0ede8;padding:24px 16px;">

  <!-- BSM Header Card -->
  <div style="background:#ffffff;border-radius:12px;padding:20px 24px;margin-bottom:12px;border:1px solid #e8e4de;">
    <table width="100%" cellpadding="0" cellspacing="0">
      <tr>
        <td>{_BSM_LOGO}</td>
      </tr>
    </table>
  </div>

  <!-- Title Card -->
  <div style="background:#ffffff;border-radius:12px;padding:24px 28px;margin-bottom:12px;border:1px solid #e8e4de;">
    <p style="margin:0 0 4px;font-size:11px;letter-spacing:2px;color:#9ca3af;text-transform:uppercase;font-weight:600;">Boulder SEO Marketing</p>
    <h1 style="margin:6px 0 8px;font-size:22px;font-weight:800;color:#111827;letter-spacing:0.5px;">SEAN'S DAILY AI UPDATES</h1>
    <p style="margin:0;font-size:13px;color:#6b7280;">{display_date} &nbsp;&nbsp;|&nbsp;&nbsp; AI Intelligence Briefing</p>
  </div>

  <!-- Greeting -->
  <div style="padding:4px 4px 12px;">
    <p style="margin:0;font-size:14px;color:#374151;">Hey <strong>{first_name}</strong>, here's your AI intelligence briefing for today 👇</p>
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
                section_html = f'<div style="background:#ffffff;border-radius:12px;padding:20px 24px;margin-bottom:12px;border:1px solid #e8e4de;border-top:3px solid {color};">'
                section_html += f'<p style="margin:0;font-size:13px;font-weight:700;color:{color};text-transform:uppercase;letter-spacing:1px;">{_esc(hdr)}</p>'
            else:
                section_html = f'<div style="background:#ffffff;border-radius:12px;padding:20px 24px;margin-bottom:12px;border:1px solid #e8e4de;border-left:4px solid {color};">'
                section_html += f'<p style="margin:0 0 14px;font-size:13px;font-weight:700;color:{color};text-transform:uppercase;letter-spacing:1px;">{_esc(hdr)}</p>'
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
                        '<tr style="background:#f9fafb;">'
                        '<th style="padding:8px 12px;font-size:11px;color:#6b7280;font-weight:600;text-align:left;border-bottom:1px solid #e5e7eb;width:28%;">CATEGORY</th>'
                        '<th style="padding:8px 12px;font-size:11px;color:#6b7280;font-weight:600;text-align:left;border-bottom:1px solid #e5e7eb;">LEADER &amp; NOTES</th>'
                        '</tr>'
                    )
                    in_table = True
                row_bg = '#ffffff' if (section_html.count('<tr') % 2 == 0) else '#f9fafb'
                section_html += (
                    f'<tr style="background:{row_bg};">'
                    f'<td style="padding:9px 12px;font-size:12px;color:#374151;font-weight:600;border-bottom:1px solid #f3f4f6;vertical-align:top;">{label}</td>'
                    f'<td style="padding:9px 12px;font-size:13px;color:#4b5563;border-bottom:1px solid #f3f4f6;">{value}</td>'
                    f'</tr>'
                )
            continue

        # Cards section (Priority Reading)
        if is_cards_section:
            section_html += (
                f'<div style="background:#f9fafb;border:1px solid #e5e7eb;border-radius:8px;'
                f'padding:12px 16px;margin-bottom:8px;font-size:13px;line-height:1.65;color:#374151;">'
                f'{linked}</div>'
            )
            continue

        # Footer section (2-minute read)
        if is_footer:
            section_html += f'<p style="margin:10px 0 0;font-size:14px;color:#374151;line-height:1.6;">{linked}</p>'
            continue

        # Standard list
        if not in_list:
            section_html += '<ul style="margin:0;padding-left:0;list-style:none;">'
            in_list = True
        section_html += (
            f'<li style="padding:8px 0;border-bottom:1px solid #f3f4f6;font-size:13px;'
            f'line-height:1.6;color:#374151;display:flex;gap:8px;">'
            f'<span style="color:#d1d5db;flex-shrink:0;">›</span>'
            f'<span>{linked}</span></li>'
        )

    close_section()

    # ── Sign-off card ──────────────────────────────────────────
    article_count = len(articles)
    html += f"""
  <!-- Sign-off -->
  <div style="background:#ffffff;border-radius:12px;padding:20px 24px;margin-bottom:12px;border:1px solid #e8e4de;">
    <p style="margin:0 0 8px;font-size:14px;color:#374151;">If you're building in SEO, AI, or automation — this is your edge.</p>
    <p style="margin:0;font-size:14px;color:#111827;font-weight:700;">– {from_name}</p>
  </div>

  <!-- Footer -->
  <div style="text-align:center;padding:12px 0 8px;">
    <p style="margin:0;font-size:11px;color:#9ca3af;">Generated from {article_count} articles &nbsp;·&nbsp; Boulder SEO Marketing</p>
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
