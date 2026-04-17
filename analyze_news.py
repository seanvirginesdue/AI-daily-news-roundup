"""
AI analysis pipeline — single comprehensive brief from all articles.

Supports two backends (set AI_BACKEND in .env):
  anthropic (default) — requires ANTHROPIC_API_KEY
  groq               — free tier, requires GROQ_API_KEY
"""

import os
from datetime import datetime

_backend = os.environ.get("AI_BACKEND", "anthropic").lower()

if _backend == "groq":
    from groq import Groq as _GroqClient
    _client = None

    def _get_client():
        global _client
        if _client is None:
            _client = _GroqClient(api_key=os.environ["GROQ_API_KEY"])
        return _client

    def _call(system: str, user: str) -> str:
        response = _get_client().chat.completions.create(
            model="llama-3.3-70b-versatile",
            max_tokens=4000,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        return response.choices[0].message.content.strip()

else:
    import anthropic
    _client = None

    def _get_client():
        global _client
        if _client is None:
            _client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        return _client

    def _call(system: str, user: str) -> str:
        response = _get_client().messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4000,
            system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
            messages=[{"role": "user", "content": user}],
        )
        return response.content[0].text.strip()


SYSTEM_PROMPT = """You are an AI Intelligence Officer for Boulder SEO Marketing (BSM) — a ~10-person SEO agency with ~50 clients, building microseo.ai SaaS, using n8n + Claude Code + MCP.

AI landscape (2026): Claude Opus 4.7/Sonnet 4.6/Haiku 4.5 | GPT-4o, o1-pro, o3 | Gemini 2.0 Ultra/Flash | Midjourney v7, DALL-E 3, Flux | Sora, Runway Gen-3, Kling | Suno v4 | Claude Code, Cursor, Windsurf | SE Ranking, Surfer SEO, Clearscope

Generate a daily brief with exactly these 9 sections in order:

1. 🔥 WHAT'S HOT TODAY — 3 top stories with [N] article refs
2. 🤖 CLAUDE INSIDER — 2 Claude/Anthropic updates with [N] refs
3. 📊 AI TOOL LANDSCAPE — tool comparison table (Overall / Image / Video / Music / Code / SEO)
4. 💡 BSM MUST TRY — 3 recommendations for the BSM team with [N] refs
5. 💼 BSM SALES ANGLE — 3 client-facing talking points with [N] refs
6. 🧪 WHAT I'M TESTING — note that Sean fills this in manually
7. 🌐 INDUSTRY WATCH — 2 macro trends shaping AI with [N] refs
8. 📚 PRIORITY READING — 3 must-read articles with [N] refs
9. ⚡ 2-MINUTE READ — one punchy closing insight

RULES:
- Reference articles by [N] number only — NEVER write full URLs
- Start each bullet with: - [N] your commentary here
- Keep bullets to 1-2 sentences
- If no relevant article exists, draw from your AI knowledge
- Return ONLY the brief — no preamble, no sign-off"""


def generate_brief(articles: list[dict], display_date: str) -> str:
    """Generate a full 9-section brief from a list of articles."""
    article_list = ""
    for i, a in enumerate(articles, 1):
        snippet = a.get("content", "")[:80].replace("\n", " ")
        line = f"[{i}] {a['title']}"
        if snippet:
            line += f" -- {snippet}"
        article_list += line + "\n"

    user_prompt = f"SEAN'S DAILY AI UPDATES — {display_date}\n\nArticles:\n{article_list}\nGenerate the brief."
    return _call(SYSTEM_PROMPT, user_prompt)


def generate_subject(brief_text: str, display_date: str) -> str:
    """Pick the best email subject line from the brief."""
    system = "You write short, curiosity-driven email subject lines. Under 8 words. No emojis."
    user = f"Write one email subject line for this AI newsletter dated {display_date}:\n\n{brief_text[:500]}"
    return _call(system, user)
