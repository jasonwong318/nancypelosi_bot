from __future__ import annotations

from typing import Any

from report_bot.longbridge_utils import attr, has_longbridge_credentials, to_number


def sector_payload() -> dict[str, Any]:
    if not has_longbridge_credentials():
        return {"status": "longbridge_missing", "anomalies": [], "top_movers": []}

    try:
        from longbridge.openapi import Config, MarketContext
    except Exception as exc:
        return {"status": "sdk_unavailable", "message": str(exc), "anomalies": [], "top_movers": []}

    try:
        config = Config.from_apikey_env()
        ctx = MarketContext(config)
    except Exception as exc:
        return {"status": "error", "message": str(exc), "anomalies": [], "top_movers": []}

    anomalies: list[dict[str, Any]] = []
    for market in ("HK", "US"):
        try:
            resp = ctx.anomaly(market)
            for change in attr(resp, "changes") or []:
                anomalies.append(
                    {
                        "market": market,
                        "symbol": attr(change, "symbol"),
                        "name": attr(change, "name"),
                        "alert_name": attr(change, "alert_name"),
                        "alert_time": str(attr(change, "alert_time") or ""),
                    }
                )
        except Exception:
            continue

    top_movers: list[dict[str, Any]] = []
    try:
        resp = ctx.top_movers(["HK", "US"])
        for event in (attr(resp, "events") or [])[:15]:
            stock = attr(event, "stock")
            top_movers.append(
                {
                    "symbol": attr(stock, "symbol"),
                    "name": attr(stock, "name"),
                    "change": to_number(attr(stock, "change")),
                    "alert_type": attr(event, "alert_type"),
                    "alert_reason": attr(event, "alert_reason"),
                }
            )
    except Exception:
        pass

    return {
        "status": "ok",
        "source": "Longbridge OpenAPI MarketContext",
        "anomalies": anomalies,
        "top_movers": top_movers,
    }
