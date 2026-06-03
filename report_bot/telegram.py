from __future__ import annotations

import requests


MAX_TELEGRAM_CHARS = 3900


def split_message(text: str) -> list[str]:
    chunks: list[str] = []
    remaining = text.strip()
    while remaining:
        chunks.append(remaining[:MAX_TELEGRAM_CHARS])
        remaining = remaining[MAX_TELEGRAM_CHARS:]
    return chunks or ["空白報告。"]


def send_telegram_message(bot_token: str, chat_id: str, text: str) -> None:
    if not bot_token or not chat_id:
        raise RuntimeError("TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be configured.")

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    for chunk in split_message(text):
        response = requests.post(
            url,
            json={
                "chat_id": chat_id,
                "text": chunk,
                "disable_web_page_preview": True,
            },
            timeout=30,
        )
        response.raise_for_status()
