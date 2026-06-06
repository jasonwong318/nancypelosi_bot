from __future__ import annotations

from typing import Any


def risk_payload(
    portfolio_symbols: list[str],
    watchlist_symbols: list[str],
    symbol_metadata: dict[str, Any],
) -> dict[str, Any]:
    total = len(portfolio_symbols)
    hk_symbols = [s for s in portfolio_symbols if s.endswith(".HK")]
    us_symbols = [s for s in portfolio_symbols if s.endswith(".US")]

    def pct(n: int) -> str:
        return f"{n / total * 100:.0f}%" if total else "0%"

    etf_symbols = [
        s for s in portfolio_symbols
        if symbol_metadata.get(s, {}).get("type") == "ETF"
    ]
    stock_symbols = [
        s for s in portfolio_symbols
        if symbol_metadata.get(s, {}).get("type") == "stock"
    ]

    return {
        "status": "basic_symbol_level_risk_only",
        "note": (
            "Preliminary risk radar based on symbol count only. "
            "True VaR, beta, drawdown, margin, and P&L require "
            "account data with position sizes and cost basis (Phase 2)."
        ),
        "concentration": {
            "total_positions": total,
            "hk_count": len(hk_symbols),
            "us_count": len(us_symbols),
            "hk_symbols": hk_symbols,
            "us_symbols": us_symbols,
            "hk_weight_approx": pct(len(hk_symbols)),
            "us_weight_approx": pct(len(us_symbols)),
            "etf_count": len(etf_symbols),
            "stock_count": len(stock_symbols),
            "etf_symbols": etf_symbols,
        },
        "watchlist_count": len(watchlist_symbols),
        "watchlist_symbols": watchlist_symbols,
    }
