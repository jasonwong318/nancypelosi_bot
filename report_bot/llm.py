from __future__ import annotations

import json
from typing import Any

import requests


def build_user_payload(
    quotes: dict[str, Any],
    news: dict[str, Any],
    macro: dict[str, Any],
    account: dict[str, Any],
    risk: dict[str, Any],
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
        "macro_data": macro,
        "news_data": news,
        "account_data": account,
        "risk_data": risk,
        "instructions": [
            "Use authoritative_symbol_metadata as the only source for ticker-to-company mapping.",
            "Do not infer or rename tickers. If a symbol is unknown, say it is unknown.",
            "If market_data.status is longbridge_missing_using_yahoo_fallback, clearly state that Longbridge real-time data is not connected yet.",
            "Only attribute news to a holding/watchlist name when the article title explicitly mentions the ticker, company name, parent company, ADR, or same listed entity.",
            "Treat ETF symbols as ETF/strategy products, not operating companies.",
            "Account data is a placeholder unless status says manual_positions_loaded. Do not invent position size, cost basis, P&L, cash, or margin.",
            "Every stock-specific conclusion must be traceable to market_data, news_data, macro_data, account_data, or risk_data.",
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
                "temperature": 0.25,
                "topP": 0.85,
                "maxOutputTokens": 2200,
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
        "Gemini API key 尚未配置，因此目前只完成資料收集，未進行 LLM 整合。\n\n"
        "下一步：在 GitHub Secrets 加入 GEMINI_API_KEY 後，系統會自動套用 system_prompt.txt 生成正體中文報告。\n\n"
        "原始資料摘要：\n"
        f"{user_payload[:3000]}"
    )
