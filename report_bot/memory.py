from __future__ import annotations

import json
from pathlib import Path
from typing import Any

MEMORY_PATH = Path(__file__).resolve().parents[1] / "report_memory.json"
MAX_ENTRIES = 12  # ~4 days at 3 runs/day


def load_memory() -> list[dict[str, Any]]:
    try:
        data = json.loads(MEMORY_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def build_comparison(
    current_changes: dict[str, float | None],
    memory: list[dict[str, Any]],
) -> dict[str, Any]:
    """Compare today's per-symbol moves against the previous run and compute
    consecutive same-direction streaks across past runs."""
    if not memory:
        return {"status": "no_history", "note": "首次運行，無上次報告可比較。"}

    previous = memory[-1]
    prev_changes: dict[str, Any] = previous.get("changes", {})

    per_symbol: dict[str, Any] = {}
    for symbol, current in current_changes.items():
        entry: dict[str, Any] = {}
        prev = prev_changes.get(symbol)
        if prev is not None:
            entry["previous_change_pct"] = prev
        if current is not None:
            streak = 1
            direction = current > 0
            if current != 0:
                for past in reversed(memory):
                    past_value = past.get("changes", {}).get(symbol)
                    if past_value is None or past_value == 0 or (past_value > 0) != direction:
                        break
                    streak += 1
                if streak >= 3:
                    entry["streak"] = f"連續{streak}次報告{'上升' if direction else '下跌'}"
        if entry:
            per_symbol[symbol] = entry

    return {
        "status": "ok",
        "previous_run": {
            "generated_at_hkt": previous.get("generated_at_hkt"),
            "session": previous.get("session"),
            "significant_summary": previous.get("significant_summary"),
        },
        "per_symbol": per_symbol,
    }


def append_memory(
    memory: list[dict[str, Any]],
    generated_at_hkt: str,
    session: str,
    current_changes: dict[str, float | None],
    significant_summary: str,
) -> None:
    memory.append(
        {
            "generated_at_hkt": generated_at_hkt,
            "session": session,
            "changes": {k: v for k, v in current_changes.items() if v is not None},
            "significant_summary": significant_summary,
        }
    )
    MEMORY_PATH.write_text(
        json.dumps(memory[-MAX_ENTRIES:], ensure_ascii=False, indent=1),
        encoding="utf-8",
    )
