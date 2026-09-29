from __future__ import annotations

from datetime import datetime
import json
import uuid

from .journal import Journal
from .model import ThreadRecord
from .store import Store
from .writer import Writer


def plan(journal: Journal, *, operation: str | None = None, batch: str | None = None,
         since: str | None = None, thread_id: str | None = None) -> list[dict]:
    rows = journal.applied()
    if operation: rows = [x for x in rows if x.get("operation") == operation]
    if batch: rows = [x for x in rows if x.get("batch") == batch]
    if since:
        boundary = datetime.fromisoformat(since.replace("Z", "+00:00"))
        rows = [x for x in rows if datetime.fromisoformat(x["at"].replace("Z", "+00:00")) >= boundary]
    if thread_id: rows = [x for x in rows if x.get("threadId") == thread_id]
    return list(reversed(rows))


def apply(writer: Writer, rows: list[dict], *, force: bool = False) -> dict:
    batch = f"rollback-{uuid.uuid4()}"; restored = []; conflicts = []
    for row in rows:
        current = writer.current_title(row["threadId"])
        expected = row.get("actualTitle", row.get("newTitle"))
        if current != expected and not force:
            conflicts.append({"threadId": row["threadId"], "current": current, "expected": expected})
            continue
        restored.append(writer.write(row["threadId"], row["oldTitle"], batch=batch,
                                      reason=f"rollback:{row.get('operation')}", expected=None if force else current))
    return {"batch": batch, "restored": restored, "conflicts": conflicts}


def snapshot_rows(store: Store, name: str) -> list[dict]:
    value = json.loads(store.find_snapshot(name).read_text(encoding="utf-8"))
    rows = []
    for raw in value.get("threads", []):
        record = ThreadRecord.from_dict(raw)
        target = record.last_rendered or record.base_title
        rows.append({"threadId": record.thread_id, "oldTitle": target, "newTitle": target,
                     "actualTitle": None, "operation": f"snapshot:{name}"})
    return rows
