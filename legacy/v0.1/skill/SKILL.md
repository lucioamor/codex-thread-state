---
name: thread-status
description: Review Codex conversation lifecycle, goal state, failures, usage limits, declared completion, and pending validation; propose, apply, audit, or reverse compact emoji status prefixes in thread titles. Use when the user asks to identify unfinished chats, mark recent conversations, maintain title status, or undo those title changes.
---

# Thread status

Use the Codex app thread tools as the supported read/write interface. Never edit `state_*.sqlite`, `goals_*.sqlite`, rollout JSONL, or other Codex internals to rename a thread. A read-only goal query may supplement evidence when no supported goal-state tool is available; label that dependency as internal and potentially unstable.

The title convention is `<state> <🏁 when goal evidence exists> [project] original title`. Preserve existing `[project]` prefixes. Do not replace the user's wording, repair truncation by guessing, or infer a project solely from a similar title. Read [references/taxonomy.md](references/taxonomy.md) whenever classifying or applying titles.

## Modes

- **Audit/dry run:** list conversations, inspect recent turns and goal evidence, generate proposals and a report; do not rename.
- **Apply:** first complete the audit, save a ledger containing thread ID, observed current title and runtime status, proposed title, evidence, turn ID, and response hash. Re-read the current title/status and, for conversations that were active during review, the latest turn immediately before mutation. Skip changed or ambiguous entries. Apply with `set_thread_title`, then verify by listing the threads again.
- **Rollback:** read the apply results and ledger. Use `scripts/rollback_plan.py`; restore `oldTitle` only when the current title still equals the recorded `actualTitle` and the original is within the supported 60-character limit. Otherwise skip it to preserve later user edits or avoid irreversible truncation. Verify afterward and save rollback results beside the apply ledger.

Use `scripts/thread_status.py` for deterministic classification and report generation. Its semantic reviews are bound to the latest turn ID and SHA-256 of the final response, so resumed or edited conversations invalidate stale judgments. Use `scripts/make_ledger.py` to create the mutation ledger from reviewed proposals and the fresh thread listing.

## Evidence rules

Runtime evidence has priority: an in-progress turn is 🔵; a failed latest turn with a structured usage-limit error is 🚩; another failed turn is 🔴; an interrupted turn is ⏸️. Do not label credit exhaustion by searching user text or assistant prose.

Formal current goal state comes next. Keep usage limits (`usage_limited`) distinct from goal token budget (`budget_limited`). A stale goal row older than a resumed latest turn is historical evidence and must not override the current turn.

Semantic review is last. A completed turn only means the turn ended. Use ✅ only when the requested deliverable was declared complete in the examined scope. Use 🟡 when required validation or material work remains, 🔴 for an explicit blocker, 🔁 for a recurring monitor between cycles, and ⚪ when one recent turn is insufficient.

🏁 is independent of status. Add it only with formal goal state or explicit evidence that a goal governed the work. Merely mentioning “goal”, reading a `goal-*.md`, or proposing `/goal` is insufficient.

## Safety and lifecycle

Before applying, preserve a JSON ledger outside the skill folder in the current task output directory or another user-approved durable location. A skill update must never erase prior ledgers. Do not auto-apply titles to archived ChatGPT conversations, titles containing control characters, or original/proposed titles above the observed 60-character mutation limit. The supported title API truncates longer values, so changing them would not be fully reversible.

Automatic updates must remain outside the model loop. Do not ask the agent to classify or rename a thread after every response. The installed command hook invokes deterministic Python, reads structured App Server state, and writes through `thread/name/set`. It must not call `turn/start`, Responses, Chat Completions, an agent handler, or any model endpoint.

`Stop` covers normal turn termination, `Interrupt` covers user interruption, and `UserPromptSubmit` marks a newly active turn. A usage-limit failure is classified only when the persisted latest turn contains the structured runtime error. If a Codex version does not emit `Stop` on a quota failure, record that as a runtime compatibility gap; do not add inference or high-frequency polling to guess the state.

At the end of an apply run, report counts for applied, skipped, failed, and verified, plus the ledger path. At the end of rollback, report restored and skipped titles and why.

## Deterministic automatic runtime

The preferred runtime is `scripts/hook.py`, registered in the user or plugin `hooks.json` for `UserPromptSubmit`, `Stop`, and `Interrupt`. The hook receives `session_id`, invokes the supported App Server, classifies with deterministic branches, writes through `thread/name/set`, and appends to `$CODEX_HOME/thread-status/changes.jsonl`. It does not use this skill or a model at runtime.

The division of responsibility is intentional:

- hook: lifecycle trigger;
- Python: deterministic state machine and title mutation;
- App Server: supported read/write boundary;
- skill: optional operator instructions for audit, installation, rollback, and maintenance.

The former scheduled-task poller is retained only as a reversible compatibility fallback. Do not run it together with the hooks. Install it only when lifecycle hooks are unavailable, and use a conservative interval. `scripts/uninstall_daemon.ps1` removes that fallback.

Before enabling hooks, run `python scripts/daemon.py --once --dry-run --thread-id <id>` and a synthetic event through `scripts/hook.py`. Review and trust the exact hook definition with `/hooks`; changed definitions require renewed trust. Update `projectRoots` for stable project tags and keep the 60-character limit.
