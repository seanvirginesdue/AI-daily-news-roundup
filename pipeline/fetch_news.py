"""
STEP 1 — RSS News Fetcher
Pulls the latest articles from configured feeds, skipping duplicates.
Also extracts thumbnail image URLs from RSS media tags.
"""

import calendar
import html
import json
import os
import re
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import feedparser

_MAX_AGE_DAYS = 30

CONFIG_FILE = Path(__file__).parent.parent / "config.json"


# Matt Wolfe — AI tools & news (810K subs). Swap channel ID to change source.
_YT_CHANNEL_ID = "UChpleBmo18P08aKCIgti38g"

def fetch_latest_yt_video(channel_id: str = _YT_CHANNEL_ID) -> dict | None:
    """Return the latest YouTube video from the channel as {title, url, thumbnail, channel}."""
    try:
        feed_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
        parsed = feedparser.parse(feed_url)
        if not parsed.entries:
            return None
        entry  = parsed.entries[0]
        vid_id = entry.get("yt_videoid") or entry.get("id", "").split(":")[-1]
        title  = entry.get("title", "")
        url    = entry.get("link", f"https://www.youtube.com/watch?v={vid_id}")
        thumb  = f"https://img.youtube.com/vi/{vid_id}/maxresdefault.jpg"
        channel = parsed.feed.get("title", "YouTube")
        return {"title": title, "url": url, "thumbnail": thumb, "channel": channel}
    except Exception:
        return None


_SEO_TIPS_URL = "https://chrisraulf.com/ai-seo-tips/"

def fetch_latest_seo_tip() -> dict | None:
    """Get the latest Chris Raulf AI SEO tip, always using the article's og:image (branded thumbnail)."""
    try:
        parsed = feedparser.parse("https://chrisraulf.com/feed/")
        for entry in parsed.entries:
            article = _entry_to_article(entry, "Chris Raulf AI SEO")
            if not article["title"] or not article["url"]:
                continue
            # Always fetch og:image from article page — RSS thumbnail is a smaller generic image
            og = _fetch_og_image(article["url"])
            if og:
                article["image"] = og
            return article
    except Exception:
        pass
    return None


def _is_recent(entry) -> bool:
    """Return True if the entry was published within _MAX_AGE_DAYS days."""
    parsed = getattr(entry, "published_parsed", None) or getattr(entry, "updated_parsed", None)
    if not parsed:
        return True  # no date info — include it
    age_days = (time.time() - calendar.timegm(parsed)) / 86400
    return age_days <= _MAX_AGE_DAYS


def _load_config() -> dict:
    with open(CONFIG_FILE) as f:
        return json.load(f)


def _load_seen(path: str) -> set:
    if os.path.exists(path):
        try:
            with open(path) as f:
                return set(json.load(f))
        except (json.JSONDecodeError, ValueError):
            print(f"  [WARN] {path} is malformed — resetting to empty")
            _save_seen(path, set())
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


def _parse_og(html: str) -> str:
    for pat in _OG_PATTERNS:
        m = re.search(pat, html, re.IGNORECASE)
        if m:
            img = m.group(1).strip()
            if img.startswith("http"):
                return img
    return ""


def _fetch_og_image(url: str) -> str:
    """Resolve Google News redirect → fetch og:image from actual article page."""
    if not url:
        return ""

    import requests as _req

    # Step 1: follow redirects to get the real article URL
    article_url = url
    try:
        r = _req.get(url, headers=_BROWSER_HEADERS, timeout=4, allow_redirects=True)
        # If we're no longer on google.com we have the real article URL
        if "google.com" not in r.url and r.status_code == 200:
            article_url = r.url
            img = _parse_og(r.content[:131072].decode("utf-8", errors="ignore"))
            if img:
                return img
    except Exception as e:
        print(f"  [IMG] {type(e).__name__} fetching {url[:70]}")

    # Step 2: Microlink with the resolved (non-Google) URL
    if "google.com" in article_url:
        return ""   # couldn't resolve past Google — skip rather than return Google logo
    try:
        api = "https://api.microlink.io/?url=" + urllib.parse.quote(article_url, safe="")
        r = _req.get(api, timeout=5)
        if r.status_code == 200:
            img_obj = r.json().get("data", {}).get("image") or {}
            src = img_obj.get("url", "") if isinstance(img_obj, dict) else ""
            if src and src.startswith("http"):
                return src
    except Exception:
        pass

    return ""


def _entry_to_article(entry, source_name: str) -> dict:
    content = ""
    if hasattr(entry, "content") and entry.content:
        content = entry.content[0].get("value", "")
    elif hasattr(entry, "summary"):
        content = entry.summary or ""

    content = re.sub(r"<[^>]+>", " ", content)
    content = html.unescape(content)
    content = re.sub(r"\s+", " ", content).strip()[:2000]

    return {
        "title":  entry.get("title", "").strip(),
        "source": source_name,
        "url":    entry.get("link", ""),
        "content": content or entry.get("title", ""),
        "image":  _extract_image(entry),
    }


def fetch_articles() -> list[dict]:
    config       = _load_config()
    seen_path    = config["seen_articles_file"]
    seen_urls    = _load_seen(seen_path)
    max_articles = config.get("max_articles", 18)
    feeds        = config["rss_feeds"]
    # at most 2 articles per feed so every source gets represented
    max_per_feed = max(2, max_articles // len(feeds))

    collected: list[dict] = []

    for feed_cfg in feeds:
        if len(collected) >= max_articles:
            break
        try:
            parsed = feedparser.parse(feed_cfg["url"])
        except Exception as exc:
            print(f"  [WARN] Could not fetch {feed_cfg['url']}: {exc}")
            continue

        feed_count = 0
        for entry in parsed.entries:
            if feed_count >= max_per_feed:
                break
            url = entry.get("link", "")
            if url in seen_urls:
                continue
            if not _is_recent(entry):
                continue
            article = _entry_to_article(entry, feed_cfg["name"])
            if not article["title"]:
                continue
            collected.append(article)
            seen_urls.add(url)
            feed_count += 1
            if len(collected) >= max_articles:
                break

    if collected:
        _save_seen(seen_path, seen_urls)

    # Enrich missing images by resolving redirects + fetching og:image in parallel
    missing = [a for a in collected if not a["image"]]
    if missing:
        print(f"  [IMG] Resolving images for {len(missing)} article(s)...")
        with ThreadPoolExecutor(max_workers=12) as pool:
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
        print(f"  {img}  [{a['source']}] {a['title'][:70]}".encode("ascii", errors="replace").decode())
