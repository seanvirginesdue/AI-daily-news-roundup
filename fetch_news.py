"""
STEP 1 — RSS News Fetcher
Pulls the latest articles from configured feeds, skipping duplicates.
Also extracts thumbnail image URLs from RSS media tags.
"""

import json
import os
import re
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
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


_BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

_OG_PATTERNS = [
    r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
    r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']',
    r'<meta[^>]+name=["\']twitter:image(?::src)?["\'][^>]+content=["\']([^"\']+)["\']',
    r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']twitter:image(?::src)?["\']',
]


def _fetch_og_image(url: str) -> str:
    """Fetch og:image / twitter:image from an article page."""
    if not url:
        return ""
    try:
        # Try requests first (better redirect + cookie handling)
        import requests as _req
        r = _req.get(url, headers=_BROWSER_HEADERS, timeout=8, allow_redirects=True)
        html = r.content[:131072].decode("utf-8", errors="ignore")
    except Exception:
        try:
            req = urllib.request.Request(url, headers=_BROWSER_HEADERS)
            with urllib.request.urlopen(req, timeout=8) as r:
                html = r.read(131072).decode("utf-8", errors="ignore")
        except Exception:
            return ""

    for pat in _OG_PATTERNS:
        m = re.search(pat, html, re.IGNORECASE)
        if m:
            img = m.group(1).strip()
            if img.startswith("http"):
                return img
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

    # Enrich missing images by fetching og:image from article pages in parallel
    missing = [a for a in collected if not a["image"]]
    if missing:
        print(f"  [IMG] Fetching og:image for {len(missing)} article(s)...")
        with ThreadPoolExecutor(max_workers=8) as pool:
            futures = {pool.submit(_fetch_og_image, a["url"]): a for a in missing}
            for fut in as_completed(futures):
                article = futures[fut]
                img = fut.result()
                if img:
                    article["image"] = img

    return collected


if __name__ == "__main__":
    articles = fetch_articles()
    print(f"Fetched {len(articles)} new article(s):")
    for a in articles:
        img = "✓ img" if a.get("image") else "  no img"
        print(f"  {img}  [{a['source']}] {a['title'][:70]}")
