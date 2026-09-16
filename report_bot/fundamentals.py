from __future__ import annotations

from typing import Any

import requests

from report_bot.longbridge_utils import (
    attr,
    has_longbridge_credentials,
    to_longbridge_symbol,
    to_number,
    to_yahoo_symbol,
)


def fundamentals_payload(symbols: list[str]) -> dict[str, Any]:
    if has_longbridge_credentials():
        try:
            items = _fetch_longbridge_fundamentals(symbols)
            return {
                "status": "ok",
                "source": "Longbridge OpenAPI (valuation + institution_rating + forecast_eps)",
                "items": items,
            }
        except Exception as exc:
            return _fetch_yahoo_fundamentals(symbols, error=str(exc))
    return _fetch_yahoo_fundamentals(symbols)


def _fetch_longbridge_fundamentals(symbols: list[str]) -> dict[str, Any]:
    from longbridge.openapi import Config, FundamentalContext

    config = Config.from_apikey_env()
    ctx = FundamentalContext(config)

    items: dict[str, Any] = {}
    for symbol in symbols:
        lb_symbol = to_longbridge_symbol(symbol)
        entry: dict[str, Any] = {"source": "Longbridge OpenAPI"}

        try:
            valuation = ctx.valuation(lb_symbol)
            metrics = attr(valuation, "metrics")
            entry["pe_ttm"] = _latest_metric(attr(metrics, "pe"))
            entry["pb"] = _latest_metric(attr(metrics, "pb"))
            entry["ps"] = _latest_metric(attr(metrics, "ps"))
            entry["dividend_yield_pct"] = _latest_metric(attr(metrics, "dvd_yld"))
        except Exception as exc:
            entry["valuation_error"] = str(exc)

        try:
            rating = ctx.institution_rating(lb_symbol)
            latest = attr(rating, "latest")
            target = attr(latest, "target")
            low = to_number(attr(target, "lowest_price"))
            high = to_number(attr(target, "highest_price"))
            if low is not None and high is not None:
                entry["analyst_target_price"] = round((low + high) / 2, 2)
                entry["analyst_target_low"] = low
                entry["analyst_target_high"] = high
            evaluate = attr(latest, "evaluate")
            entry["analyst_recommend_counts"] = {
                "strong_buy": to_number(attr(evaluate, "over")),
                "buy": to_number(attr(evaluate, "buy")),
                "hold": to_number(attr(evaluate, "hold")),
                "sell": to_number(attr(evaluate, "sell")),
                "under": to_number(attr(evaluate, "under")),
            }
        except Exception as exc:
            entry["institution_rating_error"] = str(exc)

        try:
            forecast = ctx.forecast_eps(lb_symbol)
            forecast_items = attr(forecast, "items") or []
            if forecast_items:
                entry["forecast_eps_mean"] = to_number(attr(forecast_items[0], "forecast_eps_mean"))
        except Exception:
            pass

        items[symbol] = entry

    return items


def _fetch_yahoo_fundamentals(symbols: list[str], error: str | None = None) -> dict[str, Any]:
    items: dict[str, Any] = {}
    for symbol in symbols:
        yahoo_symbol = to_yahoo_symbol(symbol)
        try:
            items[symbol] = _fetch_yahoo_summary(yahoo_symbol)
        except Exception as exc:
            items[symbol] = {"error": str(exc), "source": "Yahoo Finance quoteSummary"}

    return {
        "status": "ok",
        "source": "Yahoo Finance quoteSummary (Longbridge fallback)",
        "note": error and f"Longbridge fundamentals failed: {error}" or None,
        "items": items,
    }


def _fetch_yahoo_summary(yahoo_symbol: str) -> dict[str, Any]:
    url = f"https://query1.finance.yahoo.com/v10/finance/quoteSummary/{yahoo_symbol}"
    response = requests.get(
        url,
        params={"modules": "summaryDetail,defaultKeyStatistics,financialData"},
        timeout=15,
        headers={"User-Agent": "Mozilla/5.0"},
    )
    response.raise_for_status()
    result = response.json().get("quoteSummary", {}).get("result") or []
    if not result:
        return {"source": "Yahoo Finance quoteSummary", "note": "no data"}

    sd = result[0].get("summaryDetail", {})
    ks = result[0].get("defaultKeyStatistics", {})
    fd = result[0].get("financialData", {})

    def _raw(d: dict, key: str) -> Any:
        v = d.get(key, {})
        return v.get("raw") if isinstance(v, dict) else v

    pe = _raw(sd, "trailingPE") or _raw(ks, "trailingPE")
    div = _raw(sd, "dividendYield") or _raw(sd, "trailingAnnualDividendYield")
    target = _raw(fd, "targetMeanPrice")

    return {
        "pe_ttm": round(pe, 2) if pe else None,
        "dividend_yield_pct": round(div * 100, 2) if div else None,
        "analyst_target_price": target,
        "source": "Yahoo Finance quoteSummary",
    }


def _latest_metric(metric: Any) -> float | None:
    """Extract the most recent value from a Longbridge ValuationMetricData time-series."""
    points = attr(metric, "list") or []
    if not points:
        return None
    return to_number(attr(points[-1], "value"))
