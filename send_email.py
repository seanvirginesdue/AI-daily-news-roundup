"""
STEP 6 — Email Sender
Sends the finished newsletter via Gmail SMTP (App Password).
"""

import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import json
from pathlib import Path

CONFIG_FILE = Path(__file__).parent / "config.json"


def _load_config() -> dict:
    with open(CONFIG_FILE) as f:
        return json.load(f)


def _build_plain_body(first_name: str, newsletter_content: str, from_name: str) -> str:
    return f"""Hey {first_name},

Here's your AI update for today 👇

---

{newsletter_content}

---

If you're building in SEO, AI, or automation — this is your edge.

– {from_name}"""


def _build_html_body(first_name: str, newsletter_content: str, from_name: str) -> str:
    # Convert plain text markers to simple HTML
    import re
    html_content = newsletter_content

    # Bold headlines (lines starting with 🔥)
    html_content = re.sub(
        r"^(🔥.+)$",
        r"<h2 style='color:#1a1a1a;margin-top:24px'>\1</h2>",
        html_content,
        flags=re.MULTILINE,
    )

    # Section emoji headers
    for emoji, color in [("🧠", "#4a4aff"), ("📊", "#0a8a0a"), ("🚀", "#d45f00"), ("✅", "#007a7a")]:
        html_content = re.sub(
            rf"^({re.escape(emoji)}.+)$",
            rf"<p style='font-weight:600;color:{color};margin-top:16px'>\1</p>",
            html_content,
            flags=re.MULTILINE,
        )

    # Horizontal rules
    html_content = html_content.replace("---", "<hr style='border:none;border-top:1px solid #e5e5e5;margin:20px 0'>")

    # Wrap paragraphs
    paragraphs = html_content.split("\n\n")
    wrapped = "".join(
        p if p.strip().startswith("<") else f"<p style='line-height:1.6;color:#333'>{p.strip()}</p>"
        for p in paragraphs
        if p.strip()
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;max-width:600px;margin:0 auto;padding:20px 16px;background:#fff">

  <p style="color:#555;margin-bottom:24px">Hey {first_name},<br><br>
  Here's your AI update for today 👇</p>

  <hr style="border:none;border-top:1px solid #e5e5e5;margin:0 0 24px">

  {wrapped}

  <hr style="border:none;border-top:1px solid #e5e5e5;margin:24px 0">

  <p style="color:#555;font-size:14px">
    If you're building in SEO, AI, or automation — this is your edge.<br><br>
    – {from_name}
  </p>

</body>
</html>"""


def send_newsletter(subject: str, newsletter_content: str) -> None:
    """Send the newsletter to all recipients defined in config.json."""
    config = _load_config()
    email_cfg = config["email"]

    smtp_user = os.environ["SMTP_USER"]
    smtp_password = os.environ["SMTP_PASSWORD"]

    for recipient in email_cfg["recipients"]:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{email_cfg['from_name']} <{email_cfg['from_address']}>"
        msg["To"] = recipient["email"]
        msg["Reply-To"] = email_cfg.get("reply_to", email_cfg["from_address"])

        first_name = recipient.get("first_name", "there")
        from_name = email_cfg.get("from_name", "Sean")

        plain = _build_plain_body(first_name, newsletter_content, from_name)
        html = _build_html_body(first_name, newsletter_content, from_name)

        msg.attach(MIMEText(plain, "plain"))
        msg.attach(MIMEText(html, "html"))

        with smtplib.SMTP(email_cfg["smtp_host"], email_cfg["smtp_port"]) as server:
            server.ehlo()
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.sendmail(email_cfg["from_address"], recipient["email"], msg.as_string())

        print(f"  ✓ Sent to {recipient['email']}")
