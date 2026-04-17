"""
Email sender — dark professional HTML template styled after Harold's Daily AI Updates.
Sends plain + HTML multipart via Gmail SMTP.
"""

import os
import re
import smtplib
import json
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

CONFIG_FILE = Path(__file__).parent / "config.json"

# Section header → (accent colour, background, content type)
_SECTION_STYLES = {
    "what's hot today":   ("#ff6b6b", "#2a1a1a", "list"),
    "claude insider":     ("#a78bfa", "#1a1a2e", "list"),
    "ai tool landscape":  ("#fbbf24", "#2a2a1a", "table"),
    "bsm must try":       ("#f59e0b", "#2a2418", "list"),
    "bsm sales angle":    ("#34d399", "#1a2a1a", "list"),
    "what i'm testing":   ("#60a5fa", "#1a1a2a", "list"),
    "industry watch":     ("#a78bfa", "#1e1a2a", "list"),
    "priority reading":   ("#f472b6", "#2a1a22", "cards"),
    "2-minute read":      ("#9ca3af", "none",    "footer"),
}


def _esc(t: str) -> str:
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _refs_to_links(text: str, articles: list[dict]) -> str:
    def replace(m):
        idx = int(m.group(1)) - 1
        if 0 <= idx < len(articles):
            url = _esc(articles[idx].get("url", "#"))
            title = _esc(articles[idx].get("title", m.group(0)))
            return f'<a href="{url}" style="color:#4da6ff;text-decoration:underline;" target="_blank">{title}</a>'
        return m.group(0)
    return re.sub(r"\[(\d+)\]", replace, text)


def _get_section_style(line: str):
    lower = line.lower()
    for key, style in _SECTION_STYLES.items():
        if key in lower:
            return style
    return None


def _build_html(brief_text: str, articles: list[dict], display_date: str, first_name: str, from_name: str) -> str:
    lines = brief_text.split("\n")

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Sean's Daily AI Updates</title>
</head>
<body style="margin:0;padding:0;background:#0a0a14;font-family:Arial,Helvetica,sans-serif;">
<div style="max-width:640px;margin:0 auto;background:#0f0f1a;color:#e0e0e0;">

  <!-- Header -->
  <div style="background:linear-gradient(135deg,#1a1a2e 0%,#16213e 50%,#0f3460 100%);padding:32px 24px;text-align:center;">
    <p style="margin:0 0 6px;font-size:11px;letter-spacing:3px;color:#8892b0;text-transform:uppercase;">Boulder SEO Marketing</p>
    <h1 style="margin:0;font-size:22px;font-weight:700;color:#ffffff;letter-spacing:2px;">SEAN'S DAILY AI UPDATES</h1>
    <p style="margin:10px 0 0;color:#8892b0;font-size:13px;">{display_date} &nbsp;|&nbsp; AI Intelligence Briefing</p>
  </div>

  <!-- Greeting -->
  <div style="padding:20px 24px 0;">
    <p style="margin:0;font-size:14px;color:#9ca3af;">Hey {first_name}, here's your AI intelligence briefing for today 👇</p>
  </div>

  <!-- Sections -->
  <div style="padding:12px 24px 24px;">
"""

    cur_color = None
    cur_bg = None
    cur_type = None
    section_html = ""
    in_content = False

    def close_section():
        nonlocal html, section_html, in_content, cur_type
        if cur_color is None:
            return
        if in_content:
            if cur_type == "table":
                section_html += "</table>"
            elif cur_type == "cards":
                section_html += "</div>"
            else:
                section_html += "</ul>"
            in_content = False
        html += section_html + "</div></div>\n"
        section_html = ""

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        # Skip duplicate title line
        if "sean's daily ai updates" in stripped.lower():
            continue

        style = _get_section_style(stripped)
        if style:
            close_section()
            color, bg, stype = style
            cur_color, cur_bg, cur_type = color, bg, stype
            in_content = False

            hdr_clean = re.sub(r"^#+\s*", "", stripped)

            if stype == "footer":
                html += f'<div style="text-align:center;padding:16px;color:#9ca3af;font-size:13px;border-top:1px solid #2a2a3a;margin-top:8px;">{_esc(hdr_clean)}</div>\n'
                cur_color = None
                continue

            bg_style = f"background:{bg};" if bg != "none" else ""
            html += f'<div style="{bg_style}border-left:4px solid {color};border-radius:8px;margin:12px 0;">\n'
            section_html = f'<div style="padding:16px 20px;"><h3 style="color:{color};font-size:14px;font-weight:700;margin:0 0 12px;letter-spacing:0.5px;">{_esc(hdr_clean)}</h3>\n'
            continue

        if cur_color is None:
            continue

        # Strip leading bullet marker
        content = re.sub(r"^-\s*", "", stripped)
        linked = _refs_to_links(_esc(content), articles)

        if cur_type == "table":
            colon = content.find(":")
            if colon > 0:
                label = _esc(content[:colon].strip())
                value = _refs_to_links(_esc(content[colon+1:].strip()), articles)
                if not in_content:
                    section_html += '<table style="width:100%;border-collapse:collapse;">'
                    in_content = True
                section_html += (
                    f'<tr style="border-bottom:1px solid #2a2a3a;">'
                    f'<td style="padding:8px 12px;color:#9ca3af;font-size:12px;white-space:nowrap;vertical-align:top;width:30%;">{label}</td>'
                    f'<td style="padding:8px 12px;color:#e0e0e0;font-size:13px;">{value}</td>'
                    f'</tr>'
                )
            else:
                if not in_content:
                    section_html += '<ul style="margin:0;padding-left:18px;">'
                    in_content = True
                section_html += f'<li style="margin-bottom:8px;line-height:1.6;font-size:13px;">{linked}</li>'

        elif cur_type == "cards":
            if not in_content:
                section_html += "<div>"
                in_content = True
            section_html += (
                f'<div style="background:#1a1218;border:1px solid #3a2030;border-radius:6px;padding:12px 16px;margin:8px 0;">'
                f'<span style="font-size:13px;line-height:1.6;">{linked}</span>'
                f'</div>'
            )
        else:
            if not in_content:
                section_html += '<ul style="margin:0;padding-left:18px;">'
                in_content = True
            section_html += f'<li style="margin-bottom:8px;line-height:1.6;font-size:13px;">{linked}</li>'

    close_section()

    article_count = len(articles)
    html += f"""
  </div>

  <!-- Footer -->
  <div style="background:#0a0a14;border-top:1px solid #1e1e2e;padding:20px 24px;text-align:center;">
    <p style="margin:0 0 6px;font-size:14px;color:#e0e0e0;">If you're building in SEO, AI, or automation — this is your edge.</p>
    <p style="margin:0 0 16px;font-size:14px;color:#9ca3af;">– {from_name}</p>
    <p style="margin:0;font-size:11px;color:#4a4a5a;">Generated from {article_count} articles &nbsp;|&nbsp; Boulder SEO Marketing</p>
  </div>

</div>
</body>
</html>"""

    return html


def _build_plain(brief_text: str, first_name: str, from_name: str) -> str:
    return f"""Hey {first_name},

Here's your AI intelligence briefing for today 👇

---

{brief_text}

---

If you're building in SEO, AI, or automation — this is your edge.

– {from_name}"""


def send_newsletter(subject: str, brief_text: str, articles: list[dict], display_date: str) -> None:
    config = json.loads((CONFIG_FILE).read_text())
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
        html = _build_html(brief_text, articles, display_date, first_name, from_name)

        msg.attach(MIMEText(plain, "plain"))
        msg.attach(MIMEText(html, "html"))

        with smtplib.SMTP(email_cfg["smtp_host"], email_cfg["smtp_port"]) as server:
            server.ehlo()
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.sendmail(email_cfg["from_address"], recipient["email"], msg.as_string())

        print(f"  ✓ Sent to {recipient['email']}")
