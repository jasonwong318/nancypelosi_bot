from __future__ import annotations

import json
import os
from typing import Any


def account_payload(portfolio_symbols: list[str]) -> dict[str, Any]:
    raw = os.getenv("ACCOUNT_POSITIONS_JSON", "").strip()
    if raw:
        try:
            positions = json.loads(raw)
            return {
                "status": "manual_positions_loaded",
                "source": "ACCOUNT_POSITIONS_JSON env var",
                "positions": positions,
            }
        except json.JSONDecodeError as exc:
            return {
                "status": "error",
                "message": f"ACCOUNT_POSITIONS_JSON parse error: {exc}",
                "positions": [],
            }
    return {
        "status": "placeholder",
        "message": (
            "Account data not connected. "
            "Set ACCOUNT_POSITIONS_JSON to provide manual positions, "
            "or wait for IBKR integration in Phase 2."
        ),
        "positions": [],
    }
