from __future__ import annotations

import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import uuid

from .events import SUPPORTED_EVENTS
from .store import Store, codex_home, lock, read_json, write_json


def install(uninstall: bool = False) -> None:
    path = codex_home() / "hooks.json"; store = Store()
    store.snapshot("before-uninstall" if uninstall else "before-install")
    with lock("install"):
        data = read_json(path, {"hooks": {}})
        script = str((Path(__file__).parent.parent / "thread_state.py").resolve())
        command = subprocess.list2cmdline([sys.executable, script, "hook"]) if os.name == "nt" else shlex.join([sys.executable, script, "hook"])
        for name in sorted(SUPPORTED_EVENTS):
            kept = []
            for group in data.setdefault("hooks", {}).get(name, []):
                handlers = [x for x in group.get("hooks", []) if x.get("statusMessage") != "Thread State"]
                if handlers: kept.append({**group, "hooks": handlers})
            if not uninstall:
                kept.append({"hooks": [{"type": "command", "command": command, "async": True,
                    "timeout": 3 if name == "Interrupt" else 30, "statusMessage": "Thread State"}]})
            if kept: data["hooks"][name] = kept
            else: data["hooks"].pop(name, None)
        if path.exists():
            store.root.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, store.root / f"hooks-backup-{uuid.uuid4().hex}.json")
        write_json(path, data)
