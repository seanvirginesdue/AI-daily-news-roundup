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

    # Model priority: best quality first, fall back to higher-limit models
    _GROQ_MODELS = [
        "llama-3.3-70b-versatile",   # 100K tokens/day
        "llama-3.1-8b-instant",      # 500K tokens/day
        "gemma2-9b-it",              # 500K tokens/day
    ]

    def _call(system: str, user: str) -> str:
        last_err = None
        for model in _GROQ_MODELS:
            try:
                response = _get_client().chat.completions.create(
                    model=model,
                    max_tokens=4000,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                )
                return response.choices[0].message.content.strip()
            except Exception as e:
                if "rate_limit" in str(e).lower() or "429" in str(e):
                    print(f"  [WARN] {model} rate-limited, trying next model...")
                    last_err = e
                else:
                    raise
        raise last_err

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


def generate_prompt_of_the_day() -> dict:
    """Generate a daily AI prompt + example output for SEO professionals."""
    import json as _json
    system = "You are an AI productivity expert for SEO professionals and digital marketers."
    user = """Create a powerful AI Prompt of the Day for SEO professionals.

Return valid JSON with exactly these fields:
- "use_case": 3-5 word label for what this prompt does (e.g. "Content Gap Analysis")
- "prompt": the full prompt to paste into ChatGPT or Claude (60-90 words, specific and actionable)
- "example_output": a realistic 2-3 sentence snippet showing what the AI would actually respond (make it feel authentic, include specific numbers or insights)

Return only the JSON object, no markdown, no extra text."""
    try:
        raw = _call(system, user)
        # Strip markdown fences if present
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return _json.loads(raw.strip())
    except Exception:
        return {
            "use_case": "Content Brief Generator",
            "prompt": "Act as an expert SEO content strategist. I will give you a target keyword. Create a comprehensive content brief including: search intent, recommended title, H2 subheadings (5-7), key points to cover under each heading, internal linking suggestions, and a meta description under 155 characters. Keyword: [INSERT KEYWORD]",
            "example_output": "Search Intent: Informational. Title: 'The Complete Guide to [Keyword] in 2026'. Suggested H2s: What Is [Keyword], Why It Matters for SEO, Step-by-Step Implementation, Common Mistakes to Avoid, Tools & Resources, Case Studies, FAQs. Meta: Discover proven [keyword] strategies used by top SEO agencies in 2026. Includes step-by-step guide, tools, and real examples.",
        }
