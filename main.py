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

from fetch_news import fetch_articles, fetch_latest_seo_tip
from analyze_news import generate_brief, generate_subject
from send_email import send_newsletter


def run() -> None:
    now = datetime.now()
    display_date = now.strftime("%A, %B %d, %Y").replace(" 0", " ")

    print(f"\n{'='*60}")
    print(f"  AI Daily News Roundup  —  {now.strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*60}\n")

    # ── STEP 1: Fetch ──────────────────────────────────────────
    print("📡 Fetching news from 10 sources...")
    articles = fetch_articles()

    if not articles:
        print("✓ No new articles today — skipping email.\n")
        return

    print(f"✓ Found {len(articles)} article(s)\n")
    for i, a in enumerate(articles, 1):
        print(f"  [{i:2}] [{a['source']}] {a['title'][:65]}")

    # ── STEP 2: Generate 9-section brief ───────────────────────
    print(f"\n🤖 Generating brief with AI ({len(articles)} articles)...")
    brief_text = generate_brief(articles, display_date)

    # ── STEP 3: Subject line ───────────────────────────────────
    subject = generate_subject(brief_text, display_date)
    print(f"✉️  Subject: {subject}")

    # ── STEP 4: Fetch latest SEO tip ───────────────────────────
    print("🔍 Fetching latest Chris Raulf SEO tip...")
    seo_tip = fetch_latest_seo_tip()
    if seo_tip:
        print(f"✓ SEO tip: {seo_tip['title'][:60]}")
    else:
        print("  (no SEO tip found)")

    # ── STEP 5: Send ───────────────────────────────────────────
    print("\n📬 Sending email...")
    send_newsletter(subject, brief_text, articles, display_date, seo_tip)

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
