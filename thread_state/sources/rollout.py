from __future__ import annotations

import json
from pathlib import Path

BASELINE = 12_000


def pressure_from_counts(total_tokens: int, context_window: int) -> float:
    usable = max(1, context_window - BASELINE)
    remaining = max(0, context_window - total_tokens - BASELINE)
    return 1 - min(1, remaining / usable)


def context_pressure(path: Path) -> float | None:
    if not path.exists(): return None
    last = None; window = None
    for line in path.read_text(encoding="utf-8").splitlines():
        try: row = json.loads(line)
        except ValueError: continue
        payload = row.get("payload", row)
        if row.get("type") == "token_count" or payload.get("type") == "token_count":
            info = payload.get("info", payload)
            last = info.get("total_token_usage", info.get("total_tokens"))
            if isinstance(last, dict): last = last.get("total_tokens")
            window = info.get("model_context_window") or payload.get("model_context_window")
    return pressure_from_counts(int(last), int(window)) if last is not None and window else None
