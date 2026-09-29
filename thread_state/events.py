from __future__ import annotations

from datetime import datetime, timezone
import uuid

from .model import Event

SUPPORTED_EVENTS = {"SessionStart", "UserPromptSubmit", "PermissionRequest", "PreToolUse",
                    "PostToolUse", "Stop", "Interrupt"}


def normalize(payload: dict) -> Event:
    name = payload.get("hook_event_name") or payload.get("event")
    if name not in SUPPORTED_EVENTS:
        raise ValueError(f"unsupported hook event: {name!r}")
    thread_id = str(uuid.UUID(payload.get("session_id") or payload.get("thread_id")))
    return Event(name, thread_id, payload.get("turn_id"),
                 payload.get("timestamp") or datetime.now(timezone.utc).isoformat(), payload)


def is_user_input_tool(event: Event) -> bool:
    if event.name != "PreToolUse":
        return False
    return (event.payload.get("tool_name") or event.payload.get("tool", {}).get("name")) == "request_user_input"
