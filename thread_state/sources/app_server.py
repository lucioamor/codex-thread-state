from __future__ import annotations

import json
import time

from ..model import Evidence, State

USAGE_CODES = ("usage_limit", "insufficient_quota", "credit balance exhausted", "hit your usage limit")


def terminal_state(turn: dict | None, interrupt_turn_id: str | None = None) -> State | None:
    status = (turn or {}).get("status")
    if status == "failed":
        error = json.dumps((turn or {}).get("error"), ensure_ascii=False).lower()
        return State.USAGE_LIMITED if any(x in error for x in USAGE_CODES) else State.FAILED
    if status == "completed": return State.COMPLETED
    if status in ("interrupted", "cancelled") and interrupt_turn_id == (turn or {}).get("id"):
        return State.INTERRUPTED
    return None


def snapshot(server, thread_id: str):
    thread = server.call("thread/read", {"threadId": thread_id, "includeTurns": False})["thread"]
    turns = server.call("thread/turns/list", {"threadId": thread_id, "limit": 1,
        "sortDirection": "desc", "itemsView": "full"}).get("data", [])
    goal = server.call("thread/goal/get", {"threadId": thread_id}).get("goal")
    return thread, turns[0] if turns else None, goal


def collect(server, thread_id: str, *, retries: int = 1, delay: float = .2,
            interrupt_turn_id: str | None = None):
    result = None
    for attempt in range(retries):
        result = snapshot(server, thread_id)
        if terminal_state(result[1], interrupt_turn_id) is not None: break
        if attempt + 1 < retries: time.sleep(delay)
    thread, turn, goal = result
    return thread, turn, goal, Evidence(terminal_state(turn, interrupt_turn_id),
        (goal or {}).get("status"), bool(goal))
