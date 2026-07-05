from __future__ import annotations

import decimal
import json
from typing import Any

import requests


class _Encoder(json.JSONEncoder):
    def default(self, o: Any) -> Any:
        if isinstance(o, decimal.Decimal):
            return float(o)
        return super().default(o)


def _build_holdings_table(
    quotes: dict[str, Any],
    portfolio: list[str],
    fundamentals: dict[str, Any],
    symbol_metadata: dict[str, Any],
) -> list[dict[str, Any]]:
    """Pre-format holdings so the LLM receives actual numbers, not raw JSON to parse."""
    quote_map = {q.get("symbol", ""): q for q in quotes.get("quotes", [])}
    fund_items = fundamentals.get("items", {})
    rows = []
    for symbol in portfolio:
        q = quote_map.get(symbol, {})
        cp_raw = q.get("change_percent")
        try:
            cp_str = f"{float(str(cp_raw).rstrip('%')):+.2f}%"
        except (TypeError, ValueError):
            cp_str = "N/A"

        fund = fund_items.get(symbol, {})
        pe = fund.get("pe_ttm")
        div = fund.get("dividend_yield_pct")
        target = fund.get("analyst_target_price")
        last = q.get("last_done")

        if pe:
            metric = f"P/E {float(pe):.1f}"
        elif div:
            metric = f"股息率 {float(div):.2f}%"
        else:
            metric = "估值資料不足"

        upside = None
        if target and last:
            try:
                upside = f"{(float(target) / float(last) - 1) * 100:+.1f}%"
            except (TypeError, ValueError, ZeroDivisionError):
                pass

        recommend = fund.get("analyst_recommend_counts") or {}
        buy_total = sum(
            int(v) for k, v in recommend.items() if v and k in ("strong_buy", "buy")
        )
        rating_total = sum(int(v) for v in recommend.values() if v)
        rating_str = f"{buy_total}/{rating_total} 買入" if rating_total else None

        rows.append(
            {
                "symbol": symbol,
                "name": symbol_metadata.get(symbol, {}).get("name", ""),
                "security_type": symbol_metadata.get(symbol, {}).get("type", ""),
                "change": cp_str,
                "last_price": str(last) if last else "N/A",
                "valuation_metric": metric,
                "analyst_upside": upside,
                "analyst_rating": rating_str,
                "forecast_eps_mean": fund.get("forecast_eps_mean"),
            }
        )
    return rows


def _slim_quotes(quotes: dict[str, Any]) -> dict[str, Any]:
    """Keep only the fields the LLM actually uses; open/high/low/turnover are noise."""
    return {
        "status": quotes.get("status"),
        "message": quotes.get("message"),
        "quotes": [
            {
                "symbol": q.get("symbol"),
                "name": q.get("name"),
                "change_percent": q.get("change_percent"),
                "last_done": q.get("last_done"),
                "source": q.get("source"),
            }
            for q in quotes.get("quotes", [])
        ],
    }


def build_user_payload(
    quotes: dict[str, Any],
    movers: dict[str, Any],
    news: dict[str, Any],
    macro: dict[str, Any],
    account: dict[str, Any],
    risk: dict[str, Any],
    fundamentals: dict[str, Any],
    sector: dict[str, Any],
    comparison: dict[str, Any],
    session: dict[str, str],
    sectors: dict[str, Any],
    portfolio: list[str],
    watchlist: list[str],
    symbol_metadata: dict[str, Any],
) -> str:
    holdings_table = _build_holdings_table(quotes, portfolio, fundamentals, symbol_metadata)

    data = {
        "report_type": "scheduled_investment_intelligence_memo",
        "report_session": session,
        "portfolio_symbols": portfolio,
        "watchlist_symbols": watchlist,
        "authoritative_symbol_metadata": symbol_metadata,
        "portfolio_sector_map": sectors,
        # Pre-formatted holdings table: use the 'change' field directly — no parsing needed
        "holdings_table": holdings_table,
        "movers_summary": movers,
        "fundamentals_status": {"status": fundamentals.get("status"), "source": fundamentals.get("source")},
        "previous_report_comparison": comparison,
        "market_data": _slim_quotes(quotes),
        "sector_data": sector,
        "macro_data": macro,
        "news_data": news,
        "account_data": account,
        "risk_data": risk,
        "instructions": [
            "SESSION: report_session.focus tells you which of the 3 daily runs this is (morning/midday/evening). The Executive Summary and overall framing MUST match that session's perspective.",
            "DIRECTION RULE: For all up/down statements, use movers_summary.gainers_summary and losers_summary verbatim. Never guess direction from prices.",
            "HOLDINGS TABLE: Use holdings_table for the portfolio section. Each row has 'change' (the pre-computed +/-% string) and 'valuation_metric'. Use these exact values — do NOT write the word '漲跌' literally.",
            "ANALYST DATA: holdings_table rows carry 'analyst_upside' (% to consensus target), 'analyst_rating' (buy count / total), and 'forecast_eps_mean'. The Buffett and Quant sections MUST cite these numbers where present instead of generic statements.",
            "CONTINUITY: previous_report_comparison contains each symbol's move in the previous report and any multi-run streaks. Reference streaks and reversals (e.g. 連續3次報告下跌 / 扭轉昨日跌勢) — this is what makes the report feel like a series, not isolated snapshots.",
            "QUIET DAY: movers_summary.is_quiet_day indicates low volatility. Do not output 'is_quiet_day=true' in the report — just adjust tone accordingly.",
            "Use authoritative_symbol_metadata as the only source for ticker-to-company mapping.",
            "If market_data.status contains 'yahoo_fallback', state Longbridge is not connected.",
            "Only attribute news to a stock when the article explicitly names the ticker, company, parent, ADR, or same listed entity.",
            "ETF symbols must be analysed as ETF/strategy products only.",
            "Do not invent fundamentals. If fundamentals_data fields are missing, write '資料不足'.",
            "SECTOR DATA: sector_data.top_movers and sector_data.anomalies are real-time structured market-wide signals (not LLM-inferred). Use them as the factual basis for the sector/theme section instead of guessing from news headlines alone. If both lists are empty, say market-wide moves are unremarkable today.",
            "SECTOR MAP: portfolio_sector_map lists the sectors this portfolio/watchlist is actually exposed to. Check news_data and sector_data against THESE sectors — do not spend words on sectors with no exposure.",
            "NEWS ATTRIBUTION: news_data.items are pre-filtered to the last 48 hours and sorted newest first; each has 'published_hkt'. Items with source 'Longbridge News' include a 'symbol' field — these are already correctly tied to that ticker. Items with source 'Google News RSS' are broader market/macro context and must only be attributed to a holding if the title explicitly names it.",
        ],
    }
    return "Generate the scheduled investment intelligence memo from this JSON payload.\n\n" + json.dumps(
        data,
        ensure_ascii=False,
        indent=2,
        cls=_Encoder,
    )


def generate_report(
    api_key: str,
    model: str,
    system_prompt: str,
    user_payload: str,
) -> str:
    if not api_key:
        return fallback_report(user_payload)

    response = requests.post(
        "https://open.bigmodel.cn/api/paas/v4/chat/completions",
        headers={"Authorization": f"Bearer {api_key}"},
        json={
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_payload},
            ],
            "temperature": 0.15,
            "top_p": 0.85,
            "max_tokens": 8000,
        },
        timeout=90,
    )
    response.raise_for_status()
    payload = response.json()
    choices = payload.get("choices", [])
    if not choices:
        return "LLM 沒有返回內容。請檢查 GLM API key、模型名稱與 quota。"

    finish_reason = choices[0].get("finish_reason", "")
    print(f"GLM finish reason: {finish_reason}")

    text = (choices[0].get("message", {}).get("content") or "").strip()
    if not text:
        return "LLM 返回空白內容。"
    if finish_reason == "length":
        text += "\n\n⚠️ 報告因篇幅上限被截斷。"
    return text


def fallback_report(user_payload: str) -> str:
    return (
        "【市場報告系統提示】\n"
        "GLM API key 尚未配置。\n\n"
        f"{user_payload[:3000]}"
    )
