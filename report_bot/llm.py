from __future__ import annotations

import json

import requests


def build_user_payload(quotes: dict, news: dict, portfolio: list[str], watchlist: list[str]) -> str:
    data = {
        "portfolio_symbols": portfolio,
        "watchlist_symbols": watchlist,
        "quotes": quotes,
        "news": news,
    }
    return (
        "請根據以下即時/最新資料，生成我的市場報告。"
        "若 Longbridge credentials 未配置或資料不足，必須明確說明不可作實時股價判斷。\n\n"
        + json.dumps(data, ensure_ascii=False, indent=2)
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
                "temperature": 0.35,
                "topP": 0.9,
                "maxOutputTokens": 1800,
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
