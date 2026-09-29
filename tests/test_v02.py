import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from thread_state.config import DEFAULT_CONFIG, load_config
from thread_state.events import normalize
from thread_state.journal import Journal
from thread_state.hook import _reconcile_stale, handle
from thread_state.model import Evidence, Event, Modifier, State, Telemetry, ThreadRecord, ThreadView
from thread_state.reducer import reduce
from thread_state.render.compose import compose, prefix_for, strip_prefix
from thread_state.rollback import apply, plan
from thread_state.sources.app_server import terminal_state
from thread_state.sources.artifacts import detect_artifacts
from thread_state.sources.rollout import pressure_from_counts
from thread_state.sources.projects import project_tag, title_tag, without_title_tag
from thread_state.store import Store
from thread_state.writer import Writer


class FakeServer:
    def __init__(self, title="[demo] Trabalho"):
        self.title = title; self.writes = []; self.turn_status = "interrupted"
    def call(self, method, params):
        if method == "thread/read": return {"thread": {"id": params["threadId"], "name": self.title}}
        if method == "thread/turns/list": return {"data": [{"id": "t", "status": self.turn_status}]}
        if method == "thread/goal/get": return {"goal": None}
        if method == "thread/name/set": self.title = params["name"]; self.writes.append(params); return {}
        raise AssertionError(method)
    def __enter__(self): return self
    def __exit__(self, *_): pass


class V02Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {"CODEX_HOME": self.temp.name})
        self.env.start()
    def tearDown(self): self.env.stop(); self.temp.cleanup()

    def test_event_authority_and_waiting(self):
        start = normalize({"hook_event_name": "UserPromptSubmit", "session_id": "12345678-1234-1234-1234-123456789abc", "turn_id": "t"})
        running = reduce(ThreadView(State.INTERRUPTED), start, Evidence(terminal_state=State.INTERRUPTED))
        self.assertEqual(running.state, State.RUNNING)
        waiting = reduce(running, Event("PreToolUse", start.thread_id, "t", payload={"tool_name": "request_user_input"}))
        self.assertEqual(waiting.state, State.WAITING_ON_USER)
        self.assertEqual(reduce(waiting, Event("PostToolUse", start.thread_id)).state, State.RUNNING)

    def test_stop_ambiguous_keeps_running(self):
        result = reduce(ThreadView(State.RUNNING), Event("Stop", "id"), Evidence())
        self.assertEqual(result.state, State.RUNNING); self.assertTrue(result.needs_reconciliation)
        active_goal = reduce(ThreadView(State.RUNNING), Event("Stop", "id"), Evidence(goal_status="active", has_goal=True))
        self.assertEqual(active_goal.state, State.RUNNING); self.assertTrue(active_goal.needs_reconciliation)

    def test_interrupted_persistence_requires_matching_event(self):
        turn = {"id": "new", "status": "interrupted"}
        self.assertIsNone(terminal_state(turn, None))
        self.assertIsNone(terminal_state(turn, "old"))
        self.assertEqual(terminal_state(turn, "new"), State.INTERRUPTED)

    def test_renderer_taxonomy_budget_and_adoption_strip(self):
        view = ThreadView(State.RUNNING, frozenset({Modifier.GOAL, Modifier.ARTIFACTS, Modifier.RECURRING}),
                          Telemetry(.95, True))
        config = json.loads(json.dumps(DEFAULT_CONFIG)); config["max_badges"] = 3
        title = compose("[x] Fazer", view, config)
        self.assertEqual(title, "▶︎ 🏆 ● [x] Fazer")
        self.assertEqual(strip_prefix("🔵 🏁 [x] Fazer", config), "[x] Fazer")

    def test_writer_journal_and_conflict_safe_rollback(self):
        server = FakeServer(); journal = Journal(Store().root / "journal.jsonl"); writer = Writer(server, journal)
        written = writer.write("t", "✓ [demo] Trabalho", batch="b", reason="test")
        self.assertEqual([x["phase"] for x in journal.rows()], ["intent", "applied"])
        server.title = "Título do usuário"
        result = apply(writer, plan(journal, operation=written["operation"]))
        self.assertEqual(len(result["conflicts"]), 1); self.assertEqual(server.title, "Título do usuário")
        result = apply(writer, plan(journal, operation=written["operation"]), force=True)
        self.assertEqual(server.title, "[demo] Trabalho"); self.assertEqual(len(result["restored"]), 1)

    def test_store_snapshot_roundtrip(self):
        store = Store(); record = ThreadRecord("t", "Original", "Base", ThreadView(State.COMPLETED))
        store.save(record); loaded = store.load("t")
        self.assertEqual(loaded.to_dict(), record.to_dict())
        self.assertTrue(store.snapshot("antes-lab").exists())

    def test_artifacts_only_created_allowlist(self):
        self.assertTrue(detect_artifacts({"created_files": ["report.pdf"]}, ["pdf"]))
        self.assertFalse(detect_artifacts({"modified_files": ["app.py"]}, ["pdf", "py"]))
        self.assertTrue(detect_artifacts({"items": [{"type": "ImageGeneration"}]}, []))

    def test_context_formula(self):
        self.assertAlmostEqual(pressure_from_counts(12_000, 100_000), 12_000 / 88_000)
        self.assertEqual(pressure_from_counts(100_000, 100_000), 1)

    def test_profiles_merge_without_losing_defaults(self):
        path = Store().root / "config.json"; path.parent.mkdir(parents=True); path.write_text('{"profile":"minimal"}', encoding="utf-8")
        config = load_config(path, Store().profiles)
        self.assertFalse(config["modifiers"]["goal"]); self.assertEqual(config["style"], "hybrid")

    def test_project_tag_precedence_and_rendering(self):
        config = json.loads(json.dumps(DEFAULT_CONFIG))
        config["projectRoots"] = {"C:/AI/iesbrazil": "iesbrazil"}
        self.assertEqual(project_tag({"cwd": "C:/AI/iesbrazil/ops"}, config), "iesbrazil")
        self.assertEqual(project_tag({"cwd": "C:/tmp/x", "gitInfo": {"originUrl": "https://github.com/o/Repo.git"}}, config), "repo")
        self.assertEqual(project_tag({"cwd": "C:/AI/codex-thread-state"}, config), "codex-thread-state")
        self.assertEqual(project_tag({}, config, "[Custom] Título"), "custom")
        self.assertEqual(without_title_tag("[Custom] Título"), "Título")
        self.assertEqual(title_tag("[Custom] Título"), "Custom")
        rendered = compose("Título", ThreadView(State.COMPLETED), config, "Título", "repo")
        self.assertEqual(rendered, "✓ [repo] Título")

    def test_record_project_tag_roundtrip(self):
        record = ThreadRecord("t", "Original", "Título", ThreadView(State.COMPLETED),
                              project_tag="repo")
        self.assertEqual(ThreadRecord.from_dict(record.to_dict()).project_tag, "repo")

    def test_hook_event_beats_cross_process_interrupted_read(self):
        server = FakeServer()
        result = handle({"hook_event_name": "UserPromptSubmit",
                         "session_id": "12345678-1234-1234-1234-123456789abc", "turn_id": "t"},
                        server_factory=lambda _: server)
        self.assertEqual(result["state"], "running")
        self.assertTrue(server.title.startswith("▶︎ "))
        record = Store().load("12345678-1234-1234-1234-123456789abc")
        self.assertEqual(record.original_title, "[demo] Trabalho")

    def test_late_reconciliation_promotes_persisted_terminal(self):
        store = Store(); tid = "12345678-1234-1234-1234-123456789abc"
        record = ThreadRecord(tid, "[demo] Trabalho", "[demo] Trabalho", ThreadView(State.RUNNING),
                              "▶︎ [demo] Trabalho", {"name": "UserPromptSubmit", "at": "2000-01-01T00:00:00+00:00"})
        store.save(record)
        server = FakeServer("▶︎ [demo] Trabalho"); server.turn_status = "completed"
        config = json.loads(json.dumps(DEFAULT_CONFIG)); config["reconcile_after_seconds"] = 0
        results = _reconcile_stale(store, server, config)
        self.assertEqual(len(results), 1)
        self.assertEqual(store.load(tid).view.state, State.COMPLETED)
        self.assertTrue(server.title.startswith("✓ "))


if __name__ == "__main__": unittest.main()
