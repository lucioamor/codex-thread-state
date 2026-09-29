from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import uuid


class Journal:
    def __init__(self, path: Path): self.path = path

    def append(self, phase: str, *, batch: str, operation: str | None = None, **data) -> str:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        operation = operation or str(uuid.uuid4())
        row = {"at": datetime.now(timezone.utc).isoformat(), "operation": operation,
               "batch": batch, "phase": phase, **data}
        with self.path.open("a", encoding="utf-8") as output:
            output.write(json.dumps(row, ensure_ascii=False) + "\n")
        return operation

    def rows(self) -> list[dict]:
        if not self.path.exists(): return []
        return [json.loads(line) for line in self.path.read_text(encoding="utf-8").splitlines() if line.strip()]

    def applied(self) -> list[dict]:
        return [x for x in self.rows() if x.get("phase") == "applied"]
