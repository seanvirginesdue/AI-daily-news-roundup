# AI Daily News Roundup — Setup Guide

> Automated AI newsletter delivered to your inbox every morning at 8 AM.
> Powered by Claude (Anthropic). No manual work needed after setup.

---

## What this does

Every morning the system:
1. Pulls the 3 latest AI articles from TechCrunch, The Verge, and OpenAI
2. Skips articles you've already received
3. Analyzes each article with Claude — summary, business impact, SEO/GEO angle, action tip
4. Formats everything into a clean newsletter section
5. Generates 5 subject line options (uses the best one automatically)
6. Combines all sections into one email
7. Sends it to your inbox

---

## One-time setup (5 minutes)

### 1. Install Python dependencies

```
cd "C:\Users\seand\AI daily news\AI-daily-news-roundup"
pip install -r requirements.txt
```

### 2. Create your `.env` file

Copy `.env.example` to `.env` and fill in your keys:

```
copy .env.example .env
```

Open `.env` and set:

| Variable | Where to get it |
|---|---|
| `ANTHROPIC_API_KEY` | https://console.anthropic.com/keys |
| `SMTP_USER` | Your Gmail address |
| `SMTP_PASSWORD` | Gmail App Password (see below) |

**Gmail App Password:**
1. Go to https://myaccount.google.com/apppasswords
2. Select app: **Mail** / device: **Windows Computer**
3. Copy the 16-character password into `.env`

### 3. Edit recipients in `config.json`

Open `config.json` and update the `recipients` list:

```json
"recipients": [
  { "first_name": "Sean", "email": "sean@boulderseomarketing.com" }
]
```

Add as many people as you want.

### 4. Test it manually

```
python main.py
```

You should see articles being fetched, processed, and an email arriving in your inbox.

### 5. Schedule it (runs every day at 8 AM automatically)

Right-click `setup_schedule_windows.bat` → **Run as Administrator**

That's it. The task is now registered in Windows Task Scheduler.

To verify: open **Task Scheduler** → search for `AI-Daily-News-Roundup`.

---

## File overview

| File | Purpose |
|---|---|
| `main.py` | Orchestrator — runs the full pipeline |
| `fetch_news.py` | Step 1: RSS feed fetcher |
| `analyze_news.py` | Steps 2–5: Claude analysis, formatting, subjects, combining |
| `send_email.py` | Step 6: Gmail SMTP email sender |
| `config.json` | Settings (feeds, recipients, schedule hour) |
| `.env` | Secret keys (never commit this file) |
| `seen_articles.json` | Auto-generated — tracks sent articles to avoid duplicates |
| `setup_schedule_windows.bat` | One-click Windows Task Scheduler registration |

---

## Workflow diagram

```
RSS Feeds (3 sources)
      │
      ▼
[STEP 1] fetch_news.py
  Pull top 3 new articles
  Skip duplicates via seen_articles.json
      │
      ▼
[STEP 2] Claude: analyze_article()
  • 2-3 sentence summary
  • Why it matters for business
  • SEO / GEO impact
  • 1 action tip
      │
      ▼
[STEP 3] Claude: format_section()
  Turn analysis into newsletter block
  🧠 What happened / 📊 Why it matters
  🚀 SEO/GEO impact / ✅ What to do
      │
      ▼
[STEP 4] Claude: generate_subjects()
  5 curiosity-driven subject lines
      │
      ▼
[STEP 5] Claude: combine_sections()
  Merge all articles into one email body
      │
      ▼
[STEP 6] send_email.py
  Subject: best subject line
  Body: newsletter + Sean sign-off
  Sent via Gmail SMTP
```

---

## Customising

**Change send time:** Edit `setup_schedule_windows.bat` — change `/ST 08:00` to any time.

**Add/remove RSS feeds:** Edit the `rss_feeds` array in `config.json`.

**Add recipients:** Add objects to `recipients` in `config.json`.

**Change max articles:** Edit `"max_articles"` in `config.json`.

**Change Claude model:** Edit the `model=` line in `analyze_news.py`.

---

## Troubleshooting

| Issue | Fix |
|---|---|
| `ANTHROPIC_API_KEY` error | Check `.env` file exists and key is correct |
| Gmail auth failed | Use App Password, not your Gmail login password |
| No articles fetched | RSS feeds may be temporarily down; try again later |
| Duplicate emails | `seen_articles.json` tracks this automatically |
