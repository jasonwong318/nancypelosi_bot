from __future__ import annotations

import os
from typing import Any

import requests


def fundamentals_payload(symbols: list[str]) -> dict[str, Any]:
    items: dict[str, Any] = {}
    for symbol in symbols:
        yahoo_symbol = _to_yahoo_symbol(symbol)
        try:
            data = _fetch_yahoo_summary(yahoo_symbol)
        except Exception as exc:
            data = {"error": str(exc), "source": "Yahoo Finance quoteSummary"}
        items[symbol] = data

    # Supplement with Longbridge calc_indexes where credentials exist
    _supplement_longbridge(symbols, items)

    return {
        "status": "ok",
        "note": "P/E TTM, dividend yield, 52-week range, analyst target price where available.",
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
    fpe = _raw(sd, "forwardPE") or _raw(ks, "forwardPE")
    div = _raw(sd, "dividendYield") or _raw(sd, "trailingAnnualDividendYield")
    w52h = _raw(sd, "fiftyTwoWeekHigh")
    w52l = _raw(sd, "fiftyTwoWeekLow")
    target = _raw(fd, "targetMeanPrice")
    rec = _raw(fd, "recommendationKey")

    return {
        "pe_ttm": round(pe, 2) if pe else None,
        "forward_pe": round(fpe, 2) if fpe else None,
        "dividend_yield_pct": round(div * 100, 2) if div else None,
        "52w_high": w52h,
        "52w_low": w52l,
        "analyst_target_price": target,
        "analyst_recommendation": rec,
        "source": "Yahoo Finance quoteSummary",
    }


def _supplement_longbridge(symbols: list[str], items: dict[str, Any]) -> None:
    if not all(os.getenv(k) for k in ("LONGBRIDGE_APP_KEY", "LONGBRIDGE_APP_SECRET", "LONGBRIDGE_ACCESS_TOKEN")):
        return
    try:
        from longbridge.openapi import CalcIndex, Config, QuoteContext

        config = Config.from_apikey_env()
        ctx = QuoteContext(config)

        lb_symbols = [_to_longbridge_symbol(s) for s in symbols]
        index_candidates = ["PeTtmRatio", "PbRatio", "DividendRatioTtm", "TotalMarketValue"]
        indexes = []
        for name in index_candidates:
            idx = getattr(CalcIndex, name, None)
            if idx is not None:
                indexes.append(idx)
        if not indexes:
            return

        response = ctx.calc_indexes(lb_symbols, indexes)
        for i, row in enumerate(response):
            if i >= len(symbols):
                break
            symbol = symbols[i]
            lb_entry = {
                "lb_pe_ttm": _attr(row, "pe_ttm_ratio"),
                "lb_pb": _attr(row, "pb_ratio"),
                "lb_dividend_yield_pct": _attr(row, "dividend_ratio_ttm"),
                "lb_market_cap": _attr(row, "total_market_value"),
                "source_lb": "Longbridge calc_indexes",
            }
            items.setdefault(symbol, {}).update({k: v for k, v in lb_entry.items() if v is not None})
    except Exception:
        pass


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
