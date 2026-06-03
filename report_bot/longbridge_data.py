from __future__ import annotations

import os
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any

import requests


@dataclass
class Quote:
    symbol: str
    last_done: str | None = None
    open: str | None = None
    high: str | None = None
    low: str | None = None
    prev_close: str | None = None
    volume: int | None = None
    turnover: str | None = None
    timestamp: str | None = None
    source: str = "Longbridge OpenAPI"


def has_longbridge_credentials() -> bool:
    return all(
        os.getenv(name)
        for name in ("LONGBRIDGE_APP_KEY", "LONGBRIDGE_APP_SECRET", "LONGBRIDGE_ACCESS_TOKEN")
    )


def _read_attr(obj: Any, name: str) -> Any:
    if isinstance(obj, dict):
        return obj.get(name)
    return getattr(obj, name, None)


def _quote_to_dict(item: Any) -> dict[str, Any]:
    timestamp = _read_attr(item, "timestamp")
    if isinstance(timestamp, (int, float)):
        timestamp = datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat()
    symbol = _read_attr(item, "symbol") or _read_attr(item, "security") or "UNKNOWN"
    quote = Quote(
        symbol=str(symbol),
        last_done=_to_str(_read_attr(item, "last_done")),
        open=_to_str(_read_attr(item, "open")),
        high=_to_str(_read_attr(item, "high")),
        low=_to_str(_read_attr(item, "low")),
        prev_close=_to_str(_read_attr(item, "prev_close")),
        volume=_read_attr(item, "volume"),
        turnover=_to_str(_read_attr(item, "turnover")),
        timestamp=str(timestamp) if timestamp else None,
    )
    return asdict(quote)


def _to_str(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


def fetch_quotes(symbols: list[str]) -> dict[str, Any]:
    if not has_longbridge_credentials():
        yahoo_quotes = fetch_yahoo_quotes(symbols)
        return {
            "status": "longbridge_missing_using_yahoo_fallback",
            "message": "Longbridge OpenAPI credentials are not configured yet.",
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


def fetch_yahoo_quotes(symbols: list[str]) -> list[dict[str, Any]]:
    quotes: list[dict[str, Any]] = []
    for symbol in symbols:
        yahoo_symbol = _to_yahoo_symbol(symbol)
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{yahoo_symbol}"
        try:
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
                continue
            meta = result[0].get("meta", {})
            quote = Quote(
                symbol=symbol,
                last_done=_to_str(meta.get("regularMarketPrice")),
                prev_close=_to_str(meta.get("chartPreviousClose") or meta.get("previousClose")),
                timestamp=datetime.now(timezone.utc).isoformat(),
                source="Yahoo Finance chart API fallback",
            )
            quotes.append(asdict(quote))
        except Exception as exc:
            quotes.append(
                {
                    "symbol": symbol,
                    "source": "Yahoo Finance chart API fallback",
                    "error": str(exc),
                }
            )
    return quotes


def _to_yahoo_symbol(symbol: str) -> str:
    if symbol.endswith(".US"):
        return symbol.removesuffix(".US")
    if symbol.endswith(".HK"):
        code = symbol.removesuffix(".HK")
        return f"{code.zfill(4)}.HK"
    return symbol

    try:
        if hasattr(Config, "from_apikey_env"):
            config = Config.from_apikey_env()
        else:
            config = Config.from_env()
        ctx = QuoteContext(config)
        response = ctx.quote(symbols)
        quotes = [_quote_to_dict(item) for item in response]
        return {"status": "ok", "quotes": quotes}
    except Exception as exc:
        return {
            "status": "error",
            "message": f"Longbridge quote request failed: {exc}",
            "quotes": [],
        }
