SYMBOL_METADATA = {
    "TSLA.US": {"name": "Tesla, Inc.", "market": "US", "type": "stock"},
    "VOO.US": {"name": "Vanguard S&P 500 ETF", "market": "US", "type": "ETF"},
    "0941.HK": {"name": "China Mobile", "market": "HK", "type": "stock"},
    "0883.HK": {"name": "CNOOC", "market": "HK", "type": "stock"},
    "2802.HK": {"name": "CSOP HSCEI Covered Call ETF", "market": "HK", "type": "ETF"},
    "3416.HK": {"name": "Global X HSCEI Covered Call Active ETF", "market": "HK", "type": "ETF"},
    "MRVL.US": {"name": "Marvell Technology, Inc.", "market": "US", "type": "stock"},
    "LITE.US": {"name": "Lumentum Holdings Inc.", "market": "US", "type": "stock"},
    "9988.HK": {"name": "Alibaba Group Holding", "market": "HK", "type": "stock"},
    "9888.HK": {"name": "Baidu, Inc.", "market": "HK", "type": "stock"},
    "3896.HK": {"name": "Kingsoft Cloud Holdings", "market": "HK", "type": "stock"},
    "NVDA.US": {"name": "NVIDIA Corporation", "market": "US", "type": "stock"},
    "AAPL.US": {"name": "Apple Inc.", "market": "US", "type": "stock"},
    "GOOGL.US": {"name": "Alphabet Inc. Class A", "market": "US", "type": "stock"},
    "AMZN.US": {"name": "Amazon.com, Inc.", "market": "US", "type": "stock"},
    "0700.HK": {"name": "Tencent Holdings", "market": "HK", "type": "stock"},
    "0100.HK": {"name": "MiniMax Group Inc. / MINIMAX-W", "market": "HK", "type": "stock"},
    "2513.HK": {"name": "Knowledge Atlas Technology / Zhipu", "market": "HK", "type": "stock"},
}


def metadata_for(symbol: str) -> dict[str, str]:
    return SYMBOL_METADATA.get(symbol) or SYMBOL_METADATA.get(_pad_hk_symbol(symbol)) or {
        "name": "Unknown - do not infer company name",
        "market": "Unknown",
        "type": "Unknown",
    }


def selected_metadata(symbols: list[str]) -> dict[str, dict[str, str]]:
    return {symbol: metadata_for(symbol) for symbol in symbols}


def _pad_hk_symbol(symbol: str) -> str:
    if symbol.endswith(".HK"):
        code = symbol.removesuffix(".HK")
        if code.isdigit():
            return f"{code.zfill(4)}.HK"
    return symbol
