"""
STEP 2 — Analyzer
STEP 3 — Newsletter Formatter
STEP 4 — Subject Line Generator
STEP 5 — Multi-article Combiner

Supports two backends (set AI_BACKEND in .env):
  anthropic (default) — requires ANTHROPIC_API_KEY + credits
  groq               — free tier, requires GROQ_API_KEY
"""

import os

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
            max_tokens=1024,
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
            max_tokens=1024,
            system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
            messages=[{"role": "user", "content": user}],
        )
        return response.content[0].text.strip()


# ── STEP 2 ─────────────────────────────────────────────────────────────────

ANALYZE_SYSTEM = """You are an AI news analyst focused on business, SEO, and GEO strategy.
Summarize news in simple terms and extract business value.
Rules: Simple English. No jargon. Under 120 words total."""

ANALYZE_TEMPLATE = """Title: {title}
Source: {source}
Content: {content}

TASK:
- Write a 2-3 sentence summary
- Explain why it matters for businesses
- Explain SEO/GEO impact
- Give 1 action step

FORMAT (use these exact labels):
Summary:
...

Why it matters:
...

SEO/GEO Impact:
...

Action Tip:
..."""


def analyze_article(article: dict) -> str:
    """Returns the structured analysis text for one article."""
    prompt = ANALYZE_TEMPLATE.format(
        title=article["title"],
        source=article["source"],
        content=article["content"],
    )
    return _call(ANALYZE_SYSTEM, prompt)


# ── STEP 3 ─────────────────────────────────────────────────────────────────

FORMAT_SYSTEM = """You are a newsletter editor. Turn AI news analysis into a clean daily newsletter section.
Style: Clear, modern, slightly conversational. No fluff."""

FORMAT_TEMPLATE = """Turn this analysis into a clean newsletter section.

FORMAT:
Headline: (compelling title, max 10 words)
Hook: (1 punchy sentence that makes the reader want to read on)

🧠 What happened
(2-3 sentences)

📊 Why it matters
(2-3 sentences)

🚀 SEO / GEO impact
(1-2 sentences)

✅ What to do
(1 clear action)

INPUT:
{analysis}"""


def format_section(analysis: str) -> str:
    """Returns a formatted newsletter section for one article."""
    return _call(FORMAT_SYSTEM, FORMAT_TEMPLATE.format(analysis=analysis))


# ── STEP 4 ─────────────────────────────────────────────────────────────────

SUBJECT_SYSTEM = """You write short, curiosity-driven email subject lines.
Rules: Under 8 words each. No clickbait. No emojis in subject lines."""

SUBJECT_TEMPLATE = """Generate 5 short email subject lines for this newsletter.

Headline: {headline}
Hook: {hook}

Return them as a numbered list (1. 2. 3. 4. 5.)"""


def _extract_headline_hook(section: str) -> tuple[str, str]:
    headline, hook = "", ""
    for line in section.splitlines():
        stripped = line.strip()
        if stripped.lower().startswith("headline:"):
            headline = stripped[9:].strip()
        elif stripped.lower().startswith("hook:"):
            hook = stripped[5:].strip()
        if headline and hook:
            break
    return headline or "Today's AI Update", hook or ""


def generate_subjects(section: str) -> list[str]:
    """Returns 5 subject line candidates."""
    headline, hook = _extract_headline_hook(section)
    raw = _call(SUBJECT_SYSTEM, SUBJECT_TEMPLATE.format(headline=headline, hook=hook))
    lines = [l.strip() for l in raw.splitlines() if l.strip()]
    subjects = []
    for line in lines:
        # strip leading "1. " etc.
        import re
        clean = re.sub(r"^\d+\.\s*", "", line).strip()
        if clean:
            subjects.append(clean)
    return subjects[:5]


# ── STEP 5 ─────────────────────────────────────────────────────────────────

COMBINE_SYSTEM = """You are a newsletter editor combining multiple AI news sections into one cohesive email.
Style: Clear, modern, slightly conversational. No fluff."""

COMBINE_TEMPLATE = """Combine these newsletter sections into one daily email.

FORMAT:
Intro: (1-2 sentences — set the scene for today's AI news)

🔥 [Headline from section 1]
[Content from section 1]

🔥 [Headline from section 2]
[Content from section 2]

🔥 [Headline from section 3]
[Content from section 3]

End with exactly:
---
Stay ahead. See you tomorrow.

SECTIONS:
{sections}"""


def combine_sections(sections: list[str]) -> str:
    """Combines multiple formatted sections into one newsletter body."""
    if len(sections) == 1:
        return sections[0] + "\n\n---\nStay ahead. See you tomorrow."
    joined = "\n\n---SECTION BREAK---\n\n".join(sections)
    return _call(COMBINE_SYSTEM, COMBINE_TEMPLATE.format(sections=joined))
