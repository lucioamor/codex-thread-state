# Thread State

**Know where every Codex thread stands.**

Deterministic status badges for Codex threads. Thread State prefixes conversation
titles with compact state indicators while preserving existing project tags:

```text
🔵 [cue] Review visitor parser
🟡 🏁 [demo] Implement export pipeline
🚩 [demo] Investigate build failure
✅ [demo] Explain the configuration
```

Product: **Thread State** · Optional skill: **`/thread-state`** · Repository slug:
**`lucioamor/codex-thread-state`**. The repository identity is the intended public
destination; this checkout does not establish that a GitHub repository exists.

## Status and scope

Experimental 0.1.0. This repository packages lessons from a local Windows
prototype, with a smaller, structured-state runtime. It is **not an official
OpenAI component**. Local automated tests do not prove lifecycle hook delivery
in every Codex version. In particular, quota-error delivery and desktop hook
trust/reload must be checked on the installed host.

This checkout does not replace an existing installation automatically. The old
`thread-status` installation and its private logs remain outside this repository.

## How it works

```text
Codex lifecycle event
    -> command hook receives JSON on stdin
    -> Python reads the affected thread and goal
    -> deterministic state mapping
    -> App Server thread/name/set
    -> local mutation ledger and readback verification
```

There is no timer, background monitoring service, scheduled task, LLM classifier,
prompt injection, model-generated title, or API key requirement added by Thread
State. A hook starts a short-lived local App Server process; this process is an
RPC service, not a model invocation. Existing Codex authentication/configuration
still applies. Runtime RPC methods are allowlisted in code; generation methods
such as `turn/start` are rejected.

The script uses Python's standard library. It calls `initialize`, `thread/read`,
`thread/turns/list`, `thread/goal/get`, and `thread/name/set`. It returns no context
or continuation instruction to the model. Maintaining or discussing the project
with an agent consumes normal conversational inference; executing the script
does not request inference.

## Do I need the skill?

No. Hooks and Python perform automatic updates without loading `SKILL.md`.
`/thread-state` is an optional operator guide for setup, inspection, diagnostics
and removal. The skill does not create a native built-in slash command; its
availability and invocation UI depend on the Codex host.

| Component | Responsibility |
| --- | --- |
| Generated `hooks.json` entries | Invoke Python on lifecycle events |
| `thread_state.py` | Classification, local RPC, title writes and audit records |
| `skills/thread-state/SKILL.md` | Optional instructions for maintenance on request |
| Local state directory | Configuration, hook backups, event logs and ledger |

The project may later be packaged as a plugin with hooks and an optional skill.
This first release is a standalone source repository, not an installed marketplace
plugin.

## Requirements

- Python 3.11 or newer.
- A native Codex executable with App Server and the RPC methods listed above.
- A Codex host supporting trusted command lifecycle hooks.
- Permission to read and update local conversation titles.

Windows is the locally tested platform. POSIX locking and executable discovery
are implemented but have not been validated on macOS/Linux. `thread/turns/list`
is experimental; protocol compatibility can change. The host must support
`app-server --listen stdio://`.

## Quick start

From this repository:

```sh
python -m unittest discover -s tests -v
python thread_state.py inspect THREAD_UUID
python thread_state.py inspect THREAD_UUID --apply
python thread_state.py install
```

`inspect` is a dry run unless `--apply` is present. Use an actual conversation UUID.
Installation merges three handlers into `$CODEX_HOME/hooks.json` (default:
`~/.codex/hooks.json`) and saves a uniquely named backup. Existing unrelated
handlers are preserved. Reinstalling replaces only handlers marked `Thread State`.
Keep the checkout and the Python interpreter at their installed paths.

Then review and trust the exact definitions using **`/hooks` in the Codex CLI**.
The documentation guarantees that review path for CLI; availability in desktop
may vary. New or changed definitions require renewed trust. Restart/reload the
host as needed and verify a real event in `events.jsonl`; writing a JSON file is
not proof that the host loaded or trusted it. Do not bypass hook trust.

Optional editable CLI installation:

```sh
python -m pip install -e .
thread-state inspect THREAD_UUID
```

Pip may download build tooling. Running the source file directly needs no package
installation. To expose the optional skill, copy `skills/thread-state` to the
host's personal skills directory; runtime operation does not require that copy.

## Configuration

Create `$CODEX_HOME/thread-state/config.json` if necessary:

```json
{
  "codexExecutable": "C:/path/to/native/codex.exe",
  "maxTitleChars": 60
}
```

Executable lookup checks the configured path, `CODEX_CLI_PATH`, PATH, and the
Windows desktop installation. Shell wrappers (`.cmd`, `.bat`) are skipped.
No project paths, account credentials or personal conversations are bundled.
Project tags already present in titles are preserved; new tags are not inferred.

## State taxonomy and precedence

| Badge | State | Evidence |
| --- | --- | --- |
| 🔵 | running | In-progress turn, or matching UserPromptSubmit event |
| 🚩 | usage_limited | Structured failed-turn error with a recognized usage/quota marker, or formal goal state |
| 🔴 | failed / blocked | Other failed turn, or formal blocked goal |
| ⏸️ | interrupted / paused | Interrupted/cancelled turn, matching Interrupt event, or paused goal |
| ⏳ | budget_limited | Formal goal budget exhausted |
| 🟡 | pending | Formal goal remains active |
| ✅ | completed | Formal completed goal, otherwise completed turn |
| ⚪ | unknown | Insufficient structured state |
| 🏁 | goal modifier | A formal goal object exists |

Priority: active turn -> failed/interrupted turn -> formal goal -> completed
turn -> unknown. Recognized hook events override the corresponding start/interrupt
state after checking the event turn ID, when provided.

**A completed turn does not prove that the user's whole task is complete.**
The badge describes runtime state. Without a formal goal, a response containing
unfinished work can still have a completed turn. The code deliberately does not
read prose for phrases such as “done” or “falta validar”: those rules are
deterministic but semantically unreliable. Account quota and goal token budgets
are separate states. HTTP rate limiting alone is not account quota exhaustion.

Unlike the prototype, mentioning `/goal` in a prompt does not establish a formal
goal, and recurring monitoring is not inferred from response text.

## Events and compatibility boundaries

- `UserPromptSubmit`: request an update for the affected thread.
- `Stop`: inspect persisted terminal state after a normal response.
- `Interrupt`: reflect an explicit interruption.

`Stop` is not a token-stream or every-commentary callback. The script does not
assume that every host emits it on a quota failure. A process crash, missing
event, untrusted hook or event received before state persistence can leave a stale
badge. There is no polling fallback enabled here.

Turn IDs prevent stale events from overwriting newer turns when the host provides
them. Events without a turn ID have weaker ordering guarantees. A `Stop` event
with an in-progress persisted turn is skipped instead of guessing completion.
The handler fails open: it logs failures and exits successfully without blocking
the conversation. Interrupt's three-second host timeout may end a slow lookup.

## Title preservation, concurrency and rollback

- Updates target the event's UUID directly, not a recent-conversation scan.
- Kernel locks serialize work per thread and release on process exit.
- Title/turn/goal are reread before mutation; a changed snapshot is skipped.
- The title API has no compare-and-swap guarantee; a residual race remains.
- Known badge prefixes are replaced idempotently. Existing `[project]` text stays.
- Empty, control-character and overlength titles are skipped, never truncated.
- A 60-character conservative limit comes from the original local observation;
  server counting can differ for Unicode. Readback detects mismatches.
- An intent record is written before mutation and an applied record after
  readback. Crashes can leave an intent with no applied record; audit it before
  retrying or restoring.

To undo a change, inspect `changes.jsonl`, select the relevant applied operation,
and restore `oldTitle` through the supported title interface **only if** the
current title still equals that operation's `actualTitle`. Later edits must be
preserved. Automated rollback is not included in 0.1.0. Removing hooks does not
remove badges, logs or backups.

```sh
python thread_state.py uninstall
```

This removes only handlers marked `Thread State`, preserves other hooks and saves
a backup. Disable hooks before moving/deleting this checkout. Runtime data lives
outside Git under `$CODEX_HOME/thread-state/`:

| File | Contents |
| --- | --- |
| `config.json` | Optional runtime settings |
| `changes.jsonl` | Thread IDs, old/new titles and mutation outcomes |
| `events.jsonl` | Hook outcomes and diagnostics |
| `*.lock` | Reusable kernel lock files |
| `hooks-backup-*.json` | Previous hook configuration |

These files can contain private metadata and should not be published. Thread
State has no telemetry; the spawned Codex executable retains its own behavior.

## Migrating from the local thread-status prototype

The old prototype is not a dependency. Before enabling this release, disable its
three hook handlers and any `CodexThreadStatus` scheduled task. The installer
intentionally does not remove unrecognized/legacy handlers. Preserve old ledgers;
this release uses a separate `thread-state` directory. Run a dry run, install,
trust, then verify a real event. Never leave both implementations active.

Lessons carried forward: a skill is not a scheduler; pythonw alone does not stop
child console allocation; repeated App Server launches are unnecessary when idle;
events are preferable to polling; completed turns and completed tasks differ;
tests of a classifier do not validate lifecycle delivery; reversibility requires
preserving titles before writes, not just after them.

## Validation and release readiness

Tests cover state precedence, quota versus rate limits, prose independence,
idempotence, Unicode titles, overlength skips, dry runs, mutation journaling,
stale events, lock contention, generation-RPC rejection, and reversible hook
configuration merging. Tests use isolated temporary configuration and fake RPC
responses; they do not start a model or modify real titles.

Before a public release, validate trusted desktop lifecycle events, quota failures,
concurrent user edits, hook timeouts and supported OS versions. A synthetic event
is useful but not a substitute for these checks. See `CHANGELOG.md` for scope.

## Publishing and upstream contributions

Intended GitHub destination: `lucioamor/codex-thread-state`. Local Git initialization
and a commit do not create a hosted repository or publish it. No push is required
to use this checkout. A distributable plugin can later bundle hooks plus the
optional `/thread-state` operator skill.

For upstream, propose structured thread status and reliable terminal events in
the open Codex App Server before coupling presentation to editable titles.
Desktop sidebar source availability and contribution policies must be checked
before proposing a UI PR. No upstream PR or public repository is created here.

Reference contracts (review compatibility against the installed version):

- [Codex hooks](https://learn.chatgpt.com/docs/hooks)
- [Codex App Server](https://learn.chatgpt.com/docs/app-server)
- [Codex plugins](https://learn.chatgpt.com/docs/plugins)
- [Codex open-source components](https://learn.chatgpt.com/docs/open-source)

## Authorship and maintenance

This project was created by [Lucio Amorim](https://linkedin.com/in/lucioamorim).

When reusing, redistributing, or citing this work, keep the attribution credits and include a link to this repository.

Licensed under Apache License 2.0; see `LICENSE` and `NOTICE`.
