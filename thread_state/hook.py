from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import time
import uuid

from .config import config_hash, load_config
from .events import normalize
from .journal import Journal
from .model import Evidence, State, ThreadRecord
from .reducer import reduce
from .render.compose import compose, strip_prefix
from .rpc import Server
from .sources.app_server import collect
from .sources.artifacts import detect_artifacts
from .sources.rollout import context_pressure
from .sources.automations import is_recurring
from .sources.projects import project_tag, without_title_tag
from .motion import frame
from .store import Store, lock
from .writer import Writer


def _record_event(store: Store, **data):
    store.root.mkdir(parents=True, exist_ok=True)
    with (store.root / "events.jsonl").open("a", encoding="utf-8") as output:
        output.write(json.dumps({"at": datetime.now(timezone.utc).isoformat(), **data}, ensure_ascii=False) + "\n")


def handle(payload: dict, *, server_factory=Server) -> dict:
    started = time.perf_counter(); store = Store()
    config = load_config(store.root / "config.json", store.profiles)
    if not config.get("enabled", True):
        result = {"result": "disabled", "elapsedMs": (time.perf_counter() - started) * 1000}
        _record_event(store, **result); return result
    event = normalize(payload)
    with lock(event.thread_id):
        with server_factory(config) as server:
            retries = 3 if event.name == "Stop" else 1
            thread, turn, goal, evidence = collect(server, event.thread_id, retries=retries)
            if thread.get("ephemeral") or thread.get("archived"): raise ValueError("ephemeral or archived thread")
            current = thread.get("name") or ""
            existing = store.load(event.thread_id)
            is_new = existing is None
            if is_new:
                observed = strip_prefix(current, config)
                tag = project_tag(thread, config, observed)
                existing = ThreadRecord(event.thread_id, current, without_title_tag(observed),
                                        project_tag=tag)
            elif current != existing.last_rendered and strip_prefix(current, config) != existing.base_title:
                observed = strip_prefix(current, config)
                existing.project_tag = project_tag(thread, config, observed)
                existing.base_title = without_title_tag(observed)
                Journal(store.root / "journal.jsonl").append("adopt", batch=f"event:{event.name}",
                    threadId=event.thread_id, actualTitle=current, baseTitle=existing.base_title)
            if not existing.project_tag:
                existing.project_tag = project_tag(thread, config, existing.base_title)
                existing.base_title = without_title_tag(existing.base_title)
            artifact_config = config.get("modifiers", {}).get("artifacts", {})
            artifacts = ModifierSafe.artifacts(existing, payload, artifact_config)
            rollout_path = thread.get("rolloutPath") or thread.get("rollout_path")
            pressure = context_pressure(Path(rollout_path)) if rollout_path else None
            recurring_enabled = bool(config.get("modifiers", {}).get("recurring", False))
            recurring = recurring_enabled and is_recurring(event.thread_id, store.root.parent / "automations")
            evidence = replace(evidence, has_artifacts=artifacts, context_pressure=pressure,
                               recurring=recurring)
            view = reduce(existing.view, event, evidence)
            if view.state == State.WAITING_ON_USER and not config.get("states", {}).get("waiting_on_user", True):
                view = replace(view, state=State.RUNNING)
            long_config = config.get("telemetry", {}).get("long_running", {})
            if long_config.get("enabled") and view.turn_started_at:
                try:
                    began = datetime.fromisoformat(view.turn_started_at.replace("Z", "+00:00"))
                    elapsed = (datetime.now(timezone.utc) - began).total_seconds() / 60
                    view = replace(view, telemetry=replace(view.telemetry,
                        long_running=elapsed >= float(long_config.get("minutes", 15))))
                except ValueError:
                    pass
            existing.view = view
            existing.last_event = {"name": event.name, "turnId": event.turn_id, "at": event.at}
            existing.config_hash = config_hash(config)
            writer = Writer(server, Journal(store.root / "journal.jsonl"))
            motion_write = config.get("motion") == "events" and view.state == State.RUNNING
            render_config = config
            if motion_write:
                render_config = json.loads(json.dumps(config))
                event_number = 0
                events_path = store.root / "events.jsonl"
                if events_path.exists():
                    for line in events_path.read_text(encoding="utf-8").splitlines():
                        try: prior = json.loads(line)
                        except ValueError: continue
                        if prior.get("id") == event.thread_id: event_number += 1
                render_config.setdefault("icons", {})["running"] = frame(event_number)
            if is_new and view.state == State.UNKNOWN and current == strip_prefix(current, config):
                desired = current
                write = {"id": event.thread_id, "oldTitle": current, "newTitle": current,
                         "changed": False, "reason": "unknown-not-introduced"}
            else:
                desired = compose(current, view, render_config, existing.base_title,
                                  existing.project_tag)
                write = writer.write(event.thread_id, desired, batch=f"event:{event.name}:{uuid.uuid4()}",
                                     reason=event.name, expected=current, journal=not motion_write)
            existing.last_rendered = desired
            store.save(existing)
            reconciled = _reconcile_stale(store, server, config, exclude=event.thread_id)
    result = {"result": "ok", "event": event.name, "id": event.thread_id,
              "state": view.state.value, "write": write, "reconciled": reconciled,
              "elapsedMs": (time.perf_counter() - started) * 1000}
    _record_event(store, **result); return result


class ModifierSafe:
    @staticmethod
    def artifacts(record, payload, config):
        from .model import Modifier
        return Modifier.ARTIFACTS in record.view.modifiers or (config.get("enabled", False) and
            detect_artifacts(payload, config.get("extensions", [])))


def _parse_time(value: str | None):
    if not value: return None
    try: return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError: return None


def _reconcile_stale(store: Store, server, config: dict, *, exclude: str | None = None) -> list[dict]:
    """Late reconciliation, invoked by the next event of any thread."""
    results = []; now = datetime.now(timezone.utc)
    reconcile_after = float(config.get("reconcile_after_seconds", 120))
    stale_after = float(config.get("stale_after_minutes", 60)) * 60
    writer = Writer(server, Journal(store.root / "journal.jsonl"))
    for record in store.all():
        if record.thread_id == exclude or record.view.state not in (State.RUNNING, State.WAITING_ON_USER):
            continue
        last = _parse_time((record.last_event or {}).get("at"))
        age = (now - last).total_seconds() if last else stale_after
        if age < reconcile_after: continue
        try:
            thread, _, _, evidence = collect(server, record.thread_id)
            terminal = evidence.terminal_state
            if terminal not in (State.COMPLETED, State.FAILED, State.USAGE_LIMITED) and age < stale_after:
                continue
            state = terminal if terminal in (State.COMPLETED, State.FAILED, State.USAGE_LIMITED) else State.UNKNOWN
            record.view = replace(record.view, state=state, needs_reconciliation=False)
            current = thread.get("name") or writer.current_title(record.thread_id)
            desired = compose(current, record.view, config, record.base_title, record.project_tag)
            result = writer.write(record.thread_id, desired, batch=f"reconcile:{uuid.uuid4()}",
                                  reason="late-reconciliation", expected=current)
            record.last_rendered = desired; record.config_hash = config_hash(config); store.save(record)
            results.append(result)
        except Exception as exc:
            results.append({"id": record.thread_id, "error": str(exc)})
    return results


def main() -> int:
    try: handle(json.load(sys.stdin))
    except Exception as exc:
        _record_event(Store(), result="error", error=str(exc))
    return 0
