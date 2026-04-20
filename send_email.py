"""
Email sender — Premium AI newsletter template.
Corporate tech style: soft blue-gray background, white rounded container,
red accent, neural-network hero, article cards, stats bar, dark footer.
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

# ── Colour system ──────────────────────────────────────────
_RED       = "#ff3b3b"
_NAVY      = "#1a1a3e"
_NAVY2     = "#0d0d2b"
_WHITE     = "#ffffff"
_BG        = "#eef2f7"       # soft blue-gray page background
_CARD      = "#ffffff"
_CARD_ALT  = "#f8faff"
_BORDER    = "#dde4f0"
_DIV       = "#f0f4fb"
_T_HEAD    = "#1a1a2e"
_T_BODY    = "#4a5568"
_T_META    = "#8896b0"
_BLUE_PILL = "#eef2ff"       # tag background


# ── SVG assets ─────────────────────────────────────────────

def _neural_svg() -> str:
    """Static neural-network illustration for the hero."""
    layers = [
        [(38, 32), (38, 72), (38, 112)],
        [(98, 18), (98, 52), (98, 86), (98, 120)],
        [(158, 32), (158, 72), (158, 112)],
        [(198, 52), (198, 92)],
    ]
    lines, nodes = [], []
    for i in range(len(layers) - 1):
        for x1, y1 in layers[i]:
            for x2, y2 in layers[i + 1]:
                op = round(0.15 + ((x1 + y2) % 5) * 0.07, 2)
                lines.append(
                    f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" '
                    f'stroke="{_RED}" stroke-width="1.2" stroke-opacity="{op}"/>'
                )
    for li, layer in enumerate(layers):
        for xi, (x, y) in enumerate(layer):
            active = (li + xi) % 3 == 0
            fill = _RED if active else "#5a6fa0"
            if active:
                nodes.append(f'<circle cx="{x}" cy="{y}" r="11" fill="{_RED}" fill-opacity="0.12"/>')
            nodes.append(f'<circle cx="{x}" cy="{y}" r="5" fill="{fill}"/>')
    grid = '<pattern id="g" width="18" height="18" patternUnits="userSpaceOnUse"><path d="M18 0L0 0 0 18" fill="none" stroke="#ffffff" stroke-width="0.25"/></pattern>'
    return (
        '<svg width="228" height="148" viewBox="0 0 228 148" xmlns="http://www.w3.org/2000/svg">'
        f'<defs>{grid}</defs>'
        f'<rect width="228" height="148" rx="14" fill="{_NAVY2}"/>'
        '<rect width="228" height="148" rx="14" fill="url(#g)"/>'
        + "".join(lines) + "".join(nodes)
        + f'<text x="114" y="142" text-anchor="middle" font-size="8" fill="{_T_META}" font-family="Arial">NEURAL NETWORK AI</text>'
        "</svg>"
    )


def _icon_svg(kind: str) -> str:
    """Mini icon SVGs for stats and insight cards."""
    icons = {
        "sources":  f'<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><circle cx="12" cy="12" r="10" fill="{_RED}" fill-opacity="0.12"/><path d="M8 12h8M12 8v8" stroke="{_RED}" stroke-width="2" stroke-linecap="round"/></svg>',
        "sections": f'<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><circle cx="12" cy="12" r="10" fill="{_NAVY}" fill-opacity="0.1"/><rect x="7" y="8" width="10" height="2" rx="1" fill="{_NAVY}"/><rect x="7" y="12" width="7" height="2" rx="1" fill="{_NAVY}"/><rect x="7" y="16" width="9" height="2" rx="1" fill="{_NAVY}"/></svg>',
        "tools":    f'<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><circle cx="12" cy="12" r="10" fill="#7c3aed" fill-opacity="0.1"/><path d="M9.5 9.5a3.5 3.5 0 0 1 5 5l3 3-1.5 1.5-3-3a3.5 3.5 0 0 1-5-5z" stroke="#7c3aed" stroke-width="1.5"/></svg>',
        "insight":  f'<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><circle cx="12" cy="12" r="10" fill="#059669" fill-opacity="0.1"/><path d="M12 7v5l3 3" stroke="#059669" stroke-width="2" stroke-linecap="round"/></svg>',
        "brain":    f'<svg width="28" height="28" viewBox="0 0 28 28" fill="none" xmlns="http://www.w3.org/2000/svg"><rect width="28" height="28" rx="8" fill="{_RED}"/><circle cx="10" cy="11" r="3" stroke="white" stroke-width="1.5"/><circle cx="18" cy="11" r="3" stroke="white" stroke-width="1.5"/><path d="M7 17c0-2 3-3 7-3s7 1 7 3" stroke="white" stroke-width="1.5" stroke-linecap="round"/></svg>',
        "prompt":   f'<svg width="28" height="28" viewBox="0 0 28 28" fill="none" xmlns="http://www.w3.org/2000/svg"><rect width="28" height="28" rx="8" fill="#7c3aed"/><path d="M8 10h12M8 14h8M8 18h10" stroke="white" stroke-width="1.8" stroke-linecap="round"/></svg>',
        "tip":      f'<svg width="28" height="28" viewBox="0 0 28 28" fill="none" xmlns="http://www.w3.org/2000/svg"><rect width="28" height="28" rx="8" fill="#059669"/><path d="M14 7v3M14 18v3M7 14h3M18 14h3" stroke="white" stroke-width="1.8" stroke-linecap="round"/><circle cx="14" cy="14" r="4" stroke="white" stroke-width="1.8"/></svg>',
    }
    return icons.get(kind, "")


# ── Helpers ────────────────────────────────────────────────

def _esc(t: str) -> str:
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _refs_to_links(text: str, articles: list[dict]) -> str:
    def replace(m):
        idx = int(m.group(1)) - 1
        if 0 <= idx < len(articles):
            url   = _esc(articles[idx].get("url", "#"))
            title = _esc(articles[idx].get("title", m.group(0)))
            return f'<a href="{url}" style="color:{_RED};text-decoration:none;font-weight:600;" target="_blank">{title}</a>'
        return m.group(0)
    return re.sub(r"\[(\d+)\]", replace, text)


def _logo_tag(height: int = 40) -> str:
    if _LOGO_FILE.exists():
        b64 = base64.b64encode(_LOGO_FILE.read_bytes()).decode()
        return f'<img src="data:image/png;base64,{b64}" height="{height}" alt="BSM" style="display:block;">'
    return f'<span style="color:{_RED};font-size:24px;font-weight:900;letter-spacing:1px;font-family:Arial;">BSM</span>'


def _img_tag(url: str, alt: str = "", w: int = 180, h: int = 120) -> str:
    if not url:
        return ""
    return (
        f'<img src="{_esc(url)}" alt="{_esc(alt[:40])}" width="{w}" '
        f'style="width:{w}px;height:{h}px;object-fit:cover;border-radius:10px;display:block;border:0;" />'
    )


def _tag_badge(label: str, color: str = _RED) -> str:
    return (
        f'<span style="display:inline-block;background:{color};color:{_WHITE};'
        f'font-size:10px;font-weight:700;letter-spacing:1px;text-transform:uppercase;'
        f'padding:3px 9px;border-radius:20px;">{_esc(label)}</span>'
    )


def _cta_button(label: str, url: str = "#", bg: str = _RED) -> str:
    return (
        f'<a href="{_esc(url)}" target="_blank" style="display:inline-block;background:{bg};'
        f'color:{_WHITE};font-size:12px;font-weight:700;text-decoration:none;'
        f'padding:9px 20px;border-radius:6px;letter-spacing:0.5px;">{_esc(label)}</a>'
    )


# ── Section parser ─────────────────────────────────────────

_SECTION_KEYS = [
    "what's hot today", "claude insider", "ai tool landscape",
    "bsm must try", "bsm sales angle", "what i'm testing",
    "industry watch", "priority reading", "2-minute read",
]

def _parse_sections(brief_text: str) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {k: [] for k in _SECTION_KEYS}
    current = None
    for line in brief_text.split("\n"):
        s = line.strip()
        if not s:
            continue
        lower = s.lower()
        matched = next((k for k in _SECTION_KEYS if k in lower), None)
        if matched:
            current = matched
            continue
        if current:
            item = re.sub(r"^-\s*", "", s).strip()
            if item:
                sections[current].append(item)
    return sections


# ── Main HTML builder ──────────────────────────────────────

def _build_html(brief_text: str, articles: list[dict],
                display_date: str, first_name: str, from_name: str) -> str:

    S = _parse_sections(brief_text)
    hot       = S["what's hot today"]
    claude    = S["claude insider"]
    must_try  = S["bsm must try"]
    sales     = S["bsm sales angle"]
    testing   = S["what i'm testing"]
    industry  = S["industry watch"]
    priority  = S["priority reading"]
    closing   = S["2-minute read"]

    count     = len(articles)
    imgs      = [a for a in articles if a.get("image")]
    feat_art  = imgs[0] if imgs else (articles[0] if articles else {})
    grid_arts = [a for a in articles if a.get("image")][:3]

    def linked(text: str) -> str:
        return _refs_to_links(_esc(text), articles)

    # ── 1. WRAPPER + NAV ──────────────────────────────────
    html = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:{_BG};font-family:Arial,Helvetica,sans-serif;">
<div style="max-width:660px;margin:0 auto;padding:24px 12px 40px;">

<!-- container -->
<div style="background:{_CARD};border-radius:20px;overflow:hidden;border:1px solid {_BORDER};">

  <!-- NAV -->
  <div style="background:{_WHITE};padding:16px 28px;border-bottom:1px solid {_BORDER};">
    <table width="100%" cellpadding="0" cellspacing="0"><tr>
      <td style="vertical-align:middle;">{_logo_tag(40)}</td>
      <td style="vertical-align:middle;text-align:right;">
        <span style="font-size:11px;color:{_T_META};">
          <a href="#" style="color:{_T_META};text-decoration:none;margin-left:14px;">AI News</a>
          <a href="#" style="color:{_T_META};text-decoration:none;margin-left:14px;">Tools</a>
          <a href="#" style="color:{_T_META};text-decoration:none;margin-left:14px;">Trends</a>
          <a href="#" style="color:{_RED};text-decoration:none;font-weight:700;margin-left:14px;">Contact</a>
        </span>
      </td>
    </tr></table>
  </div>

  <!-- ── 2. HERO ── -->
  <div style="background:linear-gradient(135deg,{_NAVY} 0%,#2d2060 100%);padding:36px 28px 32px;">
    <table width="100%" cellpadding="0" cellspacing="0"><tr>
      <td style="vertical-align:middle;width:55%;padding-right:20px;">
        {_tag_badge("Daily Brief", _RED)}
        <h1 style="margin:14px 0 10px;font-size:24px;font-weight:900;color:{_WHITE};line-height:1.25;">
          Your Daily AI<br>News Roundup
        </h1>
        <p style="margin:0 0 20px;font-size:14px;color:rgba(255,255,255,0.75);line-height:1.6;">
          Stay ahead with the latest AI updates, tools, and breakthroughs — curated for you.
        </p>
        {_cta_button("Explore Today's News", "#", _RED)}
        <p style="margin:16px 0 0;font-size:12px;color:rgba(255,255,255,0.45);">{display_date}</p>
      </td>
      <td style="vertical-align:middle;text-align:right;">{_neural_svg()}</td>
    </tr></table>
  </div>

  <!-- ── 3. STATS BAR ── -->
  <div style="background:{_NAVY};border-bottom:3px solid {_RED};">
    <table width="100%" cellpadding="0" cellspacing="0"><tr>
      <td style="width:25%;padding:16px 0;text-align:center;border-right:1px solid rgba(255,255,255,0.08);">
        {_icon_svg("sources")}
        <p style="margin:6px 0 0;font-size:20px;font-weight:800;color:{_WHITE};">{count}</p>
        <p style="margin:3px 0 0;font-size:9px;color:{_T_META};text-transform:uppercase;letter-spacing:1px;">Sources</p>
      </td>
      <td style="width:25%;padding:16px 0;text-align:center;border-right:1px solid rgba(255,255,255,0.08);">
        {_icon_svg("sections")}
        <p style="margin:6px 0 0;font-size:20px;font-weight:800;color:{_WHITE};">9</p>
        <p style="margin:3px 0 0;font-size:9px;color:{_T_META};text-transform:uppercase;letter-spacing:1px;">Sections</p>
      </td>
      <td style="width:25%;padding:16px 0;text-align:center;border-right:1px solid rgba(255,255,255,0.08);">
        {_icon_svg("tools")}
        <p style="margin:6px 0 0;font-size:20px;font-weight:800;color:{_RED};">AI</p>
        <p style="margin:3px 0 0;font-size:9px;color:{_T_META};text-transform:uppercase;letter-spacing:1px;">Powered</p>
      </td>
      <td style="width:25%;padding:16px 0;text-align:center;">
        {_icon_svg("insight")}
        <p style="margin:6px 0 0;font-size:20px;font-weight:800;color:{_WHITE};">BSM</p>
        <p style="margin:3px 0 0;font-size:9px;color:{_T_META};text-transform:uppercase;letter-spacing:1px;">Intel</p>
      </td>
    </tr></table>
  </div>

  <!-- greeting -->
  <div style="padding:22px 28px 8px;">
    <p style="margin:0;font-size:15px;color:{_T_BODY};line-height:1.6;">
      Hey <strong style="color:{_T_HEAD};">{first_name}</strong> 👋 — here's your AI intelligence briefing for today.
    </p>
  </div>
"""

    # ── 4. FEATURED STORY ─────────────────────────────────
    if hot:
        feat_img = feat_art.get("image", "") if feat_art else ""
        feat_url = feat_art.get("url", "#") if feat_art else "#"
        feat_txt = linked(hot[0]) if hot else ""
        html += f"""
  <!-- FEATURED STORY -->
  <div style="margin:12px 16px;background:{_CARD};border:1px solid {_BORDER};border-radius:14px;overflow:hidden;">
    <div style="background:linear-gradient(90deg,{_NAVY} 0%,#1e1e50 100%);padding:10px 18px;">
      <p style="margin:0;font-size:10px;font-weight:700;color:{_RED};text-transform:uppercase;letter-spacing:2px;">🔥 What's Hot Today</p>
    </div>
    <div style="padding:20px 20px 16px;">
      <table width="100%" cellpadding="0" cellspacing="0"><tr>
        <td style="vertical-align:top;padding-right:16px;">
          {_tag_badge("Breaking", _RED)}
          <p style="margin:10px 0 8px;font-size:15px;font-weight:700;color:{_T_HEAD};line-height:1.4;">{feat_txt}</p>
          {"".join(f'<p style="margin:0 0 6px;font-size:13px;color:{_T_BODY};line-height:1.6;">{"• " + linked(item)}</p>' for item in hot[1:3])}
          <div style="margin-top:14px;">{_cta_button("Read More →", feat_url)}</div>
        </td>
        {"<td style='vertical-align:top;width:180px;'>" + _img_tag(feat_img, "", 170, 160) + "</td>" if feat_img else ""}
      </tr></table>
    </div>
  </div>
"""

    # ── 5. CLAUDE INSIDER ─────────────────────────────────
    if claude:
        items_html = "".join(
            f'<tr><td style="padding:10px 0;border-bottom:1px solid {_DIV};font-size:14px;color:{_T_BODY};line-height:1.6;">'
            f'<span style="display:inline-block;width:6px;height:6px;background:#7c3aed;border-radius:50%;margin-right:8px;vertical-align:middle;"></span>'
            f'{linked(item)}</td></tr>'
            for item in claude
        )
        html += f"""
  <!-- CLAUDE INSIDER -->
  <div style="margin:8px 16px;background:{_BLUE_PILL};border:1px solid #ddd8f8;border-radius:14px;padding:20px;">
    <p style="margin:0 0 14px;font-size:11px;font-weight:700;color:#7c3aed;text-transform:uppercase;letter-spacing:2px;">🤖 Claude Insider</p>
    <table width="100%" cellpadding="0" cellspacing="0">{items_html}</table>
  </div>
"""

    # ── 6. NEWS GRID (3 article cards) ────────────────────
    if grid_arts:
        col_w = 174
        cards_html = ""
        for i, a in enumerate(grid_arts):
            pad = "padding-left:10px;" if i > 0 else ""
            src_tag = _tag_badge(a.get("source", "News")[:18], _NAVY)
            cards_html += (
                f'<td style="width:{col_w}px;vertical-align:top;{pad}">'
                f'<div style="background:{_CARD};border:1px solid {_BORDER};border-radius:12px;overflow:hidden;">'
                f'<a href="{_esc(a.get("url","#"))}" target="_blank" style="text-decoration:none;">'
                f'{_img_tag(a["image"], a["title"], col_w, 110)}'
                f'</a>'
                f'<div style="padding:12px;">'
                f'<div style="margin-bottom:6px;">{src_tag}</div>'
                f'<p style="margin:0;font-size:13px;font-weight:700;color:{_T_HEAD};line-height:1.4;">'
                f'<a href="{_esc(a.get("url","#"))}" target="_blank" style="color:{_T_HEAD};text-decoration:none;">'
                f'{_esc(a["title"][:65])}{"…" if len(a["title"])>65 else ""}</a></p>'
                f'</div></div></td>'
            )
        html += f"""
  <!-- NEWS GRID -->
  <div style="margin:8px 16px;">
    <p style="margin:0 0 12px;font-size:11px;font-weight:700;color:{_T_META};text-transform:uppercase;letter-spacing:2px;">📰 Latest AI News</p>
    <table width="100%" cellpadding="0" cellspacing="0"><tr>{cards_html}</tr></table>
  </div>
"""

    # ── 7. BSM OPPORTUNITIES (Sales Angle) ────────────────
    if sales:
        opps_html = ""
        for item in sales[:3]:
            opps_html += (
                f'<tr><td style="padding:12px 0;border-bottom:1px solid {_DIV};">'
                f'<table width="100%" cellpadding="0" cellspacing="0"><tr>'
                f'<td style="vertical-align:top;padding-right:12px;width:36px;">'
                f'<div style="width:36px;height:36px;background:{_RED};border-radius:8px;text-align:center;line-height:36px;">'
                f'<span style="color:{_WHITE};font-size:16px;">💼</span></div></td>'
                f'<td style="vertical-align:top;font-size:13px;color:{_T_BODY};line-height:1.6;">{linked(item)}</td>'
                f'<td style="vertical-align:middle;text-align:right;padding-left:12px;white-space:nowrap;">{_cta_button("Use Now →", "#")}</td>'
                f'</tr></table></td></tr>'
            )
        html += f"""
  <!-- BSM OPPORTUNITIES -->
  <div style="margin:8px 16px;background:{_CARD};border:1px solid {_BORDER};border-radius:14px;padding:20px;">
    <p style="margin:0 0 6px;font-size:11px;font-weight:700;color:{_T_META};text-transform:uppercase;letter-spacing:2px;">💼 BSM Sales Angle</p>
    <p style="margin:0 0 14px;font-size:13px;color:{_T_BODY};">Client-facing talking points for this week.</p>
    <table width="100%" cellpadding="0" cellspacing="0">{opps_html}</table>
  </div>
"""

    # ── 8. INSIGHTS: Must Try + Tool + Tip ────────────────
    insight_items = [
        (_icon_svg("brain"),  "Best AI Tool Today",  must_try[0]  if must_try  else "Check out the latest from the AI landscape."),
        (_icon_svg("prompt"), "Prompt of the Day",   testing[0]   if testing   else "Sean fills this in daily based on what he's testing."),
        (_icon_svg("tip"),    "AI Tip",              industry[0]  if industry  else "Stay current — the AI space moves fast."),
    ]
    insights_html = ""
    for icon, title, body in insight_items:
        insights_html += (
            f'<td style="width:33%;vertical-align:top;padding:0 6px;">'
            f'<div style="background:{_CARD};border:1px solid {_BORDER};border-radius:12px;padding:16px;height:100%;">'
            f'<div style="margin-bottom:10px;">{icon}</div>'
            f'<p style="margin:0 0 6px;font-size:12px;font-weight:700;color:{_T_HEAD};">{_esc(title)}</p>'
            f'<p style="margin:0;font-size:12px;color:{_T_BODY};line-height:1.55;">{linked(body)}</p>'
            f'</div></td>'
        )
    html += f"""
  <!-- INSIGHTS -->
  <div style="margin:8px 16px;">
    <p style="margin:0 0 12px;font-size:11px;font-weight:700;color:{_T_META};text-transform:uppercase;letter-spacing:2px;">✨ AI Tools &amp; Insights</p>
    <table width="100%" cellpadding="0" cellspacing="0"><tr style="vertical-align:top;">{insights_html}</tr></table>
  </div>
"""

    # ── 9. PRIORITY READING ───────────────────────────────
    if priority:
        reads_html = "".join(
            f'<div style="background:{_CARD_ALT};border:1px solid {_BORDER};border-radius:10px;'
            f'padding:13px 16px;margin-bottom:8px;font-size:13px;line-height:1.65;color:{_T_BODY};">'
            f'<span style="color:{_RED};margin-right:6px;">📚</span>{linked(item)}</div>'
            for item in priority
        )
        html += f"""
  <!-- PRIORITY READING -->
  <div style="margin:8px 16px;">
    <p style="margin:0 0 12px;font-size:11px;font-weight:700;color:{_T_META};text-transform:uppercase;letter-spacing:2px;">📚 Priority Reading</p>
    {reads_html}
  </div>
"""

    # ── 10. CLOSING ───────────────────────────────────────
    if closing:
        html += f"""
  <!-- CLOSING -->
  <div style="margin:8px 16px 16px;background:linear-gradient(135deg,{_NAVY},#2d2060);border-radius:14px;padding:22px 24px;">
    <p style="margin:0 0 4px;font-size:10px;font-weight:700;color:{_RED};text-transform:uppercase;letter-spacing:2px;">⚡ 2-Minute Read</p>
    <p style="margin:8px 0 0;font-size:15px;color:{_WHITE};line-height:1.65;font-style:italic;">{linked(closing[0])}</p>
  </div>
"""

    # ── 11. SIGN-OFF + FOOTER ─────────────────────────────
    html += f"""
  <!-- SIGN-OFF -->
  <div style="background:{_RED};padding:26px 28px;">
    <p style="margin:0 0 4px;font-size:15px;color:{_WHITE};line-height:1.6;">
      If you're building in SEO, AI, or automation — this is your edge.
    </p>
    <p style="margin:0;font-size:16px;font-weight:700;color:{_WHITE};">– {from_name}</p>
  </div>

  <!-- FOOTER -->
  <div style="background:#16162a;padding:24px 28px;">
    <table width="100%" cellpadding="0" cellspacing="0"><tr>
      <td style="vertical-align:top;width:40%;padding-right:20px;">
        {_logo_tag(36)}
        <p style="margin:10px 0 4px;font-size:12px;color:#8896b0;line-height:1.5;">Boulder SEO Marketing — AI Intelligence for your business, every morning.</p>
        <p style="margin:0;font-size:11px;color:#555e7a;">sean@boulderseomarketing.com</p>
      </td>
      <td style="vertical-align:top;width:30%;padding-right:20px;">
        <p style="margin:0 0 10px;font-size:11px;font-weight:700;color:{_WHITE};text-transform:uppercase;letter-spacing:1px;">Quick Links</p>
        {"".join(f'<p style="margin:0 0 5px;"><a href="#" style="font-size:12px;color:#8896b0;text-decoration:none;">{l}</a></p>' for l in ["About BSM", "Blog", "AI Tools", "Contact"])}
      </td>
      <td style="vertical-align:top;width:30%;">
        <p style="margin:0 0 10px;font-size:11px;font-weight:700;color:{_WHITE};text-transform:uppercase;letter-spacing:1px;">Contact</p>
        <p style="margin:0 0 4px;font-size:12px;color:#8896b0;">boulderseomarketing.com</p>
        <p style="margin:0;font-size:12px;color:#8896b0;">microseo.ai</p>
      </td>
    </tr></table>
    <div style="border-top:1px solid #2a2a45;margin-top:20px;padding-top:16px;text-align:center;">
      <p style="margin:0;font-size:11px;color:#3a3a5a;">© 2026 Boulder SEO Marketing · AI Intelligence Officer · {display_date}</p>
    </div>
  </div>

</div><!-- /container -->
</div><!-- /wrapper -->
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
