"""Update one Codex thread title from a lifecycle hook; no model calls."""
from __future__ import annotations

import json
import sys
import time

import daemon


def main() -> int:
    try:
        event = json.load(sys.stdin)
        thread_id = event.get('session_id')
        event_name = event.get('hook_event_name', 'unknown')
        if not thread_id:
            daemon.log(f'hook_skip event={event_name} reason=no_session_id')
            return 0

        # Give the main App Server a brief moment to persist the terminal turn.
        if event_name in ('Stop', 'Interrupt'):
            time.sleep(0.5)

        config = daemon.load_json(daemon.CONFIG_PATH, {})
        lock = daemon.acquire_lock()
        if not lock:
            daemon.log(f'hook_skip event={event_name} thread={thread_id} reason=busy')
            return 0
        server = None
        try:
            server = daemon.AppServer(config)
            rows = daemon.cycle(server, config, only_ids={thread_id})
            changed = bool(rows and rows[0].get('changed'))
            daemon.log(f'hook_ok event={event_name} thread={thread_id} changed={changed}')
        finally:
            if server:
                server.close()
            lock.close()
        return 0
    except Exception as exc:
        daemon.log(f'hook_error {type(exc).__name__}: {exc}')
        return 0


if __name__ == '__main__':
    raise SystemExit(main())
