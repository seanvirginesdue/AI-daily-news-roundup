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
    candidates: list[str] = []

    if hasattr(entry, "media_thumbnail") and entry.media_thumbnail:
        candidates.append(entry.media_thumbnail[0].get("url", ""))
    if hasattr(entry, "media_content") and entry.media_content:
        for m in entry.media_content:
            u = m.get("url", "")
            if u and any(ext in u.lower() for ext in [".jpg", ".jpeg", ".png", ".webp", "image"]):
                candidates.append(u)
    if hasattr(entry, "enclosures") and entry.enclosures:
        for enc in entry.enclosures:
            if "image" in enc.get("type", ""):
                candidates.append(enc.get("href", ""))
    raw = ""
    if hasattr(entry, "content") and entry.content:
        raw = entry.content[0].get("value", "")
    elif hasattr(entry, "summary"):
        raw = entry.summary or ""
    m = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', raw)
    if m:
        candidates.append(m.group(1))

    for url in candidates:
        url = _clean_img_url(url)
        if url and not _is_logo_or_icon(url):
            return url
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

# Tracking params to strip from image URLs (CDN sizing params are kept)
_STRIP_PARAMS = frozenset({
    "utm_source", "utm_medium", "utm_campaign", "utm_content",
    "utm_term", "utm_id", "fbclid", "gclid", "_ga", "mc_cid", "mc_eid",
})

# Path patterns that indicate a logo, icon, or other non-article image
_LOGO_RE = re.compile(
    r"(logo|favicon|icon|avatar|sprite|watermark|badge|16x16|32x32|48x48|64x64)",
    re.IGNORECASE,
)


def _clean_img_url(url: str) -> str:
    """Normalize image URL: force HTTPS, strip tracking params."""
    if not url:
        return ""
    if url.startswith("http://"):
        url = "https://" + url[7:]
    try:
        p = urllib.parse.urlparse(url)
        qs = {k: v for k, v in urllib.parse.parse_qs(p.query, keep_blank_values=True).items()
              if k.lower() not in _STRIP_PARAMS}
        return urllib.parse.urlunparse(p._replace(query=urllib.parse.urlencode(qs, doseq=True)))
    except Exception:
        return url


def _is_logo_or_icon(url: str) -> bool:
    """Return True if the URL looks like a logo, favicon, or icon."""
    path = urllib.parse.urlparse(url).path
    return bool(_LOGO_RE.search(path))


def _validate_img_url(url: str, referer: str = "") -> bool:
    """Return False only when the URL is definitively not an image (404 or confirmed wrong type).
    Keep images that return 403/timeout — CDN bot-blocking doesn't mean email clients can't load them."""
    if not url or not url.startswith("http"):
        return False
    if _is_logo_or_icon(url):
        return False
    try:
        import requests as _req
        hdrs = {**_BROWSER_HEADERS}
        if referer:
            hdrs["Referer"] = referer
        r = _req.head(url, headers=hdrs, timeout=3, allow_redirects=True)
        if r.status_code == 405:
            r = _req.get(url, headers=hdrs, timeout=3, allow_redirects=True, stream=True)
        if r.status_code == 404:
            return False
        if r.status_code == 200:
            ct = r.headers.get("content-type", "")
            if ct and not ct.startswith("image/"):
                return any(
                    url.lower().split("?")[0].endswith(ext)
                    for ext in (".jpg", ".jpeg", ".png", ".webp", ".gif")
                )
        # 403, 5xx, redirect chains — keep the URL, email clients may load it fine
        return True
    except Exception:
        return True  # network error ≠ broken image


def _picsum_fallback(source: str) -> str:
    """Resolve a consistent seeded picsum direct URL for the given source."""
    try:
        import requests as _req
        seed = re.sub(r"[^a-z0-9]", "-", source.lower().strip())[:20] or "tech"
        r = _req.get(
            f"https://picsum.photos/seed/{seed}/200/150",
            timeout=5, allow_redirects=True,
        )
        if r.status_code == 200 and r.headers.get("content-type", "").startswith("image/"):
            return r.url
    except Exception:
        pass
    return ""


def _parse_og(html: str) -> str:
    for pat in _OG_PATTERNS:
        m = re.search(pat, html, re.IGNORECASE)
        if m:
            img = _clean_img_url(m.group(1).strip())
            if img.startswith("http") and not _is_logo_or_icon(img):
                return img
    return ""


def _fetch_og_image(url: str) -> str:
    """Resolve Google News redirect → fetch og:image from actual article page."""
    if not url:
        return ""

    import requests as _req

    _html = ""
    article_url = url

    # Step 1: fetch article page, parse og:image / twitter:image
    try:
        r = _req.get(url, headers=_BROWSER_HEADERS, timeout=4, allow_redirects=True)
        if "google.com" not in r.url and r.status_code == 200:
            article_url = r.url
            _html = r.content[:131072].decode("utf-8", errors="ignore")
            img = _parse_og(_html)
            if img:
                return img
    except Exception as e:
        print(f"  [IMG] {type(e).__name__} fetching {url[:70]}")

    if "google.com" in article_url:
        return ""

    # Step 2: Microlink metadata API
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

    # Step 3: first sizeable <img> in the article body (skips icons/logos)
    if _html:
        for m in re.finditer(r'<img\b[^>]+\bsrc=["\']([^"\']{40,})["\']', _html, re.IGNORECASE):
            src = _clean_img_url(m.group(1))
            if src.startswith("http") and not _is_logo_or_icon(src) and not src.startswith("data:"):
                return src

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

    # Enrich missing images via og:image / Microlink
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

    # Validate all image URLs — clear hotlink-blocked or expired CDN URLs
    with_images = [a for a in collected if a.get("image")]
    if with_images:
        with ThreadPoolExecutor(max_workers=12) as pool:
            val_futures = {
                pool.submit(_validate_img_url, a["image"], a["url"]): a
                for a in with_images
            }
            for fut in as_completed(val_futures):
                if not fut.result():
                    art = val_futures[fut]
                    print(f"  [IMG] Blocked/invalid, clearing: {art['image'][:70]}")
                    art["image"] = ""

    return collected


if __name__ == "__main__":
    articles = fetch_articles()
    print(f"Fetched {len(articles)} new article(s):")
    for a in articles:
        img = "✓ img" if a.get("image") else "  no img"
        print(f"  {img}  [{a['source']}] {a['title'][:70]}".encode("ascii", errors="replace").decode())
