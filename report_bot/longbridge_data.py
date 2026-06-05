from __future__ import annotations

import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any

import requests

from report_bot.symbols import metadata_for


@dataclass
class Quote:
    symbol: str
    name: str | None = None
    market: str | None = None
    security_type: str | None = None
    last_done: str | None = None
    prev_close: str | None = None
    change: str | None = None
    change_percent: str | None = None
    open: str | None = None
    high: str | None = None
    low: str | None = None
    volume: int | None = None
    turnover: str | None = None
    timestamp: str | None = None
    source: str = "Longbridge OpenAPI"


def fetch_quotes(symbols: list[str]) -> dict[str, Any]:
    if not _has_longbridge_credentials():
        yahoo_quotes = fetch_yahoo_quotes(symbols)
        return {
            "status": "longbridge_missing_using_yahoo_fallback",
            "message": "Longbridge OpenAPI credentials are not configured yet. Yahoo Finance chart API is used as a temporary fallback.",
            "quotes": yahoo_quotes,
        }

    try:
        from longbridge.openapi import Config, QuoteContext
    except Exception as exc:
        return {
            "status": "sdk_unavailable",
            "message": f"Longbridge SDK import failed: {exc}",
            "quotes": [],
        }

    try:
        config = Config.from_apikey_env()
        ctx = QuoteContext(config)
        response = ctx.quote([_to_longbridge_symbol(symbol) for symbol in symbols])
        quotes = [_longbridge_quote_to_dict(item) for item in response]
        return {"status": "ok", "message": "Quotes loaded from Longbridge OpenAPI.", "quotes": quotes}
    except Exception as exc:
        return {
            "status": "error",
            "message": f"Longbridge quote request failed: {exc}",
            "quotes": [],
        }


def fetch_yahoo_quotes(symbols: list[str]) -> list[dict[str, Any]]:
    quotes: list[dict[str, Any]] = []
    for symbol in symbols:
        yahoo_symbol = _to_yahoo_symbol(symbol)
        try:
            quote = _fetch_yahoo_chart_quote(
                requested_symbol=symbol,
                yahoo_symbol=yahoo_symbol,
                source="Yahoo Finance chart API fallback",
            )
            quotes.append(quote)
        except Exception as exc:
            metadata = metadata_for(symbol)
            quotes.append(
                {
                    "symbol": symbol,
                    "name": metadata["name"],
                    "market": metadata["market"],
                    "security_type": metadata["type"],
                    "source": "Yahoo Finance chart API fallback",
                    "error": str(exc),
                }
            )
    return quotes


def fetch_yahoo_index_quote(symbol: str, yahoo_symbol: str, name: str) -> dict[str, Any]:
    quote = _fetch_yahoo_chart_quote(
        requested_symbol=symbol,
        yahoo_symbol=yahoo_symbol,
        source="Yahoo Finance chart API",
    )
    quote["name"] = name
    return quote


def _has_longbridge_credentials() -> bool:
    return all(
        os.getenv(name)
        for name in ("LONGBRIDGE_APP_KEY", "LONGBRIDGE_APP_SECRET", "LONGBRIDGE_ACCESS_TOKEN")
    )


def _fetch_yahoo_chart_quote(requested_symbol: str, yahoo_symbol: str, source: str) -> dict[str, Any]:
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{yahoo_symbol}"
    response = requests.get(
        url,
        params={"range": "1d", "interval": "1m"},
        timeout=20,
        headers={"User-Agent": "Mozilla/5.0"},
    )
    response.raise_for_status()
    payload = response.json()
    result = payload.get("chart", {}).get("result", [])
    if not result:
        raise RuntimeError("Yahoo Finance returned no chart result.")

    meta = result[0].get("meta", {})
    last_done = _number(meta.get("regularMarketPrice"))
    prev_close = _number(meta.get("chartPreviousClose") or meta.get("previousClose"))
    change = None
    change_percent = None
    if last_done is not None and prev_close not in (None, 0):
        raw_change = last_done - prev_close
        change = f"{raw_change:.4f}"
        change_percent = f"{(raw_change / prev_close) * 100:.2f}%"

    metadata = metadata_for(requested_symbol)
    quote = Quote(
        symbol=requested_symbol,
        name=metadata["name"],
        market=metadata["market"],
        security_type=metadata["type"],
        last_done=_to_str(last_done),
        prev_close=_to_str(prev_close),
        change=change,
        change_percent=change_percent,
        timestamp=datetime.now(timezone.utc).isoformat(),
        source=source,
    )
    return asdict(quote)


def _longbridge_quote_to_dict(item: Any) -> dict[str, Any]:
    symbol = _read_attr(item, "symbol") or _read_attr(item, "security") or "UNKNOWN"
    metadata = metadata_for(str(symbol))
    last_done = _to_str(_read_attr(item, "last_done"))
    prev_close = _to_str(_read_attr(item, "prev_close"))
    timestamp = _read_attr(item, "timestamp")
    if isinstance(timestamp, (int, float)):
        timestamp = datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat()

    return asdict(
        Quote(
            symbol=str(symbol),
            name=metadata["name"],
            market=metadata["market"],
            security_type=metadata["type"],
            last_done=last_done,
            prev_close=prev_close,
            change=_to_str(_read_attr(item, "change")),
            change_percent=_to_str(_read_attr(item, "change_percent")),
            open=_to_str(_read_attr(item, "open")),
            high=_to_str(_read_attr(item, "high")),
            low=_to_str(_read_attr(item, "low")),
            volume=_read_attr(item, "volume"),
            turnover=_to_str(_read_attr(item, "turnover")),
            timestamp=str(timestamp) if timestamp else None,
            source="Longbridge OpenAPI",
        )
    )


def _read_attr(obj: Any, name: str) -> Any:
    if isinstance(obj, dict):
        return obj.get(name)
    return getattr(obj, name, None)


def _to_yahoo_symbol(symbol: str) -> str:
    if symbol.endswith(".US"):
        return symbol.removesuffix(".US")
    if symbol.endswith(".HK"):
        code = symbol.removesuffix(".HK")
        return f"{code.zfill(4)}.HK"
    return symbol


def _to_longbridge_symbol(symbol: str) -> str:
    if symbol.endswith(".HK"):
        code = symbol.removesuffix(".HK")
        if code.isdigit():
            return f"{int(code)}.HK"
    return symbol


def _number(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_str(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)
