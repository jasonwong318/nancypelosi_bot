from __future__ import annotations

import os
from typing import Any

import requests


def fundamentals_payload(symbols: list[str]) -> dict[str, Any]:
    if _has_longbridge_credentials():
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
        lb_symbol = _to_longbridge_symbol(symbol)
        entry: dict[str, Any] = {"source": "Longbridge OpenAPI"}

        try:
            valuation = ctx.valuation(lb_symbol)
            metrics = _attr(valuation, "metrics")
            entry["pe_ttm"] = _latest_metric(_attr(metrics, "pe"))
            entry["pb"] = _latest_metric(_attr(metrics, "pb"))
            entry["ps"] = _latest_metric(_attr(metrics, "ps"))
            entry["dividend_yield_pct"] = _latest_metric(_attr(metrics, "dvd_yld"))
        except Exception as exc:
            entry["valuation_error"] = str(exc)

        try:
            rating = ctx.institution_rating(lb_symbol)
            latest = _attr(rating, "latest")
            target = _attr(latest, "target")
            low = _num(_attr(target, "lowest_price"))
            high = _num(_attr(target, "highest_price"))
            if low is not None and high is not None:
                entry["analyst_target_price"] = round((low + high) / 2, 2)
                entry["analyst_target_low"] = low
                entry["analyst_target_high"] = high
            evaluate = _attr(latest, "evaluate")
            entry["analyst_recommend_counts"] = {
                "strong_buy": _num(_attr(evaluate, "over")),
                "buy": _num(_attr(evaluate, "buy")),
                "hold": _num(_attr(evaluate, "hold")),
                "sell": _num(_attr(evaluate, "sell")),
                "under": _num(_attr(evaluate, "under")),
            }
        except Exception as exc:
            entry["institution_rating_error"] = str(exc)

        try:
            forecast = ctx.forecast_eps(lb_symbol)
            forecast_items = _attr(forecast, "items") or []
            if forecast_items:
                entry["forecast_eps_mean"] = _num(_attr(forecast_items[0], "forecast_eps_mean"))
        except Exception:
            pass

        items[symbol] = entry

    return items


def _fetch_yahoo_fundamentals(symbols: list[str], error: str | None = None) -> dict[str, Any]:
    items: dict[str, Any] = {}
    for symbol in symbols:
        yahoo_symbol = _to_yahoo_symbol(symbol)
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


def _has_longbridge_credentials() -> bool:
    return all(
        os.getenv(name)
        for name in ("LONGBRIDGE_APP_KEY", "LONGBRIDGE_APP_SECRET", "LONGBRIDGE_ACCESS_TOKEN")
    )


def _to_yahoo_symbol(symbol: str) -> str:
    if symbol.endswith(".US"):
        return symbol.removesuffix(".US")
    if symbol.endswith(".HK"):
        return symbol.removesuffix(".HK").zfill(4) + ".HK"
    return symbol


def _to_longbridge_symbol(symbol: str) -> str:
    if symbol.endswith(".HK"):
        code = symbol.removesuffix(".HK")
        if code.isdigit():
            return f"{int(code)}.HK"
    return symbol


def _attr(obj: Any, name: str) -> Any:
    return obj.get(name) if isinstance(obj, dict) else getattr(obj, name, None)


def _num(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _latest_metric(metric: Any) -> float | None:
    """Extract the most recent value from a Longbridge ValuationMetricData time-series."""
    points = _attr(metric, "list") or []
    if not points:
        return None
    return _num(_attr(points[-1], "value"))
