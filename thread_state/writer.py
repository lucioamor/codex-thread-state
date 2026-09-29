from __future__ import annotations

import uuid

from .journal import Journal


class Writer:
    """The sole title mutation boundary."""
    def __init__(self, server, journal: Journal): self.server, self.journal = server, journal

    def current_title(self, thread_id: str) -> str:
        return self.server.call("thread/read", {"threadId": thread_id, "includeTurns": False})["thread"].get("name") or ""

    def write(self, thread_id: str, desired: str, *, batch: str, reason: str,
              dry_run: bool = False, expected: str | None = None, journal: bool = True) -> dict:
        current = self.current_title(thread_id)
        if expected is not None and current != expected:
            raise ValueError("title changed concurrently; skipped")
        result = {"id": thread_id, "oldTitle": current, "newTitle": desired, "changed": current != desired}
        if dry_run or current == desired: return result
        operation = str(uuid.uuid4())
        if journal:
            self.journal.append("intent", operation=operation, batch=batch, threadId=thread_id,
                                oldTitle=current, newTitle=desired, reason=reason)
        self.server.call("thread/name/set", {"threadId": thread_id, "name": desired})
        actual = self.current_title(thread_id)
        if journal:
            self.journal.append("applied", operation=operation, batch=batch, threadId=thread_id,
                                oldTitle=current, newTitle=desired, actualTitle=actual, reason=reason)
        if actual != desired: raise ValueError("title readback mismatch; inspect journal")
        return {**result, "operation": operation if journal else None, "actualTitle": actual,
                "journaled": journal}
