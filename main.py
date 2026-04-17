"""
AI Daily News Roundup — Main Orchestrator
==========================================
Run manually:   python main.py
Scheduled:      runs daily at 8 AM via Windows Task Scheduler / cron

Pipeline
--------
  fetch_news  →  analyze_article  →  format_section  →  generate_subjects
                                                       ↘
                                                  combine_sections  →  send_email
"""

import sys
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()  # loads ANTHROPIC_API_KEY, SMTP_USER, SMTP_PASSWORD from .env

from fetch_news import fetch_articles
from analyze_news import analyze_article, format_section, generate_subjects, combine_sections
from send_email import send_newsletter


def run() -> None:
    print(f"\n{'='*60}")
    print(f"  AI Daily News Roundup  —  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*60}\n")

    # ── STEP 1: Fetch ──────────────────────────────────────────
    print("📡 Fetching news...")
    articles = fetch_articles()

    if not articles:
        print("✓ No new articles today — skipping email.\n")
        return

    print(f"✓ Found {len(articles)} new article(s)\n")

    # ── STEPS 2 + 3: Analyze + Format each article ─────────────
    sections: list[str] = []
    all_subjects: list[str] = []

    for i, article in enumerate(articles, 1):
        print(f"🤖 Processing article {i}/{len(articles)}: {article['title'][:60]}...")

        # STEP 2 — Claude analysis
        analysis = analyze_article(article)

        # STEP 3 — Newsletter section
        section = format_section(analysis)
        sections.append(section)

        # STEP 4 — Subject lines (use first article for the primary subject)
        if i == 1:
            all_subjects = generate_subjects(section)

    # ── STEP 5: Combine into one email body ────────────────────
    print("\n📝 Combining sections...")
    newsletter_body = combine_sections(sections)

    # ── Pick best subject line ──────────────────────────────────
    subject = all_subjects[0] if all_subjects else "Your AI update for today"
    print(f"\n✉️  Subject: {subject}")
    print(f"\nSubject line candidates:")
    for j, s in enumerate(all_subjects, 1):
        marker = "→" if j == 1 else " "
        print(f"  {marker} {j}. {s}")

    # ── STEP 6: Send ───────────────────────────────────────────
    print("\n📬 Sending email...")
    send_newsletter(subject, newsletter_body)

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
