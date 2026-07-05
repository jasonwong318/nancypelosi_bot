from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from typing import Any
from urllib.parse import quote_plus

import feedparser

from report_bot.symbols import metadata_for

MAX_NEWS_AGE_HOURS = 48


def _parse_published(value: str) -> datetime | None:
    if not value:
        return None
    try:
        parsed = parsedate_to_datetime(value)  # RFC 2822, used by Google News RSS
    except (TypeError, ValueError):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _filter_and_sort_recent(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Drop stale articles and sort newest first. Items with unparseable dates are
    kept (Longbridge timestamps vary) but sorted after dated ones."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=MAX_NEWS_AGE_HOURS)
    kept: list[tuple[datetime | None, dict[str, Any]]] = []
    for item in items:
        published = _parse_published(str(item.get("published", "")))
        if published is not None and published < cutoff:
            continue
        if published is not None:
            item["published_hkt"] = published.astimezone(timezone(timedelta(hours=8))).strftime("%m-%d %H:%M HKT")
        kept.append((published, item))
    kept.sort(key=lambda pair: pair[0] or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    return [item for _, item in kept]


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


def fetch_longbridge_news(symbols: list[str], limit_per_symbol: int = 3) -> list[dict[str, Any]]:
    if not _has_longbridge_credentials():
        return []
    try:
        from longbridge.openapi import Config, ContentContext

        config = Config.from_apikey_env()
        ctx = ContentContext(config)
    except Exception:
        return []

    items: list[dict[str, Any]] = []
    for symbol in symbols:
        try:
            news_items = ctx.news(_to_longbridge_symbol(symbol))
        except Exception:
            continue
        for item in news_items[:limit_per_symbol]:
            items.append(
                {
                    "title": _attr(item, "title") or "",
                    "description": (_attr(item, "description") or "")[:300],
                    "link": _attr(item, "url") or "",
                    "published": str(_attr(item, "published_at") or ""),
                    "source": "Longbridge News",
                    "symbol": symbol,
                }
            )
    return items


def news_payload(
    queries: list[str],
    symbols: list[str] | None = None,
    focus_symbols: list[str] | None = None,
) -> dict[str, object]:
    # Primary: Longbridge per-symbol news. Tied directly to a ticker, so it can
    # never be mis-attributed to the wrong holding the way keyword RSS search can.
    items: list[dict[str, Any]] = fetch_longbridge_news(symbols or [])

    # Supplement: broad macro/sector themes that aren't tied to a single ticker
    # (rate decisions, geopolitics, IPOs) — Longbridge's news endpoint is per-symbol only.
    google_items = fetch_google_news(queries, limit_per_query=6)
    en_items = fetch_google_news(
        queries,
        limit_per_query=4,
        lang="en-US",
        region="US",
        ceid="US:en",
    )
    seen_links = {i.get("link") for i in items}
    for entry in google_items + en_items:
        if entry["link"] not in seen_links:
            items.append(entry)
            seen_links.add(entry["link"])

    # Targeted queries for today's biggest movers
    if focus_symbols:
        dynamic: list[str] = []
        for symbol in focus_symbols[:3]:
            meta = metadata_for(symbol)
            ticker = symbol.split(".")[0]
            name = meta.get("name", "")
            dynamic.append(f"{ticker} {name}")
        extra = fetch_google_news(dynamic, limit_per_query=4)
        for entry in extra:
            if entry["link"] not in seen_links:
                items.append(entry)
                seen_links.add(entry["link"])

    items = _filter_and_sort_recent(items)

    # Cap the payload: symbol-attributed Longbridge items first, then the freshest
    # of the rest, so the LLM's attention isn't diluted by dozens of stale headlines.
    longbridge_items = [i for i in items if i.get("source") == "Longbridge News"]
    other_items = [i for i in items if i.get("source") != "Longbridge News"]
    items = longbridge_items[:20] + other_items[: max(0, 30 - min(len(longbridge_items), 20))]

    return {
        "fetched_at_utc": datetime.now(timezone.utc).isoformat(),
        "max_age_hours": MAX_NEWS_AGE_HOURS,
        "items": items,
    }


def _has_longbridge_credentials() -> bool:
    return all(
        os.getenv(name)
        for name in ("LONGBRIDGE_APP_KEY", "LONGBRIDGE_APP_SECRET", "LONGBRIDGE_ACCESS_TOKEN")
    )


def _to_longbridge_symbol(symbol: str) -> str:
    if symbol.endswith(".HK"):
        code = symbol.removesuffix(".HK")
        if code.isdigit():
            return f"{int(code)}.HK"
    return symbol


def _attr(obj: Any, name: str) -> Any:
    return obj.get(name) if isinstance(obj, dict) else getattr(obj, name, None)
