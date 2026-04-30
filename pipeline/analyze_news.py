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


_BSM_SYSTEM = (
    "You are BSM Copilot, the AI intelligence officer for Boulder SEO Marketing "
    "(~10-person SEO agency, ~50 clients, building microseo.ai SaaS). "
    "Write like a senior strategist: direct, decisive, no filler words.\n\n"
    "BSM CONTEXT — use this when generating Three Moves:\n"
    "— 30-35% of BSM's own leads now arrive through ChatGPT, Claude, and Perplexity. "
    "GEO readiness audits are a live sales conversation, not a future initiative.\n"
    "— BSM runs virtual client agents for every account. These agents get smarter with "
    "more context (call transcripts, case studies, results screenshots). "
    "Knowledge base depth is a direct competitive differentiator.\n"
    "— BSM's service delivery principle: unless it's legal, medical, or a sensitive "
    "industry, move forward and notify. Asking for approval on every optimization "
    "is hesitation dressed up as process.\n"
    "— PITCH moves must name a specific client-facing conversation BSM can have today. "
    "BUILD moves must target the virtual agent system or internal tooling BSM already runs. "
    "KILL moves must name something specific the team is actively doing wrong right now.\n"
    "— Fhul manages Google Business Profile for the majority of BSM's local clients every day. "
    "Any GBP policy change, feature release, or ranking signal shift is immediately operational — "
    "it changes what Fhul does tomorrow morning.\n"
    "— BSM actively uses Featured.com for E-E-A-T building across client accounts. "
    "Platform changes or shifts in journalist query patterns directly affect off-page strategy.\n"
    "— BSM clients pay $2,000–$5,000/month because they trust the team is ahead of the curve. "
    "The credibility risk is real: if a client hears about a Google update from someone else first, "
    "trust erodes immediately. Every bsm_note must reflect this urgency — "
    "not 'this is worth watching' but what BSM is doing about it today."
)

_RELEVANCE_FILTER = """
RELEVANCE FILTER — include ONLY items from these 6 categories:
  (1) Google Search Central or Google Blog: algorithm updates, Search Console features, AI Overview changes — anything Google announces that affects how clients rank or appear in search.
  (2) Perplexity, ChatGPT (OpenAI), Claude (Anthropic) release notes: actual product or feature releases that change how these platforms surface and cite content. Not funding news. Not partnerships. The changelog.
  (3) SE Ranking product updates: new features, UI changes, data updates to the platform BSM uses and ambassadors daily.
  (4) Google Business Profile: policy changes, new features, ranking signal shifts — anything that changes how BSM manages client GBP listings.
  (5) Featured.com and digital PR signals: platform changes, journalist query pattern shifts, E-E-A-T building opportunities that affect BSM's off-page strategy for clients.
  (6) AI Overviews research and case studies: actual data on what content formats appear in AI Overviews, citation rate studies, format and structure findings. Not opinion pieces — studies with numbers.

EXCLUDE without exception: corporate AI adoption stories, "AI is changing business" think pieces, image/video/music generators, manufacturing AI, fundraising announcements, general tech news, anything that doesn't change what BSM does for clients by Friday.
"""


def generate_brief(articles: list[dict], display_date: str) -> dict:
    """Generate structured brief as a dict: top_story, three_moves, client_angles, top_reads."""
    headlines = "\n".join(
        f"[{i+1}] ({a['source']}) {a['title']}"
        for i, a in enumerate(articles[:18])
    )
    system = _BSM_SYSTEM
    user = f"""Today is {display_date}.

Here are today's AI and marketing news headlines:
{headlines}
{_RELEVANCE_FILTER}
Return ONLY valid JSON — no markdown, no code fences, no explanation. Use this exact structure:
{{
  "top_story": {{
    "headline": "One punchy sentence (max 10 words) naming today's biggest AI shift",
    "subtext": "Exactly 2 sentences. Sentence 1: what happened. Sentence 2: why BSM clients will be affected.",
    "field_note": "1 sentence stating what BSM is doing about this right now. Start with a direct verb or 'We are'. No hedging — not 'this may signal' but a concrete action or stance."
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
  ],
  "top_reads": [
    {{
      "article_index": 1,
      "title": "Exact title from the headlines list above",
      "source": "Source name from the (source) prefix",
      "bsm_note": "One sentence: what BSM is doing differently because of this. Not 'this may affect' — a specific operational change, client conversation, or deliverable adjustment. Example: 'We are updating our GBP audit checklist to include the new review response policy.' Never write: 'This could impact how clients approach SEO.'"
    }}
  ]
}}

For top_reads: select the 2-3 articles that passed the relevance filter above. If only 1 passes, return only 1. Never pad with irrelevant articles to hit a count."""
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
            ],
            "top_reads": [
                {"article_index": 1, "title": "Check today's AI search headlines", "source": "BSM Intel", "bsm_note": "Review manually — LLM fallback active today."}
            ]
        }


def generate_digest_brief(articles: list[dict], display_date: str) -> dict:
    """Generate a tight, BSM-relevant brief for the Team Digest (Tier 2)."""
    headlines = "\n".join(
        f"[{i+1}] ({a['source']}) {a['title']}"
        for i, a in enumerate(articles[:18])
    )
    system = _BSM_SYSTEM
    user = f"""Today is {display_date}.

Here are today's AI and marketing news headlines:
{headlines}
{_RELEVANCE_FILTER}
Return ONLY valid JSON — no markdown, no code fences, no explanation. Use this exact structure:
{{
  "top_story": {{
    "headline": "One punchy sentence (max 10 words) naming today's most BSM-relevant AI shift",
    "subtext": "Exactly 2 sentences. Sentence 1: what happened. Sentence 2: why BSM clients will be affected.",
    "field_note": "1 sentence stating what BSM is doing about this right now. Start with a direct verb or 'We are'. No hedging — not 'this may signal' but a concrete action or stance."
  }},
  "three_moves": [
    {{
      "type": "pitch",
      "title": "Client-facing action to do today (verb-first, imperative)",
      "description": "2 short sentences: the opportunity and why it matters for BSM clients",
      "deadline": "BY [specific time like 5 PM or day of week]"
    }},
    {{
      "type": "build",
      "title": "Internal experiment or capability to build this week",
      "description": "2 short sentences: what to test and what success looks like",
      "deadline": "BY [specific day of week]"
    }}
  ],
  "client_angles": [
    {{"title": "Concrete client talking point or pitch angle for this week", "source": "BSM Intel"}},
    {{"title": "Second specific angle tied to today's news", "source": "BSM Intel"}}
  ],
  "top_reads": [
    {{
      "article_index": 1,
      "title": "Exact title from the headlines list above",
      "source": "Source name from the (source) prefix",
      "bsm_note": "One sentence: what BSM is doing differently because of this. Not 'this may affect' — a specific operational change, client conversation, or deliverable adjustment. Example: 'We are updating our GBP audit checklist to include the new review response policy.' Never write: 'This could impact how clients approach SEO.'"
    }}
  ]
}}

For top_reads: select the 2-3 articles that passed the relevance filter above. If only 1 passes, return only 1. Never pad with irrelevant articles to hit a count."""
    import json as _json
    try:
        raw = _call(system, user).strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return _json.loads(raw.strip())
    except Exception as e:
        print(f"  [WARN] digest brief JSON parse failed ({type(e).__name__})")
        return {
            "top_story": {
                "headline": "AI tools are reshaping how agencies compete.",
                "subtext": "Today's developments signal a shift in how marketing teams operate at scale. BSM has a narrow window to position ahead of this curve before clients ask competitors first.",
                "field_note": "Agencies that move now capture the transition fee. Those that wait absorb the price pressure."
            },
            "three_moves": [
                {"type": "pitch", "title": "Lead with an AI workflow audit for every client.", "description": "Clients need help mapping which tasks AI can automate today. Position BSM as the guide, not the executor.", "deadline": "BY 5 PM"},
                {"type": "build", "title": "Run one client brief through each major AI tool.", "description": "Document speed, quality, and gaps. Your differentiation lives in the interpretation layer.", "deadline": "BY FRIDAY"},
            ],
            "client_angles": [
                {"title": "AI workflow audit: how BSM maps automation opportunities for SEO clients", "source": "BSM Intel"},
                {"title": "Why the agencies winning with AI are charging more, not less", "source": "BSM Intel"},
            ],
            "top_reads": [
                {"article_index": 1, "title": "Check today's AI search headlines", "source": "BSM Intel", "bsm_note": "Review manually — LLM fallback active today."}
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
