# AI Daily News Roundup

An automated AI newsletter pipeline that fetches the latest AI and SEO news from RSS feeds, summarizes it using Groq (or Claude), and emails a premium HTML digest to your subscribers every day.

Includes a Next.js dashboard for managing feeds, recipients, and triggering manual runs.

---

## How It Works

```
RSS Feeds (11 sources)
    → fetch_news.py       — fetches & deduplicates articles
    → analyze_news.py     — generates 9-section brief via Groq/Claude
    → send_email.py       — builds premium HTML email and sends via Gmail SMTP
```

The pipeline runs daily at **10 PM Philippine time** via GitHub Actions. No server needs to be running for emails to send.

---

## Project Structure

```
├── pipeline/
│   ├── fetch_news.py        — RSS fetching, deduplication, og:image extraction
│   ├── analyze_news.py      — AI brief generation + prompt of the day
│   └── send_email.py        — HTML email builder and SMTP/Resend sender
├── frontend/                — Next.js dashboard (feeds, recipients, run, settings)
├── assets/
│   └── bsm_logo.png         — Logo embedded in every email
├── scripts/
│   ├── setup_schedule_windows.bat  — Windows Task Scheduler setup
│   └── SETUP.md             — Detailed setup notes
├── .github/workflows/
│   └── newsletter.yml       — Daily GitHub Actions cron job
├── main.py                  — Pipeline entry point
├── api.py                   — FastAPI backend for the dashboard
├── config.json              — Feeds, recipients, email settings
├── seen_articles.json       — Tracks sent articles to prevent duplicates
└── requirements.txt
```

---

## Prerequisites

- Python 3.11+
- Node.js 18+ (for the dashboard)
- A **Groq API key** (free at [console.groq.com](https://console.groq.com)) or Anthropic API key
- A **Gmail account** with an App Password enabled
- A GitHub account (for automated daily runs)

---

## Local Setup

### 1. Clone the repo

```bash
git clone https://github.com/seanvirginesdue/AI-daily-news-roundup.git
cd AI-daily-news-roundup
```

### 2. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 3. Create a `.env` file in the project root

```env
# AI backend — use "groq" (free) or "anthropic"
AI_BACKEND=groq
GROQ_API_KEY=your_groq_api_key_here

# Gmail SMTP — use an App Password, not your login password
SMTP_USER=you@gmail.com
SMTP_PASSWORD=your_16_char_app_password

# Optional — Resend API (alternative to Gmail SMTP)
# RESEND_API_KEY=re_...
```

> **Gmail App Password:** Go to Google Account → Security → 2-Step Verification → App Passwords. Generate one for "Mail".

### 4. Configure `config.json`

Edit `config.json` to set your sender details and recipients:

```json
{
  "email": {
    "from_name": "Your Name",
    "from_address": "you@gmail.com",
    "reply_to": "you@gmail.com",
    "recipients": [
      { "first_name": "Alice", "email": "alice@example.com" },
      { "first_name": "Bob",   "email": "bob@example.com" }
    ]
  },
  "max_articles": 22
}
```

### 5. Run the pipeline manually

```bash
python main.py
```

This fetches news, generates the brief, and sends the email to all recipients.

---

## Dashboard Setup

The dashboard lets you manage feeds, recipients, and trigger runs from a UI.

### Start the API

```bash
python -m uvicorn api:app --reload --port 8000
```

### Start the frontend

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

---

## Production Deployment (GitHub Actions + Railway)

### How it works in production

- **Email sending** runs on GitHub Actions (free, no SMTP restrictions)
- **Dashboard** runs on Railway (always-on FastAPI + Next.js via Vercel)
- **Config changes** made in the dashboard are fetched by GitHub Actions before each run via the `/config-export` endpoint

### GitHub Actions setup

1. Go to your repo → **Settings → Secrets and variables → Actions**
2. Add these secrets:

| Secret | Value |
|--------|-------|
| `GROQ_API_KEY` | Your Groq API key |
| `SMTP_USER` | Your Gmail address |
| `SMTP_PASSWORD` | Your Gmail App Password |
| `RAILWAY_URL` | Your Railway deployment URL (e.g. `https://your-app.up.railway.app`) |

3. The workflow runs daily at **14:00 UTC (10 PM Philippine time)**. You can also trigger it manually from the **Actions** tab or via the dashboard **Run Now** button.

### Railway setup (dashboard API)

1. Connect your GitHub repo to [Railway](https://railway.app)
2. Set these environment variables in Railway:

| Variable | Value |
|----------|-------|
| `AI_BACKEND` | `groq` |
| `GROQ_API_KEY` | Your Groq API key |
| `GITHUB_TOKEN` | A GitHub personal access token (repo + workflow scopes) |
| `GITHUB_REPO` | `yourusername/your-repo-name` |
| `DATA_DIR` | `/data` (attach a Railway Volume at this path) |

3. Railway uses the start command from `railway.toml`:
   ```
   python -m uvicorn api:app --host 0.0.0.0 --port $PORT
   ```

### Vercel setup (dashboard frontend)

1. Import the repo into [Vercel](https://vercel.com)
2. Set the root directory to `frontend`
3. Add environment variable: `NEXT_PUBLIC_API_URL` = your Railway URL
4. Deploy

---

## Email Schedule

The newsletter sends once daily. To change the time, edit the cron in `.github/workflows/newsletter.yml`:

```yaml
schedule:
  - cron: "0 14 * * *"   # 14:00 UTC = 10 PM Philippine time (UTC+8)
```

Use [crontab.guru](https://crontab.guru) to calculate the UTC time for your timezone.

---

## Adding RSS Feeds

Via the dashboard: go to **Feeds** and click **Add Feed**.

Or edit `config.json` directly:

```json
{
  "rss_feeds": [
    { "name": "My Feed", "url": "https://example.com/feed.xml" }
  ]
}
```

---

## AI Backends

| Backend | Key | Notes |
|---------|-----|-------|
| `groq` | `GROQ_API_KEY` | Free tier, fast. Uses llama-3.3-70b with fallbacks |
| `anthropic` | `ANTHROPIC_API_KEY` | Uses claude-sonnet-4-6 |

Set `AI_BACKEND=groq` or `AI_BACKEND=anthropic` in your `.env` or GitHub Actions secret.

---

## Resetting Duplicate Tracking

The pipeline skips articles it has already sent (tracked in `seen_articles.json`). To reset and re-fetch all articles:

```bash
echo "[]" > seen_articles.json
```

Or use the **Clear Seen Articles** button in the dashboard.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Pipeline | Python 3.11, feedparser, requests |
| AI | Groq (llama-3.3-70b) / Anthropic Claude |
| Email | Gmail SMTP / Resend API |
| Dashboard API | FastAPI + uvicorn |
| Dashboard UI | Next.js 14, Tailwind CSS |
| Hosting | Railway (API) + Vercel (frontend) |
| Scheduling | GitHub Actions (cron) |
