from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from report_bot.config import load_settings
from report_bot.llm import build_user_payload, generate_report
from report_bot.longbridge_data import fetch_quotes
from report_bot.news import news_payload
from report_bot.telegram import send_telegram_message


def main() -> None:
    settings = load_settings()
    symbols = sorted(set(settings.portfolio_symbols + settings.watchlist_symbols))
    quotes = fetch_quotes(symbols)
    news = news_payload(settings.news_queries)
    print(f"Quote status: {quotes.get('status')}")
    print(f"Quote count: {len(quotes.get('quotes', []))}")
    print(f"News query count: {len(settings.news_queries)}")
    print(f"News item count: {len(news.get('items', []))}")
    system_prompt = settings.system_prompt_path.read_text(encoding="utf-8")
    user_payload = build_user_payload(
        quotes=quotes,
        news=news,
        portfolio=settings.portfolio_symbols,
        watchlist=settings.watchlist_symbols,
    )
    report = generate_report(
        api_key=settings.gemini_api_key,
        model=settings.gemini_model,
        system_prompt=system_prompt,
        user_payload=user_payload,
    )

    hkt_now = datetime.now(ZoneInfo("Asia/Hong_Kong")).strftime("%Y-%m-%d %H:%M HKT")
    message = f"市場報告｜{hkt_now}\n\n{report}\n\n免責聲明：以上內容只作資訊整理，不構成投資建議。"
    send_telegram_message(settings.telegram_bot_token, settings.telegram_chat_id, message)


if __name__ == "__main__":
    main()
