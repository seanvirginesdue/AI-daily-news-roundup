"""
Email sender — Micro SEO daily intelligence.
Table-based layout, inline CSS, Gmail-compatible. Max width: 600px.
"""

import hashlib
import hmac
import os
import smtplib
import json
from datetime import date as _date
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import parseaddr
from pathlib import Path
from urllib.parse import urlencode

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
_H_TEXT  = "#111111"
_B_TEXT  = "#666666"
_M_TEXT  = "#A1A1AA"
_ACC     = "#E5484D"   # BSM brand red
_ACC2    = "#C93C40"   # BSM brand red — dark
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


def _prefs_url(email: str) -> str:
    try:
        cfg     = json.loads(CONFIG_FILE.read_text())
        secret  = cfg.get("preferences_secret", "")
        base    = cfg.get("preferences_url", "")
        if not secret or not base:
            return f"mailto:{email}?subject=Manage+Preferences"
        token = hmac.new(secret.encode(), email.encode(), hashlib.sha256).hexdigest()[:24]
        return f"{base}/preferences?{urlencode({'email': email, 'token': token})}"
    except Exception:
        return f"mailto:{email}?subject=Manage+Preferences"


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
def _source_color(source: str) -> str:
    return _ACC


def _render_email(brief_data: dict, articles: list, display_date: str,
                  first_name: str, from_name: str, max_moves: int = 3,
                  prefs_url: str = "") -> str:

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
        if 0 <= idx < len(articles):
            url = articles[idx].get("url", "#")
            img = articles[idx].get("image", "")
        else:
            url, img = "#", ""
        return {**read, "url": url, "image": img}
    top_reads = [_resolve_read(r) for r in top_reads[:3]]
    if not top_reads and articles:
        top_reads = [
            {"title": a["title"], "source": a["source"], "url": a["url"],
             "bsm_note": "", "image": a.get("image", "")}
            for a in articles[:3]
        ]

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
        reads_display.append({"title": _a["title"], "source": _a["source"], "url": _u,
                              "bsm_note": "", "image": _a.get("image", "")})
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
<style>@import url('https://fonts.googleapis.com/css2?family=Lora:ital,wght@0,400;0,700;1,400;1,600&display=swap');
@media only screen and (max-width:600px){{.thumb-img{{width:100% !important;height:auto !important;border-radius:10px 10px 0 0 !important;}}}}</style>
</head>
<body style="margin:0;padding:0;background:{_CANVAS};font-family:{_FONT};">
<div style="display:none;max-height:0;overflow:hidden;mso-hide:all;opacity:0;">Today: {headline} &mdash; See what Micro SEO should do before noon.</div>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:{_CANVAS};">
<tr><td align="center" style="padding:32px 16px 48px;">
<table role="presentation" width="600" cellpadding="0" cellspacing="0"
  style="max-width:600px;width:100%;background:{_WHITE};border-radius:16px;overflow:hidden;
  box-shadow:0 8px 40px rgba(0,0,0,0.18),0 2px 8px rgba(0,0,0,0.10);">
<tr><td>
"""

    # ── 1. HEADER (indigo background) ──────────────────────────────────────────
    H += f"""
  <table width="100%" cellpadding="0" cellspacing="0" style="background:linear-gradient(135deg,{_ACC},{_ACC2});">
  <tr><td style="padding:24px 28px 22px;">
    <table width="100%" cellpadding="0" cellspacing="0"><tr>
      <td align="right">
        <span style="display:inline-block;background:rgba(0,0,0,0.22);color:#ffffff;
          padding:5px 14px;border-radius:999px;font-size:11px;font-weight:600;
          font-family:{_FONT};">{_esc(short_date)}</span>
      </td>
    </tr></table>
    <p style="margin:18px 0 5px;font-size:26px;font-weight:700;color:#ffffff;font-family:{_SERIF};line-height:1.2;">AI Daily Brief</p>
    <p style="margin:0;font-size:13px;color:rgba(255,255,255,0.72);font-family:{_FONT};">What changed overnight and what Boulder SEO Marketing does about it.</p>
  </td></tr>
  </table>
"""

    # ── 2. HERO: two-column (GIF left + story right) ───────────────────────────
    H += f"""
  <table width="100%" cellpadding="0" cellspacing="0" style="background:{_WHITE};">
  <tr><td style="padding:20px 24px 12px;">
    <p style="margin:0;font-size:11px;font-weight:700;color:{_M_TEXT};
      text-transform:uppercase;letter-spacing:2px;font-family:{_FONT};">&#128276;&nbsp;&nbsp;Today&rsquo;s Top Story</p>
  </td></tr>
  <tr><td style="padding:0 24px 24px;">
    <table width="100%" cellpadding="0" cellspacing="0"
      style="border:1px solid {_BDR};border-radius:12px;overflow:hidden;">
    <tr valign="top">
      <td width="240" style="width:240px;background:{_ACC};
        background-image:url('{_gif_url}');background-size:cover;
        background-position:center;padding:0;vertical-align:top;
        font-size:0;line-height:0;">&nbsp;</td>
      <td valign="top" style="padding:20px;border-left:1px solid {_BDR};vertical-align:top;">
        <p style="margin:0 0 12px;font-size:17px;font-weight:700;color:{_H_TEXT};
          line-height:1.3;font-family:{_SERIF};">
          <a href="{_esc(top_url)}" target="_blank"
            style="color:{_H_TEXT};text-decoration:none;">{headline}</a>
        </p>
        <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:12px;">
        <tr>
          <td width="3" style="background:{_ACC};border-radius:2px;">&nbsp;</td>
          <td style="padding:6px 10px;font-size:12px;font-weight:600;color:{_H_TEXT};
            line-height:1.5;font-family:{_FONT};">{field_note}</td>
        </tr>
        </table>
        <p style="margin:0 0 16px;font-size:13px;color:{_B_TEXT};line-height:1.6;
          font-family:{_FONT};">{subtext}</p>
        <a href="{_esc(top_url)}" target="_blank"
          style="display:inline-block;background:{_ACC};color:#ffffff;padding:10px 18px;
          border-radius:6px;font-size:12px;font-weight:600;text-decoration:none;
          font-family:{_FONT};letter-spacing:0.2px;">Keep Reading &rarr;</a>
      </td>
    </tr>
    </table>
  </td></tr>
  </table>
"""

    # ── 3. WHAT THIS MEANS FOR BOULDER SEO MARKETING (directly under hero) ───────
    _bsm_moves = [
        (
            "Rolling out GEO readiness audits",
            "identifying AI visibility gaps across client content to maintain competitive rankings.",
        ),
        (
            "Expanding virtual agent knowledge systems",
            "improving how AI interprets and surfaces client information for better engagement.",
        ),
        (
            "Removing approval bottlenecks",
            "accelerating execution to respond faster to AI-driven search changes.",
        ),
    ]
    _shown_moves = _bsm_moves[:max_moves]
    H += f"""
  <table width="100%" cellpadding="0" cellspacing="0"
    style="background:{_WHITE};border-top:1px solid {_BDR};">
  <tr><td style="padding:20px 24px 20px;">
    <p style="margin:0 0 14px;font-size:10px;font-weight:700;color:{_M_TEXT};
      text-transform:uppercase;letter-spacing:2px;font-family:{_FONT};">
      What This Means for Boulder SEO Marketing</p>
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
    <tr><td style="border-left:3px solid {_ACC};padding-left:12px;">
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
"""
    for _i, (_lead, _ctx) in enumerate(_shown_moves):
        _pb = "14px" if _i < len(_shown_moves) - 1 else "0"
        H += (
            f'      <tr><td style="padding-bottom:{_pb};">'
            f'<table width="100%" cellpadding="0" cellspacing="0"><tr>'
            f'<td width="14" valign="top" style="font-size:18px;font-weight:700;'
            f'color:{_ACC};line-height:1.2;padding-right:6px;font-family:{_FONT};">&#8226;</td>'
            f'<td valign="top">'
            f'<p style="margin:0 0 3px;font-size:15px;font-weight:600;color:{_H_TEXT};'
            f'line-height:1.4;font-family:{_FONT};">{_esc(_lead)}</p>'
            f'<p style="margin:0;font-size:13px;color:#666666;line-height:1.5;'
            f'font-family:{_FONT};">{_esc(_ctx)}</p>'
            f'</td></tr></table>'
            f'</td></tr>\n'
        )
    H += '      </table>\n    </td></tr>\n    </table>\n  </td></tr>\n  </table>\n'

    # ── 4. ARTICLE CARDS (alternating two-column, from top_reads) ─────────────
    if reads_display:
        H += f"""
  <table width="100%" cellpadding="0" cellspacing="0"
    style="background:{_WHITE};border-top:1px solid {_BDR};">
  <tr><td style="padding:20px 24px 8px;">
    <p style="margin:0;font-size:11px;font-weight:700;color:{_M_TEXT};
      text-transform:uppercase;letter-spacing:2px;font-family:{_FONT};">Also In Today&rsquo;s Brief</p>
  </td></tr>
"""
        for _ri, _read in enumerate(reads_display):
            _rt  = _esc(_read.get("title",    ""))
            _rs  = _esc(_read.get("source",   ""))
            _ru  = _esc(_read.get("url",      "#"))
            _rn  = _esc(_read.get("bsm_note", ""))
            _img =      _read.get("image",    "")
            _rc  = _source_color(_read.get("source", ""))
            _note_html = (
                f'<p style="margin:0 0 10px;font-size:12px;color:{_B_TEXT};'
                f'line-height:1.5;font-family:{_FONT};">{_rn}</p>'
            ) if _rn else ""
            # Two image cell variants — border-radius matches the card corner on each side
            if _img:
                _img_left = (
                    f'<td width="160" style="width:160px;background:#f3f4f6;'
                    f'vertical-align:top;padding:0;font-size:0;line-height:0;">'
                    f'<img src="{_esc(_img)}" width="160" height="120" alt="Article thumbnail" '
                    f'class="thumb-img" style="display:block;width:160px;height:120px;'
                    f'object-fit:cover;border-radius:10px 0 0 10px;" /></td>'
                )
                _img_right = (
                    f'<td width="160" style="width:160px;background:#f3f4f6;'
                    f'vertical-align:top;padding:0;font-size:0;line-height:0;">'
                    f'<img src="{_esc(_img)}" width="160" height="120" alt="Article thumbnail" '
                    f'class="thumb-img" style="display:block;width:160px;height:120px;'
                    f'object-fit:cover;border-radius:0 10px 10px 0;" /></td>'
                )
            else:
                _img_left = (
                    f'<td width="160" style="width:160px;background:#f3f4f6;vertical-align:top;'
                    f'font-size:0;line-height:0;">&nbsp;</td>'
                )
                _img_right = _img_left
            _text_cell = (
                f'<td valign="top" style="padding:16px;vertical-align:top;">'
                f'<p style="margin:0 0 6px;font-size:10px;font-weight:700;color:{_rc};'
                f'text-transform:uppercase;letter-spacing:1.5px;font-family:{_FONT};">{_rs}</p>'
                f'<p style="margin:0 0 8px;font-size:14px;font-weight:700;color:{_H_TEXT};'
                f'line-height:1.35;font-family:{_SERIF};">'
                f'<a href="{_ru}" target="_blank" style="color:{_H_TEXT};text-decoration:none;">{_rt}</a></p>'
                f'{_note_html}'
                f'<a href="{_ru}" target="_blank" '
                f'style="font-size:12px;font-weight:600;color:{_rc};text-decoration:none;'
                f'font-family:{_FONT};">Keep Reading &rarr;</a>'
                f'</td>'
            )
            if _ri % 2 == 0:
                _left  = _img_left
                _right = _text_cell.replace(
                    'style="padding:16px;',
                    f'style="border-left:1px solid {_BDR};padding:16px;',
                )
            else:
                _left  = _text_cell.replace(
                    'style="padding:16px;',
                    f'style="border-right:1px solid {_BDR};padding:16px;',
                )
                _right = _img_right
            H += (
                f'  <tr><td style="padding:0 24px 16px;">'
                f'<table width="100%" cellpadding="0" cellspacing="0" '
                f'style="border:1px solid {_BDR};border-radius:10px;overflow:hidden;">'
                f'<tr>{_left}{_right}</tr>'
                f'</table></td></tr>\n'
            )
        H += "  </table>\n"

    # ── 5. FOOTER (dark) ───────────────────────────────────────────────────────
    H += f"""
  <table width="100%" cellpadding="0" cellspacing="0" style="background:{_H_TEXT};">
  <tr><td style="padding:28px 28px 24px;">
    <table width="100%" cellpadding="0" cellspacing="0"><tr>
      <td valign="top">
        <p style="margin:0 0 6px;">
          <span style="font-size:18px;font-weight:900;color:#ffffff;font-family:{_FONT};letter-spacing:-0.3px;">Micro</span><span
            style="font-size:18px;font-style:italic;font-weight:400;color:{_ACC};font-family:{_SERIF};">&nbsp;SEO</span>
        </p>
        <p style="margin:0 0 3px;font-size:12px;color:rgba(255,255,255,0.45);font-family:{_FONT};">AI-powered daily intelligence for the team</p>
        <p style="margin:0;font-size:12px;color:rgba(255,255,255,0.30);font-family:{_FONT};">Boulder, Colorado &nbsp;&middot;&nbsp; boulderseomarketing.com &nbsp;&middot;&nbsp; {_esc(display_date)}</p>
      </td>
    </tr></table>
    <p style="margin:16px 0 0;font-size:12px;color:rgba(255,255,255,0.25);font-family:{_FONT};">Reply to share feedback or flag a story for the team.</p>
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
                first_name: str, from_name: str, recipient_email: str = "") -> str:
    return _render_email(brief_data, articles, display_date, first_name, from_name,
                         max_moves=3, prefs_url=_prefs_url(recipient_email))


def _build_html_tier2(brief_data: dict, articles: list, display_date: str,
                      first_name: str, from_name: str, recipient_email: str = "") -> str:
    return _render_email(brief_data, articles, display_date, first_name, from_name,
                         max_moves=2, prefs_url=_prefs_url(recipient_email))


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
        html  = _build_html(brief_data, articles, display_date, fn, from_name, recipient_email=to)
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
            html  = _build_html_tier2(tier2_brief, articles, display_date, fn, from_name, recipient_email=to)
            plain = _build_plain(tier2_brief, fn, from_name)
            if use_resend:
                _send_resend(t2_subj, from_str, to, reply_to, html, plain, logo_data)
            else:
                _send_smtp(t2_subj, from_str, to, reply_to, html, plain, logo_data,
                           smtp_host, smtp_port)
            print(f"  ✓ Sent to {to} (Tier 2 — Team Digest)")
