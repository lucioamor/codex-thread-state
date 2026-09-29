"""Thread State: event-driven title badges. Standard library only; no model calls."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import queue
import re
import shutil
import subprocess
import sys
import threading
import time
import uuid

ICONS = {"running": "🔵", "usage_limited": "🚩", "budget_limited": "⏳",
         "failed": "🔴", "blocked": "🔴", "pending": "🟡", "interrupted": "⏸️",
         "paused": "⏸️", "completed": "✅", "unknown": "⚪"}
EVENTS = ("UserPromptSubmit", "Stop", "Interrupt")
METHODS = {"initialize", "thread/read", "thread/turns/list", "thread/goal/get", "thread/name/set"}
USAGE_CODES = ("usage_limit", "insufficient_quota", "credit balance exhausted", "hit your usage limit")


def home():
    return Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex")))


def root():
    return home() / "thread-state"


def read_json(path, default=None):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def record(filename, data):
    root().mkdir(parents=True, exist_ok=True)
    with (root() / filename).open("a", encoding="utf-8") as out:
        out.write(json.dumps({"at": datetime.now(timezone.utc).isoformat(), **data}, ensure_ascii=False) + "\n")


@contextmanager
def lock(name, timeout=5):
    """Kernel lock: automatically released on exit/crash; separate per thread."""
    root().mkdir(parents=True, exist_ok=True)
    with (root() / (name + ".lock")).open("a+b") as handle:
        handle.seek(0, 2)
        if handle.tell() == 0:
            handle.write(b"0"); handle.flush()
        deadline = time.monotonic() + timeout
        while True:
            try:
                handle.seek(0)
                if os.name == "nt":
                    import msvcrt
                    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except OSError:
                if time.monotonic() >= deadline:
                    raise TimeoutError("thread-state lock busy")
                time.sleep(0.05)
        try:
            yield
        finally:
            handle.seek(0)
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def executable(config):
    candidates = [config.get("codexExecutable"), os.environ.get("CODEX_CLI_PATH"), shutil.which("codex")]
    if os.name == "nt":
        folder = Path(os.environ.get("LOCALAPPDATA", "")) / "OpenAI/Codex/bin"
        candidates += [str(p) for p in sorted(folder.glob("*/codex.exe"), key=lambda p: p.stat().st_mtime, reverse=True)]
    for value in candidates:
        if value and Path(value).is_file() and Path(value).suffix.lower() not in (".cmd", ".bat"):
            return value
    raise FileNotFoundError("Set codexExecutable or CODEX_CLI_PATH to the native Codex executable")


class Server:
    def __init__(self, config):
        self.seq = 0
        self.responses = queue.Queue()
        self.process = subprocess.Popen([executable(config), "app-server", "--listen", "stdio://"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            text=True, encoding="utf-8", creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        threading.Thread(target=self._read, daemon=True).start()
        try:
            self.call("initialize", {"clientInfo": {"name": "thread_state", "version": "0.1.0"},
                                     "capabilities": {"experimentalApi": True}})
            self._send({"method": "initialized"})
        except Exception:
            self.close(); raise

    def _read(self):
        for line in self.process.stdout:
            try:
                self.responses.put(json.loads(line))
            except ValueError:
                continue
        self.responses.put(None)

    def _send(self, data):
        self.process.stdin.write(json.dumps(data) + "\n")
        self.process.stdin.flush()

    def call(self, method, params):
        if method not in METHODS:
            raise ValueError("RPC method is not allowed")
        self.seq += 1
        self._send({"id": self.seq, "method": method, "params": params})
        deadline = time.monotonic() + 5
        while True:
            try:
                message = self.responses.get(timeout=max(0.001, deadline - time.monotonic()))
            except queue.Empty:
                raise TimeoutError("App Server response timeout") from None
            if message is None:
                raise RuntimeError("App Server closed output")
            if message.get("id") == self.seq:
                if "error" in message:
                    raise RuntimeError(str(message["error"]))
                return message.get("result", {})
            if time.monotonic() >= deadline:
                raise TimeoutError("App Server response timeout")

    def close(self):
        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.process.kill(); self.process.wait(timeout=2)
        self.process.stdin.close()
        self.process.stdout.close()


def classify(turn, goal):
    status = (turn or {}).get("status")
    if status == "inProgress":
        return "running", "turn.inProgress"
    if status == "failed":
        error = json.dumps(turn.get("error"), ensure_ascii=False).lower()
        limited = any(code in error for code in USAGE_CODES)
        return ("usage_limited" if limited else "failed"), "turn.error"
    if status in ("interrupted", "cancelled"):
        return "interrupted", "turn.interrupted"
    gs = (goal or {}).get("status")
    states = {"active": "pending", "complete": "completed", "paused": "paused",
              "blocked": "blocked", "budget_limited": "budget_limited", "usage_limited": "usage_limited"}
    if gs in states:
        return states[gs], "goal." + gs
    if status == "completed":
        return "completed", "turn.completed (not proof of task completion)"
    return "unknown", "no structured state"


def compose(title, state, goal, limit=60):
    """Skip overlength titles rather than destroy editorial wording."""
    prefix = ICONS[state] + " " + ("🏁 " if goal else "")
    icons = "|".join(re.escape(x) for x in {*ICONS.values(), "🏁", "🔁"})
    base = re.sub(r"^(?:(?:" + icons + r")\s+)+", "", title)
    desired = prefix + base
    if not base.strip() or any(ord(c) < 32 or ord(c) == 127 for c in title):
        raise ValueError("empty title or control characters")
    if len(title) > limit or len(desired) > limit:
        raise ValueError("title exceeds configured limit; no truncation performed")
    return desired


def snapshot(server, tid):
    thread = server.call("thread/read", {"threadId": tid, "includeTurns": False})["thread"]
    turns = server.call("thread/turns/list", {"threadId": tid, "limit": 1, "sortDirection": "desc", "itemsView": "full"}).get("data", [])
    # Fail closed if goal state is unavailable instead of silently declaring completion.
    goal = server.call("thread/goal/get", {"threadId": tid}).get("goal")
    return thread, turns[0] if turns else None, goal


def update(server, tid, config, apply=False, event=None):
    thread, turn, goal = snapshot(server, tid)
    if thread.get("ephemeral") or thread.get("archived"):
        raise ValueError("ephemeral or archived thread")
    event_turn = (event or {}).get("turn_id")
    if event_turn and event_turn != (turn or {}).get("id"):
        raise ValueError("event turn differs from persisted latest turn; skipped")
    state, reason = classify(turn, goal)
    if (event or {}).get("hook_event_name") == "UserPromptSubmit":
        state, reason = "running", "event.UserPromptSubmit"
    elif (event or {}).get("hook_event_name") == "Interrupt":
        state, reason = "interrupted", "event.Interrupt"
    elif (event or {}).get("hook_event_name") == "Stop" and state == "running":
        raise ValueError("Stop arrived before terminal state persisted; skipped")
    old = thread.get("name") or ""
    new = compose(old, state, bool(goal), config.get("maxTitleChars", 60))
    change = {"id": tid, "oldTitle": old, "newTitle": new, "state": state, "reason": reason}
    if apply and old != new:
        if snapshot(server, tid) != (thread, turn, goal):
            raise ValueError("thread changed during inspection; skipped")
        operation = str(uuid.uuid4())
        with lock("ledger"):
            record("changes.jsonl", {"operation": operation, "phase": "intent", **change})
            server.call("thread/name/set", {"threadId": tid, "name": new})
            actual = server.call("thread/read", {"threadId": tid, "includeTurns": False})["thread"].get("name")
            record("changes.jsonl", {"operation": operation, "phase": "applied", "actualTitle": actual, **change})
        if actual != new:
            raise ValueError("title readback mismatch; inspect ledger")
    return change


def hook():
    try:
        event = json.load(sys.stdin)
        if event.get("hook_event_name") not in EVENTS:
            raise ValueError("unsupported hook event")
        tid = str(uuid.UUID(event["session_id"]))
        with lock(tid):
            config = read_json(root() / "config.json", {})
            server = Server(config)
            try:
                result = update(server, tid, config, apply=True, event=event)
                record("events.jsonl", {"event": event["hook_event_name"], "id": tid, "state": result["state"], "result": "ok"})
            finally:
                server.close()
    except Exception as exc:
        record("events.jsonl", {"result": "error", "error": str(exc)})
    # No stdout/context/continuation: never prompt the model from a hook.
    return 0


def install(uninstall=False):
    path = home() / "hooks.json"
    with lock("install"):
        data = read_json(path, {"hooks": {}})
        script = str(Path(__file__).resolve())
        python = sys.executable
        command = subprocess.list2cmdline([python, script, "hook"]) if os.name == "nt" else __import__("shlex").join([python, script, "hook"])
        for name in EVENTS:
            groups = data.setdefault("hooks", {}).get(name, [])
            kept = []
            for group in groups:
                handlers = [h for h in group.get("hooks", []) if h.get("statusMessage") != "Thread State"]
                if handlers:
                    kept.append({**group, "hooks": handlers})
            if not uninstall:
                kept.append({"hooks": [{"type": "command", "command": command, "async": True,
                                         "timeout": 3 if name == "Interrupt" else 30, "statusMessage": "Thread State"}]})
            if kept:
                data["hooks"][name] = kept
            else:
                data["hooks"].pop(name, None)
        if path.exists():
            shutil.copy2(path, root() / ("hooks-backup-" + uuid.uuid4().hex + ".json"))
        write_json(path, data)
    print("Hooks removed; titles and ledger preserved." if uninstall else "Hooks installed. Review/trust using Codex CLI /hooks before use. Keep this checkout in place.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("hook")
    sub.add_parser("install")
    sub.add_parser("uninstall")
    inspect = sub.add_parser("inspect")
    inspect.add_argument("thread_id", type=lambda x: str(uuid.UUID(x)))
    inspect.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    if args.command == "hook":
        return hook()
    if args.command in ("install", "uninstall"):
        install(args.command == "uninstall"); return 0
    with lock(args.thread_id):
        config = read_json(root() / "config.json", {})
        server = Server(config)
        try:
            print(json.dumps(update(server, args.thread_id, config, args.apply), ensure_ascii=False, indent=2))
        finally:
            server.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
