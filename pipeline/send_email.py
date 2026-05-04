"""
Email sender — Micro SEO daily intelligence.
Table-based layout, inline CSS, Gmail-compatible. Max width: 600px.
"""

import os, smtplib, json
from datetime import date as _date
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import parseaddr
from pathlib import Path

CONFIG_FILE = Path(__file__).parent.parent / "config.json"
_LOGO_FILE  = Path(__file__).parent.parent / "assets" / "bsm_logo.png"

_LAUNCH = _date(2026, 3, 17)

def _issue_num() -> str:
    delta = (_date.today() - _LAUNCH).days + 1
    return f"#{delta:03d}"

# ── Design system ──────────────────────────────────────────────────────────────
_WHITE   = "#FFFFFF"
_CANVAS  = "#C9C9CE"
_PG_BG   = "#F4F4F5"
_BDR     = "#E4E4E7"
_H_TEXT  = "#09090B"
_B_TEXT  = "#52525B"
_M_TEXT  = "#A1A1AA"
_ACC     = "#6366F1"   # indigo — build
_GREEN   = "#10B981"   # green  — pitch / opportunity
_RED     = "#EF4444"   # red    — kill / risk
_FONT    = "-apple-system,BlinkMacSystemFont,'Segoe UI','Helvetica Neue',Arial,sans-serif"
_SERIF   = "Lora,Georgia,'Times New Roman',serif"

_N2W = {
    0:"zero",1:"one",2:"two",3:"three",4:"four",5:"five",6:"six",7:"seven",
    8:"eight",9:"nine",10:"ten",11:"eleven",12:"twelve",13:"thirteen",
    14:"fourteen",15:"fifteen",16:"sixteen",17:"seventeen",18:"eighteen",
    19:"nineteen",20:"twenty",21:"twenty-one",22:"twenty-two",
}

def _esc(t: str) -> str:
    return str(t).replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")

def _logo(h: int = 32) -> str:
    if _LOGO_FILE.exists():
        return f'<img src="cid:bsm_logo" height="{h}" style="display:block;" alt="Micro SEO">'
    return (f'<span style="font-size:18px;font-weight:900;color:{_H_TEXT};'
            f'font-family:{_FONT};">Micro</span>'
            f'<span style="font-size:18px;font-style:italic;font-weight:400;'
            f'color:{_ACC};font-family:{_SERIF};"> SEO</span>')


# Daily-rotating GIFs — one per day, cycles through the list (all verified)
_DAILY_GIFS = [
    ("https://media.giphy.com/media/DrJm6F9poo4aA/giphy.gif",        "Wake up coffee"),
    ("https://media.giphy.com/media/tD2jaMOEBFXel9Yp5Z/giphy.gif",   "Let's go work"),
    ("https://media.giphy.com/media/dxJ80m2xjh9TlqwzDi/giphy.gif",   "Monday motivation"),
    ("https://media.giphy.com/media/oQIwgd77gZJtuwBcxQ/giphy.gif",   "Typing fast"),
    ("https://media.giphy.com/media/sfxlOSTXORjOobH2QG/giphy.gif",   "High five"),
    ("https://media.giphy.com/media/UKF08uKqWch0Y/giphy.gif",        "This is fine"),
    ("https://media.giphy.com/media/U4DswrBiaz0p67ZweH/giphy.gif",   "Celebration"),
]


# ── Shared email renderer ──────────────────────────────────────────────────────
def _render_email(brief_data: dict, articles: list, display_date: str,
                  first_name: str, from_name: str, max_moves: int = 3) -> str:

    ts  = brief_data.get("top_story", {})
    tms = brief_data.get("three_moves", [])

    headline   = _esc(ts.get("headline", "Today's top AI story"))
    subtext    = _esc(ts.get("subtext", ""))
    field_note = _esc(ts.get("field_note", ""))

    _gif_url, _gif_alt = _DAILY_GIFS[_date.today().toordinal() % len(_DAILY_GIFS)]

    # Resolve article URLs from LLM-returned index references
    top_reads = brief_data.get("top_reads", [])
    def _resolve_read(read: dict) -> dict:
        idx = read.get("article_index", 0) - 1
        url = articles[idx].get("url", "#") if 0 <= idx < len(articles) else "#"
        return {**read, "url": url}
    top_reads = [_resolve_read(r) for r in top_reads[:3]]
    if not top_reads and articles:
        top_reads = [{"title": a["title"], "source": a["source"], "url": a["url"], "bsm_note": ""} for a in articles[:3]]

    top_url = (top_reads[0].get("url", "#") if top_reads else
               (articles[0].get("url", "#") if articles else "#"))

    reads_display = list(top_reads[1:])
    _used = {top_url} | {r.get("url", "") for r in reads_display}
    for _a in articles:
        if len(reads_display) >= 3:
            break
        _u = _a.get("url", "")
        if _u in _used:
            continue
        reads_display.append({"title": _a["title"], "source": _a["source"], "url": _u, "bsm_note": ""})
        _used.add(_u)
    reads_display = reads_display[:3]

    move_colors = {"pitch": _GREEN, "build": _ACC, "kill": _RED}
    move_labels = {"pitch": "PITCH", "build": "BUILD", "kill": "KILL"}
    issue = _issue_num()
    try:
        from datetime import datetime as _dt
        _d = _dt.strptime(display_date, "%A, %B %d, %Y")
        short_date = _d.strftime("%A, %b ") + str(_d.day)
    except Exception:
        short_date = display_date


    # ── OPEN ───────────────────────────────────────────────────────────────────
    H = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
@import url('https://fonts.googleapis.com/css2?family=Lora:ital,wght@0,400;0,700;1,400;1,600&display=swap');
</style>
</head>
<body style="margin:0;padding:0;background:{_CANVAS};font-family:{_FONT};">
<div style="display:none;max-height:0;overflow:hidden;mso-hide:all;opacity:0;">Today: {headline} &mdash; See what Micro SEO should do before noon.</div>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:{_CANVAS};">
<tr><td align="center" style="padding:32px 16px 48px;">
<table role="presentation" width="600" cellpadding="0" cellspacing="0"
  style="max-width:600px;width:100%;background:{_WHITE};border-radius:16px;
  overflow:hidden;box-shadow:0 8px 40px rgba(0,0,0,0.18),0 2px 8px rgba(0,0,0,0.10);">
<tr><td>
"""

    # ── 1. HEADER ──────────────────────────────────────────────────────────────
    H += f"""
  <table width="100%" cellpadding="0" cellspacing="0"
    style="background:{_WHITE};border-bottom:1px solid {_BDR};">
  <tr>
    <td style="padding:20px 24px;vertical-align:middle;">
      <span style="font-size:18px;font-weight:900;color:{_H_TEXT};
        font-family:{_FONT};letter-spacing:-0.4px;">Micro</span><span
        style="font-size:18px;font-style:italic;font-weight:400;color:{_ACC};
        font-family:{_SERIF};">&nbsp;SEO</span>
    </td>
    <td style="padding:20px 24px;text-align:right;vertical-align:middle;">
      <p style="margin:0 0 2px;font-size:10px;font-weight:600;color:{_M_TEXT};
        font-family:{_FONT};letter-spacing:0.5px;">{_esc(issue)}</p>
      <p style="margin:0;font-size:12px;font-style:italic;color:{_B_TEXT};
        font-family:{_SERIF};">{_esc(short_date)}</p>
    </td>
  </tr>
  <tr><td colspan="2"
    style="padding:10px 24px 12px;border-top:1px solid {_BDR};">
    <p style="margin:0;font-size:13px;font-style:italic;color:{_B_TEXT};
      font-family:{_SERIF};line-height:1.5;">Good morning. Here&rsquo;s what changed
      overnight and what to do about it.</p>
  </td></tr>
  </table>
"""

    # ── 2. PRIMARY INSIGHT (single column) ─────────────────────────────────────
    H += f"""
  <table width="100%" cellpadding="0" cellspacing="0"
    style="background:{_WHITE};border-bottom:1px solid {_BDR};">
  <tr><td style="padding:16px 24px 0 24px;line-height:0;font-size:0;">
    <img src="{_gif_url}"
      alt="Illustration representing rapid changes and uncertainty in AI-generated search results"
      width="552"
      style="display:block;width:100%;height:220px;border-radius:12px;
      object-fit:cover;object-position:center center;" />
  </td></tr>
  <tr><td style="padding:20px 24px 32px 24px;">
    <p style="margin:0 0 8px;">
      <span style="font-size:10px;font-weight:700;color:{_M_TEXT};
        text-transform:uppercase;letter-spacing:2px;
        font-family:{_FONT};">One Thing That Matters Today</span>
    </p>
    <p style="margin:0 0 16px;font-size:26px;font-weight:700;color:{_H_TEXT};
      line-height:1.25;letter-spacing:-0.3px;font-family:{_SERIF};">
      <a href="{_esc(top_url)}" target="_blank"
        style="color:{_H_TEXT};text-decoration:none;">{headline}</a>
    </p>
    <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:16px;">
    <tr>
      <td width="3" style="background:{_ACC};border-radius:2px;">&nbsp;</td>
      <td style="padding:8px 12px;">
        <p style="margin:0;font-size:13px;font-weight:600;color:{_H_TEXT};
          line-height:1.55;font-family:{_FONT};">{field_note}</p>
      </td>
    </tr>
    </table>
    <p style="margin:0 0 20px;font-size:14px;color:{_B_TEXT};line-height:1.7;
      font-family:{_FONT};">{subtext}</p>
    <table cellpadding="0" cellspacing="0">
    <tr><td style="background:{_ACC};border-radius:6px;">
      <a href="{_esc(top_url)}" target="_blank"
        aria-label="Read full article: {headline}"
        style="display:inline-block;padding:12px 24px;font-size:13px;
        font-weight:600;color:#ffffff;text-decoration:none;
        font-family:{_FONT};letter-spacing:0.2px;">Read Full Article &rarr;</a>
    </td></tr>
    </table>
  </td></tr>
  </table>
"""

    # ── 3. KEY INSIGHTS (stacked, one per move) ────────────────────────────────
    for move in tms[:max_moves]:
        mtitle = _esc(move.get("title", ""))
        mdesc  = _esc(move.get("description", ""))
        if not mtitle:
            continue
        H += f"""
  <table width="100%" cellpadding="0" cellspacing="0"
    style="background:{_WHITE};border-top:1px solid {_BDR};">
  <tr><td style="padding:24px;">
    <table width="100%" cellpadding="0" cellspacing="0"><tr>
      <td width="3" valign="top"
        style="background:{_ACC};border-radius:2px;padding:0;line-height:1;">&nbsp;</td>
      <td style="padding:0 0 0 14px;">
        <p style="margin:0 0 8px;">
          <span style="font-size:10px;font-weight:700;color:{_M_TEXT};
            text-transform:uppercase;letter-spacing:2px;
            font-family:{_FONT};">Key Insight</span>
        </p>
        <p style="margin:0 0 10px;font-size:16px;font-weight:700;color:{_H_TEXT};
          line-height:1.35;font-family:{_SERIF};">{mtitle}</p>
        <p style="margin:0;font-size:14px;color:{_B_TEXT};line-height:1.65;
          font-family:{_FONT};">{mdesc}</p>
      </td>
    </tr></table>
  </td></tr>
  </table>
"""

    # ── 7. FOOTER ──────────────────────────────────────────────────────────────
    H += f"""
  <table width="100%" cellpadding="0" cellspacing="0"
    style="background:{_PG_BG};border-top:1px solid {_BDR};">
  <tr><td style="padding:24px 24px 28px;">
    <div style="margin-bottom:10px;">{_logo(28)}</div>
    <p style="margin:0 0 4px;font-size:12px;color:{_M_TEXT};font-family:{_FONT};">
      AI-powered daily intelligence for the team
    </p>
    <p style="margin:0 0 16px;font-size:12px;color:{_M_TEXT};font-family:{_FONT};">
      Boulder, Colorado &nbsp;&middot;&nbsp; boulderseomarketing.com
      &nbsp;&middot;&nbsp; {_esc(display_date)}
    </p>
    <p style="margin:0 0 8px;font-size:12px;color:{_M_TEXT};font-family:{_FONT};">
      <a href="mailto:sean@boulderseomarketing.com?subject=Unsubscribe"
        style="color:{_M_TEXT};text-decoration:underline;">Unsubscribe</a>
      &nbsp;&middot;&nbsp;
      <a href="mailto:sean@boulderseomarketing.com?subject=Manage+Preferences"
        style="color:{_M_TEXT};text-decoration:underline;">Manage Preferences</a>
    </p>
    <p style="margin:0;font-size:12px;color:{_M_TEXT};font-family:{_FONT};">
      Reply to share feedback or flag a story for the team.
    </p>
  </td></tr>
  </table>

</td></tr>
</table>

</td></tr>
</table>
</body>
</html>"""

    return H


def _build_html(brief_data: dict, articles: list, display_date: str,
                first_name: str, from_name: str) -> str:
    return _render_email(brief_data, articles, display_date, first_name, from_name, max_moves=3)


def _build_html_tier2(brief_data: dict, articles: list, display_date: str,
                      first_name: str, from_name: str) -> str:
    return _render_email(brief_data, articles, display_date, first_name, from_name, max_moves=2)


def _build_plain(brief_data: dict, first_name: str, from_name: str) -> str:
    ts = brief_data.get("top_story", {}) if isinstance(brief_data, dict) else {}
    headline = ts.get("headline", "") if ts else str(brief_data)[:200]
    return (f"Hey {first_name},\n\nToday's top story: {headline}\n\n"
            f"---\n\n"
            f"If you're building in SEO, AI, or automation — this is your edge.\n\n"
            f"- {from_name}\nMicro SEO")


def _send_resend(subject: str, from_str: str, to: str, reply_to: str,
                 html: str, plain: str, logo_data: bytes | None) -> None:
    import resend, base64
    resend.api_key = os.environ["RESEND_API_KEY"]
    params: dict = {
        "from":     from_str,
        "to":       [to],
        "reply_to": reply_to,
        "subject":  subject,
        "html":     html,
        "text":     plain,
    }
    if logo_data:
        params["attachments"] = [{
            "filename":   "bsm_logo.png",
            "content":    base64.b64encode(logo_data).decode(),
            "content_id": "bsm_logo",
        }]
    resend.Emails.send(params)


def _send_smtp(subject: str, from_str: str, to: str, reply_to: str,
               html: str, plain: str, logo_data: bytes | None,
               smtp_host: str, smtp_port: int) -> None:
    related = MIMEMultipart("related")
    alt = MIMEMultipart("alternative")
    alt.attach(MIMEText(plain, "plain"))
    alt.attach(MIMEText(html,  "html"))
    related.attach(alt)
    if logo_data:
        img = MIMEImage(logo_data, "png")
        img.add_header("Content-ID", "<bsm_logo>")
        img.add_header("Content-Disposition", "inline", filename="bsm_logo.png")
        related.attach(img)
    related["Subject"]  = subject
    related["From"]     = from_str
    related["To"]       = to
    related["Reply-To"] = reply_to
    with smtplib.SMTP(smtp_host, smtp_port) as s:
        s.ehlo(); s.starttls()
        s.login(os.environ["SMTP_USER"], os.environ["SMTP_PASSWORD"])
        _, sender_addr = parseaddr(from_str)
        s.sendmail(sender_addr, to, related.as_string())


def send_newsletter(subject: str, brief_data: dict,
                    articles: list, display_date: str,
                    tier1_recipients: list | None = None,
                    tier2_recipients: list | None = None,
                    tier2_brief: dict | None = None,
                    tier2_subject: str | None = None) -> None:
    config    = json.loads(CONFIG_FILE.read_text())
    ec        = config.get("email", {})
    if not ec.get("from_address"):
        raise ValueError("config.json missing email.from_address")
    from_name  = ec.get("from_name", "Sean")
    from_str   = f"{from_name} <{ec['from_address']}>"
    reply_to   = ec.get("reply_to", ec["from_address"])
    logo_data  = _LOGO_FILE.read_bytes() if _LOGO_FILE.exists() else None
    use_resend = bool(os.environ.get("RESEND_API_KEY"))
    smtp_host  = ec.get("smtp_host", "smtp.gmail.com")
    smtp_port  = ec.get("smtp_port", 587)

    t1 = tier1_recipients if tier1_recipients is not None else ec.get("recipients", [])
    t2 = tier2_recipients or []

    if not t1 and not t2:
        raise ValueError("config.json missing email.recipients")

    # Tier 1 — full newsletter (3 moves)
    for recip in t1:
        fn    = recip.get("first_name", "there")
        to    = recip["email"]
        html  = _build_html(brief_data, articles, display_date, fn, from_name)
        plain = _build_plain(brief_data, fn, from_name)
        if use_resend:
            _send_resend(subject, from_str, to, reply_to, html, plain, logo_data)
        else:
            _send_smtp(subject, from_str, to, reply_to, html, plain, logo_data,
                       smtp_host, smtp_port)
        print(f"  ✓ Sent to {to} (Tier 1 — Research)")

    # Tier 2 — team digest (2 moves)
    if t2 and tier2_brief:
        t2_subj = tier2_subject or subject
        for recip in t2:
            fn    = recip.get("first_name", "there")
            to    = recip["email"]
            html  = _build_html_tier2(tier2_brief, articles, display_date, fn, from_name)
            plain = _build_plain(tier2_brief, fn, from_name)
            if use_resend:
                _send_resend(t2_subj, from_str, to, reply_to, html, plain, logo_data)
            else:
                _send_smtp(t2_subj, from_str, to, reply_to, html, plain, logo_data,
                           smtp_host, smtp_port)
            print(f"  ✓ Sent to {to} (Tier 2 — Team Digest)")
