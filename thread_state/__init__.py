"""Thread State v0.2 public API."""
from .config import DEFAULT_CONFIG, load_config
from .model import Evidence, Event, Modifier, State, Telemetry, ThreadRecord, ThreadView
from .reducer import reduce
from .render.compose import compose as _compose, strip_prefix
from .rpc import Server
from .sources.app_server import terminal_state
from .store import codex_home as home, lock, read_json, state_root as root, write_json
from .install import install as _install_v2

__version__ = "0.2.0"

def main():
    from .cli import main as cli_main
    return cli_main()


def classify(turn, goal):
    """Compatibility helper retained for v0.1 callers."""
    status = (turn or {}).get("status")
    if status == "inProgress": return "running", "turn.inProgress"
    terminal = terminal_state(turn, (turn or {}).get("id"))
    if terminal and terminal.value != "completed": return terminal.value, "turn." + terminal.value
    mapping = {"active": "pending", "complete": "completed", "paused": "paused",
               "blocked": "blocked", "budget_limited": "budget_limited", "usage_limited": "usage_limited"}
    if (goal or {}).get("status") in mapping:
        value = mapping[goal["status"]]; return value, "goal." + goal["status"]
    if status == "completed": return "completed", "turn.completed (not proof of task completion)"
    return "unknown", "no structured state"


def compose(title, state, goal_or_config=None, limit=60, base_title=None):
    """Render v0.2 views and accept the old compose(title, state, goal) form."""
    if isinstance(goal_or_config, dict):
        return _compose(title, state, goal_or_config, base_title)
    config = dict(DEFAULT_CONFIG); config["maxTitleChars"] = limit
    view = state if isinstance(state, ThreadView) else ThreadView(State(state),
        frozenset({Modifier.GOAL}) if goal_or_config else frozenset())
    return _compose(title, view, config, base_title)


def update(server, tid, config, apply=False, event=None):
    """Compatibility inspection path; new hooks use the event reducer/store."""
    from .journal import Journal
    from .sources.app_server import snapshot
    from .writer import Writer
    thread, turn, goal = snapshot(server, tid)
    event_turn = (event or {}).get("turn_id")
    if event_turn and event_turn != (turn or {}).get("id"):
        raise ValueError("event turn differs from persisted latest turn; skipped")
    state, reason = classify(turn, goal)
    if (event or {}).get("hook_event_name") == "UserPromptSubmit": state, reason = "running", "event.UserPromptSubmit"
    elif (event or {}).get("hook_event_name") == "Interrupt": state, reason = "interrupted", "event.Interrupt"
    desired = compose(thread.get("name") or "", state, bool(goal), config.get("maxTitleChars", 60))
    result = {"id": tid, "oldTitle": thread.get("name") or "", "newTitle": desired, "state": state, "reason": reason}
    if apply:
        writer = Writer(server, Journal(root() / "changes.jsonl"))
        written = writer.write(tid, desired, batch="compat", reason=reason, expected=result["oldTitle"])
        result.update(written)
    return result


def install(uninstall=False):
    return _install_v2(uninstall)

__all__ = ["DEFAULT_CONFIG", "Evidence", "Event", "Modifier", "State", "Telemetry",
           "ThreadRecord", "ThreadView", "Server", "classify", "compose", "home", "install",
           "load_config", "lock", "main", "read_json", "reduce", "root", "strip_prefix",
           "update", "write_json"]
