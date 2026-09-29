from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


DEFAULT_CONFIG: dict[str, Any] = {
    "enabled": True, "style": "hybrid", "max_badges": 3, "maxTitleChars": 60,
    "states": {"completed_marker": "✓", "unknown_marker": "?", "waiting_on_user": True},
    "modifiers": {"goal": True, "artifacts": {"enabled": True, "extensions":
        ["pdf", "pptx", "docx", "xlsx", "zip", "png", "jpg", "svg", "html", "csv", "mp4"]},
        "recurring": False},
    "telemetry": {"context": {"enabled": True, "warn": .75, "critical": .90},
                  "long_running": {"enabled": False, "minutes": 15}},
    "motion": "off", "icons": {}, "reconcile_after_seconds": 120, "stale_after_minutes": 60,
    "projectRoots": {}, "projects": {"cwd_basename": True},
}

PROFILES = {
    "minimal": {"modifiers": {"goal": False, "artifacts": {"enabled": False}, "recurring": False},
                "telemetry": {"context": {"enabled": False}, "long_running": {"enabled": False}}},
    "default": {},
    "full": {"modifiers": {"goal": True, "artifacts": {"enabled": True}, "recurring": True},
             "telemetry": {"context": {"enabled": True}, "long_running": {"enabled": True}}},
    "lab": {"modifiers": {"goal": True, "artifacts": {"enabled": True}, "recurring": True},
            "telemetry": {"context": {"enabled": True}, "long_running": {"enabled": True}},
            "motion": "events"},
}


def merge(base: dict, overlay: dict) -> dict:
    result = dict(base)
    for key, value in overlay.items():
        result[key] = merge(result.get(key, {}), value) if isinstance(value, dict) else value
    return result


def load_config(path: Path, profile_dir: Path | None = None) -> dict:
    user = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    profile = user.get("profile")
    selected = PROFILES.get(profile or "default", {})
    if profile and profile_dir and (profile_dir / f"{profile}.json").exists():
        selected = json.loads((profile_dir / f"{profile}.json").read_text(encoding="utf-8"))
    return merge(merge(DEFAULT_CONFIG, selected), user)


def config_hash(config: dict) -> str:
    return hashlib.sha256(json.dumps(config, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
