from __future__ import annotations

import time

import requests


MAX_TELEGRAM_CHARS = 3900


def split_message(text: str) -> list[str]:
    text = text.strip()
    if not text:
        return ["空白報告。"]
    if len(text) <= MAX_TELEGRAM_CHARS:
        return [text]

    chunks: list[str] = []
    remaining = text
    while remaining:
        if len(remaining) <= MAX_TELEGRAM_CHARS:
            chunks.append(remaining)
            break
        # Prefer splitting at a section heading so chunks start cleanly
        boundary = remaining.rfind("\n## ", 500, MAX_TELEGRAM_CHARS)
        if boundary < 0:
            boundary = remaining.rfind("\n", 500, MAX_TELEGRAM_CHARS)
        split_at = boundary if boundary > 0 else MAX_TELEGRAM_CHARS
        chunks.append(remaining[:split_at].rstrip())
        remaining = remaining[split_at:].lstrip()
    return chunks


def send_telegram_message(bot_token: str, chat_id: str, text: str) -> None:
    if not bot_token or not chat_id:
        raise RuntimeError("TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be configured.")

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    chunks = split_message(text)
    for i, chunk in enumerate(chunks):
        if i > 0:
            time.sleep(1)  # avoid Telegram rate limiting between chunks
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
