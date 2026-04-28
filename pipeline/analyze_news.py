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
                else:
                    print(f"  [WARN] {model} error ({type(e).__name__}), trying next model...")
                last_err = e
        raise last_err or RuntimeError("All Groq models failed")

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


def generate_brief(articles: list[dict], display_date: str) -> dict:
    """Generate structured brief as a dict: top_story, three_moves, client_angles."""
    headlines = "\n".join(
        f"[{i+1}] ({a['source']}) {a['title']}"
        for i, a in enumerate(articles[:18])
    )
    system = (
        "You are BSM Copilot, the AI intelligence officer for Boulder SEO Marketing "
        "(~10-person SEO agency, ~50 clients, building microseo.ai SaaS). "
        "Write like a senior strategist: direct, decisive, no filler words."
    )
    user = f"""Today is {display_date}.

Here are today's AI and marketing news headlines:
{headlines}

Return ONLY valid JSON — no markdown, no code fences, no explanation. Use this exact structure:
{{
  "top_story": {{
    "headline": "One punchy sentence (max 10 words) naming today's biggest AI shift",
    "subtext": "2-3 sentences: what happened and exactly why the BSM team should act",
    "field_note": "1 sharp strategic observation or warning (must differ from the headline)"
  }},
  "three_moves": [
    {{
      "type": "pitch",
      "title": "Client-facing action to do today (verb-first, imperative)",
      "description": "2 short sentences: the opportunity and competitive urgency",
      "deadline": "BY [specific time like 5 PM or day of week]"
    }},
    {{
      "type": "build",
      "title": "Internal experiment or capability to build this week",
      "description": "2 short sentences: what to test and what success looks like",
      "deadline": "BY [specific day of week]"
    }},
    {{
      "type": "kill",
      "title": "One specific practice or pitch to stop immediately",
      "description": "2 short sentences: why it is now obsolete and what replaces it",
      "deadline": "EFFECTIVE TODAY"
    }}
  ],
  "client_angles": [
    {{"title": "Concrete client talking point or pitch angle for this week", "source": "BSM Intel"}},
    {{"title": "Second specific angle tied to today's news", "source": "BSM Intel"}},
    {{"title": "Third client angle or objection handler", "source": "BSM Intel"}}
  ]
}}"""
    import json as _json
    try:
        raw = _call(system, user).strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return _json.loads(raw.strip())
    except Exception as e:
        print(f"  [WARN] brief JSON parse failed ({type(e).__name__})")
        return {
            "top_story": {
                "headline": "AI tools are reshaping how agencies compete.",
                "subtext": "Today's developments signal a shift in how marketing teams operate at scale. BSM has a narrow window to position ahead of this curve before clients ask competitors first.",
                "field_note": "Agencies that move now capture the transition fee. Those that wait absorb the price pressure."
            },
            "three_moves": [
                {"type": "pitch", "title": "Lead with an AI workflow audit for every client.", "description": "Clients need help mapping which tasks AI can automate today. Position BSM as the guide, not the executor.", "deadline": "BY 5 PM"},
                {"type": "build", "title": "Run one client brief through each major AI tool.", "description": "Document speed, quality, and gaps. Your differentiation lives in the interpretation layer.", "deadline": "BY FRIDAY"},
                {"type": "kill", "title": "Stop pitching AI as a cost-cutting tool.", "description": "That framing commoditizes your services. Lead with AI as a competitive advantage for the client.", "deadline": "EFFECTIVE TODAY"}
            ],
            "client_angles": [
                {"title": "AI workflow audit: how BSM maps automation opportunities for SEO clients", "source": "BSM Intel"},
                {"title": "Why the agencies winning with AI are charging more, not less", "source": "BSM Intel"},
                {"title": "Three AI talking points for Q2 client check-ins", "source": "BSM Intel"}
            ]
        }


def generate_subject(brief_data, display_date: str) -> str:
    """Generate email subject from structured brief dict or plain text."""
    if isinstance(brief_data, dict):
        headline = brief_data.get("top_story", {}).get("headline", "")
        context  = f"Headline: {headline}"
    else:
        context = str(brief_data)[:400]
    system = "You write short, curiosity-driven email subject lines. Under 8 words. No emojis. No quotes."
    user   = f"Write one email subject line for the BSM AI newsletter ({display_date}).\n{context}"
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
    except Exception as e:
        print(f"  [WARN] prompt-of-day parse failed ({type(e).__name__}): {raw[:120] if 'raw' in dir() else 'no response'}")
        return {
            "use_case": "Content Brief Generator",
            "prompt": "Act as an expert SEO content strategist. I will give you a target keyword. Create a comprehensive content brief including: search intent, recommended title, H2 subheadings (5-7), key points to cover under each heading, internal linking suggestions, and a meta description under 155 characters. Keyword: [INSERT KEYWORD]",
            "example_output": "Search Intent: Informational. Title: 'The Complete Guide to [Keyword] in 2026'. Suggested H2s: What Is [Keyword], Why It Matters for SEO, Step-by-Step Implementation, Common Mistakes to Avoid, Tools & Resources, Case Studies, FAQs. Meta: Discover proven [keyword] strategies used by top SEO agencies in 2026. Includes step-by-step guide, tools, and real examples.",
        }
