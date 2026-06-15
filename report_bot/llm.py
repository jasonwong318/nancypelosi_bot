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
        pe = fund.get("lb_pe_ttm") or fund.get("pe_ttm")
        div = fund.get("lb_dividend_yield_pct") or fund.get("dividend_yield_pct")
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

        rows.append(
            {
                "symbol": symbol,
                "name": symbol_metadata.get(symbol, {}).get("name", ""),
                "security_type": symbol_metadata.get(symbol, {}).get("type", ""),
                "change": cp_str,
                "last_price": str(last) if last else "N/A",
                "valuation_metric": metric,
                "analyst_upside": upside,
            }
        )
    return rows


def build_user_payload(
    quotes: dict[str, Any],
    movers: dict[str, Any],
    news: dict[str, Any],
    macro: dict[str, Any],
    account: dict[str, Any],
    risk: dict[str, Any],
    fundamentals: dict[str, Any],
    portfolio: list[str],
    watchlist: list[str],
    symbol_metadata: dict[str, Any],
) -> str:
    holdings_table = _build_holdings_table(quotes, portfolio, fundamentals, symbol_metadata)

    data = {
        "report_type": "scheduled_investment_intelligence_memo",
        "portfolio_symbols": portfolio,
        "watchlist_symbols": watchlist,
        "authoritative_symbol_metadata": symbol_metadata,
        # Pre-formatted holdings table: use the 'change' field directly — no parsing needed
        "holdings_table": holdings_table,
        "movers_summary": movers,
        "fundamentals_data": fundamentals,
        "macro_data": macro,
        "news_data": news,
        "account_data": account,
        "risk_data": risk,
        "instructions": [
            "DIRECTION RULE: For all up/down statements, use movers_summary.gainers_summary and losers_summary verbatim. Never guess direction from prices.",
            "HOLDINGS TABLE: Use holdings_table for the portfolio section. Each row has 'change' (the pre-computed +/-% string) and 'valuation_metric'. Use these exact values — do NOT write the word '漲跌' literally.",
            "QUIET DAY: movers_summary.is_quiet_day indicates low volatility. Do not output 'is_quiet_day=true' in the report — just adjust tone accordingly.",
            "Use authoritative_symbol_metadata as the only source for ticker-to-company mapping.",
            "If market_data.status contains 'yahoo_fallback', state Longbridge is not connected.",
            "Only attribute news to a stock when the article explicitly names the ticker, company, parent, ADR, or same listed entity.",
            "ETF symbols must be analysed as ETF/strategy products only.",
            "Do not invent fundamentals. If fundamentals_data item has error or missing fields, write '資料不足'.",
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

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    response = requests.post(
        url,
        params={"key": api_key},
        json={
            "systemInstruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"role": "user", "parts": [{"text": user_payload}]}],
            "generationConfig": {
                "temperature": 0.15,
                "topP": 0.85,
                "maxOutputTokens": 4000,
            },
        },
        timeout=90,
    )
    response.raise_for_status()
    payload = response.json()
    candidates = payload.get("candidates", [])
    if not candidates:
        return "LLM 沒有返回內容。請檢查 Gemini API key、模型名稱與 quota。"

    finish_reason = candidates[0].get("finishReason", "")
    print(f"Gemini finish reason: {finish_reason}")

    parts = candidates[0].get("content", {}).get("parts", [])
    text = "".join(part.get("text", "") for part in parts).strip()
    if not text:
        return "LLM 返回空白內容。"
    if finish_reason == "MAX_TOKENS":
        text += "\n\n⚠️ 報告因篇幅上限被截斷。"
    return text


def fallback_report(user_payload: str) -> str:
    return (
        "【市場報告系統提示】\n"
        "Gemini API key 尚未配置。\n\n"
        f"{user_payload[:3000]}"
    )
