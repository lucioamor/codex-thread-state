---
name: thread-state
description: Configure, inspect, troubleshoot or uninstall Thread State deterministic Codex title badges when requested. Not part of automatic per-turn execution.
---

# Thread State

Read the repository README before installation or migration. Run the repository's
`thread_state.py` CLI with Python 3.11+. Start with `doctor` and `preview`.
`inspect THREAD_ID` is a dry run; `--apply` writes the title. Hooks invoke the
script directly without this skill.

For appearance controls, run `python thread_state.py panel`. Open the returned
loopback URL in the Codex browser panel (right or bottom) when available, or use
`panel --open` for the default browser. Keep the process running while the user
uses the panel. It supports themes, an offline symbol/emoji picker, preview,
save and undo. Saving changes future hook events; it does not bulk-rename chats.

Never add an agent turn, model call, semantic LLM classification or periodic
poller to update badges. A completed turn is not proof of completed work. Use
structured goal state to identify pending work. Do not interpret quoted prose.

Review existing hooks before installation. Do not run the legacy thread-status
hooks alongside Thread State. Preserve unrelated hooks. Do not bypass trust.
Use `snapshot create` before UX experiments. Prefer rollback without `--force` so
concurrent editorial renames become explicit conflicts. Never edit Codex databases
directly. Use `migrate --from-legacy` only after reviewing the old ledger/hooks.

Report synthetic tests separately from actual trusted lifecycle execution.
