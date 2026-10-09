import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile

from thread_state.events import SUPPORTED_EVENTS
from thread_state import __version__

ROOT = Path(__file__).resolve().parents[1]


class PluginTests(unittest.TestCase):
    def test_hooks_preserve_manual_behavior(self):
        manifest = json.loads((ROOT / "plugin.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["version"], __version__)
        hooks = json.loads((ROOT / "hooks/hooks.json").read_text(encoding="utf-8"))["hooks"]
        previous = json.loads((ROOT / "docs/history/manual-hooks-2026-10-09.json").read_text(encoding="utf-8"))["hooks"]
        self.assertEqual(set(hooks), SUPPORTED_EVENTS)
        for name in SUPPORTED_EVENTS:
            current = dict(hooks[name][0]["hooks"][0])
            old = dict(previous[name][0]["hooks"][0])
            self.assertEqual(current.pop("command"), 'python "${PLUGIN_ROOT}/thread_state.py" hook')
            old.pop("command")
            self.assertEqual(current, old)

    def test_archive_runs_from_relocated_path_with_spaces(self):
        spec = importlib.util.spec_from_file_location("build_plugin", ROOT / "scripts/build_plugin.py")
        builder = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(builder)
        with tempfile.TemporaryDirectory(prefix="thread state plugin ") as directory:
            archive = builder.build(Path(directory) / "plugin.zip")
            with zipfile.ZipFile(archive) as package:
                names = package.namelist()
                self.assertTrue(all(not any(part in name.split("/") for part in
                    ("work", ".git", "__pycache__", "runtime")) for name in names))
                package.extractall(directory)
            result = subprocess.run([sys.executable, str(Path(directory) / "thread-state/thread_state.py"),
                                     "preview"], cwd=directory, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(result.stdout.strip())


if __name__ == "__main__":
    unittest.main()
