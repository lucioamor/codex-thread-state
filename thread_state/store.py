from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import time
import uuid

from .model import ThreadRecord


def codex_home() -> Path:
    return Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex")))


def state_root() -> Path:
    return codex_home() / "thread-state"


def read_json(path: Path, default=None):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f"{path.name}.{uuid.uuid4().hex}.tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


@contextmanager
def lock(name: str, timeout: float = 5):
    state_root().mkdir(parents=True, exist_ok=True)
    with (state_root() / f"{name}.lock").open("a+b") as handle:
        if handle.seek(0, 2) == 0: handle.write(b"0"); handle.flush()
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
                if time.monotonic() >= deadline: raise TimeoutError("thread-state lock busy")
                time.sleep(.05)
        try: yield
        finally:
            handle.seek(0)
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


class Store:
    def __init__(self, root: Path | None = None):
        self.root = root or state_root()
        self.threads = self.root / "threads"
        self.snapshots = self.root / "snapshots"
        self.profiles = self.root / "profiles"

    def load(self, thread_id: str) -> ThreadRecord | None:
        value = read_json(self.threads / f"{thread_id}.json")
        return ThreadRecord.from_dict(value) if value else None

    def save(self, record: ThreadRecord) -> None:
        write_json(self.threads / f"{record.thread_id}.json", record.to_dict())

    def all(self) -> list[ThreadRecord]:
        return [ThreadRecord.from_dict(read_json(path)) for path in sorted(self.threads.glob("*.json"))] if self.threads.exists() else []

    def snapshot(self, label: str) -> Path:
        safe = "".join(c if c.isalnum() or c in "-_" else "-" for c in label).strip("-") or "snapshot"
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        path = self.snapshots / f"{timestamp}-{safe}.json"
        write_json(path, {"createdAt": datetime.now(timezone.utc).isoformat(), "label": label,
                          "threads": [x.to_dict() for x in self.all()]})
        return path

    def find_snapshot(self, name: str) -> Path:
        candidate = Path(name)
        if candidate.exists(): return candidate
        matches = sorted(self.snapshots.glob(f"*-{name}.json"))
        if not matches: raise FileNotFoundError(f"snapshot not found: {name}")
        return matches[-1]
