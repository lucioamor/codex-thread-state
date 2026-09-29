from __future__ import annotations

import re

from ..model import Modifier, State, ThreadView
from .themes import THEMES

DROP_ORDER = ["long_running", "recurring", "artifacts", "context", "goal"]


def icons(config: dict) -> dict[str, str]:
    result = dict(THEMES[config.get("style", "hybrid")])
    result.update(config.get("icons", {}))
    states = config.get("states", {})
    if states.get("completed_marker") is not None: result["completed"] = states["completed_marker"]
    if states.get("unknown_marker") is not None: result["unknown"] = states["unknown_marker"]
    return result


def recognized_markers(config: dict | None = None) -> set[str]:
    values = set()
    for theme in THEMES.values(): values.update(theme.values())
    if config: values.update(icons(config).values())
    values.update(("◕", "●", "⏱", "🏁", "🔵", "▷"))
    return {x for x in values if x}


def strip_prefix(title: str, config: dict | None = None) -> str:
    markers = sorted(recognized_markers(config), key=len, reverse=True)
    pattern = r"^(?:(?:" + "|".join(re.escape(x) for x in markers) + r")\s+)+"
    return re.sub(pattern, "", title).strip()


def _badges(view: ThreadView, config: dict) -> list[tuple[str, str]]:
    theme = icons(config)
    result: list[tuple[str, str]] = [("state", theme[view.state.value])]
    modifier_config = config.get("modifiers", {})
    for modifier in (Modifier.GOAL, Modifier.ARTIFACTS, Modifier.RECURRING):
        option = modifier_config.get(modifier.value, False)
        enabled = option.get("enabled", False) if isinstance(option, dict) else bool(option)
        if modifier in view.modifiers and enabled:
            result.append((modifier.value, theme[modifier.value]))
    context = config.get("telemetry", {}).get("context", {})
    pressure = view.telemetry.context_pressure
    if context.get("enabled") and pressure is not None:
        if pressure >= context.get("critical", .90): result.append(("context", "●"))
        elif pressure >= context.get("warn", .75): result.append(("context", "◕"))
    if view.telemetry.long_running and config.get("telemetry", {}).get("long_running", {}).get("enabled"):
        result.append(("long_running", "⏱"))
    maximum = max(1, int(config.get("max_badges", 3)))
    while len(result) > maximum:
        for name in DROP_ORDER:
            found = next((i for i, item in enumerate(result) if item[0] == name), None)
            if found is not None:
                result.pop(found); break
        else: break
    return result


def prefix_for(view: ThreadView, config: dict) -> str:
    return " ".join(value for _, value in _badges(view, config))


def compose(title: str, view: ThreadView | State | str, config: dict,
            base_title: str | None = None, project_tag: str | None = None) -> str:
    if isinstance(view, str): view = ThreadView(State(view))
    if isinstance(view, State): view = ThreadView(view)
    base = base_title if base_title is not None else strip_prefix(title, config)
    if not base.strip() or any(ord(c) < 32 or ord(c) == 127 for c in base):
        raise ValueError("empty title or control characters")
    tag = f"[{project_tag}] " if project_tag else ""
    desired = f"{prefix_for(view, config)} {tag}{base}".strip()
    if len(desired) > int(config.get("maxTitleChars", 60)):
        raise ValueError("title exceeds configured limit; no truncation performed")
    return desired
