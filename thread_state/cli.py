from __future__ import annotations

import argparse
from dataclasses import replace
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import sys
import uuid

from .config import DEFAULT_CONFIG, PROFILES, config_hash, load_config
from .hook import main as hook_main
from .install import install
from .journal import Journal
from .model import Modifier, State, ThreadRecord, ThreadView
from .render.compose import compose, prefix_for, strip_prefix
from .rollback import apply as apply_rollback, plan as plan_rollback
from .rpc import Server
from .sources.app_server import collect
from .sources.projects import project_tag, without_title_tag
from .store import Store, codex_home, lock, read_json, write_json
from .writer import Writer


def output(value): print(json.dumps(value, ensure_ascii=False, indent=2))


def _config(store): return load_config(store.root / "config.json", store.profiles)


def inspect_thread(thread_id: str, apply: bool = False):
    store = Store(); config = _config(store)
    with lock(thread_id), Server(config) as server:
        thread, turn, goal, evidence = collect(server, thread_id)
        current = thread.get("name") or ""; record = store.load(thread_id)
        if record is None:
            observed = strip_prefix(current, config)
            record = ThreadRecord(thread_id, current, without_title_tag(observed),
                                  project_tag=project_tag(thread, config, observed))
        elif not record.project_tag:
            record.project_tag = project_tag(thread, config, record.base_title)
            record.base_title = without_title_tag(record.base_title)
        from .reducer import _derived
        record.view = replace(record.view, state=_derived(evidence, record.view.state),
                              modifiers=record.view.modifiers | ({Modifier.GOAL} if goal else set()))
        desired = compose(current, record.view, config, record.base_title, record.project_tag)
        result = Writer(server, Journal(store.root / "journal.jsonl")).write(thread_id, desired,
            batch=f"inspect:{uuid.uuid4()}", reason="inspect", dry_run=not apply, expected=current)
        if apply: record.last_rendered = desired; record.config_hash = config_hash(config); store.save(record)
        return {**result, "state": record.view.state.value, "goal": bool(goal)}


def preview():
    store = Store(); config = _config(store); base = "[project] Exemplo de conversa"
    return [{"state": state.value, "title": compose(base, ThreadView(state,
        frozenset({Modifier.GOAL, Modifier.ARTIFACTS})), config, base)} for state in State]


def render_all(clean: bool = False):
    store = Store(); config = _config(store); store.snapshot("before-render-all")
    results = []
    with Server(config) as server:
        writer = Writer(server, Journal(store.root / "journal.jsonl")); batch = f"render:{uuid.uuid4()}"
        for record in store.all():
            current = writer.current_title(record.thread_id)
            if record.view.state == State.UNKNOWN and not clean:
                _, _, goal, evidence = collect(server, record.thread_id)
                from .reducer import _derived
                record.view = replace(record.view, state=_derived(evidence, State.UNKNOWN),
                    modifiers=record.view.modifiers | ({Modifier.GOAL} if goal else set()))
            if not record.project_tag:
                thread = server.call("thread/read", {"threadId": record.thread_id,
                                                      "includeTurns": False})["thread"]
                record.project_tag = project_tag(thread, config, record.base_title)
                record.base_title = without_title_tag(record.base_title)
            clean_title = f"[{record.project_tag}] {record.base_title}" if record.project_tag else record.base_title
            desired = clean_title if clean else compose(current, record.view, config, record.base_title,
                                                         record.project_tag)
            try:
                result = writer.write(record.thread_id, desired, batch=batch,
                                      reason="clean" if clean else "render-all", expected=current)
                record.last_rendered = desired; record.config_hash = config_hash(config); store.save(record)
                results.append(result)
            except Exception as exc: results.append({"id": record.thread_id, "error": str(exc)})
    return results


def toggle(enabled: bool, clean: bool = False):
    store = Store(); path = store.root / "config.json"; value = read_json(path, {})
    value["enabled"] = enabled; write_json(path, value)
    return {"enabled": enabled, "cleaned": render_all(clean=True) if clean else []}


def flip_toggle():
    store = Store(); enabled = bool(_config(store).get("enabled", True))
    return toggle(not enabled)


def use_profile(name: str):
    store = Store(); store.snapshot(f"before-profile-{name}")
    if name not in PROFILES and not (store.profiles / f"{name}.json").exists():
        raise ValueError(f"profile not found: {name}")
    path = store.root / "config.json"; value = read_json(path, {}); value["profile"] = name
    write_json(path, value); return {"profile": name}


def rollback_command(args):
    store = Store(); journal = Journal(store.root / "journal.jsonl"); config = _config(store)
    with Server(config) as server:
        writer = Writer(server, journal)
        if args.to_snapshot:
            raw = json.loads(store.find_snapshot(args.to_snapshot).read_text(encoding="utf-8"))
            rows = []
            for item in raw.get("threads", []):
                record = ThreadRecord.from_dict(item); current = writer.current_title(record.thread_id)
                rows.append({"threadId": record.thread_id, "oldTitle": record.last_rendered or record.base_title,
                             "newTitle": current, "actualTitle": current, "operation": f"snapshot:{args.to_snapshot}"})
        elif args.original:
            rows = []
            for record in store.all():
                current = writer.current_title(record.thread_id)
                rows.append({"threadId": record.thread_id, "oldTitle": record.original_title,
                             "newTitle": current, "actualTitle": current, "operation": "original"})
        else:
            rows = plan_rollback(journal, operation=args.op, batch=args.batch, since=args.since,
                                 thread_id=args.thread)
        return apply_rollback(writer, rows, force=args.force)


def capture(path: str | None):
    payload = json.load(sys.stdin) if path in (None, "-") else json.loads(Path(path).read_text(encoding="utf-8"))
    sensitive = {"prompt", "cwd", "transcript_path", "user_email", "account_id", "email",
                 "access_token", "token", "authorization", "content", "text"}
    def sanitize(value):
        if isinstance(value, dict):
            return {key: ("<redacted>" if key.lower() in sensitive else sanitize(item))
                    for key, item in value.items()}
        if isinstance(value, list): return [sanitize(item) for item in value]
        return value
    sanitized = sanitize(payload)
    destination = Store().root / "captures" / f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}-{uuid.uuid4().hex[:8]}.json"
    write_json(destination, sanitized); return {"path": str(destination)}


def migrate_legacy():
    store = Store(); store.snapshot("before-legacy-migration")
    legacy = codex_home() / "thread-status" / "changes.jsonl"; imported = 0
    if legacy.exists():
        originals = {}
        for line in legacy.read_text(encoding="utf-8").splitlines():
            try: row = json.loads(line)
            except ValueError: continue
            tid = row.get("threadId") or row.get("id"); old = row.get("oldTitle")
            if tid and old: originals.setdefault(tid, old)
        legacy_states = {"🚩": State.USAGE_LIMITED, "🔴": State.FAILED,
                         "⏸️": State.INTERRUPTED, "⏳": State.BUDGET_LIMITED,
                         "🟡": State.PENDING, "✅": State.COMPLETED, "🔵": State.RUNNING,
                         "⚪": State.UNKNOWN}
        for tid, title in originals.items():
            if not store.load(tid):
                observed = strip_prefix(title, DEFAULT_CONFIG)
                marker = next((key for key in legacy_states if title.startswith(key)), None)
                modifiers = frozenset({Modifier.GOAL}) if "🏁" in title.split(" ", 3)[:3] else frozenset()
                store.save(ThreadRecord(tid, title, without_title_tag(observed),
                    ThreadView(legacy_states.get(marker, State.UNKNOWN), modifiers),
                    project_tag=project_tag({}, DEFAULT_CONFIG, observed)))
            imported += 1
    # Legacy hooks are disabled only after the snapshot/import succeeds.
    hooks = codex_home() / "hooks.json"; data = read_json(hooks, {"hooks": {}}); changed = False
    for event, groups in list(data.get("hooks", {}).items()):
        kept = []
        for group in groups:
            handlers = [h for h in group.get("hooks", []) if "thread-status" not in str(h.get("command", "")).lower()
                        and h.get("statusMessage") != "Codex Thread Status"]
            if len(handlers) != len(group.get("hooks", [])): changed = True
            if handlers: kept.append({**group, "hooks": handlers})
        if kept: data["hooks"][event] = kept
        else: data["hooks"].pop(event, None)
    if changed: write_json(hooks, data)
    return {"imported": imported, "legacyHooksDisabled": changed}


def doctor():
    store = Store(); config = _config(store)
    from . import __version__
    return {"version": __version__, "root": str(store.root), "enabled": config["enabled"],
            "profile": config.get("profile", "default"), "threads": len(store.all()),
            "journalEntries": len(Journal(store.root / "journal.jsonl").rows()),
            "hooksFile": str(codex_home() / "hooks.json")}


def parser():
    root = argparse.ArgumentParser(description="Deterministic state badges for Codex threads")
    sub = root.add_subparsers(dest="command", required=True)
    sub.add_parser("hook"); sub.add_parser("install"); sub.add_parser("uninstall")
    inspect = sub.add_parser("inspect"); inspect.add_argument("thread_id", type=lambda x: str(uuid.UUID(x))); inspect.add_argument("--apply", action="store_true")
    sub.add_parser("status"); sub.add_parser("preview")
    render = sub.add_parser("render"); render.add_argument("--all", action="store_true", required=True)
    clean = sub.add_parser("clean"); clean.add_argument("--all", action="store_true", default=True)
    off = sub.add_parser("off"); off.add_argument("--clean", action="store_true")
    sub.add_parser("on"); sub.add_parser("toggle")
    snapshot = sub.add_parser("snapshot"); snapshot_sub = snapshot.add_subparsers(dest="snapshot_command", required=True)
    create = snapshot_sub.add_parser("create"); create.add_argument("label")
    profile = sub.add_parser("profile"); profile_sub = profile.add_subparsers(dest="profile_command", required=True)
    use = profile_sub.add_parser("use"); use.add_argument("name")
    rollback = sub.add_parser("rollback"); selector = rollback.add_mutually_exclusive_group(required=True)
    selector.add_argument("--op"); selector.add_argument("--batch"); selector.add_argument("--since")
    selector.add_argument("--thread"); selector.add_argument("--to-snapshot"); selector.add_argument("--original", action="store_true")
    rollback.add_argument("--force", action="store_true")
    capture_parser = sub.add_parser("capture"); capture_parser.add_argument("path", nargs="?")
    migrate = sub.add_parser("migrate"); migrate.add_argument("--from-legacy", action="store_true", required=True)
    sub.add_parser("doctor")
    panel = sub.add_parser("panel", help="Open the local appearance controls")
    panel.add_argument("--port", type=int, default=0)
    panel.add_argument("--open", action="store_true", dest="open_browser")
    return root


def main(argv=None):
    args = parser().parse_args(argv)
    if args.command == "hook": return hook_main()
    if args.command == "panel":
        from .panel import serve
        return serve(args.port, args.open_browser)
    if args.command in ("install", "uninstall"): install(args.command == "uninstall"); return 0
    if args.command == "inspect": output(inspect_thread(args.thread_id, args.apply))
    elif args.command == "preview": output(preview())
    elif args.command == "status": output(doctor())
    elif args.command == "doctor": output(doctor())
    elif args.command == "render": output(render_all())
    elif args.command == "clean": output(render_all(clean=True))
    elif args.command == "off": output(toggle(False, args.clean))
    elif args.command == "on": output(toggle(True))
    elif args.command == "toggle": output(flip_toggle())
    elif args.command == "snapshot": output({"path": str(Store().snapshot(args.label))})
    elif args.command == "profile": output(use_profile(args.name))
    elif args.command == "rollback": output(rollback_command(args))
    elif args.command == "capture": output(capture(args.path))
    elif args.command == "migrate": output(migrate_legacy())
    return 0
