from __future__ import annotations

import re
import time

import requests

MAX_TELEGRAM_CHARS = 3900
MAX_RETRIES = 3
RETRY_BACKOFF_SECONDS = (3, 8)


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


# A lone "*" followed by whitespace at the start of a line is a CommonMark list
# bullet, distinct from "**" (bold). Telegram's legacy Markdown doesn't know
# the difference — it just hunts for the next "*" to close an entity — so an
# unpaired bullet marker throws off every bold span after it on that line and
# can break the whole message. Swap it for a plain bullet character first.
_LIST_BULLET_RE = re.compile(r"^(\s*)\*(?!\*)(\s+)", re.MULTILINE)
_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")


def _to_telegram_markdown(text: str) -> str:
    """The LLM writes CommonMark (## headings, **bold**, * bullets), but
    Telegram's legacy Markdown mode has no heading syntax, uses a single
    asterisk for bold, and has no concept of a list marker at all."""
    lines = []
    for line in text.split("\n"):
        stripped = line.lstrip("#").strip()
        if line.startswith("#") and stripped:
            line = f"*{stripped}*"
        lines.append(line)
    text = "\n".join(lines)
    text = _LIST_BULLET_RE.sub(r"\1•\2", text)
    return _BOLD_RE.sub(r"*\1*", text)


def _strip_markdown(text: str) -> str:
    """Used only when Telegram rejects the converted Markdown outright (some
    other stray character still broke entity matching) — better to show the
    report with no formatting than with literal ##/** clutter."""
    lines = []
    for line in text.split("\n"):
        stripped = line.lstrip("#").strip()
        lines.append(stripped if line.startswith("#") and stripped else line)
    text = "\n".join(lines)
    text = _LIST_BULLET_RE.sub(r"\1•\2", text)
    return _BOLD_RE.sub(r"\1", text)


def _post_chunk(url: str, chat_id: str, text: str, *, parse_mode: str | None) -> requests.Response:
    payload = {"chat_id": chat_id, "text": text, "disable_web_page_preview": True}
    if parse_mode:
        payload["parse_mode"] = parse_mode
    last_error: Exception | None = None
    for attempt in range(MAX_RETRIES):
        try:
            response = requests.post(url, json=payload, timeout=30)
            # A malformed-entity 400 won't be fixed by retrying — surface it
            # immediately so the caller can fall back to plain text instead.
            if response.status_code == 400:
                return response
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as exc:
            last_error = exc
            if attempt < MAX_RETRIES - 1:
                wait = RETRY_BACKOFF_SECONDS[attempt]
                print(f"Telegram send failed ({exc}), retrying in {wait}s (attempt {attempt + 1}/{MAX_RETRIES})")
                time.sleep(wait)
    raise last_error  # type: ignore[misc]


def send_telegram_message(bot_token: str, chat_id: str, text: str) -> None:
    if not bot_token or not chat_id:
        raise RuntimeError("TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be configured.")

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    chunks = split_message(text)
    for i, chunk in enumerate(chunks):
        if i > 0:
            time.sleep(1)  # avoid Telegram rate limiting between chunks
        response = _post_chunk(url, chat_id, _to_telegram_markdown(chunk), parse_mode="Markdown")
        if response.status_code == 400:
            # Formatting broke on some other stray */_ character (e.g. from a news
            # title) — strip markdown syntax entirely rather than resend it raw,
            # so the report never shows literal ##/** clutter.
            print(f"Telegram rejected Markdown formatting ({response.text}); resending with formatting stripped")
            response = _post_chunk(url, chat_id, _strip_markdown(chunk), parse_mode=None)
        response.raise_for_status()
