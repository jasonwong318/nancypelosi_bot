from __future__ import annotations

import os
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any


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
        return {
            "status": "missing_credentials",
            "message": "Longbridge OpenAPI credentials are not configured yet.",
            "quotes": [],
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
