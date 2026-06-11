from __future__ import annotations

import json
from typing import Any

import requests


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
    data = {
        "report_type": "scheduled_investment_intelligence_memo",
        "portfolio_symbols": portfolio,
        "watchlist_symbols": watchlist,
        "authoritative_symbol_metadata": symbol_metadata,
        "market_data": quotes,
        "movers_summary": movers,
        "fundamentals_data": fundamentals,
        "macro_data": macro,
        "news_data": news,
        "account_data": account,
        "risk_data": risk,
        "instructions": [
            "CRITICAL DIRECTION RULE: Copy gainers_summary and losers_summary verbatim for all up/down statements. Never infer direction from price numbers.",
            "FOCUS RULE: Deep analysis only for symbols in movers_summary.focus_symbols. All other holdings use one-line table format.",
            "Use authoritative_symbol_metadata as the only source for ticker-to-company mapping.",
            "If market_data.status is longbridge_missing_using_yahoo_fallback, state this clearly.",
            "Only attribute news to a stock when the article title explicitly names the ticker, company, parent, ADR, or same listed entity.",
            "Treat ETF symbols as ETF/strategy products, not operating companies.",
            "Account data is a placeholder unless status is manual_positions_loaded.",
            "If fundamentals_data item has error or no data, write 資料不足, do not invent ratios.",
            "Every stock-specific conclusion must trace to market_data, movers_summary, news_data, fundamentals_data, macro_data, account_data, or risk_data.",
        ],
    }
    return "Generate the scheduled investment intelligence memo from this JSON payload.\n\n" + json.dumps(
        data,
        ensure_ascii=False,
        indent=2,
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
                "temperature": 0.2,
                "topP": 0.85,
                "maxOutputTokens": 3000,
            },
        },
        timeout=60,
    )
    response.raise_for_status()
    payload = response.json()
    candidates = payload.get("candidates", [])
    if not candidates:
        return "LLM 沒有返回內容。請檢查 Gemini API key、模型名稱與 quota。"

    parts = candidates[0].get("content", {}).get("parts", [])
    text = "".join(part.get("text", "") for part in parts).strip()
    return text or "LLM 返回空白內容。"


def fallback_report(user_payload: str) -> str:
    return (
        "【市場報告系統提示】\n"
        "Gemini API key 尚未配置。\n\n"
        f"{user_payload[:3000]}"
    )
