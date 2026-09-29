# Validation — v0.2 · 2026-09-28

Executed on the local Windows host with Python 3.11:

- `python -m unittest discover -s tests -v`: 23 tests passed (10 v0.1 regressions + 13 v0.2 tests).
- Codex skill validator: `skills/thread-state` is valid.
- `preview` and `doctor`: CLI smoke checks passed.
- The v0.2 migration imported 8 legacy thread records after an automatic snapshot.
- Seven v0.2 hook definitions were installed, reviewed and trusted through the
  native Codex hook browser without bypassing trust.
- One explicitly synthetic `PostToolUse` event exercised App Server mutation,
  intent/applied journal and readback successfully on the current thread.
- The legacy skill was archived outside the active skills directory; its runtime
  ledger and logs remain preserved.

Not executed: automatic start/stop/interrupt delivery after desktop reload,
quota failure delivery, or macOS/Linux integration.

The synthetic event is not proof of real lifecycle delivery. The desktop session
that performed installation must reload before its automatic hooks use the new
configuration; observe the next real prompt/stop after reload.
