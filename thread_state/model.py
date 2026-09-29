from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any


class State(StrEnum):
    USAGE_LIMITED = "usage_limited"
    FAILED = "failed"
    BLOCKED = "blocked"
    WAITING_ON_USER = "waiting_on_user"
    RUNNING = "running"
    INTERRUPTED = "interrupted"
    PAUSED = "paused"
    BUDGET_LIMITED = "budget_limited"
    PENDING = "pending"
    COMPLETED = "completed"
    UNKNOWN = "unknown"


class Modifier(StrEnum):
    GOAL = "goal"
    ARTIFACTS = "artifacts"
    RECURRING = "recurring"


@dataclass(frozen=True)
class Telemetry:
    context_pressure: float | None = None
    long_running: bool = False


@dataclass(frozen=True)
class ThreadView:
    state: State = State.UNKNOWN
    modifiers: frozenset[Modifier] = frozenset()
    telemetry: Telemetry = field(default_factory=Telemetry)
    needs_reconciliation: bool = False
    turn_started_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["state"] = self.state.value
        value["modifiers"] = sorted(x.value for x in self.modifiers)
        return value

    @classmethod
    def from_dict(cls, value: dict[str, Any] | None) -> "ThreadView":
        value = value or {}
        telemetry = value.get("telemetry") or {}
        return cls(State(value.get("state", "unknown")),
                   frozenset(Modifier(x) for x in value.get("modifiers", [])),
                   Telemetry(telemetry.get("context_pressure"), bool(telemetry.get("long_running"))),
                   bool(value.get("needs_reconciliation")), value.get("turn_started_at"))


@dataclass(frozen=True)
class Event:
    name: str
    thread_id: str
    turn_id: str | None = None
    at: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Evidence:
    terminal_state: State | None = None
    goal_status: str | None = None
    has_goal: bool = False
    has_artifacts: bool = False
    recurring: bool = False
    context_pressure: float | None = None
    stale: bool = False


@dataclass
class ThreadRecord:
    thread_id: str
    original_title: str
    base_title: str
    view: ThreadView = field(default_factory=ThreadView)
    last_rendered: str | None = None
    last_event: dict[str, Any] | None = None
    config_hash: str | None = None
    project_tag: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {"threadId": self.thread_id, "originalTitle": self.original_title,
                "baseTitle": self.base_title, "view": self.view.to_dict(),
                "lastRendered": self.last_rendered, "lastEvent": self.last_event,
                "configHash": self.config_hash, "projectTag": self.project_tag}

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "ThreadRecord":
        return cls(value["threadId"], value["originalTitle"], value["baseTitle"],
                   ThreadView.from_dict(value.get("view")), value.get("lastRendered"),
                   value.get("lastEvent"), value.get("configHash"), value.get("projectTag"))
