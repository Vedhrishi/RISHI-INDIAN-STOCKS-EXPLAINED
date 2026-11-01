"""Step 1: pull the newest unused article from an RSS feed."""
import json
import logging

import feedparser
import trafilatura

import config

log = logging.getLogger(__name__)


def _load_used() -> set:
    if config.STATE_FILE.exists():
        return set(json.loads(config.STATE_FILE.read_text()))
    return set()


def mark_used(link: str) -> None:
    used = _load_used()
    used.add(link)
    config.STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    config.STATE_FILE.write_text(json.dumps(sorted(used)))


def get_next_article() -> dict:
    feed = feedparser.parse(config.RSS_FEED_URL)
    if not feed.entries:
        raise RuntimeError(f"No entries in feed {config.RSS_FEED_URL}")
    used = _load_used()
    for entry in feed.entries:
        link = entry.get("link")
        if not link or link in used:
            continue
        text = ""
        downloaded = trafilatura.fetch_url(link)
        if downloaded:
            text = trafilatura.extract(downloaded) or ""
        if len(text) < 300:  # paywall / extraction failure: fall back to the feed summary
            text = entry.get("summary", "")
        if len(text) < 100:
            continue
        log.info("Selected article: %s", entry.get("title"))
        return {"title": entry.get("title", ""), "link": link, "text": text[:8000]}
    raise RuntimeError("No unused articles with usable text found")
