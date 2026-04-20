"""
STEP 1 — RSS News Fetcher
Pulls the latest articles from configured feeds, skipping duplicates.
Also extracts thumbnail image URLs from RSS media tags.
"""

import json
import os
import re
from pathlib import Path

import feedparser

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


def _extract_image(entry) -> str:
    """Try to extract a thumbnail/image URL from a feed entry."""
    # media:thumbnail (Google News, many feeds)
    if hasattr(entry, "media_thumbnail") and entry.media_thumbnail:
        return entry.media_thumbnail[0].get("url", "")
    # media:content with image type
    if hasattr(entry, "media_content") and entry.media_content:
        for m in entry.media_content:
            url = m.get("url", "")
            if url and any(ext in url.lower() for ext in [".jpg", ".jpeg", ".png", ".webp", "image"]):
                return url
    # enclosure (podcast/media feeds)
    if hasattr(entry, "enclosures") and entry.enclosures:
        for enc in entry.enclosures:
            if "image" in enc.get("type", ""):
                return enc.get("href", "")
    # img tag inside summary/content HTML
    raw = ""
    if hasattr(entry, "content") and entry.content:
        raw = entry.content[0].get("value", "")
    elif hasattr(entry, "summary"):
        raw = entry.summary or ""
    m = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', raw)
    if m:
        return m.group(1)
    return ""


def _entry_to_article(entry, source_name: str) -> dict:
    content = ""
    if hasattr(entry, "content") and entry.content:
        content = entry.content[0].get("value", "")
    elif hasattr(entry, "summary"):
        content = entry.summary or ""

    content = re.sub(r"<[^>]+>", " ", content).strip()
    content = re.sub(r"\s+", " ", content)[:2000]

    return {
        "title":  entry.get("title", "").strip(),
        "source": source_name,
        "url":    entry.get("link", ""),
        "content": content or entry.get("title", ""),
        "image":  _extract_image(entry),
    }


def fetch_articles() -> list[dict]:
    config    = _load_config()
    seen_path = config["seen_articles_file"]
    seen_urls = _load_seen(seen_path)
    max_articles = config.get("max_articles", 15)

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
        img = "✓ img" if a.get("image") else "  no img"
        print(f"  {img}  [{a['source']}] {a['title'][:70]}")
