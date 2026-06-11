from __future__ import annotations

from datetime import datetime, timezone
from urllib.parse import quote_plus

import feedparser

from report_bot.symbols import metadata_for


def fetch_google_news(queries: list[str], limit_per_query: int = 8) -> list[dict[str, str]]:
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


def news_payload(queries: list[str], focus_symbols: list[str] | None = None) -> dict[str, object]:
    items = fetch_google_news(queries)

    # Add targeted queries for today's significant movers so news is always relevant
    if focus_symbols:
        dynamic: list[str] = []
        for symbol in focus_symbols[:3]:
            meta = metadata_for(symbol)
            ticker = symbol.split(".")[0]
            name = meta.get("name", "")
            dynamic.append(f"{ticker} {name}")
        extra = fetch_google_news(dynamic, limit_per_query=5)
        seen_links = {i["link"] for i in items}
        items += [e for e in extra if e["link"] not in seen_links]

    return {
        "fetched_at_utc": datetime.now(timezone.utc).isoformat(),
        "items": items,
    }
