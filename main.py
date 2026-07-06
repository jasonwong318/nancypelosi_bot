from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from report_bot.account_data import account_payload
from report_bot.config import load_settings
from report_bot.fundamentals import fundamentals_payload
from report_bot.llm import build_user_payload, generate_report
from report_bot.longbridge_data import fetch_quotes
from report_bot.macro_data import macro_payload
from report_bot.market_calendar import calendar_payload, closure_notice
from report_bot.memory import append_memory, build_comparison, load_memory
from report_bot.movers import compute_movers
from report_bot.news import news_payload
from report_bot.risk import risk_payload
from report_bot.sector_data import sector_payload
from report_bot.symbols import sector_map, selected_metadata
from report_bot.telegram import send_telegram_message


def report_session(now_hkt: datetime) -> dict[str, str]:
    """The 3 scheduled runs serve different readers; tell the LLM which one this is."""
    hour = now_hkt.hour
    if hour < 11:
        return {
            "session": "morning",
            "focus": "隔夜美股已收市：總結美股持倉隔夜表現，展望今日港股（開市在即），指出今日港股需要關注的事件。",
        }
    if hour < 17:
        return {
            "session": "midday",
            "focus": "港股上午時段已完結：總結港股持倉上午走勢，指出下午及今晚美股開市前需要關注的變數。",
        }
    return {
        "session": "evening",
        "focus": "港股已收市、美股即將開市：總結港股持倉全日表現，展望今晚美股（含持倉美股的盤前訊號）。",
    }


def main() -> None:
    settings = load_settings()
    try:
        _run(settings)
    except Exception as exc:
        # Make failures visible in Telegram instead of only in GitHub Actions logs —
        # otherwise a broken run looks like the cron simply didn't fire.
        now_hkt = datetime.now(ZoneInfo("Asia/Hong_Kong")).strftime("%Y-%m-%d %H:%M HKT")
        failure_message = (
            f"⚠️ 市場報告生成失敗｜{now_hkt}\n\n"
            f"錯誤: {type(exc).__name__}: {exc}\n\n"
            "請檢查 GitHub Actions logs。"
        )
        try:
            send_telegram_message(settings.telegram_bot_token, settings.telegram_chat_id, failure_message)
        except Exception:
            pass  # Telegram itself may be down/misconfigured; don't mask the original error
        raise


def _run(settings) -> None:
    symbols = sorted(set(settings.portfolio_symbols + settings.watchlist_symbols))
    symbol_metadata = selected_metadata(symbols)

    now_hkt = datetime.now(ZoneInfo("Asia/Hong_Kong"))
    session = report_session(now_hkt)
    calendar = calendar_payload(now_hkt.date())
    notice = closure_notice(calendar)
    if notice:
        session = dict(session)
        session["market_closure"] = notice

    quotes = fetch_quotes(symbols)
    movers = compute_movers(quotes)
    focus_symbols = movers.get("focus_symbols", [])

    macro = macro_payload()
    news = news_payload(settings.news_queries, symbols=symbols, focus_symbols=focus_symbols)
    account = account_payload(settings.portfolio_symbols)
    risk = risk_payload(settings.portfolio_symbols, settings.watchlist_symbols, symbol_metadata)
    fundamentals = fundamentals_payload(settings.portfolio_symbols)
    sector = sector_payload()

    current_changes: dict[str, float | None] = {}
    for q in quotes.get("quotes", []):
        try:
            current_changes[q.get("symbol", "")] = float(str(q.get("change_percent")).rstrip("%"))
        except (TypeError, ValueError):
            current_changes[q.get("symbol", "")] = None
    memory = load_memory()
    comparison = build_comparison(current_changes, memory)

    print(f"Session: {session['session']}")
    print(f"Calendar: {calendar}")
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
    print(f"Comparison status: {comparison.get('status')}")

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
        comparison=comparison,
        session=session,
        sectors=sector_map(settings.portfolio_symbols, settings.watchlist_symbols),
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

    hkt_str = now_hkt.strftime("%Y-%m-%d %H:%M HKT")
    header = f"市場報告｜{hkt_str}"
    if notice:
        header += f"\n{notice}"
    message = f"{header}\n\n{report}\n\n免責聲明：以上內容只作資訊整理，不構成投資建議。"
    send_telegram_message(settings.telegram_bot_token, settings.telegram_chat_id, message)

    append_memory(
        memory,
        generated_at_hkt=hkt_str,
        session=session["session"],
        current_changes=current_changes,
        significant_summary=str(movers.get("significant_summary", "")),
    )


if __name__ == "__main__":
    main()
