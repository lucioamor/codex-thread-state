from __future__ import annotations

from dataclasses import replace

from .events import is_user_input_tool
from .model import Evidence, Event, Modifier, State, Telemetry, ThreadView

GOAL_STATES = {"active": State.PENDING, "complete": State.COMPLETED, "paused": State.PAUSED,
               "blocked": State.BLOCKED, "budget_limited": State.BUDGET_LIMITED,
               "usage_limited": State.USAGE_LIMITED}


def _derived(evidence: Evidence, fallback: State) -> State:
    if evidence.terminal_state in (State.USAGE_LIMITED, State.FAILED, State.COMPLETED):
        if evidence.terminal_state == State.COMPLETED and evidence.goal_status in GOAL_STATES:
            return GOAL_STATES[evidence.goal_status]
        return evidence.terminal_state
    if evidence.goal_status in GOAL_STATES:
        return GOAL_STATES[evidence.goal_status]
    return State.UNKNOWN if evidence.stale else fallback


def reduce(previous: ThreadView, event: Event, evidence: Evidence = Evidence()) -> ThreadView:
    modifiers = set(previous.modifiers)
    for enabled, modifier in ((evidence.has_goal, Modifier.GOAL),
                              (evidence.has_artifacts, Modifier.ARTIFACTS),
                              (evidence.recurring, Modifier.RECURRING)):
        if enabled: modifiers.add(modifier)
    telemetry = Telemetry(evidence.context_pressure if evidence.context_pressure is not None
                          else previous.telemetry.context_pressure, previous.telemetry.long_running)
    if event.name == "UserPromptSubmit":
        return ThreadView(State.RUNNING, frozenset(modifiers), telemetry, False, event.at)
    if event.name == "PermissionRequest" or is_user_input_tool(event):
        return ThreadView(State.WAITING_ON_USER, frozenset(modifiers), telemetry, False,
                          previous.turn_started_at)
    if event.name == "PostToolUse":
        return ThreadView(State.RUNNING, frozenset(modifiers), telemetry, False,
                          previous.turn_started_at)
    if event.name == "Interrupt":
        return ThreadView(State.INTERRUPTED, frozenset(modifiers), telemetry, False,
                          previous.turn_started_at)
    if event.name == "Stop":
        if evidence.terminal_state in (State.USAGE_LIMITED, State.FAILED, State.COMPLETED):
            state = _derived(evidence, State.RUNNING)
            ambiguous = False
        else:
            state = State.RUNNING
            ambiguous = True
        return ThreadView(state, frozenset(modifiers), telemetry, ambiguous,
                          previous.turn_started_at)
    state = _derived(evidence, previous.state)
    return replace(previous, state=state, modifiers=frozenset(modifiers), telemetry=telemetry,
                   needs_reconciliation=state in (State.RUNNING, State.WAITING_ON_USER))
