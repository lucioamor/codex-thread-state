from __future__ import annotations

from pathlib import Path


def detect_artifacts(payload: dict, extensions: list[str]) -> bool:
    allowed = {x.lower().lstrip(".") for x in extensions}
    items = payload.get("items", [])
    if any((x.get("type") or x.get("kind")) == "ImageGeneration" for x in items if isinstance(x, dict)):
        return True
    paths = payload.get("created_files", []) + payload.get("files_created", [])
    return any(Path(str(path)).suffix.lower().lstrip(".") in allowed for path in paths)
