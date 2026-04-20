"""
Email sender — pixel-perfect codeflair-style AI newsletter.
Table-based layout, inline CSS, Gmail-compatible.
"""

import base64, os, re, smtplib, json
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

CONFIG_FILE = Path(__file__).parent / "config.json"
_LOGO_FILE  = Path(__file__).parent / "bsm_logo.png"

# ── Colour palette (extracted from reference) ─────────────
_RED     = "#d63c2f"
_WHITE   = "#ffffff"
_PG_BG   = "#9aaabb"    # muted blue-gray canvas
_ST_BG   = "#fef3f1"    # stats section warm beige/pink
_IC_BG   = "#ffecea"    # icon circle fill (light rose)
_LT_BG   = "#f8f8f8"    # alternating light sections
_BDR     = "#e8e8e8"
_T_HED   = "#1a1a1a"
_T_BOD   = "#555555"
_T_MET   = "#999999"

# ── Helpers ────────────────────────────────────────────────

def _esc(t: str) -> str:
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def _lnk(text: str, arts: list) -> str:
    def r(m):
        idx = int(m.group(1)) - 1
        if 0 <= idx < len(arts):
            u = _esc(arts[idx].get("url", "#"))
            t = _esc(arts[idx].get("title", m.group(0)))
            return f'<a href="{u}" style="color:{_RED};text-decoration:none;font-weight:600;" target="_blank">{t}</a>'
        return m.group(0)
    return re.sub(r"\[(\d+)\]", r, text)

def _logo(h: int = 36) -> str:
    if _LOGO_FILE.exists():
        b64 = base64.b64encode(_LOGO_FILE.read_bytes()).decode()
        return f'<img src="data:image/png;base64,{b64}" height="{h}" style="display:block;" alt="BSM">'
    return f'<span style="color:{_RED};font-size:22px;font-weight:900;font-family:Arial;">BSM</span>'

def _img(url: str, alt: str = "", w: int = 200, h: int = 140, r: int = 10) -> str:
    if not url:
        return f'<div style="width:{w}px;height:{h}px;border-radius:{r}px;background:#e4e8ee;"></div>'
    return (f'<img src="{_esc(url)}" alt="{_esc(alt[:40])}" width="{w}" '
            f'style="width:{w}px;height:{h}px;object-fit:cover;display:block;border:0;border-radius:{r}px;">')

def _btn(label: str, url: str = "#", sm: bool = False) -> str:
    p  = "7px 15px" if sm else "11px 26px"
    fs = "11px"     if sm else "13px"
    return (f'<a href="{_esc(url)}" target="_blank" '
            f'style="display:inline-block;background:{_RED};color:#fff;font-size:{fs};'
            f'font-weight:700;padding:{p};border-radius:6px;text-decoration:none;'
            f'letter-spacing:0.3px;">{_esc(label)}</a>')

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


# ── Main HTML builder ──────────────────────────────────────

def _build_html(brief_text: str, articles: list, display_date: str,
                first_name: str, from_name: str) -> str:

    S      = _parse(brief_text)
    hot    = S["what's hot today"]
    must   = S["bsm must try"]
    sales  = S["bsm sales angle"]
    watch  = S["industry watch"]
    prior  = S["priority reading"]
    close  = S["2-minute read"]
    claude = S["claude insider"]

    cnt   = len(articles)
    imgs  = [a for a in articles if a.get("image")]
    feat  = imgs[0] if imgs else (articles[0] if articles else {})
    feat2 = imgs[1] if len(imgs) > 1 else feat
    g3    = (imgs + [{}] * 3)[:3]   # always 3 items, padded with {}

    def L(t): return _lnk(t, articles)

    # ── SHELL ──────────────────────────────────────────────
    H = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:{_PG_BG};font-family:Arial,Helvetica,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" border="0" style="background:{_PG_BG};">
<tr><td align="center" style="padding:32px 12px 40px;">

<table width="640" cellpadding="0" cellspacing="0" border="0"
  style="max-width:640px;width:100%;background:{_WHITE};border-radius:20px;overflow:hidden;border:1px solid #c8d2dc;">
<tr><td>
"""

    # ── 1. NAV ─────────────────────────────────────────────
    H += f"""
  <table width="100%" cellpadding="0" cellspacing="0" style="background:{_WHITE};border-bottom:1px solid #eeeeee;">
  <tr><td style="padding:14px 26px;">
    <table cellpadding="0" cellspacing="0"><tr>
      <td style="vertical-align:middle;padding-right:14px;">{_logo(34)}</td>
      <td style="vertical-align:middle;border-left:1px solid #dddddd;padding-left:14px;">
        <span style="font-size:12px;color:{_RED};font-weight:700;margin-right:14px;">Home</span>
        <span style="font-size:12px;color:{_T_MET};margin-right:14px;">AI News</span>
        <span style="font-size:12px;color:{_T_MET};margin-right:14px;">Tools</span>
        <span style="font-size:12px;color:{_T_MET};margin-right:14px;">Trends</span>
        <span style="font-size:12px;color:{_T_MET};">Contact</span>
      </td>
    </tr></table>
  </td></tr>
  </table>
"""

    # ── 2. HERO ────────────────────────────────────────────
    blob_url = feat.get("image", "") if feat else ""
    blob_href = feat.get("url", "#") if feat else "#"
    if blob_url:
        blob_html = (
            f'<div style="display:inline-block;width:230px;height:230px;'
            f'border-radius:62% 38% 46% 54% / 60% 44% 56% 40%;overflow:hidden;">'
            f'<a href="{_esc(blob_href)}" target="_blank">'
            f'<img src="{_esc(blob_url)}" width="230" '
            f'style="width:230px;height:230px;object-fit:cover;display:block;" alt=""></a></div>'
        )
    else:
        blob_html = (
            f'<div style="display:inline-block;width:230px;height:230px;'
            f'border-radius:62% 38% 46% 54% / 60% 44% 56% 40%;'
            f'background:{_RED};text-align:center;vertical-align:middle;">'
            f'<p style="margin:0;padding:80px 20px 0;font-size:14px;font-weight:700;'
            f'color:#fff;line-height:1.5;">AI Daily<br>Intelligence</p></div>'
        )

    H += f"""
  <table width="100%" cellpadding="0" cellspacing="0" style="background:{_WHITE};">
  <tr>
    <td style="padding:38px 28px;vertical-align:middle;width:54%;">
      <p style="margin:0 0 16px;font-size:30px;font-weight:900;color:{_T_HED};line-height:1.2;">
        AI Daily<br>News Roundup
      </p>
      <p style="margin:0 0 24px;font-size:13px;color:{_T_BOD};line-height:1.75;">
        Stay ahead with the latest AI updates, tools, and breakthroughs — curated every morning for the BSM team.
      </p>
      {_btn("Explore Today's News")}
    </td>
    <td style="padding:28px 24px 28px 0;vertical-align:middle;text-align:right;width:46%;">
      {blob_html}
    </td>
  </tr>
  </table>
"""

    # ── 3. STATS (warm beige bg) ───────────────────────────
    stats = [
        (str(cnt),  "Sources Today",  "Articles collected across the AI landscape today."),
        ("9",       "Brief Sections", "Structured categories covering all major AI topics."),
        ("Claude",  "AI Powered",     "Anthropic's Sonnet model generates every insight.", True),
        ("BSM",     "Intelligence",   "Boulder SEO Marketing daily AI briefing."),
    ]
    H += f"""
  <table width="100%" cellpadding="0" cellspacing="0" style="background:{_ST_BG};">
  <tr><td style="padding:34px 28px;">
    <p style="margin:0 0 2px;font-size:20px;font-weight:700;color:{_RED};text-align:center;">Daily AI Highlights</p>
    <p style="margin:0 0 24px;font-size:12px;color:{_T_MET};text-align:center;">{_esc(display_date)}</p>
    <table width="100%" cellpadding="0" cellspacing="0"><tr>
"""
    for val, lbl, desc, *hi in stats:
        red = bool(hi)
        bg  = _RED  if red else _WHITE
        tc  = _WHITE if red else _T_HED
        sc  = "rgba(255,255,255,0.8)" if red else _T_MET
        brd = "" if red else f"border:1.5px solid {_BDR};"
        H += f"""      <td style="width:25%;padding:0 5px;vertical-align:top;">
        <div style="background:{bg};{brd}border-radius:12px;padding:18px 10px;text-align:center;">
          <p style="margin:0 0 4px;font-size:22px;font-weight:900;color:{tc};">{_esc(val)}</p>
          <p style="margin:0 0 8px;font-size:11px;font-weight:700;color:{tc};text-transform:uppercase;letter-spacing:0.5px;">{_esc(lbl)}</p>
          <p style="margin:0;font-size:11px;color:{sc};line-height:1.5;">{_esc(desc)}</p>
        </div>
      </td>
"""
    H += "    </tr></table>\n  </td></tr>\n  </table>\n"

    # ── 4. SERVICES / AI INSIGHTS ─────────────────────────
    svcs = [
        ("🤖", "BSM Must Try",   must[0]  if must            else "Explore today's top AI tool recommendation."),
        ("📊", "SEO / AI Impact", must[1]  if len(must) > 1  else "Understand how AI is reshaping organic search."),
        ("🚀", "Action Step",    must[2]  if len(must) > 2  else "Apply these insights to your client workflow today."),
    ]
    H += f"""
  <table width="100%" cellpadding="0" cellspacing="0" style="background:{_WHITE};">
  <tr><td style="padding:36px 28px;">
    <p style="margin:0 0 8px;font-size:20px;font-weight:800;color:{_T_HED};">Today's AI Insights</p>
    <p style="margin:0 0 26px;font-size:13px;color:{_T_BOD};line-height:1.65;">
      The most actionable intelligence for BSM and your SEO clients — straight from today's feeds.
    </p>
    <table width="100%" cellpadding="0" cellspacing="0"><tr>
"""
    for icon, title, body in svcs:
        H += f"""      <td style="width:33%;padding:0 10px;vertical-align:top;text-align:center;">
        <div style="width:58px;height:58px;border-radius:50%;background:{_IC_BG};
          margin:0 auto 12px;text-align:center;line-height:58px;font-size:26px;">{icon}</div>
        <p style="margin:0 0 8px;font-size:11px;font-weight:700;color:{_T_HED};
          text-transform:uppercase;letter-spacing:0.5px;">{_esc(title)}</p>
        <p style="margin:0;font-size:12px;color:{_T_BOD};line-height:1.55;">{L(body)}</p>
      </td>
"""
    H += f"""    </tr></table>
    <p style="margin:26px 0 0;text-align:left;">{_btn("Explore All Insights")}</p>
  </td></tr>
  </table>
"""

    # ── 5. FEATURE / HIRING-STYLE SPLIT ───────────────────
    watch_txt = watch[0] if watch else "The AI landscape continues to evolve rapidly, with major implications for SEO and GEO strategy."
    H += f"""
  <table width="100%" cellpadding="0" cellspacing="0"
    style="background:{_LT_BG};border-top:1px solid {_BDR};border-bottom:1px solid {_BDR};">
  <tr>
    <td style="padding:32px 0 32px 28px;vertical-align:middle;width:50%;">
      <p style="margin:0 0 12px;font-size:20px;font-weight:900;color:{_T_HED};line-height:1.3;">
        We Are Watching<br>AI Closely 🌐
      </p>
      <p style="margin:0 0 20px;font-size:13px;color:{_T_BOD};line-height:1.7;">{L(watch_txt)}</p>
      {_btn("Read Full Story", feat2.get("url", "#") if feat2 else "#")}
    </td>
    <td style="padding:28px 24px 28px 20px;vertical-align:middle;text-align:right;width:50%;">
      <div style="border-radius:14px;overflow:hidden;display:inline-block;">
        {_img(feat2.get("image", "") if feat2 else "", feat2.get("title", "") if feat2 else "", 270, 190, 14)}
      </div>
    </td>
  </tr>
  </table>
"""

    # ── 6. OPEN POSITIONS (BSM Sales Angle) ───────────────
    icons3 = ["💡", "📈", "🎯"]
    titles3 = ["Client Opportunity", "BSM Sales Angle", "Action Talking Point"]
    H += f"""
  <table width="100%" cellpadding="0" cellspacing="0" style="background:{_WHITE};">
  <tr><td style="padding:34px 28px;">
    <p style="margin:0 0 20px;font-size:18px;font-weight:800;color:{_T_HED};">Today's Client Opportunities:</p>
    <table width="100%" cellpadding="0" cellspacing="0">
"""
    for i, item in enumerate(sales[:3]):
        sep = f"border-bottom:1px solid {_BDR};" if i < 2 else ""
        H += f"""      <tr style="{sep}">
        <td style="padding:16px 0;">
          <table width="100%" cellpadding="0" cellspacing="0"><tr>
            <td style="width:44px;vertical-align:top;padding-right:14px;">
              <div style="width:38px;height:38px;background:{_RED};border-radius:9px;
                text-align:center;line-height:38px;font-size:20px;">{icons3[i]}</div>
            </td>
            <td style="vertical-align:top;">
              <p style="margin:0 0 3px;font-size:14px;font-weight:700;color:{_T_HED};">{titles3[i]}</p>
              <p style="margin:0 0 2px;font-size:11px;color:{_T_MET};">📍 Client-Facing · BSM Intelligence</p>
              <p style="margin:6px 0 0;font-size:13px;color:{_T_BOD};line-height:1.55;">{L(item)}</p>
            </td>
            <td style="vertical-align:middle;padding-left:14px;text-align:right;white-space:nowrap;">
              {_btn("Use Now →", sm=True)}
            </td>
          </tr></table>
        </td>
      </tr>
"""
    H += "    </table>\n  </td></tr>\n  </table>\n"

    # ── 7. LATEST NEWS GRID ────────────────────────────────
    H += f"""
  <table width="100%" cellpadding="0" cellspacing="0"
    style="background:{_LT_BG};border-top:1px solid {_BDR};">
  <tr><td style="padding:32px 28px;">
    <p style="margin:0 0 20px;font-size:18px;font-weight:800;color:{_T_HED};">Latest AI News</p>
    <table width="100%" cellpadding="0" cellspacing="0"><tr>
"""
    for i, a in enumerate(g3):
        pad = "padding-left:10px;" if i > 0 else ""
        if a:
            ih   = _img(a.get("image", ""), a.get("title", ""), 182, 122, 10)
            titl = _esc(a.get("title", "")[:65]) + ("…" if len(a.get("title", "")) > 65 else "")
            src  = _esc(a.get("source", "AI News")[:22])
            url  = _esc(a.get("url", "#"))
            snip = _esc((a.get("content", "")[:90]).replace("\n", " ")) + "…"
        else:
            ih   = _img("", "", 182, 122, 10)
            titl = "AI Update"
            src  = "AI News"
            url  = "#"
            snip = "Latest developments from the AI landscape."
        H += f"""      <td style="width:33%;vertical-align:top;{pad}">
        <a href="{url}" target="_blank" style="text-decoration:none;">{ih}</a>
        <p style="margin:10px 0 3px;font-size:13px;font-weight:700;color:{_T_HED};line-height:1.4;">
          <a href="{url}" target="_blank" style="color:{_T_HED};text-decoration:none;">{titl}</a>
        </p>
        <p style="margin:0 0 5px;font-size:10px;color:{_RED};font-weight:700;
          text-transform:uppercase;letter-spacing:0.5px;">{src}</p>
        <p style="margin:0;font-size:11px;color:{_T_MET};line-height:1.5;">{snip}</p>
      </td>
"""
    H += "    </tr></table>\n  </td></tr>\n  </table>\n"

    # ── 8. PRIORITY READING (if available) ────────────────
    if prior:
        rows = "".join(
            f'<p style="margin:0 0 10px;font-size:13px;color:{_T_BOD};line-height:1.6;'
            f'padding:12px 14px;background:{_WHITE};border-radius:8px;border:1px solid {_BDR};">'
            f'<span style="color:{_RED};font-weight:700;margin-right:6px;">📚</span>{L(p)}</p>'
            for p in prior
        )
        H += f"""
  <table width="100%" cellpadding="0" cellspacing="0" style="background:{_ST_BG};border-top:1px solid {_BDR};">
  <tr><td style="padding:28px 28px;">
    <p style="margin:0 0 16px;font-size:16px;font-weight:800;color:{_T_HED};">Priority Reading</p>
    {rows}
  </td></tr>
  </table>
"""

    # ── 9. 2-MINUTE READ ──────────────────────────────────
    if close:
        H += f"""
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#1a1a3e;">
  <tr><td style="padding:26px 28px;">
    <p style="margin:0 0 6px;font-size:10px;font-weight:700;color:{_RED};
      text-transform:uppercase;letter-spacing:2px;">⚡ 2-Minute Read</p>
    <p style="margin:0;font-size:15px;color:#e8eaf0;line-height:1.7;font-style:italic;">{L(close[0])}</p>
  </td></tr>
  </table>
"""

    # ── 10. SIGN-OFF ───────────────────────────────────────
    H += f"""
  <table width="100%" cellpadding="0" cellspacing="0" style="background:{_RED};">
  <tr><td style="padding:28px 28px;">
    <p style="margin:0 0 6px;font-size:15px;color:#fff;line-height:1.6;">
      If you're building in SEO, AI, or automation — this is your edge.
    </p>
    <p style="margin:0;font-size:16px;font-weight:700;color:#fff;">– {_esc(from_name)}</p>
  </td></tr>
  </table>
"""

    # ── 11. FOOTER ─────────────────────────────────────────
    links = ["Homepage", "About Us", "AI Tools", "Jobs", "Blog", "Contact"]
    social = [("f","#3b5998"),("G+","#dd4b39"),("tw","#1da1f2"),("in","#0077b5")]
    social_html = "".join(
        f'<td style="padding-right:6px;">'
        f'<a href="#" style="display:inline-block;width:30px;height:30px;border-radius:50%;'
        f'background:{c};text-align:center;line-height:30px;font-size:11px;font-weight:700;'
        f'color:#fff;text-decoration:none;">{l}</a></td>'
        for l, c in social
    )
    link_html = "".join(
        f'<p style="margin:0 0 6px;"><a href="#" style="font-size:12px;color:{_T_BOD};text-decoration:none;">{l}</a></p>'
        for l in links
    )
    H += f"""
  <table width="100%" cellpadding="0" cellspacing="0" style="background:{_WHITE};border-top:1px solid {_BDR};">
  <tr><td style="padding:32px 28px;">
    <table width="100%" cellpadding="0" cellspacing="0"><tr>
      <td style="width:38%;vertical-align:top;padding-right:24px;">
        <div style="margin-bottom:12px;">{_logo(32)}</div>
        <p style="margin:0 0 16px;font-size:12px;color:{_T_BOD};line-height:1.65;">
          AI-powered daily intelligence for SEO professionals. Curated by Boulder SEO Marketing every morning.
        </p>
        <table cellpadding="0" cellspacing="0"><tr>{social_html}</tr></table>
      </td>
      <td style="width:31%;vertical-align:top;padding-right:20px;">
        <p style="margin:0 0 12px;font-size:13px;font-weight:700;color:{_T_HED};">Contact Info</p>
        <p style="margin:0 0 6px;font-size:12px;color:{_T_BOD};">Ph: +1 (720) 594-6224</p>
        <p style="margin:0 0 6px;font-size:12px;color:{_T_BOD};">Email: sean@boulderseomarketing.com</p>
        <p style="margin:0;font-size:12px;color:{_RED};font-weight:600;">boulderseomarketing.com</p>
      </td>
      <td style="width:31%;vertical-align:top;">
        <p style="margin:0 0 12px;font-size:13px;font-weight:700;color:{_T_HED};">Quick Link</p>
        {link_html}
      </td>
    </tr></table>
  </td></tr>
  </table>

  <!-- Footer bottom bar -->
  <table width="100%" cellpadding="0" cellspacing="0"
    style="background:#f2f4f6;border-top:1px solid {_BDR};border-radius:0 0 20px 20px;overflow:hidden;">
  <tr><td style="padding:13px 28px;text-align:center;">
    <p style="margin:0;font-size:11px;color:{_T_MET};">
      © 2026 Boulder SEO Marketing &nbsp;·&nbsp; AI Intelligence Officer &nbsp;·&nbsp; {_esc(display_date)}
    </p>
  </td></tr>
  </table>
"""

    # ── Close shell ────────────────────────────────────────
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

def send_newsletter(subject: str, brief_text: str,
                    articles: list, display_date: str) -> None:
    config    = json.loads(CONFIG_FILE.read_text())
    ec        = config["email"]
    from_name = ec.get("from_name", "Sean")

    for recip in ec["recipients"]:
        fn  = recip.get("first_name", "there")
        msg = MIMEMultipart("alternative")
        msg["Subject"]  = subject
        msg["From"]     = f"{from_name} <{ec['from_address']}>"
        msg["To"]       = recip["email"]
        msg["Reply-To"] = ec.get("reply_to", ec["from_address"])
        msg.attach(MIMEText(_build_plain(brief_text, fn, from_name), "plain"))
        msg.attach(MIMEText(_build_html(brief_text, articles, display_date, fn, from_name), "html"))

        with smtplib.SMTP(ec["smtp_host"], ec["smtp_port"]) as s:
            s.ehlo(); s.starttls()
            s.login(os.environ["SMTP_USER"], os.environ["SMTP_PASSWORD"])
            s.sendmail(ec["from_address"], recip["email"], msg.as_string())
        print(f"  ✓ Sent to {recip['email']}")
