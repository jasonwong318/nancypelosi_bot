"""One-off probe: check which Longbridge SDK endpoints this account can access.

Run via GitHub Actions (needs LONGBRIDGE_* secrets). Prints status + a short
sample of each response so we can decide how to redesign news/fundamentals.
"""
from __future__ import annotations

import json
import decimal

from longbridge.openapi import Config, ContentContext, FundamentalContext, MarketContext, Market


class _Encoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, decimal.Decimal):
            return float(o)
        return str(o)


SAMPLE_SYMBOLS = ["TSLA.US", "0941.HK", "9988.HK", "MRVL.US"]


def show(label, fn):
    try:
        result = fn()
        print(f"OK   {label}")
        print(json.dumps(result, cls=_Encoder, default=lambda o: str(o), ensure_ascii=False)[:600])
    except Exception as e:
        print(f"FAIL {label}: {type(e).__name__}: {e}")
    print("-" * 60)


def main():
    config = Config.from_apikey_env()
    content_ctx = ContentContext(config)
    market_ctx = MarketContext(config)
    fundamental_ctx = FundamentalContext(config)

    for symbol in SAMPLE_SYMBOLS:
        show(f"ContentContext.news({symbol})", lambda s=symbol: content_ctx.news(s))
        show(f"FundamentalContext.valuation({symbol})", lambda s=symbol: fundamental_ctx.valuation(s))
        show(f"FundamentalContext.consensus({symbol})", lambda s=symbol: fundamental_ctx.consensus(s))
        show(f"FundamentalContext.forecast_eps({symbol})", lambda s=symbol: fundamental_ctx.forecast_eps(s))
        show(f"FundamentalContext.institution_rating({symbol})", lambda s=symbol: fundamental_ctx.institution_rating(s))
        show(f"FundamentalContext.industry_valuation({symbol})", lambda s=symbol: fundamental_ctx.industry_valuation(s))
        show(f"FundamentalContext.company({symbol})", lambda s=symbol: fundamental_ctx.company(s))

    show("MarketContext.anomaly(HK)", lambda: market_ctx.anomaly(Market.HK))
    show("MarketContext.anomaly(US)", lambda: market_ctx.anomaly(Market.US))
    show("MarketContext.top_movers([HK, US])", lambda: market_ctx.top_movers([Market.HK, Market.US]))
    show("MarketContext.market_status()", lambda: market_ctx.market_status())


if __name__ == "__main__":
    main()
