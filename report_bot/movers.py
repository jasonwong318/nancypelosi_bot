from __future__ import annotations

from typing import Any


def compute_movers(quotes: dict[str, Any], threshold_pct: float = 2.0) -> dict[str, Any]:
    """Pre-compute explicit up/down lists from quote data so the LLM never guesses direction."""
    items = quotes.get("quotes", [])
    parsed: list[dict[str, Any]] = []

    for q in items:
        cp = q.get("change_percent")
        if cp is None:
            continue
        try:
            pct = float(str(cp).rstrip("%"))
        except (ValueError, TypeError):
            continue
        parsed.append(
            {
                "symbol": q.get("symbol", ""),
                "name": q.get("name", ""),
                "change_percent": pct,
                "display": f"{pct:+.2f}%",
                "last_done": q.get("last_done"),
            }
        )

    gainers = sorted([p for p in parsed if p["change_percent"] > 0], key=lambda x: -x["change_percent"])
    losers = sorted([p for p in parsed if p["change_percent"] < 0], key=lambda x: x["change_percent"])
    flat = [p for p in parsed if p["change_percent"] == 0]
    by_magnitude = sorted(parsed, key=lambda x: -abs(x["change_percent"]))
    significant = [p for p in by_magnitude if abs(p["change_percent"]) >= threshold_pct]

    def _fmt(items: list[dict]) -> str:
        return ", ".join(f"{m['symbol']} {m['display']}" for m in items) or "無"

    return {
        "threshold_pct": threshold_pct,
        "gainers": gainers,
        "losers": losers,
        "flat": flat,
        "significant_movers": significant,
        # Always pick the 3 biggest movers regardless of threshold, so the
        # focus section is never empty even on a quiet day.
        "focus_symbols": [m["symbol"] for m in by_magnitude[:3]],
        "is_quiet_day": len(significant) == 0,
        "gainers_summary": _fmt(gainers),
        "losers_summary": _fmt(losers),
        "significant_summary": _fmt(significant),
        "instruction": (
            "DIRECTION RULE: All up/down directional statements MUST be copied verbatim from "
            "gainers_summary or losers_summary. Never infer direction from price numbers."
        ),
    }
