SYMBOL_METADATA = {
    "TSLA.US": {"name": "Tesla, Inc.", "market": "US", "type": "stock", "sectors": ["EV/自動駕駛", "AI"]},
    "VOO.US": {"name": "Vanguard S&P 500 ETF", "market": "US", "type": "ETF", "sectors": ["美股大盤指數"]},
    "0941.HK": {"name": "China Mobile", "market": "HK", "type": "stock", "sectors": ["中國電訊", "AI基礎設施", "高股息"]},
    "0883.HK": {"name": "CNOOC", "market": "HK", "type": "stock", "sectors": ["能源/石油", "高股息", "地緣政治敏感"]},
    "2802.HK": {"name": "CSOP HSCEI Covered Call ETF", "market": "HK", "type": "ETF", "sectors": ["HSCEI備兌認購/收息策略"]},
    "3416.HK": {"name": "Global X HSCEI Covered Call Active ETF", "market": "HK", "type": "ETF", "sectors": ["HSCEI備兌認購/收息策略"]},
    "MRVL.US": {"name": "Marvell Technology, Inc.", "market": "US", "type": "stock", "sectors": ["AI基礎設施", "數據中心晶片", "光通訊"]},
    "LITE.US": {"name": "Lumentum Holdings Inc.", "market": "US", "type": "stock", "sectors": ["AI基礎設施", "光通訊/激光"]},
    "9988.HK": {"name": "Alibaba Group Holding", "market": "HK", "type": "stock", "sectors": ["中國科技", "電商", "雲端/AI"]},
    "9888.HK": {"name": "Baidu, Inc.", "market": "HK", "type": "stock", "sectors": ["中國科技", "AI/自動駕駛"]},
    "3896.HK": {"name": "Kingsoft Cloud Holdings", "market": "HK", "type": "stock", "sectors": ["雲端/AI算力", "中國科技"]},
    "NVDA.US": {"name": "NVIDIA Corporation", "market": "US", "type": "stock", "sectors": ["AI基礎設施", "晶片"]},
    "AAPL.US": {"name": "Apple Inc.", "market": "US", "type": "stock", "sectors": ["消費電子", "美國科技"]},
    "GOOGL.US": {"name": "Alphabet Inc. Class A", "market": "US", "type": "stock", "sectors": ["AI", "廣告/搜尋"]},
    "AMZN.US": {"name": "Amazon.com, Inc.", "market": "US", "type": "stock", "sectors": ["電商", "雲端/AI"]},
    "0700.HK": {"name": "Tencent Holdings", "market": "HK", "type": "stock", "sectors": ["中國科技", "遊戲/社交", "AI"]},
    "0100.HK": {"name": "MiniMax Group Inc. / MINIMAX-W", "market": "HK", "type": "stock", "sectors": ["AI", "中國科技"]},
    "2513.HK": {"name": "Knowledge Atlas Technology / Zhipu", "market": "HK", "type": "stock", "sectors": ["AI", "中國科技"]},
}


def metadata_for(symbol: str) -> dict[str, object]:
    return SYMBOL_METADATA.get(symbol) or SYMBOL_METADATA.get(_pad_hk_symbol(symbol)) or {
        "name": "Unknown - do not infer company name",
        "market": "Unknown",
        "type": "Unknown",
        "sectors": [],
    }


def selected_metadata(symbols: list[str]) -> dict[str, dict[str, object]]:
    return {symbol: metadata_for(symbol) for symbol in symbols}


def sector_map(portfolio: list[str], watchlist: list[str]) -> dict[str, dict[str, list[str]]]:
    """Group symbols by sector so the LLM knows which themes matter to this portfolio
    without hardcoding tickers in the system prompt."""
    result: dict[str, dict[str, list[str]]] = {}
    for group, symbols in (("portfolio", portfolio), ("watchlist", watchlist)):
        for symbol in symbols:
            for sector in metadata_for(symbol).get("sectors", []) or []:
                result.setdefault(sector, {"portfolio": [], "watchlist": []})[group].append(symbol)
    return result


def _pad_hk_symbol(symbol: str) -> str:
    if symbol.endswith(".HK"):
        code = symbol.removesuffix(".HK")
        if code.isdigit():
            return f"{code.zfill(4)}.HK"
    return symbol
