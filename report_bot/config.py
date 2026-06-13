import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()


def csv_env(name: str, default: str = "") -> list[str]:
    raw = os.getenv(name) or default
    return [item.strip() for item in raw.split(",") if item.strip()]


@dataclass(frozen=True)
class Settings:
    telegram_bot_token: str
    telegram_chat_id: str
    gemini_api_key: str
    gemini_model: str
    portfolio_symbols: list[str]
    watchlist_symbols: list[str]
    news_queries: list[str]
    system_prompt_path: Path


def load_settings() -> Settings:
    root = Path(__file__).resolve().parents[1]
    return Settings(
        telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
        telegram_chat_id=os.getenv("TELEGRAM_CHAT_ID", ""),
        gemini_api_key=os.getenv("GEMINI_API_KEY", ""),
        gemini_model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite"),
        portfolio_symbols=csv_env(
            "PORTFOLIO_SYMBOLS",
            "TSLA.US,VOO.US,0941.HK,0883.HK,2802.HK,3416.HK,MRVL.US,LITE.US,9988.HK,9888.HK,3896.HK",
        ),
        watchlist_symbols=csv_env(
            "WATCHLIST_SYMBOLS",
            "NVDA.US,AAPL.US,GOOGL.US,AMZN.US,0700.HK,0100.HK,2513.HK",
        ),
        news_queries=csv_env(
            "NEWS_QUERIES",
            # Broad market events - catches IPOs, geopolitical shocks, macro surprises
            "US stock market major news IPO earnings geopolitical today,"
            # Chinese/HK market themes
            "港股 美股 科技股 AI 板塊 要聞 市場,"
            # AI infrastructure sector - optical comms, storage, chips, data center
            "AI data center optical communications storage semiconductor chips NVDA MRVL LITE,"
            # Space, defence, energy, geopolitical
            "SpaceX space stocks aerospace defense oil energy Iran geopolitical market,"
            # China tech + HK stocks
            "中概股 港股 科技 AI 阿里巴巴 騰讯 Tesla Nvidia 影響",
        ),
        system_prompt_path=root / "system_prompt.txt",
    )
