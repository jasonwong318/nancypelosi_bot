from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from report_bot.longbridge_data import fetch_yahoo_index_quote


_MACRO_SYMBOLS = [
    ("VIX", "^VIX", "CBOE Volatility Index"),
    ("US10Y", "^TNX", "US 10-Year Treasury Yield"),
    ("DXY", "DX-Y.NYB", "US Dollar Index"),
    ("GOLD", "GC=F", "Gold Futures"),
    ("OIL", "CL=F", "WTI Crude Oil Futures"),
]


def macro_payload() -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    for key, yahoo_symbol, name in _MACRO_SYMBOLS:
        try:
            quote = fetch_yahoo_index_quote(key, yahoo_symbol, name)
            items.append(quote)
        except Exception as exc:
            items.append(
                {
                    "symbol": key,
                    "name": name,
                    "error": str(exc),
                    "source": "Yahoo Finance chart API",
                }
            )
    return {
        "fetched_at_utc": datetime.now(timezone.utc).isoformat(),
        "items": items,
    }
