from __future__ import annotations

from datetime import datetime, timezone
from urllib.parse import quote_plus

import feedparser


def fetch_google_news(queries: list[str], limit_per_query: int = 5) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    seen: set[str] = set()
    for query in queries:
        url = (
            "https://news.google.com/rss/search?"
            f"q={quote_plus(query)}&hl=zh-HK&gl=HK&ceid=HK:zh-Hant"
        )
        feed = feedparser.parse(url)
        for entry in feed.entries[:limit_per_query]:
            link = getattr(entry, "link", "")
            if not link or link in seen:
                continue
            seen.add(link)
            items.append(
                {
                    "title": getattr(entry, "title", ""),
                    "link": link,
                    "published": getattr(entry, "published", ""),
                    "source": "Google News RSS",
                    "query": query,
                }
            )

    return items


def news_payload(queries: list[str]) -> dict[str, object]:
    return {
        "fetched_at_utc": datetime.now(timezone.utc).isoformat(),
        "items": fetch_google_news(queries),
    }
