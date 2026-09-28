---
name: thread-state
description: Configure, inspect, troubleshoot or uninstall Thread State deterministic Codex title badges when requested. Not part of automatic per-turn execution.
---

# Thread State

Read the repository README before installation or migration. Run the repository's
`thread_state.py` CLI with Python 3.11+. `inspect THREAD_ID` is a dry run;
`--apply` writes the title. Hooks invoke the script directly without this skill.

Never add an agent turn, model call, semantic LLM classification or periodic
poller to update badges. A completed turn is not proof of completed work. Use
structured goal state to identify pending work. Do not interpret quoted prose.

Review existing hooks before installation. Do not run the legacy thread-status
hooks alongside Thread State. Preserve unrelated hooks. Do not bypass trust.
Inspect the local ledger before rollback; restore only if the current title
still matches the last applied title. Never edit Codex databases directly.

Report synthetic tests separately from actual trusted lifecycle execution.
