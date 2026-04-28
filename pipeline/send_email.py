"""
Email sender — premium AI newsletter.
Table-based layout, inline CSS, Gmail-compatible.
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

# Design system
_WHITE   = "#FFFFFF"
_PG_BG   = "#F4F4F5"
_HERO_BG = "#0D1117"
_BDR     = "#E4E4E7"
_H_TEXT  = "#09090B"
_B_TEXT  = "#52525B"
_M_TEXT  = "#A1A1AA"
_ACC     = "#6366F1"
_GREEN   = "#10B981"
_RED     = "#EF4444"
_ORANGE  = "#F97316"
_NAVY    = "#1E40AF"
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
        return f'<img src="cid:bsm_logo" height="{h}" style="display:block;" alt="BSM">'
    return (f'<span style="font-size:18px;font-weight:900;color:{_H_TEXT};'
            f'font-family:{_FONT};">BSM</span>'
            f'<span style="font-size:18px;font-style:italic;font-weight:600;'
            f'color:{_ACC};font-family:{_FONT};"> Copilot</span>')


def _build_html(brief_data: dict, articles: list, display_date: str,
                first_name: str, from_name: str,
                yt_videos: list | None = None) -> str:

    ts  = brief_data.get("top_story", {})
    tms = brief_data.get("three_moves", [])
    cas = brief_data.get("client_angles", [])

    headline   = _esc(ts.get("headline", "Today's top AI story"))
    subtext    = _esc(ts.get("subtext", ""))
    field_note = _esc(ts.get("field_note", ""))

    # Categorise articles
    buckets: dict[str, list] = {"INDUSTRY": [], "SEO": [], "DEV": []}
    for a in articles:
        key = (a.get("source","") + " " + a.get("title","")).lower()
        if any(k in key for k in ["seo","se ranking","perplexity","ranking","search engine"]):
            buckets["SEO"].append(a)
        elif any(k in key for k in ["dev tools","mcp","anthropic","claude","developer","code","github"]):
            buckets["DEV"].append(a)
        else:
            buckets["INDUSTRY"].append(a)

    total_arts = len(articles)
    total_word = _N2W.get(total_arts, str(total_arts))

    vids      = yt_videos or []
    vid_count = len(vids[:3])
    vid_word  = _N2W.get(vid_count, str(vid_count))

    move_colors = {"pitch": _GREEN, "build": _ACC, "kill": _RED}
    move_labels = {"pitch": "PITCH", "build": "BUILD", "kill": "KILL"}

    top_url = articles[0].get("url","#") if articles else "#"
    issue   = _issue_num()

    H = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
@import url('https://fonts.googleapis.com/css2?family=Lora:ital,wght@0,400;0,700;1,400;1,600&display=swap');
</style>
</head>
<body style="margin:0;padding:0;background:{_PG_BG};font-family:{_FONT};">
<table width="100%" cellpadding="0" cellspacing="0" style="background:{_PG_BG};">
<tr><td align="center" style="padding:24px 12px 40px;">
<table width="640" cellpadding="0" cellspacing="0"
  style="max-width:640px;width:100%;background:{_WHITE};border-radius:12px;
  overflow:hidden;box-shadow:0 2px 16px rgba(0,0,0,0.08);">
<tr><td>
"""

    # 1. HEADER
    H += f"""
  <table width="100%" cellpadding="0" cellspacing="0"
    style="background:{_WHITE};border-bottom:1px solid {_BDR};">
  <tr>
    <td style="padding:18px 28px;vertical-align:middle;">{_logo(30)}</td>
    <td style="padding:18px 28px;text-align:right;vertical-align:middle;">
      <span style="font-size:12px;font-weight:700;color:{_H_TEXT};
        font-family:{_FONT};">{_esc(issue)}</span>
      <span style="font-size:12px;color:{_M_TEXT};font-family:{_FONT};
        margin-left:12px;">{_esc(display_date)}</span>
    </td>
  </tr>
  </table>
"""

    # 2. HERO (dark)
    H += f"""
  <table width="100%" cellpadding="0" cellspacing="0"
    style="background:{_HERO_BG};">
  <tr><td style="padding:48px 36px 40px;">
    <p style="margin:0 0 18px;">
      <span style="display:inline-block;width:6px;height:6px;border-radius:50%;
        background:{_ACC};vertical-align:middle;margin-right:7px;
        margin-bottom:2px;"></span>
      <span style="font-size:10px;font-weight:700;color:{_ACC};
        text-transform:uppercase;letter-spacing:2.5px;
        font-family:{_FONT};">Today&rsquo;s Top Story</span>
    </p>
    <p style="margin:0 0 18px;font-size:30px;font-weight:700;color:{_WHITE};
      line-height:1.2;letter-spacing:-0.3px;font-family:{_SERIF};">{headline}</p>
    <p style="margin:0 0 28px;font-size:14px;color:rgba(255,255,255,0.65);
      line-height:1.75;font-family:{_FONT};">{subtext}</p>
    <a href="{_esc(top_url)}" target="_blank"
      style="display:inline-block;border:1.5px solid rgba(255,255,255,0.35);
      color:{_WHITE};font-size:13px;font-weight:600;padding:10px 22px;
      border-radius:50px;text-decoration:none;font-family:{_FONT};">
      Read the full story &rarr;
    </a>
    <div style="border-top:1px solid rgba(255,255,255,0.1);margin:32px 0 22px;"></div>
    <table cellpadding="0" cellspacing="0"><tr>
      <td style="padding-right:14px;vertical-align:top;white-space:nowrap;">
        <span style="font-size:9px;font-weight:700;color:rgba(255,255,255,0.38);
          text-transform:uppercase;letter-spacing:2px;
          font-family:{_FONT};">Field Note</span>
      </td>
      <td>
        <p style="margin:0;font-size:13px;color:rgba(255,255,255,0.52);
          line-height:1.65;font-style:italic;
          font-family:{_SERIF};">{field_note}</p>
      </td>
    </tr></table>
  </td></tr>
  </table>
"""

    # 3. THREE MOVES
    # Inner width: 640 - 56px padding = 584px
    # 3 cards x 184px + 2 gutters x 16px = 584px
    move_cards = ""
    for i, move in enumerate(tms[:3]):
        mtype  = move.get("type","pitch").lower()
        mtitle = _esc(move.get("title",""))
        mdesc  = _esc(move.get("description",""))
        mdeadl = _esc(move.get("deadline",""))
        mc     = move_colors.get(mtype, _ACC)
        mlbl   = move_labels.get(mtype, mtype.upper())
        spacer = '<td width="16"></td>' if i > 0 else ""
        move_cards += f"""{spacer}
<td width="184" valign="top">
  <table width="184" cellpadding="0" cellspacing="0"
    style="background:{_WHITE};border-radius:8px;border:1px solid {_BDR};">
  <tr><td height="3"
    style="background:{mc};height:3px;font-size:0;line-height:0;">&nbsp;</td></tr>
  <tr><td style="padding:16px 15px 15px;">
    <p style="margin:0 0 11px;">
      <span style="display:inline-block;background:{mc};color:#fff;font-size:9px;
        font-weight:800;text-transform:uppercase;letter-spacing:1.5px;
        padding:3px 9px;border-radius:50px;font-family:{_FONT};">{mlbl}</span>
    </p>
    <p style="margin:0 0 9px;font-size:13px;font-weight:600;font-style:italic;
      color:{_H_TEXT};line-height:1.45;font-family:{_SERIF};">{mtitle}</p>
    <p style="margin:0 0 13px;font-size:12px;color:{_B_TEXT};line-height:1.6;
      font-family:{_FONT};">{mdesc}</p>
    <p style="margin:0;font-size:10px;font-weight:700;color:{mc};
      text-transform:uppercase;letter-spacing:0.8px;
      font-family:{_FONT};">{mdeadl}</p>
  </td></tr>
  </table>
</td>"""

    H += f"""
  <table width="100%" cellpadding="0" cellspacing="0"
    style="background:{_PG_BG};border-top:1px solid {_BDR};">
  <tr><td style="padding:32px 28px 28px;">
    <span style="font-size:10px;font-weight:700;color:{_M_TEXT};
      text-transform:uppercase;letter-spacing:2px;
      font-family:{_FONT};">Today &middot; Three Moves</span>
    <p style="margin:6px 0 20px;font-size:14px;font-style:italic;color:{_B_TEXT};
      font-family:{_SERIF};">What BSM should do before noon.</p>
    <table cellpadding="0" cellspacing="0" style="width:100%;"><tr>
      {move_cards}
    </tr></table>
  </td></tr>
  </table>
"""

    # 4. WE'RE WATCHING
    if vids:
        yt_cards = ""
        for i, v in enumerate(vids[:3]):
            thumb  = _esc(v.get("thumbnail",""))
            url    = _esc(v.get("url","#"))
            title  = _esc(v.get("title","")[:65])
            ch     = _esc(v.get("channel","")[:28].upper())
            spacer = '<td width="16"></td>' if i > 0 else ""
            yt_cards += f"""{spacer}
<td width="184" valign="top">
  <a href="{url}" target="_blank" style="display:block;text-decoration:none;line-height:0;">
    <img src="{thumb}" width="184" height="104"
      style="width:184px;height:104px;object-fit:cover;display:block;border:0;
      border-radius:6px;">
  </a>
  <p style="margin:8px 0 4px;font-size:9px;font-weight:700;color:{_M_TEXT};
    text-transform:uppercase;letter-spacing:1.2px;
    font-family:{_FONT};">{ch}</p>
  <p style="margin:0;font-size:12px;font-weight:600;color:{_H_TEXT};
    line-height:1.4;font-family:{_FONT};">
    <a href="{url}" target="_blank"
      style="color:{_H_TEXT};text-decoration:none;">{title}</a>
  </p>
</td>"""

        H += f"""
  <table width="100%" cellpadding="0" cellspacing="0"
    style="background:{_WHITE};border-top:1px solid {_BDR};">
  <tr><td style="padding:28px 28px 28px;">
    <table width="100%" cellpadding="0" cellspacing="0"
      style="margin-bottom:20px;"><tr>
      <td valign="middle">
        <span style="font-size:10px;font-weight:700;color:{_H_TEXT};
          text-transform:uppercase;letter-spacing:2px;
          font-family:{_FONT};">We&rsquo;re Watching</span>
      </td>
      <td valign="middle" style="text-align:right;">
        <span style="font-size:12px;font-style:italic;color:{_M_TEXT};
          font-family:{_FONT};">{vid_word}&nbsp;video{"s" if vid_count != 1 else ""}</span>
      </td>
    </tr></table>
    <table cellpadding="0" cellspacing="0" style="width:100%;"><tr>
      {yt_cards}
    </tr></table>
  </td></tr>
  </table>
"""

    # 5. WE'RE READING
    cat_config = [
        ("INDUSTRY",      _GREEN,  buckets["INDUSTRY"]),
        ("SEO",           _ACC,    buckets["SEO"]),
        ("DEV",           _NAVY,   buckets["DEV"]),
        ("CLIENT ANGLES", _ORANGE, cas),
    ]

    reading_cards = ""
    for cat_label, cat_color, cat_items in cat_config:
        if not cat_items:
            continue
        limit = cat_items[:3]
        count = len(limit)
        count_word = _N2W.get(count, str(count))

        rows = ""
        for j, item in enumerate(limit):
            bdr    = f"border-top:1px solid {_BDR};" if j > 0 else ""
            atitle = _esc(item.get("title","")[:85])
            asrc   = _esc(item.get("source","BSM Intel")[:28])
            aurl   = item.get("url","#") if cat_label != "CLIENT ANGLES" else "#"
            rows += f"""
        <tr><td style="padding:12px 20px;{bdr}">
          <table width="100%" cellpadding="0" cellspacing="0"><tr>
            <td valign="middle" style="padding-right:16px;">
              <a href="{_esc(aurl)}" target="_blank"
                style="font-size:13px;font-weight:500;color:{_H_TEXT};
                text-decoration:none;line-height:1.45;
                font-family:{_FONT};">{atitle}</a>
            </td>
            <td valign="middle" style="text-align:right;white-space:nowrap;">
              <span style="font-size:10px;color:{_M_TEXT};
                font-family:{_FONT};">{asrc}</span>
            </td>
          </tr></table>
        </td></tr>"""

        reading_cards += f"""
    <table width="100%" cellpadding="0" cellspacing="0"
      style="background:{_WHITE};border-radius:8px;border:1px solid {_BDR};
      margin-bottom:12px;">
    <tr><td height="3"
      style="background:{cat_color};height:3px;font-size:0;line-height:0;">&nbsp;</td></tr>
    <tr><td style="padding:14px 20px 12px;border-bottom:1px solid {_BDR};">
      <table width="100%" cellpadding="0" cellspacing="0"><tr>
        <td valign="middle">
          <span style="display:inline-block;background:{cat_color};color:#fff;
            font-size:9px;font-weight:800;text-transform:uppercase;
            letter-spacing:1.5px;padding:3px 9px;border-radius:50px;
            font-family:{_FONT};">{cat_label}</span>
        </td>
        <td valign="middle" style="text-align:right;">
          <span style="font-size:11px;font-style:italic;color:{_M_TEXT};
            font-family:{_FONT};">{count_word}&nbsp;article{"s" if count != 1 else ""}</span>
        </td>
      </tr></table>
    </td></tr>
    {rows}
    </table>"""

    H += f"""
  <table width="100%" cellpadding="0" cellspacing="0"
    style="background:{_PG_BG};border-top:1px solid {_BDR};">
  <tr><td style="padding:28px 28px 24px;">
    <table width="100%" cellpadding="0" cellspacing="0"
      style="margin-bottom:20px;"><tr>
      <td valign="middle">
        <span style="font-size:10px;font-weight:700;color:{_H_TEXT};
          text-transform:uppercase;letter-spacing:2px;
          font-family:{_FONT};">We&rsquo;re Reading</span>
      </td>
      <td valign="middle" style="text-align:right;">
        <span style="font-size:12px;font-style:italic;color:{_M_TEXT};
          font-family:{_FONT};">{total_word}&nbsp;article{"s" if total_arts != 1 else ""}</span>
      </td>
    </tr></table>
    {reading_cards}
  </td></tr>
  </table>
"""

    # 6. FOOTER
    H += f"""
  <table width="100%" cellpadding="0" cellspacing="0"
    style="background:{_WHITE};border-top:1px solid {_BDR};">
  <tr><td style="padding:24px 28px;text-align:center;">
    <div style="margin-bottom:10px;">{_logo(24)}</div>
    <p style="margin:0 0 4px;font-size:11px;color:{_M_TEXT};
      font-family:{_FONT};">
      AI-powered daily intelligence for the BSM team
      &nbsp;&middot;&nbsp; Boulder SEO Marketing
    </p>
    <p style="margin:0;font-size:11px;color:{_M_TEXT};font-family:{_FONT};">
      &copy; 2026 Boulder SEO Marketing
      &nbsp;&middot;&nbsp; {_esc(display_date)}
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


def _build_plain(brief_data: dict, first_name: str, from_name: str) -> str:
    ts = brief_data.get("top_story", {}) if isinstance(brief_data, dict) else {}
    headline = ts.get("headline","") if ts else str(brief_data)[:200]
    return (f"Hey {first_name},\n\nToday's top story: {headline}\n\n"
            f"---\n\n"
            f"If you're building in SEO, AI, or automation — this is your edge.\n\n"
            f"- {from_name}\nBoulder SEO Marketing")


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
                    yt_videos: list | None = None) -> None:
    config    = json.loads(CONFIG_FILE.read_text())
    ec        = config.get("email", {})
    if not ec.get("from_address"):
        raise ValueError("config.json missing email.from_address")
    if not ec.get("recipients"):
        raise ValueError("config.json missing email.recipients")
    from_name  = ec.get("from_name", "Sean")
    from_str   = f"{from_name} <{ec['from_address']}>"
    reply_to   = ec.get("reply_to", ec["from_address"])
    logo_data  = _LOGO_FILE.read_bytes() if _LOGO_FILE.exists() else None
    use_resend = bool(os.environ.get("RESEND_API_KEY"))

    for recip in ec["recipients"]:
        fn    = recip.get("first_name", "there")
        to    = recip["email"]
        html  = _build_html(brief_data, articles, display_date, fn, from_name, yt_videos)
        plain = _build_plain(brief_data, fn, from_name)
        if use_resend:
            _send_resend(subject, from_str, to, reply_to, html, plain, logo_data)
        else:
            _send_smtp(subject, from_str, to, reply_to, html, plain, logo_data,
                       ec["smtp_host"], ec["smtp_port"])
        print(f"  ✓ Sent to {to}")
