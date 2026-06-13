from __future__ import annotations

from datetime import datetime, timezone
from urllib.parse import quote_plus

import feedparser

from report_bot.symbols import metadata_for


def fetch_google_news(
    queries: list[str],
    limit_per_query: int = 6,
    lang: str = "zh-HK",
    region: str = "HK",
    ceid: str = "HK:zh-Hant",
) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    seen: set[str] = set()
    for query in queries:
        url = (
            "https://news.google.com/rss/search?"
            f"q={quote_plus(query)}&hl={lang}&gl={region}&ceid={ceid}"
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
    # Primary queries (user-configured, mix of Chinese and English)
    items = fetch_google_news(queries, limit_per_query=6)

    # English supplement for global events that Chinese queries miss
    en_items = fetch_google_news(
        queries,
        limit_per_query=4,
        lang="en-US",
        region="US",
        ceid="US:en",
    )
    seen_links = {i["link"] for i in items}
    items += [e for e in en_items if e["link"] not in seen_links]

    # Targeted queries for today's biggest movers
    if focus_symbols:
        dynamic: list[str] = []
        for symbol in focus_symbols[:3]:
            meta = metadata_for(symbol)
            ticker = symbol.split(".")[0]
            name = meta.get("name", "")
            dynamic.append(f"{ticker} {name}")
        extra = fetch_google_news(dynamic, limit_per_query=4)
        seen_links = {i["link"] for i in items}
        items += [e for e in extra if e["link"] not in seen_links]

    return {
        "fetched_at_utc": datetime.now(timezone.utc).isoformat(),
        "items": items,
    }
