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
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

from fetch_news import fetch_articles
from analyze_news import generate_brief, generate_subject
from send_email import send_newsletter


def run() -> None:
    now = datetime.now()
    display_date = now.strftime("%A, %B %-d, %Y")

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

    # ── STEP 4: Send ───────────────────────────────────────────
    print("\n📬 Sending email...")
    send_newsletter(subject, brief_text, articles, display_date)

    print(f"\n✅ Done!\n")


if __name__ == "__main__":
    # Windows strftime doesn't support %-d — patch it
    import platform
    if platform.system() == "Windows":
        _orig_run = run
        def run():
            import datetime as _dt
            _orig_strftime = _dt.datetime.strftime
            def _patched(self, fmt):
                fmt = fmt.replace("%-d", str(self.day))
                return _orig_strftime(self, fmt)
            _dt.datetime.strftime = _patched
            _orig_run()
            _dt.datetime.strftime = _orig_strftime
    try:
        run()
    except KeyboardInterrupt:
        print("\nCancelled.")
        sys.exit(0)
    except Exception as exc:
        print(f"\n❌ Error: {exc}")
        raise
