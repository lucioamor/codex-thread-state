import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import thread_state as ts


class Server:
    def __init__(self):
        self.title = "[demo] Review parser"
        self.writes = []

    def call(self, method, params):
        if method == "thread/read":
            return {"thread": {"id": "test", "name": self.title}}
        if method == "thread/turns/list":
            return {"data": [{"id": "turn", "status": "completed"}]}
        if method == "thread/goal/get":
            return {"goal": None}
        if method == "thread/name/set":
            self.writes.append(params)
            self.title = params["name"]
            return {}
        raise AssertionError(method)


class Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {"CODEX_HOME": self.temp.name})
        self.env.start()

    def tearDown(self):
        self.env.stop(); self.temp.cleanup()

    def test_states(self):
        for turn, goal, expected in [
            ({"status": "inProgress"}, {"status": "complete"}, "running"),
            ({"status": "failed", "error": {"code": "usage_limit_reached"}}, None, "usage_limited"),
            ({"status": "failed", "error": {"code": "rate_limit"}}, None, "failed"),
            ({"status": "interrupted"}, None, "interrupted"),
            ({"status": "completed"}, {"status": "active"}, "pending"),
            ({"status": "completed"}, {"status": "budget_limited"}, "budget_limited"),
            ({"status": "completed"}, None, "completed"),
            (None, None, "unknown")]:
            with self.subTest(expected=expected):
                self.assertEqual(ts.classify(turn, goal)[0], expected)

    def test_prose_does_not_classify(self):
        turn = {"status": "completed", "items": [{"text": "hit your usage limit; falta validar"}]}
        self.assertEqual(ts.classify(turn, None)[0], "completed")

    def test_title_preserved_and_idempotent(self):
        title = "[cue] Revisão de execução"
        desired = ts.compose(title, "running", True)
        self.assertEqual(desired, ts.compose(desired, "running", True))
        self.assertTrue(desired.endswith(title))

    def test_unsafe_title_skipped(self):
        for title in ("", "bad\x00name", "x" * 60):
            with self.assertRaises(ValueError):
                ts.compose(title, "running", False)

    def test_dry_run_does_not_write(self):
        server = Server()
        ts.update(server, "test", {})
        self.assertEqual(server.writes, [])

    def test_apply_ledger_and_idempotence(self):
        server = Server()
        ts.update(server, "test", {}, apply=True)
        ts.update(server, "test", {}, apply=True)
        self.assertEqual(len(server.writes), 1)
        rows = [json.loads(x) for x in (ts.root() / "changes.jsonl").read_text(encoding="utf-8").splitlines()]
        self.assertEqual([r["phase"] for r in rows], ["intent", "applied"])
        self.assertEqual(rows[0]["oldTitle"], "[demo] Review parser")

    def test_stale_event_skips(self):
        server = Server()
        with self.assertRaises(ValueError):
            ts.update(server, "test", {}, True, {"turn_id": "older", "hook_event_name": "Stop"})
        self.assertFalse(server.writes)

    def test_install_merge_repeat_and_uninstall(self):
        other = {"type": "command", "command": "existing-tool"}
        ts.write_json(ts.home() / "hooks.json", {"hooks": {"Stop": [{"hooks": [other]}]}})
        ts.install(); ts.install()
        self.assertEqual(len(ts.read_json(ts.home() / "hooks.json")["hooks"]["Stop"]), 2)
        ts.install(uninstall=True)
        self.assertEqual(ts.read_json(ts.home() / "hooks.json"), {"hooks": {"Stop": [{"hooks": [other]}]}})

    def test_rpc_denies_generation(self):
        server = ts.Server.__new__(ts.Server)
        for method in ("turn/start", "thread/resume", "responses"):
            with self.assertRaises(ValueError):
                server.call(method, {})

    def test_lock_contention_and_release(self):
        with ts.lock("test"):
            with self.assertRaises(TimeoutError):
                with ts.lock("test", timeout=0):
                    pass
        with ts.lock("test", timeout=0):
            pass


if __name__ == "__main__":
    unittest.main()
