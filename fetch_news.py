"""
STEP 1 — RSS News Fetcher
Pulls the top 3 latest articles from configured feeds, skipping duplicates.
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import feedparser
import requests


CONFIG_FILE = Path(__file__).parent / "config.json"


def _load_config() -> dict:
    with open(CONFIG_FILE) as f:
        return json.load(f)


def _load_seen(path: str) -> set:
    if os.path.exists(path):
        with open(path) as f:
            return set(json.load(f))
    return set()


def _save_seen(path: str, seen: set) -> None:
    with open(path, "w") as f:
        json.dump(list(seen), f, indent=2)


def _entry_to_article(entry, source_name: str) -> dict:
    """Convert a feedparser entry into a plain dict."""
    content = ""
    if hasattr(entry, "content") and entry.content:
        content = entry.content[0].get("value", "")
    elif hasattr(entry, "summary"):
        content = entry.summary

    # Strip basic HTML tags without extra dependencies
    import re
    content = re.sub(r"<[^>]+>", " ", content).strip()
    content = re.sub(r"\s+", " ", content)[:2000]  # keep it reasonable

    return {
        "title": entry.get("title", "").strip(),
        "source": source_name,
        "url": entry.get("link", ""),
        "content": content or entry.get("title", ""),
    }


def fetch_articles() -> list[dict]:
    """Return up to max_articles new articles across all feeds."""
    config = _load_config()
    seen_path = config["seen_articles_file"]
    seen_urls = _load_seen(seen_path)
    max_articles = config.get("max_articles", 3)

    collected: list[dict] = []

    for feed_cfg in config["rss_feeds"]:
        if len(collected) >= max_articles:
            break

        try:
            parsed = feedparser.parse(feed_cfg["url"])
        except Exception as exc:
            print(f"  [WARN] Could not fetch {feed_cfg['url']}: {exc}")
            continue

        for entry in parsed.entries:
            url = entry.get("link", "")
            if url in seen_urls:
                continue
            article = _entry_to_article(entry, feed_cfg["name"])
            if not article["title"]:
                continue
            collected.append(article)
            seen_urls.add(url)
            if len(collected) >= max_articles:
                break

    if collected:
        _save_seen(seen_path, seen_urls)

    return collected


if __name__ == "__main__":
    articles = fetch_articles()
    print(f"Fetched {len(articles)} new article(s):")
    for a in articles:
        print(f"  • [{a['source']}] {a['title']}")
