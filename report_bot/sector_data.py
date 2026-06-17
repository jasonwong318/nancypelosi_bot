from __future__ import annotations

import os
from typing import Any


def sector_payload() -> dict[str, Any]:
    if not _has_longbridge_credentials():
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
            for change in _attr(resp, "changes") or []:
                anomalies.append(
                    {
                        "market": market,
                        "symbol": _attr(change, "symbol"),
                        "name": _attr(change, "name"),
                        "alert_name": _attr(change, "alert_name"),
                        "alert_time": str(_attr(change, "alert_time") or ""),
                    }
                )
        except Exception:
            continue

    top_movers: list[dict[str, Any]] = []
    try:
        resp = ctx.top_movers(["HK", "US"])
        for event in (_attr(resp, "events") or [])[:15]:
            stock = _attr(event, "stock")
            top_movers.append(
                {
                    "symbol": _attr(stock, "symbol"),
                    "name": _attr(stock, "name"),
                    "change": _num(_attr(stock, "change")),
                    "alert_type": _attr(event, "alert_type"),
                    "alert_reason": _attr(event, "alert_reason"),
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


def _has_longbridge_credentials() -> bool:
    return all(
        os.getenv(name)
        for name in ("LONGBRIDGE_APP_KEY", "LONGBRIDGE_APP_SECRET", "LONGBRIDGE_ACCESS_TOKEN")
    )


def _attr(obj: Any, name: str) -> Any:
    return obj.get(name) if isinstance(obj, dict) else getattr(obj, name, None)


def _num(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
