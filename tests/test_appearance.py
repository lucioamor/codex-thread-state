import json
import os
from pathlib import Path
import tempfile
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from unittest.mock import patch

from thread_state.appearance import Appearance, project_settings, validate_settings, with_settings
from thread_state.config import DEFAULT_CONFIG, load_config, merge
from thread_state.hook import handle
from thread_state.model import Modifier, State, Telemetry, ThreadView
from thread_state.panel import PanelServer
from thread_state.render.compose import compose, icons, prefix_for, strip_prefix
from thread_state.render.themes import THEMES
from thread_state.store import Store, read_json, write_json
from test_v02 import FakeServer


class AppearanceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {"CODEX_HOME": self.temp.name})
        self.env.start()
        self.service = Appearance()

    def tearDown(self):
        self.env.stop(); self.temp.cleanup()

    def test_unchanged_default_and_theme_completion(self):
        self.assertEqual(prefix_for(ThreadView(State.COMPLETED), DEFAULT_CONFIG), "✓")
        cfg = merge(json.loads(json.dumps(DEFAULT_CONFIG)), {"style": "emoji"})
        self.assertEqual(prefix_for(ThreadView(State.COMPLETED), cfg), "✅")
        cfg["states"]["completed_marker"] = "+"
        self.assertEqual(icons(cfg)["completed"], "+")

    def test_every_theme_covers_taxonomy_and_roundtrips(self):
        for name in THEMES:
            cfg = with_settings(DEFAULT_CONFIG, {"style": name, "enabled": True, "max_badges": 6, "icons": {}})
            for state in State:
                with self.subTest(theme=name, state=state):
                    view = ThreadView(state, frozenset(Modifier), Telemetry(.96, True))
                    title = compose("Título íntegro", view, cfg, "Título íntegro", "demo")
                    self.assertEqual(strip_prefix(title, cfg), "[demo] Título íntegro")
                    self.assertEqual(compose(title, view, cfg), title)

    def test_minimal_never_adds_modifiers_or_telemetry(self):
        cfg = merge(DEFAULT_CONFIG, {"style": "minimal", "max_badges": 6})
        view = ThreadView(State.RUNNING, frozenset(Modifier), Telemetry(.99, True))
        self.assertEqual(prefix_for(view, cfg), "▶︎")

    def test_preview_is_read_only(self):
        state = self.service.state()
        settings = state["settings"]; settings["style"] = "blue"
        result = self.service.preview(settings)
        running = next(row for row in result["rows"] if row["state"] == "running")
        self.assertTrue(running["title"].startswith("🌊 "))
        self.assertFalse(self.service.path.exists())
        self.assertFalse(self.service.store.snapshots.exists())

    def test_color_palettes_use_semantic_emoji_without_ascii_family(self):
        self.assertNotIn("ascii", THEMES)
        self.assertNotIn("ASCII", self.service.state()["picker"])
        for color in ("red", "green", "blue", "yellow"):
            for marker in THEMES[color].values():
                self.assertFalse(marker.startswith(("🔴▶", "🔵▶", "🟢▶", "🟡▶")))
                self.assertFalse(marker.isascii())
        self.assertEqual(THEMES["red"]["failed"], "❌")
        self.assertEqual(THEMES["red"]["completed"], "💯")
        self.assertEqual(THEMES["green"]["completed"], "✅")
        self.assertEqual(THEMES["blue"]["paused"], "💤")
        self.assertEqual(THEMES["yellow"]["running"], "⚡")

    def test_themes_do_not_consume_editorial_words(self):
        for title in ("O projeto", "o trabalho", "x e y", "OK para continuar"):
            self.assertEqual(strip_prefix(title, DEFAULT_CONFIG), title)

    def test_save_preserves_other_config_and_undo_restores_preferences(self):
        original = {"codexExecutable": "preserve.exe", "projectRoots": {"/demo": "work"},
                    "profile": "minimal", "states": {"waiting_on_user": False, "completed_marker": "✓"}}
        write_json(self.service.path, original)
        state = self.service.state(); settings = state["settings"]
        settings.update(style="playful", icons={"running": "🧑‍💻"}, enabled=False)
        result = self.service.save(settings, state["revision"])
        raw = read_json(self.service.path)
        self.assertEqual(raw["codexExecutable"], "preserve.exe")
        self.assertEqual(raw["projectRoots"], original["projectRoots"])
        self.assertFalse(raw["states"]["waiting_on_user"])
        self.assertEqual(icons(load_config(self.service.path))["running"], "🧑‍💻")
        self.assertTrue(result["state"]["canUndo"])
        self.service.undo(result["state"]["revision"])
        restored = read_json(self.service.path)
        for key, value in original.items(): self.assertEqual(restored[key], value)
        self.assertIn("🧑‍💻", restored["appearance_marker_history"])
        self.assertEqual(strip_prefix("🧑‍💻 Projeto", restored), "Projeto")

    def test_concurrent_config_change_is_not_overwritten(self):
        state = self.service.state()
        write_json(self.service.path, {"enabled": False})
        with self.assertRaisesRegex(ValueError, "outra janela"):
            self.service.save(state["settings"], state["revision"])
        self.assertEqual(read_json(self.service.path), {"enabled": False})

    def test_concurrent_config_change_blocks_undo(self):
        state = self.service.state()
        result = self.service.save(state["settings"], state["revision"])
        write_json(self.service.path, {"enabled": False})
        with self.assertRaises(ValueError): self.service.undo(result["state"]["revision"])

    def test_unsafe_or_invalid_symbols_are_rejected(self):
        settings = self.service.state()["settings"]
        for bad in ("", "O", "OK", "1", "\x1b[31m", "a\nb", "a b", "x" * 13, "\u202eevil", "[slug]", "\ud800"):
            with self.subTest(marker=repr(bad)), self.assertRaises(ValueError):
                validate_settings({**settings, "icons": {"running": bad}})
        self.assertEqual(validate_settings({**settings, "icons": {"running": "🧑‍💻"}})["icons"]["running"], "🧑‍💻")
        for value in (0, 7, True, "3"):
            with self.assertRaises(ValueError): validate_settings({**settings, "max_badges": value})

    def test_saved_styles_take_effect_in_hook_without_changing_editorial_title(self):
        server = FakeServer("[demo] Trabalho")
        payload = {"hook_event_name": "UserPromptSubmit", "session_id": "12345678-1234-1234-1234-123456789abc", "turn_id": "t"}
        handle(payload, server_factory=lambda _: server)
        state = self.service.state(); settings = state["settings"]
        settings.update(style="blue", icons={"running": "🧑‍💻"})
        self.service.save(settings, state["revision"])
        handle(payload, server_factory=lambda _: server)
        self.assertEqual(server.title, "🧑‍💻 [demo] Trabalho")
        self.assertEqual(Store().load(payload["session_id"]).base_title, "Trabalho")
        state = self.service.state(); settings = state["settings"]
        settings.update(style="emoji", icons={})
        self.service.save(settings, state["revision"])
        server.turn_status = "completed"; payload["hook_event_name"] = "Stop"
        handle(payload, server_factory=lambda _: server)
        self.assertEqual(server.title, "✅ [demo] Trabalho")


class PanelTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {"CODEX_HOME": self.temp.name}); self.env.start()
        self.server = PanelServer()
        self.worker = threading.Thread(target=self.server.serve_forever, daemon=True); self.worker.start()

    def tearDown(self):
        self.server.shutdown(); self.server.server_close(); self.worker.join()
        self.env.stop(); self.temp.cleanup()

    def request(self, path, body=None, headers=None):
        combined = {"X-Thread-State-Token": self.server.token}
        if body is not None: combined["Content-Type"] = "application/json"
        combined.update(headers or {})
        req = Request(self.server.origin + path, data=json.dumps(body).encode() if body is not None else None, headers=combined)
        return urlopen(req, timeout=3)

    def test_assets_and_authenticated_settings_roundtrip(self):
        with self.request("/") as response:
            self.assertIn(b"picker-search", response.read())
            self.assertIn("frame-ancestors 'none'", response.headers["Content-Security-Policy"])
        with self.request("/api/state") as response: state = json.load(response)
        state["settings"]["style"] = "green"
        with self.request("/api/settings", {"settings": state["settings"], "revision": state["revision"]}) as response:
            result = json.load(response)
        self.assertEqual(result["state"]["settings"]["style"], "green")

    def test_rejects_foreign_origin_host_and_missing_token(self):
        for headers in ({"Origin": "https://evil.example"}, {"Host": "evil.example"}, {"X-Thread-State-Token": ""}):
            with self.subTest(headers=headers), self.assertRaises(HTTPError) as exc:
                self.request("/api/state", headers=headers)
            self.assertEqual(exc.exception.code, 403)
        self.assertFalse(self.server.appearance.path.exists())

    def test_traversal_and_invalid_mutations_do_not_write(self):
        with self.assertRaises(HTTPError): self.request("/../config.json")
        with self.assertRaises(HTTPError): self.request("/api/settings", {"settings": None})
        self.assertFalse(self.server.appearance.path.exists())


if __name__ == "__main__": unittest.main()
