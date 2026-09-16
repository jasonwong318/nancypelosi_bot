from __future__ import annotations

import os
from typing import Any

"""Shared helpers for talking to the Longbridge OpenAPI, used by every module
that fetches quotes/news/fundamentals/sector/calendar data from it."""


def has_longbridge_credentials() -> bool:
    return all(
        os.getenv(name)
        for name in ("LONGBRIDGE_APP_KEY", "LONGBRIDGE_APP_SECRET", "LONGBRIDGE_ACCESS_TOKEN")
    )


def to_longbridge_symbol(symbol: str) -> str:
    """Longbridge wants HK codes without leading zeros (e.g. '941.HK', not '0941.HK')."""
    if symbol.endswith(".HK"):
        code = symbol.removesuffix(".HK")
        if code.isdigit():
            return f"{int(code)}.HK"
    return symbol


def to_yahoo_symbol(symbol: str) -> str:
    """Yahoo wants the opposite: 4-digit zero-padded HK codes, and no '.US' suffix."""
    if symbol.endswith(".US"):
        return symbol.removesuffix(".US")
    if symbol.endswith(".HK"):
        return symbol.removesuffix(".HK").zfill(4) + ".HK"
    return symbol


def attr(obj: Any, name: str) -> Any:
    """Longbridge SDK responses are sometimes dicts, sometimes objects — read either."""
    return obj.get(name) if isinstance(obj, dict) else getattr(obj, name, None)


def to_number(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
