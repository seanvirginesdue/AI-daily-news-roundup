"""
AI Daily News Roundup — Main Orchestrator
==========================================
Run manually:   python main.py
Scheduled:      runs daily at 8 AM via Windows Task Scheduler

Pipeline
--------
  fetch_news (10 feeds, 15 articles)
      → generate_brief (single Claude call → 9-section brief)
      → generate_subject
      → send_newsletter (dark professional HTML email)
"""

import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

import json as _json
from pathlib import Path as _Path

from pipeline.fetch_news import fetch_articles
from pipeline.analyze_news import generate_brief, generate_digest_brief, generate_subject
from pipeline.send_email import send_newsletter

_CONFIG_FILE = _Path(__file__).parent / "config.json"


def run() -> None:
    now = datetime.now()
    if now.weekday() >= 5:  # 5=Saturday, 6=Sunday
        print(f"\n✓ Weekend ({now.strftime('%A')}) — no send. See you Monday.\n")
        return
    display_date = now.strftime("%A, %B %d, %Y").replace(" 0", " ")

    print(f"\n{'='*60}")
    print(f"  AI Daily News Roundup  —  {now.strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*60}\n")

    # ── STEP 1: Fetch ──────────────────────────────────────────
    print("📡 Fetching news from configured sources...")
    articles = fetch_articles()

    if not articles:
        print("✓ No new articles today — skipping email.\n")
        return

    print(f"✓ Found {len(articles)} article(s)\n")
    for i, a in enumerate(articles, 1):
        print(f"  [{i:2}] [{a['source']}] {a['title'][:65]}")

    # ── Split recipients by tier ───────────────────────────────
    all_recipients = _json.loads(_CONFIG_FILE.read_text()).get("email", {}).get("recipients", [])
    tier1 = [r for r in all_recipients if r.get("tier", 1) == 1]
    tier2 = [r for r in all_recipients if r.get("tier", 1) == 2]

    # ── STEP 2: Generate full brief (Tier 1 — Research Layer) ──
    print(f"\n🤖 Generating brief with AI ({len(articles)} articles)...")
    brief_data = generate_brief(articles, display_date)

    # ── Editorial override ─────────────────────────────────────
    _OVERRIDE_FILE = _Path(__file__).parent / "custom_brief.json"
    _overrides: dict = {}
    if _OVERRIDE_FILE.exists():
        try:
            _overrides = _json.loads(_OVERRIDE_FILE.read_text(encoding="utf-8"))
            brief_data.update(_overrides)
            print(f"  ✓ Applied editorial overrides: {list(_overrides.keys())}")
            _OVERRIDE_FILE.unlink()
            print(f"  ✓ custom_brief.json consumed and removed")
        except Exception as _e:
            print(f"  [WARN] Could not load custom_brief.json: {_e}")

    # ── STEP 3: Subject line (Tier 1) ─────────────────────────
    subject = generate_subject(brief_data, display_date)
    print(f"✉️  Subject: {subject}")

    # ── STEP 4: Generate digest brief (Tier 2 — Team Digest) ──
    digest_brief = None
    digest_subject = None
    if tier2:
        print(f"\n🤖 Generating Team Digest brief ({len(tier2)} recipient(s))...")
        digest_brief = generate_digest_brief(articles, display_date)
        if _overrides:
            digest_brief.update(_overrides)
        digest_subject = generate_subject(digest_brief, display_date)
        print(f"✉️  Digest subject: {digest_subject}")

    # ── STEP 5: Send Tier 1 immediately ───────────────────────
    print("\n📬 Sending Tier 1 (Research Layer)...")
    try:
        send_newsletter(
            subject, brief_data, articles, display_date,
            tier1_recipients=tier1,
            tier2_recipients=[],   # Tier 2 is held for Harold to review
        )
    except Exception as exc:
        print(f"❌ Email send failed: {exc}")
        raise

    # ── STEP 6: Save Tier 2 digest for Harold review ──────────
    if tier2 and digest_brief:
        _PENDING_FILE = _Path(__file__).parent / "digest_pending.json"
        pending = {
            "subject":      digest_subject or subject,
            "brief_data":   digest_brief,
            "articles":     articles,
            "display_date": display_date,
        }
        _PENDING_FILE.write_text(
            _json.dumps(pending, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"\n📋 Tier 2 digest ready for review.")
        print(f"   Open digest_preview.html in a browser to check it.")
        print(f"   When ready, run:  python approve_digest.py\n")

        # Write a preview HTML for Harold to open
        from pipeline.send_email import _build_html_tier2 as _bh2
        _PREVIEW_FILE = _Path(__file__).parent / "digest_preview.html"
        preview_html = _bh2(digest_brief, articles, display_date, "Harold", "AI Task Force")
        _PREVIEW_FILE.write_text(preview_html, encoding="utf-8")
        print(f"   Preview saved → {_PREVIEW_FILE.name}")

    print(f"\n✅ Done!\n")


if __name__ == "__main__":
    try:
        run()
    except KeyboardInterrupt:
        print("\nCancelled.")
        sys.exit(0)
    except Exception as exc:
        print(f"\n❌ Error: {exc}")
        raise
