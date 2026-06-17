from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from report_bot.account_data import account_payload
from report_bot.config import load_settings
from report_bot.fundamentals import fundamentals_payload
from report_bot.llm import build_user_payload, generate_report
from report_bot.longbridge_data import fetch_quotes
from report_bot.macro_data import macro_payload
from report_bot.movers import compute_movers
from report_bot.news import news_payload
from report_bot.risk import risk_payload
from report_bot.sector_data import sector_payload
from report_bot.symbols import selected_metadata
from report_bot.telegram import send_telegram_message


def main() -> None:
    settings = load_settings()
    symbols = sorted(set(settings.portfolio_symbols + settings.watchlist_symbols))
    symbol_metadata = selected_metadata(symbols)

    quotes = fetch_quotes(symbols)
    movers = compute_movers(quotes)
    focus_symbols = movers.get("focus_symbols", [])

    macro = macro_payload()
    news = news_payload(settings.news_queries, symbols=symbols, focus_symbols=focus_symbols)
    account = account_payload(settings.portfolio_symbols)
    risk = risk_payload(settings.portfolio_symbols, settings.watchlist_symbols, symbol_metadata)
    fundamentals = fundamentals_payload(settings.portfolio_symbols)
    sector = sector_payload()

    print(f"Quote status: {quotes.get('status')}")
    print(f"Quote count: {len(quotes.get('quotes', []))}")
    print(f"Significant movers: {len(movers.get('significant_movers', []))}")
    print(f"Focus symbols: {focus_symbols}")
    print(f"Macro item count: {len(macro.get('items', []))}")
    print(f"News item count: {len(news.get('items', []))}")
    print(f"Account status: {account.get('status')}")
    print(f"Risk status: {risk.get('status')}")
    print(f"Fundamentals status: {fundamentals.get('status')}")
    print(f"Sector status: {sector.get('status')}, anomalies: {len(sector.get('anomalies', []))}, top movers: {len(sector.get('top_movers', []))}")

    system_prompt = settings.system_prompt_path.read_text(encoding="utf-8")
    user_payload = build_user_payload(
        quotes=quotes,
        movers=movers,
        news=news,
        macro=macro,
        account=account,
        risk=risk,
        fundamentals=fundamentals,
        sector=sector,
        portfolio=settings.portfolio_symbols,
        watchlist=settings.watchlist_symbols,
        symbol_metadata=symbol_metadata,
    )
    report = generate_report(
        api_key=settings.glm_api_key,
        model=settings.glm_model,
        system_prompt=system_prompt,
        user_payload=user_payload,
    )

    hkt_now = datetime.now(ZoneInfo("Asia/Hong_Kong")).strftime("%Y-%m-%d %H:%M HKT")
    message = f"市場報告｜{hkt_now}\n\n{report}\n\n免責聲明：以上內容只作資訊整理，不構成投資建議。"
    send_telegram_message(settings.telegram_bot_token, settings.telegram_chat_id, message)


if __name__ == "__main__":
    main()
