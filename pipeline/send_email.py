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
_CANVAS  = "#C9C9CE"   # outer page background — makes the card pop
_PG_BG   = "#F4F4F5"  # inner section alternating background
_HERO_BG = "#0F172A"
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
                first_name: str, from_name: str) -> str:

    ts  = brief_data.get("top_story", {})
    tms = brief_data.get("three_moves", [])
    cas = brief_data.get("client_angles", [])

    headline   = _esc(ts.get("headline", "Today's top AI story"))
    subtext    = _esc(ts.get("subtext", ""))
    field_note = _esc(ts.get("field_note", ""))

    # top_reads: LLM-selected articles with BSM relevance notes
    top_reads = brief_data.get("top_reads", [])
    # Build a URL lookup from the raw articles list using article_index
    def _resolve_read(read: dict) -> dict:
        idx = read.get("article_index", 0) - 1
        url = articles[idx].get("url", "#") if 0 <= idx < len(articles) else "#"
        return {**read, "url": url}
    top_reads = [_resolve_read(r) for r in top_reads[:3]]
    # Fallback: use first 3 articles if LLM returned nothing
    if not top_reads and articles:
        top_reads = [{"title": a["title"], "source": a["source"], "url": a["url"], "bsm_note": ""} for a in articles[:3]]

    top_url = top_reads[0].get("url", articles[0].get("url","#") if articles else "#") if top_reads else (articles[0].get("url","#") if articles else "#")
    # Skip top_reads[0] in We're Reading — it's already the linked headline above
    reads_display = list(top_reads[1:])
    _used = {top_url} | {r.get("url","") for r in reads_display}
    for _a in articles:
        if len(reads_display) >= 3:
            break
        _u = _a.get("url","")
        if _u in _used:
            continue
        reads_display.append({"title": _a["title"], "source": _a["source"], "url": _u, "bsm_note": ""})
        _used.add(_u)
    reads_display = reads_display[:3]
    total_arts = len(reads_display)
    total_word = _N2W.get(total_arts, str(total_arts))

    move_colors = {"pitch": _GREEN, "build": _ACC, "kill": _RED}
    move_labels = {"pitch": "PITCH", "build": "BUILD", "kill": "KILL"}
    issue      = _issue_num()
    try:
        from datetime import datetime as _dt
        _d = _dt.strptime(display_date, "%A, %B %d, %Y")
        short_date = _d.strftime("%A, %b ") + str(_d.day)
    except Exception:
        short_date = display_date

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
<table width="100%" cellpadding="0" cellspacing="0" style="background:{_CANVAS};">
<tr><td align="center" style="padding:32px 16px 48px;">
<table width="640" cellpadding="0" cellspacing="0"
  style="max-width:640px;width:100%;background:{_WHITE};border-radius:16px;
  overflow:hidden;box-shadow:0 8px 40px rgba(0,0,0,0.18),0 2px 8px rgba(0,0,0,0.10);">
<tr><td>
"""

    # 1. HEADER + greeting
    H += f"""
  <table width="100%" cellpadding="0" cellspacing="0"
    style="background:{_WHITE};border-bottom:1px solid {_BDR};">
  <tr>
    <td style="padding:18px 28px;vertical-align:middle;">
      <span style="font-size:18px;font-weight:900;color:{_H_TEXT};
        font-family:{_FONT};letter-spacing:-0.3px;">BSM</span><span
        style="font-size:18px;font-style:italic;font-weight:400;color:{_ACC};
        font-family:{_SERIF};">&nbsp;Copilot</span>
    </td>
    <td style="padding:18px 28px;text-align:right;vertical-align:middle;">
      <p style="margin:0 0 2px;font-size:10px;font-weight:600;color:{_M_TEXT};
        font-family:{_FONT};letter-spacing:0.5px;">{_esc(issue)}</p>
      <p style="margin:0;font-size:12px;font-style:italic;color:{_B_TEXT};
        font-family:{_SERIF};">{_esc(short_date)}</p>
    </td>
  </tr>
  <tr><td colspan="2"
    style="padding:12px 28px 14px;border-top:1px solid {_BDR};">
    <p style="margin:0;font-size:13px;font-style:italic;color:{_B_TEXT};
      font-family:{_SERIF};line-height:1.5;">Good morning. Here&rsquo;s what changed
      overnight and what to do about it.</p>
  </td></tr>
  </table>

  <!-- 2. ONE THING THAT MATTERS TODAY -->
  <table width="100%" cellpadding="0" cellspacing="0"
    style="background:{_WHITE};border-bottom:1px solid {_BDR};">
  <tr><td style="padding:36px 28px 32px;">
    <p style="margin:0 0 14px;">
      <span style="font-size:10px;font-weight:700;color:{_M_TEXT};
        text-transform:uppercase;letter-spacing:2px;
        font-family:{_FONT};">One Thing That Matters Today</span>
    </p>
    <p style="margin:0 0 14px;font-size:26px;font-weight:700;color:{_H_TEXT};
      line-height:1.25;letter-spacing:-0.2px;font-family:{_SERIF};">
      <a href="{_esc(top_url)}" target="_blank"
        style="color:{_H_TEXT};text-decoration:none;">{headline}</a>
    </p>
    <p style="margin:0;font-size:14px;color:{_B_TEXT};line-height:1.7;
      font-family:{_FONT};">{subtext}</p>
    <table cellpadding="0" cellspacing="0" style="margin-top:18px;">
    <tr><td style="background:{_ACC};border-radius:6px;">
      <a href="{_esc(top_url)}" target="_blank"
        style="display:inline-block;padding:10px 22px;font-size:13px;
        font-weight:600;color:#ffffff;text-decoration:none;
        font-family:{_FONT};letter-spacing:0.2px;">Read Full Article &rarr;</a>
    </td></tr>
    </table>
    <div style="border-top:1px solid {_BDR};margin:22px 0;"></div>
    <table cellpadding="0" cellspacing="0" style="width:100%;"><tr>
      <td style="padding-right:16px;vertical-align:top;white-space:nowrap;">
        <span style="font-size:9px;font-weight:700;color:{_M_TEXT};
          text-transform:uppercase;letter-spacing:2px;
          font-family:{_FONT};">What We&rsquo;re Doing</span>
      </td>
      <td>
        <p style="margin:0;font-size:13px;color:{_B_TEXT};line-height:1.6;
          font-style:italic;font-family:{_SERIF};">{field_note}</p>
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
<td width="184" valign="top" style="height:100%;">
  <table width="184" height="100%" cellpadding="0" cellspacing="0"
    style="height:100%;background:{_WHITE};border-radius:8px;border:1px solid {_BDR};">
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

    # 4. WE'RE READING — 3 fresh articles from feeds
    reading_rows = ""
    for j, item in enumerate(reads_display):
        bdr    = f"border-top:1px solid {_BDR};" if j > 0 else ""
        atitle = _esc(item.get("title","")[:90])
        asrc   = _esc(item.get("source","")[:30])
        aurl   = _esc(item.get("url","#"))
        anote  = _esc(item.get("bsm_note",""))
        reading_rows += f"""
    <tr><td style="padding:14px 20px;{bdr}">
      <table width="100%" cellpadding="0" cellspacing="0">
        <tr>
          <td valign="middle" style="padding-right:16px;">
            <a href="{aurl}" target="_blank"
              style="font-size:13px;font-weight:500;color:{_H_TEXT};
              text-decoration:none;line-height:1.45;
              font-family:{_FONT};">{atitle}</a>
          </td>
          <td valign="middle" style="text-align:right;white-space:nowrap;">
            <span style="font-size:10px;color:{_M_TEXT};
              font-family:{_FONT};">{asrc}</span>
          </td>
        </tr>
        {"" if not anote else f'<tr><td colspan="2" style="padding-top:5px;"><p style="margin:0;font-size:11px;font-style:italic;color:{_B_TEXT};line-height:1.5;font-family:{_FONT};">{anote}</p></td></tr>'}
      </table>
    </td></tr>"""

    H += f"""
  <table width="100%" cellpadding="0" cellspacing="0"
    style="background:{_PG_BG};border-top:1px solid {_BDR};">
  <tr><td style="padding:28px 28px 24px;">
    <span style="font-size:10px;font-weight:700;color:{_H_TEXT};
      text-transform:uppercase;letter-spacing:2px;
      font-family:{_FONT};">We&rsquo;re Reading</span>
    <table width="100%" cellpadding="0" cellspacing="0"
      style="margin-top:16px;background:{_WHITE};border-radius:8px;border:1px solid {_BDR};">
    <tr><td height="3"
      style="background:{_ACC};height:3px;font-size:0;line-height:0;">&nbsp;</td></tr>
    {reading_rows}
    </table>
  </td></tr>
  </table>
"""

    # 5. ON OUR RADAR (conditional)
    _on_radar = brief_data.get("on_radar", [])
    if _on_radar:
        _radar_items = []
        for _i, _item in enumerate(_on_radar[:2]):
            _m = "10px" if _i == 0 else "6px"
            _radar_items.append(
                f'<p style="margin:{_m} 0 0;font-size:13px;font-style:italic;'
                f'color:{_B_TEXT};line-height:1.6;font-family:{_FONT};">'
                f'&bull;&nbsp;{_esc(str(_item))}</p>'
            )
        _radar_html = "".join(_radar_items)
        H += f"""
  <table width="100%" cellpadding="0" cellspacing="0"
    style="background:{_WHITE};border-top:1px solid {_BDR};">
  <tr><td style="padding:24px 28px 20px;">
    <p style="margin:0 0 8px;"><span style="font-size:10px;font-weight:700;
      color:{_M_TEXT};text-transform:uppercase;letter-spacing:2px;
      font-family:{_FONT};">On Our Radar</span></p>
    {_radar_html}
  </td></tr>
  </table>
"""

    # 6. CHRIS'S TAKE
    _chris_take = brief_data.get("chris_take", "")
    if _chris_take:
        H += f"""
  <table width="100%" cellpadding="0" cellspacing="0"
    style="background:{_PG_BG};border-top:1px solid {_BDR};">
  <tr><td style="padding:22px 28px 24px;">
    <p style="margin:0 0 8px;"><span style="font-size:10px;font-weight:700;
      color:{_M_TEXT};text-transform:uppercase;letter-spacing:2px;
      font-family:{_FONT};">Chris&rsquo;s Take</span></p>
    <p style="margin:0;font-size:15px;font-style:italic;color:{_H_TEXT};
      line-height:1.6;font-family:{_SERIF};">&ldquo;{_esc(_chris_take)}&rdquo;</p>
  </td></tr>
  </table>
"""

    # 7. FOOTER
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


def _build_html_tier2(brief_data: dict, articles: list, display_date: str,
                      first_name: str, from_name: str) -> str:
    """Team Digest email: same design as full newsletter, tighter brief, LLM-curated top_reads."""

    ts  = brief_data.get("top_story", {})
    tms = brief_data.get("three_moves", [])
    cas = brief_data.get("client_angles", [])

    headline   = _esc(ts.get("headline", "Today's top AI story"))
    subtext    = _esc(ts.get("subtext", ""))
    field_note = _esc(ts.get("field_note", ""))

    top_reads = brief_data.get("top_reads", [])
    def _resolve_read(read: dict) -> dict:
        idx = read.get("article_index", 0) - 1
        url = articles[idx].get("url", "#") if 0 <= idx < len(articles) else "#"
        return {**read, "url": url}
    top_reads = [_resolve_read(r) for r in top_reads[:3]]
    if not top_reads and articles:
        top_reads = [{"title": a["title"], "source": a["source"], "url": a["url"], "bsm_note": ""} for a in articles[:3]]

    top_url = top_reads[0].get("url", articles[0].get("url","#") if articles else "#") if top_reads else (articles[0].get("url","#") if articles else "#")
    reads_display = list(top_reads[1:])
    _used = {top_url} | {r.get("url","") for r in reads_display}
    for _a in articles:
        if len(reads_display) >= 3:
            break
        _u = _a.get("url","")
        if _u in _used:
            continue
        reads_display.append({"title": _a["title"], "source": _a["source"], "url": _u, "bsm_note": ""})
        _used.add(_u)
    reads_display = reads_display[:3]
    total_arts = len(reads_display)
    total_word = _N2W.get(total_arts, str(total_arts))

    move_colors = {"pitch": _GREEN, "build": _ACC, "kill": _RED}
    move_labels = {"pitch": "PITCH", "build": "BUILD", "kill": "KILL"}
    issue      = _issue_num()
    try:
        from datetime import datetime as _dt
        _d = _dt.strptime(display_date, "%A, %B %d, %Y")
        short_date = _d.strftime("%A, %b ") + str(_d.day)
    except Exception:
        short_date = display_date

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
<table width="100%" cellpadding="0" cellspacing="0" style="background:{_CANVAS};">
<tr><td align="center" style="padding:32px 16px 48px;">
<table width="640" cellpadding="0" cellspacing="0"
  style="max-width:640px;width:100%;background:{_WHITE};border-radius:16px;
  overflow:hidden;box-shadow:0 8px 40px rgba(0,0,0,0.18),0 2px 8px rgba(0,0,0,0.10);">
<tr><td>
"""

    # 1. HEADER + greeting
    H += f"""
  <table width="100%" cellpadding="0" cellspacing="0"
    style="background:{_WHITE};border-bottom:1px solid {_BDR};">
  <tr>
    <td style="padding:18px 28px;vertical-align:middle;">
      <span style="font-size:18px;font-weight:900;color:{_H_TEXT};
        font-family:{_FONT};letter-spacing:-0.3px;">BSM</span><span
        style="font-size:18px;font-style:italic;font-weight:400;color:{_ACC};
        font-family:{_SERIF};">&nbsp;Copilot</span>
    </td>
    <td style="padding:18px 28px;text-align:right;vertical-align:middle;">
      <p style="margin:0 0 2px;font-size:10px;font-weight:600;color:{_M_TEXT};
        font-family:{_FONT};letter-spacing:0.5px;">{_esc(issue)}</p>
      <p style="margin:0;font-size:12px;font-style:italic;color:{_B_TEXT};
        font-family:{_SERIF};">{_esc(short_date)}</p>
    </td>
  </tr>
  <tr><td colspan="2"
    style="padding:12px 28px 14px;border-top:1px solid {_BDR};">
    <p style="margin:0;font-size:13px;font-style:italic;color:{_B_TEXT};
      font-family:{_SERIF};line-height:1.5;">Good morning. Here&rsquo;s what changed
      overnight and what to do about it.</p>
  </td></tr>
  </table>

  <!-- 2. ONE THING THAT MATTERS TODAY -->
  <table width="100%" cellpadding="0" cellspacing="0"
    style="background:{_WHITE};border-bottom:1px solid {_BDR};">
  <tr><td style="padding:36px 28px 32px;">
    <p style="margin:0 0 14px;">
      <span style="font-size:10px;font-weight:700;color:{_M_TEXT};
        text-transform:uppercase;letter-spacing:2px;
        font-family:{_FONT};">One Thing That Matters Today</span>
    </p>
    <p style="margin:0 0 14px;font-size:26px;font-weight:700;color:{_H_TEXT};
      line-height:1.25;letter-spacing:-0.2px;font-family:{_SERIF};">
      <a href="{_esc(top_url)}" target="_blank"
        style="color:{_H_TEXT};text-decoration:none;">{headline}</a>
    </p>
    <p style="margin:0;font-size:14px;color:{_B_TEXT};line-height:1.7;
      font-family:{_FONT};">{subtext}</p>
    <table cellpadding="0" cellspacing="0" style="margin-top:18px;">
    <tr><td style="background:{_ACC};border-radius:6px;">
      <a href="{_esc(top_url)}" target="_blank"
        style="display:inline-block;padding:10px 22px;font-size:13px;
        font-weight:600;color:#ffffff;text-decoration:none;
        font-family:{_FONT};letter-spacing:0.2px;">Read Full Article &rarr;</a>
    </td></tr>
    </table>
    <div style="border-top:1px solid {_BDR};margin:22px 0;"></div>
    <table cellpadding="0" cellspacing="0" style="width:100%;"><tr>
      <td style="padding-right:16px;vertical-align:top;white-space:nowrap;">
        <span style="font-size:9px;font-weight:700;color:{_M_TEXT};
          text-transform:uppercase;letter-spacing:2px;
          font-family:{_FONT};">What We&rsquo;re Doing</span>
      </td>
      <td>
        <p style="margin:0;font-size:13px;color:{_B_TEXT};line-height:1.6;
          font-style:italic;font-family:{_SERIF};">{field_note}</p>
      </td>
    </tr></table>
  </td></tr>
  </table>
"""

    # 3. THREE MOVES (max 2 cards for digest)
    move_cards = ""
    for i, move in enumerate(tms[:2]):
        mtype  = move.get("type","pitch").lower()
        mtitle = _esc(move.get("title",""))
        mdesc  = _esc(move.get("description",""))
        mc     = move_colors.get(mtype, _ACC)
        mlbl   = move_labels.get(mtype, mtype.upper())
        spacer = '<td width="16"></td>' if i > 0 else ""
        move_cards += f"""{spacer}
<td width="184" valign="top" style="height:100%;">
  <table width="184" height="100%" cellpadding="0" cellspacing="0"
    style="height:100%;background:{_WHITE};border-radius:8px;border:1px solid {_BDR};">
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

    # 4. WE'RE READING — 3 fresh articles from feeds
    reading_rows = ""
    for j, item in enumerate(reads_display):
        bdr    = f"border-top:1px solid {_BDR};" if j > 0 else ""
        atitle = _esc(item.get("title","")[:90])
        asrc   = _esc(item.get("source","")[:30])
        aurl   = _esc(item.get("url","#"))
        anote  = _esc(item.get("bsm_note",""))
        reading_rows += f"""
    <tr><td style="padding:14px 20px;{bdr}">
      <table width="100%" cellpadding="0" cellspacing="0">
        <tr>
          <td valign="middle" style="padding-right:16px;">
            <a href="{aurl}" target="_blank"
              style="font-size:13px;font-weight:500;color:{_H_TEXT};
              text-decoration:none;line-height:1.45;
              font-family:{_FONT};">{atitle}</a>
          </td>
          <td valign="middle" style="text-align:right;white-space:nowrap;">
            <span style="font-size:10px;color:{_M_TEXT};
              font-family:{_FONT};">{asrc}</span>
          </td>
        </tr>
        {"" if not anote else f'<tr><td colspan="2" style="padding-top:5px;"><p style="margin:0;font-size:11px;font-style:italic;color:{_B_TEXT};line-height:1.5;font-family:{_FONT};">{anote}</p></td></tr>'}
      </table>
    </td></tr>"""

    H += f"""
  <table width="100%" cellpadding="0" cellspacing="0"
    style="background:{_PG_BG};border-top:1px solid {_BDR};">
  <tr><td style="padding:28px 28px 24px;">
    <span style="font-size:10px;font-weight:700;color:{_H_TEXT};
      text-transform:uppercase;letter-spacing:2px;
      font-family:{_FONT};">We&rsquo;re Reading</span>
    <table width="100%" cellpadding="0" cellspacing="0"
      style="margin-top:16px;background:{_WHITE};border-radius:8px;border:1px solid {_BDR};">
    <tr><td height="3"
      style="background:{_ACC};height:3px;font-size:0;line-height:0;">&nbsp;</td></tr>
    {reading_rows}
    </table>
  </td></tr>
  </table>
"""

    # 5. ON OUR RADAR (conditional)
    _on_radar = brief_data.get("on_radar", [])
    if _on_radar:
        _radar_items = []
        for _i, _item in enumerate(_on_radar[:2]):
            _m = "10px" if _i == 0 else "6px"
            _radar_items.append(
                f'<p style="margin:{_m} 0 0;font-size:13px;font-style:italic;'
                f'color:{_B_TEXT};line-height:1.6;font-family:{_FONT};">'
                f'&bull;&nbsp;{_esc(str(_item))}</p>'
            )
        _radar_html = "".join(_radar_items)
        H += f"""
  <table width="100%" cellpadding="0" cellspacing="0"
    style="background:{_WHITE};border-top:1px solid {_BDR};">
  <tr><td style="padding:24px 28px 20px;">
    <p style="margin:0 0 8px;"><span style="font-size:10px;font-weight:700;
      color:{_M_TEXT};text-transform:uppercase;letter-spacing:2px;
      font-family:{_FONT};">On Our Radar</span></p>
    {_radar_html}
  </td></tr>
  </table>
"""

    # 6. CHRIS'S TAKE
    _chris_take = brief_data.get("chris_take", "")
    if _chris_take:
        H += f"""
  <table width="100%" cellpadding="0" cellspacing="0"
    style="background:{_PG_BG};border-top:1px solid {_BDR};">
  <tr><td style="padding:22px 28px 24px;">
    <p style="margin:0 0 8px;"><span style="font-size:10px;font-weight:700;
      color:{_M_TEXT};text-transform:uppercase;letter-spacing:2px;
      font-family:{_FONT};">Chris&rsquo;s Take</span></p>
    <p style="margin:0;font-size:15px;font-style:italic;color:{_H_TEXT};
      line-height:1.6;font-family:{_SERIF};">&ldquo;{_esc(_chris_take)}&rdquo;</p>
  </td></tr>
  </table>
"""

    # 7. FOOTER
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

    # If no explicit tier split was passed, send full newsletter to everyone
    t1 = tier1_recipients if tier1_recipients is not None else ec.get("recipients", [])
    t2 = tier2_recipients or []

    if not t1 and not t2:
        raise ValueError("config.json missing email.recipients")

    # Tier 1 — full newsletter
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

    # Tier 2 — team digest (tighter brief)
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
