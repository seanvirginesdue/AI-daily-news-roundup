"""
Email sender — premium AI newsletter.
Table-based layout, inline CSS, Gmail-compatible.
"""

import os, re, smtplib, json
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import parseaddr
from pathlib import Path

CONFIG_FILE = Path(__file__).parent / "config.json"
_LOGO_FILE  = Path(__file__).parent / "bsm_logo.png"

# ── Animated GIF for hero ──────────────────────────────────
_HERO_GIF_URL = "https://media.giphy.com/media/7ydUQC0CC2cNVtcrYH/giphy.gif"

# ── Design system ──────────────────────────────────────────
_ACC   = "#6366F1"  # indigo-500 — primary accent
_WHITE = "#ffffff"
_DARK  = "#0F172A"  # slate-900 — hero / dark sections
_PG_BG = "#F1F5F9"  # slate-100 — page background
_ST_BG = "#F8FAFC"  # slate-50  — card backgrounds
_IC_BG = "#EEF2FF"  # indigo-50 — accent card tint
_BDR   = "#E2E8F0"  # slate-200 — borders
_T_HED = "#0F172A"  # slate-900 — heading text
_T_BOD = "#475569"  # slate-600 — body text
_T_MET = "#94A3B8"  # slate-400 — meta / muted text
_FONT  = "-apple-system,BlinkMacSystemFont,'Segoe UI','Helvetica Neue',Arial,sans-serif"

# ── Helpers ────────────────────────────────────────────────

def _esc(t: str) -> str:
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def _lnk(text: str, arts: list) -> str:
    def r(m):
        idx = int(m.group(1)) - 1
        if 0 <= idx < len(arts):
            u = _esc(arts[idx].get("url", "#"))
            t = _esc(arts[idx].get("title", m.group(0)))
            return f'<a href="{u}" style="color:{_ACC};text-decoration:none;font-weight:600;" target="_blank">{t}</a>'
        return m.group(0)
    return re.sub(r"\[(\d+)\]", r, text)

def _logo(h: int = 36) -> str:
    if _LOGO_FILE.exists():
        return f'<img src="cid:bsm_logo" height="{h}" style="display:block;" alt="BSM">'
    return f'<span style="color:{_ACC};font-size:22px;font-weight:900;font-family:{_FONT};">BSM</span>'

def _img(url: str, alt: str = "", w: int = 200, h: int = 113, r: int = 0) -> str:
    if not url:
        return ""
    return (f'<img src="{_esc(url)}" alt="{_esc(alt[:40])}" width="{w}" '
            f'style="width:{w}px;height:{h}px;object-fit:cover;display:block;border:0;">')

def _btn(label: str, url: str = "#", sm: bool = False) -> str:
    p  = "8px 16px" if sm else "11px 24px"
    fs = "11px"     if sm else "13px"
    return (f'<a href="{_esc(url)}" target="_blank" '
            f'style="display:inline-block;background:{_ACC};color:#fff;font-size:{fs};'
            f'font-family:{_FONT};font-weight:700;padding:{p};border-radius:8px;'
            f'text-decoration:none;letter-spacing:0.2px;">{_esc(label)}</a>')

def _label(text: str) -> str:
    return (f'<p style="margin:0 0 8px;font-size:10px;font-weight:700;color:{_ACC};'
            f'text-transform:uppercase;letter-spacing:2px;font-family:{_FONT};">{text}</p>')

# ── Section parser ─────────────────────────────────────────
_SKEYS = [
    "what's hot today", "claude insider", "ai tool landscape",
    "bsm must try", "bsm sales angle", "what i'm testing",
    "industry watch", "priority reading", "2-minute read",
]

def _parse(brief: str) -> dict:
    out, cur = {k: [] for k in _SKEYS}, None
    for line in brief.split("\n"):
        s = line.strip()
        if not s: continue
        mk = next((k for k in _SKEYS if k in s.lower()), None)
        if mk: cur = mk; continue
        if cur:
            item = re.sub(r"^[-•]\s*", "", s).strip()
            if item: out[cur].append(item)
    return out


# ── YouTube card ───────────────────────────────────────────

def _yt_card(video: dict) -> str:
    thumb = _esc(video.get("thumbnail", ""))
    url   = _esc(video.get("url", "#"))
    title = _esc(video.get("title", "")[:65])
    ch    = _esc(video.get("channel", "YouTube"))
    if not thumb:
        return ""
    return f"""
<table cellpadding="0" cellspacing="0"
  style="width:270px;border-radius:12px;overflow:hidden;
  border:1px solid {_BDR};box-shadow:0 2px 8px rgba(0,0,0,0.08);">
<tr><td style="line-height:0;">
  <a href="{url}" target="_blank">
    <img src="{thumb}" width="270" height="152"
      style="width:270px;height:152px;object-fit:cover;display:block;border:0;">
  </a>
</td></tr>
<tr><td style="padding:14px 16px 16px;background:#fff;">
  <p style="margin:0 0 4px;font-size:10px;font-weight:700;color:{_ACC};
    text-transform:uppercase;letter-spacing:1.5px;font-family:{_FONT};">{ch}</p>
  <p style="margin:0 0 12px;font-size:13px;font-weight:700;color:{_T_HED};
    line-height:1.4;font-family:{_FONT};">
    <a href="{url}" target="_blank"
      style="color:{_T_HED};text-decoration:none;">{title}</a>
  </p>
  <a href="{url}" target="_blank"
    style="display:inline-block;background:#FF0000;color:#fff;font-size:11px;
    font-weight:700;padding:6px 14px;border-radius:6px;text-decoration:none;
    font-family:{_FONT};letter-spacing:0.2px;">
    &#x25B6;&nbsp; Watch on YouTube
  </a>
</td></tr>
</table>"""


# ── Main HTML builder ──────────────────────────────────────

def _build_html(brief_text: str, articles: list, display_date: str,
                first_name: str, from_name: str, seo_tip: dict | None = None,
                yt_video: dict | None = None, prompt_data: dict | None = None) -> str:

    S     = _parse(brief_text)
    must  = S.get("bsm must try", [])
    sales = S.get("bsm sales angle", [])
    watch = S.get("industry watch", [])
    prior = S.get("priority reading", [])
    close = S.get("2-minute read", [])

    cnt   = len(articles)
    imgs  = [a for a in articles if a.get("image")]
    feat  = imgs[0] if imgs else (articles[0] if articles else {})
    feat2 = imgs[1] if len(imgs) > 1 else feat
    g3    = (articles + [{}] * 3)[:3]

    def L(t): return _lnk(t, articles)

    # ── SHELL ──────────────────────────────────────────────
    H = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
  @keyframes pulse {{
    0%,100% {{ opacity:1; }} 50% {{ opacity:0.35; }}
  }}
  .pulse {{ animation: pulse 1.6s ease-in-out infinite; }}
</style>
</head>
<body style="margin:0;padding:0;background:{_PG_BG};font-family:{_FONT};">
<table width="100%" cellpadding="0" cellspacing="0" style="background:{_PG_BG};">
<tr><td align="center" style="padding:28px 12px 40px;">

<table width="640" cellpadding="0" cellspacing="0"
  style="max-width:640px;width:100%;background:{_WHITE};
  border-radius:16px;overflow:hidden;
  box-shadow:0 4px 32px rgba(0,0,0,0.10);
  border:1px solid {_BDR};">
<tr><td>
"""

    # ── 1. HEADER ──────────────────────────────────────────
    H += f"""
  <table width="100%" cellpadding="0" cellspacing="0"
    style="background:{_WHITE};border-bottom:1px solid {_BDR};">
  <tr>
    <td style="padding:16px 28px;">
      {_logo(32)}
    </td>
    <td style="padding:16px 28px;text-align:right;vertical-align:middle;">
      <p style="margin:0;font-size:11px;font-weight:600;color:{_T_MET};
        font-family:{_FONT};letter-spacing:0.3px;">{_esc(display_date)}</p>
    </td>
  </tr>
  </table>
"""

    # ── 2. HERO ────────────────────────────────────────────
    H += f"""
  <table width="100%" cellpadding="0" cellspacing="0"
    style="background:{_DARK};">
  <tr>
    <td style="padding:40px 32px 40px;vertical-align:middle;width:54%;">
      <p style="margin:0 0 14px;">
        <span class="pulse" style="display:inline-block;width:7px;height:7px;
          border-radius:50%;background:{_ACC};vertical-align:middle;
          margin-right:6px;">&#x25CF;</span>
        <span style="font-size:10px;font-weight:700;color:rgba(255,255,255,0.5);
          text-transform:uppercase;letter-spacing:2.5px;font-family:{_FONT};">
          Live Today</span>
      </p>
      <p style="margin:0 0 14px;font-size:34px;font-weight:800;color:{_WHITE};
        line-height:1.15;letter-spacing:-0.8px;font-family:{_FONT};">
        AI Daily<br>News Roundup
      </p>
      <p style="margin:0 0 28px;font-size:14px;color:rgba(255,255,255,0.6);
        line-height:1.75;font-family:{_FONT};">
        The latest AI updates, tools, and breakthroughs — curated every morning for the BSM team.
      </p>
      <a href="{_esc(feat.get('url','#') if feat else '#')}" target="_blank"
        style="display:inline-block;background:{_ACC};color:{_WHITE};
        font-size:13px;font-weight:700;padding:12px 24px;border-radius:8px;
        text-decoration:none;font-family:{_FONT};letter-spacing:0.2px;">
        Read Today's Top Story &rarr;
      </a>
    </td>
    <td style="padding:28px 24px 28px 0;vertical-align:middle;
      text-align:center;width:46%;">
      <div style="display:inline-block;border-radius:14px;overflow:hidden;
        border:2px solid rgba(214,60,47,0.35);line-height:0;">
        <img src="{_HERO_GIF_URL}" width="216" height="216"
          style="width:216px;height:216px;object-fit:cover;display:block;border:0;"
          alt="AI in motion">
      </div>
    </td>
  </tr>
  </table>
"""

    # ── 3. SNAPSHOT STATS ─────────────────────────────────
    stats = [
        (str(cnt), "Articles",      "Sourced today"),
        ("9",      "Sections",      "Fully briefed"),
        (os.environ.get("AI_BACKEND","Claude").capitalize(), "AI Engine", "Powers the brief"),
        ("BSM",    "Intelligence",  "Daily briefing"),
    ]
    H += f"""
  <table width="100%" cellpadding="0" cellspacing="0" style="background:{_ST_BG};">
  <tr><td style="padding:28px 28px 24px;">
    {_label("Daily Snapshot")}
    <table width="100%" cellpadding="0" cellspacing="0"><tr>
"""
    for val, lbl, sub in stats:
        H += f"""
      <td style="width:25%;padding:0 5px;vertical-align:top;">
        <table width="100%" cellpadding="0" cellspacing="0"
          style="background:{_WHITE};border-radius:10px;border:1px solid {_BDR};
          box-shadow:0 1px 4px rgba(0,0,0,0.05);">
        <tr><td style="padding:14px 12px;text-align:center;">
          <p style="margin:0 0 2px;font-size:22px;font-weight:800;color:{_T_HED};
            font-family:{_FONT};">{_esc(val)}</p>
          <p style="margin:0 0 2px;font-size:11px;font-weight:700;color:{_T_HED};
            font-family:{_FONT};">{_esc(lbl)}</p>
          <p style="margin:0;font-size:10px;color:{_T_MET};font-family:{_FONT};">{_esc(sub)}</p>
        </td></tr>
        </table>
      </td>"""
    H += "\n    </tr></table>\n  </td></tr>\n  </table>\n"

    # ── 4. PROMPT OF THE DAY ──────────────────────────────
    if prompt_data:
        use_case = _esc(prompt_data.get("use_case", "Today's AI Prompt"))
        prompt   = _esc(prompt_data.get("prompt", ""))
        example  = _esc(prompt_data.get("example_output", ""))
        H += f"""
  <table width="100%" cellpadding="0" cellspacing="0" style="background:{_WHITE};border-top:1px solid {_BDR};">
  <tr><td style="padding:32px 28px 28px;">
    {_label("Prompt of the Day")}
    <table width="100%" cellpadding="0" cellspacing="0" style="margin-top:16px;">
    <tr>
      <!-- Left: prompt copy box -->
      <td width="50%" valign="top" style="padding-right:12px;">
        <p style="margin:0 0 8px;font-size:10px;font-weight:700;color:{_T_MET};
          letter-spacing:0.8px;text-transform:uppercase;font-family:{_FONT};">
          {use_case}
        </p>
        <div style="background:{_ST_BG};border:1px solid {_BDR};border-left:3px solid {_ACC};
          border-radius:8px;padding:14px 16px;">
          <p style="margin:0;font-size:12.5px;line-height:1.65;color:{_T_BOD};
            font-family:{_FONT};font-style:italic;">
            &ldquo;{prompt}&rdquo;
          </p>
        </div>
        <p style="margin:10px 0 0;font-size:10px;color:{_T_MET};font-family:{_FONT};">
          Copy &amp; paste into ChatGPT or Claude
        </p>
      </td>
      <!-- Right: example output preview -->
      <td width="50%" valign="top" style="padding-left:12px;">
        <p style="margin:0 0 8px;font-size:10px;font-weight:700;color:{_T_MET};
          letter-spacing:0.8px;text-transform:uppercase;font-family:{_FONT};">
          Example Output
        </p>
        <div style="background:{_IC_BG};border:1px solid #C7D2FE;border-radius:8px;padding:14px 16px;">
          <table width="100%" cellpadding="0" cellspacing="0">
          <tr>
            <td width="24" valign="top">
              <div style="width:20px;height:20px;background:{_ACC};border-radius:50%;
                text-align:center;line-height:20px;font-size:11px;color:{_WHITE};
                font-weight:700;font-family:{_FONT};">AI</div>
            </td>
            <td valign="top" style="padding-left:8px;">
              <p style="margin:0;font-size:12px;line-height:1.6;color:{_T_BOD};
                font-family:{_FONT};">{example}</p>
            </td>
          </tr>
          </table>
        </div>
      </td>
    </tr>
    </table>
  </td></tr>
  </table>
"""

    # ── 5. AI INSIGHTS ────────────────────────────────────
    insights = [
        ("&#x26A1;", "BSM Must Try",    must[0]  if must            else "Explore today's top AI tool recommendation."),
        ("&#x1F4C8;","SEO / AI Impact", must[1]  if len(must) > 1  else "Understand how AI is reshaping organic search."),
        ("&#x1F3AF;","Action Step",     must[2]  if len(must) > 2  else "Apply these insights to your workflow today."),
    ]
    H += f"""
  <table width="100%" cellpadding="0" cellspacing="0" style="background:{_WHITE};">
  <tr><td style="padding:32px 28px 28px;">
    {_label("Today's Insights")}
    <p style="margin:0 0 24px;font-size:20px;font-weight:800;color:{_T_HED};
      font-family:{_FONT};letter-spacing:-0.3px;">Actionable AI Intelligence</p>
    <table width="100%" cellpadding="0" cellspacing="0"><tr>
"""
    for emoji, title, body in insights:
        H += f"""
      <td style="width:33%;padding:0 6px;vertical-align:top;">
        <table width="100%" cellpadding="0" cellspacing="0"
          style="background:{_ST_BG};border-radius:12px;border:1px solid {_BDR};
          border-top:3px solid {_ACC};height:100%;">
        <tr><td style="padding:18px 16px;">
          <p style="margin:0 0 10px;font-size:22px;">{emoji}</p>
          <p style="margin:0 0 8px;font-size:11px;font-weight:700;color:{_T_HED};
            text-transform:uppercase;letter-spacing:0.8px;font-family:{_FONT};">{_esc(title)}</p>
          <p style="margin:0;font-size:12px;color:{_T_BOD};line-height:1.65;
            font-family:{_FONT};">{L(body)}</p>
        </td></tr>
        </table>
      </td>"""
    H += "\n    </tr></table>\n  </td></tr>\n  </table>\n"

    # ── 6. INDUSTRY SPOTLIGHT ─────────────────────────────
    watch_txt = watch[0] if watch else "The AI landscape continues to evolve rapidly."
    H += f"""
  <table width="100%" cellpadding="0" cellspacing="0"
    style="background:{_ST_BG};border-top:1px solid {_BDR};
    border-bottom:1px solid {_BDR};">
  <tr>
    <td style="padding:32px 0 32px 28px;vertical-align:middle;width:50%;">
      {_label("Industry Spotlight")}
      <p style="margin:0 0 12px;font-size:20px;font-weight:800;color:{_T_HED};
        line-height:1.3;font-family:{_FONT};letter-spacing:-0.3px;">
        We Are Watching<br>AI Closely &#x1F310;
      </p>
      <p style="margin:0 0 20px;font-size:13px;color:{_T_BOD};line-height:1.75;
        font-family:{_FONT};">{L(watch_txt)}</p>
      {_btn("Read Full Story →", feat2.get("url", "#") if feat2 else "#")}
    </td>
    <td style="padding:28px 24px 28px 20px;vertical-align:middle;
      text-align:right;width:50%;">
      {_yt_card(yt_video) if yt_video else
       (f'<div style="border-radius:12px;overflow:hidden;display:inline-block;line-height:0;border:1px solid {_BDR};">{_img(feat2.get("image","") if feat2 else "",feat2.get("title","") if feat2 else "",270,152,0)}</div>' if (feat2 and feat2.get("image")) else "")}
    </td>
  </tr>
  </table>
"""

    # ── 7. CLIENT OPPORTUNITIES ───────────────────────────
    titles3 = ["Client Opportunity", "BSM Sales Angle", "Action Talking Point"]
    nums    = ["01", "02", "03"]
    H += f"""
  <table width="100%" cellpadding="0" cellspacing="0" style="background:{_WHITE};">
  <tr><td style="padding:32px 28px 28px;">
    {_label("For Your Clients")}
    <p style="margin:0 0 24px;font-size:20px;font-weight:800;color:{_T_HED};
      font-family:{_FONT};letter-spacing:-0.3px;">Today's Client Opportunities</p>
    <table width="100%" cellpadding="0" cellspacing="0">
"""
    for i, item in enumerate(sales[:3]):
        bdr = f"border-bottom:1px solid {_BDR};" if i < 2 else ""
        H += f"""
      <tr>
      <td style="padding:16px 0;{bdr}">
        <table width="100%" cellpadding="0" cellspacing="0"><tr>
          <td style="width:40px;vertical-align:top;padding-right:16px;padding-top:2px;">
            <table cellpadding="0" cellspacing="0">
            <tr><td align="center" valign="middle" width="36" height="36"
              style="background:{_ACC};border-radius:8px;width:36px;height:36px;
              font-size:12px;font-weight:800;color:{_WHITE};text-align:center;
              line-height:36px;font-family:{_FONT};">{nums[i]}</td></tr>
            </table>
          </td>
          <td style="vertical-align:top;">
            <p style="margin:0 0 2px;font-size:14px;font-weight:700;color:{_T_HED};
              font-family:{_FONT};">{titles3[i]}</p>
            <p style="margin:0 0 6px;font-size:10px;color:{_T_MET};
              font-family:{_FONT};letter-spacing:0.3px;">Client-Facing · BSM Intelligence</p>
            <p style="margin:0;font-size:13px;color:{_T_BOD};line-height:1.65;
              font-family:{_FONT};">{L(item)}</p>
          </td>
        </tr></table>
      </td>
      </tr>"""
    H += "\n    </table>\n  </td></tr>\n  </table>\n"

    # ── 8. LATEST NEWS GRID ───────────────────────────────
    H += f"""
  <table width="100%" cellpadding="0" cellspacing="0"
    style="background:{_ST_BG};border-top:1px solid {_BDR};">
  <tr><td style="padding:32px 28px 28px;">
    {_label("Latest News")}
    <p style="margin:0 0 20px;font-size:20px;font-weight:800;color:{_T_HED};
      font-family:{_FONT};letter-spacing:-0.3px;">Breaking AI Updates</p>
    <table width="100%" cellpadding="0" cellspacing="0"><tr>
"""
    col_w = 181
    img_h = 102  # 16:9
    for i, a in enumerate(g3):
        pad = "padding-left:9px;" if i > 0 else ""
        if a:
            ih   = _img(a.get("image",""), a.get("title",""), col_w, img_h, 0)
            titl = _esc(a.get("title","")[:65]) + ("…" if len(a.get("title","")) > 65 else "")
            src  = _esc(a.get("source","AI News")[:22])
            url  = _esc(a.get("url","#"))
            snip = _esc((a.get("content","")[:85]).replace("\n"," ")) + "…"
        else:
            ih   = ""
            titl = "AI Update"
            src  = "AI News"
            url  = "#"
            snip = "Latest developments from the AI landscape."

        H += f"""
      <td style="width:33%;vertical-align:top;{pad}">
        <table width="100%" cellpadding="0" cellspacing="0"
          style="background:{_WHITE};border-radius:12px;
          border:1px solid {_BDR};overflow:hidden;
          box-shadow:0 1px 6px rgba(0,0,0,0.05);">
          {"<tr><td style='line-height:0;'><a href='" + url + "' target='_blank'>" + ih + "</a></td></tr>" if ih else ""}
          <tr><td style="padding:12px 14px 16px;">
            <p style="margin:0 0 6px;font-size:9px;font-weight:700;color:{_ACC};
              text-transform:uppercase;letter-spacing:1.5px;font-family:{_FONT};">{src}</p>
            <p style="margin:0 0 6px;font-size:12px;font-weight:700;color:{_T_HED};
              line-height:1.4;font-family:{_FONT};">
              <a href="{url}" target="_blank"
                style="color:{_T_HED};text-decoration:none;">{titl}</a>
            </p>
            <p style="margin:0;font-size:11px;color:{_T_MET};line-height:1.55;
              font-family:{_FONT};">{snip}</p>
          </td></tr>
        </table>
      </td>"""
    H += "\n    </tr></table>\n  </td></tr>\n  </table>\n"

    # ── 9. SEO SPOTLIGHT ──────────────────────────────────
    if seo_tip:
        tip_img  = seo_tip.get("image","")
        tip_url  = _esc(seo_tip.get("url","#"))
        tip_titl = _esc(seo_tip.get("title","")[:100])
        tip_body = _esc(seo_tip.get("content","")[:200].replace("\n"," "))
        img_td   = (
            f'<td style="width:220px;vertical-align:top;padding-right:20px;line-height:0;">'
            f'<a href="{tip_url}" target="_blank">'
            f'<img src="{_esc(tip_img)}" width="210" '
            f'style="width:210px;height:140px;object-fit:cover;display:block;border:0;'
            f'border-radius:10px;"></a></td>'
        ) if tip_img else ""
        H += f"""
  <table width="100%" cellpadding="0" cellspacing="0"
    style="background:{_WHITE};border-top:1px solid {_BDR};">
  <tr><td style="padding:28px 28px;">
    <table width="100%" cellpadding="0" cellspacing="0"
      style="background:{_ST_BG};border-radius:12px;border:1px solid {_BDR};
      border-left:4px solid {_ACC};overflow:hidden;">
    <tr><td style="padding:22px 24px;">
      {_label("SEO Spotlight")}
      <p style="margin:0 0 16px;font-size:16px;font-weight:800;color:{_T_HED};
        font-family:{_FONT};">Latest from Chris Raulf</p>
      <table width="100%" cellpadding="0" cellspacing="0"><tr>
        {img_td}
        <td style="vertical-align:top;">
          <p style="margin:0 0 8px;font-size:14px;font-weight:700;line-height:1.4;
            font-family:{_FONT};">
            <a href="{tip_url}" target="_blank"
              style="color:{_T_HED};text-decoration:none;">{tip_titl}</a>
          </p>
          <p style="margin:0 0 14px;font-size:12px;color:{_T_BOD};line-height:1.65;
            font-family:{_FONT};">{tip_body}…</p>
          {_btn("Read Tip →", tip_url, sm=True)}
        </td>
      </tr></table>
    </td></tr>
    </table>
  </td></tr>
  </table>
"""

    # ── 10. PRIORITY READING ──────────────────────────────
    if prior:
        rows = ""
        for idx, p in enumerate(prior, 1):
            bdr = f"border-bottom:1px solid {_BDR};" if idx < len(prior) else ""
            rows += (
                f'<tr><td style="padding:14px 0;{bdr}">'
                f'<table cellpadding="0" cellspacing="0" width="100%"><tr>'
                f'<td style="width:28px;vertical-align:top;padding-top:1px;">'
                f'<span style="display:inline-block;width:22px;height:22px;'
                f'border-radius:50%;background:{_IC_BG};text-align:center;'
                f'line-height:22px;font-size:10px;font-weight:800;color:{_ACC};'
                f'font-family:{_FONT};">{idx}</span></td>'
                f'<td style="vertical-align:top;padding-left:10px;">'
                f'<p style="margin:0;font-size:13px;color:{_T_BOD};line-height:1.65;'
                f'font-family:{_FONT};">{L(p)}</p></td>'
                f'</tr></table></td></tr>'
            )
        H += f"""
  <table width="100%" cellpadding="0" cellspacing="0"
    style="background:{_ST_BG};border-top:1px solid {_BDR};">
  <tr><td style="padding:28px 28px;">
    {_label("Priority Reading")}
    <p style="margin:0 0 20px;font-size:18px;font-weight:800;color:{_T_HED};
      font-family:{_FONT};letter-spacing:-0.3px;">Must-Read This Week</p>
    <table width="100%" cellpadding="0" cellspacing="0"
      style="background:{_WHITE};border-radius:12px;border:1px solid {_BDR};
      box-shadow:0 1px 4px rgba(0,0,0,0.04);">
    <tr><td style="padding:0 20px;">
      <table width="100%" cellpadding="0" cellspacing="0">{rows}</table>
    </td></tr>
    </table>
  </td></tr>
  </table>
"""

    # ── 11. 2-MINUTE READ ─────────────────────────────────
    if close:
        H += f"""
  <table width="100%" cellpadding="0" cellspacing="0" style="background:{_DARK};">
  <tr><td style="padding:32px 32px;">
    <table cellpadding="0" cellspacing="0">
    <tr><td style="background:{_ACC};border-radius:6px;padding:4px 12px;margin-bottom:14px;display:inline-block;">
      <p style="margin:0;font-size:9px;font-weight:700;color:{_WHITE};
        text-transform:uppercase;letter-spacing:2px;font-family:{_FONT};">
        2&#8209;Minute Read
      </p>
    </td></tr>
    </table>
    <p style="margin:14px 0 0;font-size:16px;color:rgba(255,255,255,0.85);
      line-height:1.8;font-style:italic;font-family:{_FONT};">{L(close[0])}</p>
  </td></tr>
  </table>
"""

    # ── 12. SIGN-OFF ───────────────────────────────────────
    H += f"""
  <table width="100%" cellpadding="0" cellspacing="0" style="background:{_ACC};">
  <tr><td style="padding:28px 32px;">
    <p style="margin:0 0 6px;font-size:14px;color:rgba(255,255,255,0.9);
      line-height:1.7;font-family:{_FONT};">
      If you're building in SEO, AI, or automation — this is your edge.
    </p>
    <p style="margin:0;font-size:16px;font-weight:700;color:{_WHITE};
      font-family:{_FONT};">&#8212; {_esc(from_name)}</p>
  </td></tr>
  </table>
"""

    # ── 13. FOOTER ─────────────────────────────────────────
    H += f"""
  <table width="100%" cellpadding="0" cellspacing="0"
    style="background:{_WHITE};border-top:1px solid {_BDR};">
  <tr><td style="padding:28px 28px 20px;">
    <table width="100%" cellpadding="0" cellspacing="0"><tr>
      <td style="width:40%;vertical-align:top;padding-right:20px;">
        <div style="margin-bottom:12px;">{_logo(28)}</div>
        <p style="margin:0;font-size:12px;color:{_T_BOD};line-height:1.7;
          font-family:{_FONT};">AI-powered daily intelligence for SEO professionals.
          Curated by Boulder SEO Marketing.</p>
      </td>
      <td style="width:30%;vertical-align:top;padding-right:16px;">
        <p style="margin:0 0 10px;font-size:12px;font-weight:700;color:{_T_HED};
          font-family:{_FONT};">Contact</p>
        <p style="margin:0 0 4px;font-size:11px;color:{_T_BOD};font-family:{_FONT};">
          +1 (720) 594-6224</p>
        <p style="margin:0 0 4px;font-size:11px;color:{_T_BOD};font-family:{_FONT};">
          sean@boulderseomarketing.com</p>
        <p style="margin:0;font-size:11px;color:{_ACC};font-weight:600;
          font-family:{_FONT};">boulderseomarketing.com</p>
      </td>
      <td style="width:30%;vertical-align:top;">
        <p style="margin:0 0 10px;font-size:12px;font-weight:700;color:{_T_HED};
          font-family:{_FONT};">Quick Links</p>
        {"".join(f'<p style="margin:0 0 4px;"><a href="{u}" target="_blank" style="font-size:11px;color:{_T_BOD};text-decoration:none;font-family:{_FONT};">{l}</a></p>' for l, u in [("Homepage","https://boulderseomarketing.com"),("About Us","https://boulderseomarketing.com/about"),("AI Tools","https://microseo.ai"),("Blog","https://boulderseomarketing.com/blog"),("Contact","https://boulderseomarketing.com/contact")])}
      </td>
    </tr></table>
  </td></tr>
  </table>

  <table width="100%" cellpadding="0" cellspacing="0"
    style="background:{_ST_BG};border-top:1px solid {_BDR};
    border-radius:0 0 16px 16px;overflow:hidden;">
  <tr><td style="padding:12px 28px;text-align:center;">
    <p style="margin:0;font-size:11px;color:{_T_MET};font-family:{_FONT};">
      &copy; 2026 Boulder SEO Marketing &nbsp;&middot;&nbsp; AI Intelligence Officer
      &nbsp;&middot;&nbsp; {_esc(display_date)}
    </p>
  </td></tr>
  </table>
"""

    H += """
</td></tr>
</table>

</td></tr>
</table>
</body>
</html>"""

    return H


# ── Plain text fallback ────────────────────────────────────

def _build_plain(brief_text: str, first_name: str, from_name: str) -> str:
    return (f"Hey {first_name},\n\nHere's your AI intelligence briefing:\n\n"
            f"---\n\n{brief_text}\n\n---\n\n"
            f"If you're building in SEO, AI, or automation — this is your edge.\n\n"
            f"– {from_name}\nBoulder SEO Marketing")


# ── Send ───────────────────────────────────────────────────

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


def send_newsletter(subject: str, brief_text: str,
                    articles: list, display_date: str,
                    seo_tip: dict | None = None,
                    yt_video: dict | None = None,
                    prompt_data: dict | None = None) -> None:
    config    = json.loads(CONFIG_FILE.read_text())
    ec        = config.get("email", {})
    if not ec.get("from_address"):
        raise ValueError("config.json missing email.from_address")
    if not ec.get("recipients"):
        raise ValueError("config.json missing email.recipients")
    from_name = ec.get("from_name", "Sean")
    from_str  = f"{from_name} <{ec['from_address']}>"
    reply_to  = ec.get("reply_to", ec["from_address"])
    logo_data = _LOGO_FILE.read_bytes() if _LOGO_FILE.exists() else None
    use_resend = bool(os.environ.get("RESEND_API_KEY"))

    for recip in ec["recipients"]:
        fn    = recip.get("first_name", "there")
        to    = recip["email"]
        html  = _build_html(brief_text, articles, display_date, fn, from_name, seo_tip, yt_video, prompt_data)
        plain = _build_plain(brief_text, fn, from_name)

        if use_resend:
            _send_resend(subject, from_str, to, reply_to, html, plain, logo_data)
        else:
            _send_smtp(subject, from_str, to, reply_to, html, plain, logo_data,
                       ec["smtp_host"], ec["smtp_port"])
        print(f"  ✓ Sent to {to}")
