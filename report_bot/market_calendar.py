from __future__ import annotations

import os
from datetime import date, timedelta
from typing import Any


def calendar_payload(today_hkt: date) -> dict[str, Any]:
    """Whether HK/US markets trade today, from the Longbridge exchange calendar.
    Falls back to a weekday check if the API is unavailable (holidays then go undetected)."""
    result: dict[str, Any] = {
        "date": today_hkt.isoformat(),
        "hk_trading_today": today_hkt.weekday() < 5,
        "us_trading_today": today_hkt.weekday() < 5,
        "hk_half_day": False,
        "source": "weekday fallback",
    }
    if not _has_longbridge_credentials():
        return result

    try:
        from longbridge.openapi import Config, Market, QuoteContext

        ctx = QuoteContext(Config.from_apikey_env())
        begin = today_hkt - timedelta(days=1)
        end = today_hkt + timedelta(days=1)
        hk = ctx.trading_days(Market.HK, begin, end)
        us = ctx.trading_days(Market.US, begin, end)
        result["hk_trading_today"] = today_hkt in (hk.trading_days or []) or today_hkt in (hk.half_trading_days or [])
        result["hk_half_day"] = today_hkt in (hk.half_trading_days or [])
        result["us_trading_today"] = today_hkt in (us.trading_days or [])
        result["source"] = "Longbridge trading_days"
    except Exception as exc:
        result["note"] = f"trading_days lookup failed: {exc}"
    return result


def closure_notice(calendar: dict[str, Any]) -> str | None:
    """Short header line when at least one market is closed today; None on normal days."""
    hk = calendar.get("hk_trading_today")
    us = calendar.get("us_trading_today")
    if hk and us:
        return "⏰ 港股半日市" if calendar.get("hk_half_day") else None
    if not hk and not us:
        return "📅 今日港股及美股均休市（假期），以下為近況整理"
    if not hk:
        return "📅 今日港股休市（假期），美股正常交易"
    return "📅 今日美股休市（假期），港股正常交易"


def _has_longbridge_credentials() -> bool:
    return all(
        os.getenv(name)
        for name in ("LONGBRIDGE_APP_KEY", "LONGBRIDGE_APP_SECRET", "LONGBRIDGE_ACCESS_TOKEN")
    )
