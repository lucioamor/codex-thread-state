"""Deterministic Codex thread-title monitor using the supported App Server API."""
from __future__ import annotations

import argparse
import html
import json
import msvcrt
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(os.environ.get('CODEX_HOME', str(Path.home() / '.codex'))) / 'thread-status'
CONFIG_PATH = ROOT / 'config.json'
STATE_PATH = ROOT / 'state.json'
LEDGER_PATH = ROOT / 'changes.jsonl'
LOG_PATH = ROOT / 'daemon.log'
LOCK_PATH = ROOT / 'daemon.lock'
PID_PATH = ROOT / 'daemon.pid'

ICONS = ('🔵', '🚩', '⏳', '🔴', '🟡', '⏸️', '✅', '🔁', '⚪', '🏁')
USAGE_MARKERS = ('hit your usage limit', 'usage_limit_reached', 'usage limit exceeded',
                 'insufficient_quota', 'credit balance exhausted')
PENDING_MARKERS = ('falta validar', 'ainda precisa ser valid', 'ainda precisam ser valid',
                   'permanece pendente', 'ficou pendente', 'só resta ',
                   'não pôde ser concluíd', 'não foi possível concluir',
                   'goal permanece incompleto', 'objetivo permanece incompleto',
                   'precisa ser feito manualmente')
BLOCKED_MARKERS = ('goal marcado como bloqueado', 'objetivo bloqueado', 'não consigo prosseguir')
COMPLETE_MARKERS = ('objetivo concluído', 'goal concluído', 'goal marcado como complete',
                    'implementação concluída', 'implementacao concluida', 'está finalizado',
                    'está finalizada', 'tarefa concluída', 'entrega concluída')

def log(message: str) -> None:
    ROOT.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).isoformat()
    with LOG_PATH.open('a', encoding='utf-8', newline='\n') as f:
        f.write(f'{stamp} {message}\n')

def find_codex(config):
    candidates = [config.get('codexExecutable'), os.environ.get('CODEX_CLI_PATH'),
                  shutil.which('codex.exe'), shutil.which('codex')]
    local = Path(os.environ.get('LOCALAPPDATA', '')) / 'OpenAI' / 'Codex' / 'bin'
    if local.exists():
        candidates.extend(str(p) for p in sorted(local.glob('*/codex.exe'), key=lambda p: p.stat().st_mtime, reverse=True))
    for candidate in candidates:
        if candidate and Path(candidate).is_file(): return str(Path(candidate))
    raise FileNotFoundError('codex executable not found')

class AppServer:
    def __init__(self, config):
        # codex.exe is a console application.  A pythonw parent does not by
        # itself prevent Windows from allocating a visible console for the
        # child, so every polling cycle must explicitly suppress that window.
        creationflags = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
        self.proc = subprocess.Popen(
            [find_codex(config), 'app-server', '--stdio'], stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            text=True, encoding='utf-8', bufsize=1,
            creationflags=creationflags)
        self.seq = 0
        self.call('initialize', {'clientInfo': {'name': 'thread_status_daemon',
            'title': 'Thread Status Daemon', 'version': '1.0.0'},
            'capabilities': {'experimentalApi': True}})
        self.notify('initialized', {})

    def notify(self, method, params):
        self.proc.stdin.write(json.dumps({'method': method, 'params': params}) + '\n')
        self.proc.stdin.flush()

    def call(self, method, params):
        self.seq += 1
        wanted = self.seq
        self.proc.stdin.write(json.dumps({'method': method, 'id': wanted, 'params': params}) + '\n')
        self.proc.stdin.flush()
        while True:
            line = self.proc.stdout.readline()
            if not line:
                raise RuntimeError('app-server closed its output')
            msg = json.loads(line)
            if msg.get('id') != wanted:
                continue
            if 'error' in msg:
                raise RuntimeError(f'{method}: {msg["error"]}')
            return msg.get('result', {})

    def close(self):
        if self.proc.poll() is None:
            self.proc.terminate()

def load_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (FileNotFoundError, json.JSONDecodeError):
        return default

def save_json(path: Path, value) -> None:
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    os.replace(tmp, path)

def strip_status(title: str) -> str:
    title = title or ''
    pattern = r'^(?:(?:' + '|'.join(map(re.escape, ICONS)) + r')\s+)+'
    return re.sub(pattern, '', title).strip()

def project_tag(thread, config) -> str | None:
    current = strip_status(thread.get('name') or '')
    match = re.match(r'^\[([^\]]+)\]', current)
    if match:
        return match.group(1)
    cwd = (thread.get('cwd') or '').replace('/', '\\').lower().rstrip('\\')
    mappings = sorted(config.get('projectRoots', {}).items(), key=lambda x: len(x[0]), reverse=True)
    for root, tag in mappings:
        if cwd.startswith(root.replace('/', '\\').lower().rstrip('\\')):
            return tag
    origin = ((thread.get('gitInfo') or {}).get('originUrl') or '').rstrip('/').removesuffix('.git')
    if origin:
        return origin.rsplit('/', 1)[-1].lower()
    return None

def base_title(thread) -> str:
    title = strip_status(thread.get('name') or '')
    title = re.sub(r'^\[[^\]]+\]\s*', '', title).strip()
    if title:
        return title
    prompt = html.unescape(thread.get('preview') or '')
    prompt = re.sub(r'^\s*/goal\s*', '', prompt, flags=re.I)
    for line in prompt.splitlines():
        clean = re.sub(r'[`*_#>]+', '', line).strip()
        if clean and not clean.lower().startswith(('# files mentioned', 'distinguish instructions')):
            return clean
    return 'Nova conversa'

def latest_turn(server: AppServer, thread_id: str):
    result = server.call('thread/turns/list', {'threadId': thread_id, 'limit': 1,
        'sortDirection': 'desc', 'itemsView': 'full'})
    data = result.get('data') or []
    return data[0] if data else None

def assistant_text(turn) -> str:
    if not turn:
        return ''
    messages = [x.get('text', '') for x in turn.get('items', []) if x.get('type') == 'agentMessage']
    return messages[-1] if messages else ''

def goal_info(server: AppServer, thread) -> tuple[dict | None, bool]:
    try:
        goal = server.call('thread/goal/get', {'threadId': thread['id']}).get('goal')
    except Exception:
        goal = None
    explicit = bool(re.match(r'^\s*/goal(?:\s|&|$)', html.unescape(thread.get('preview') or ''), re.I))
    return goal, bool(goal) or explicit

def classify(thread, turn, goal, has_goal):
    status = (turn or {}).get('status')
    error = json.dumps((turn or {}).get('error'), ensure_ascii=False).lower()
    text = assistant_text(turn).lower()
    tail = text[-800:]
    if status == 'inProgress': return 'running', 'latest_turn_in_progress'
    if status == 'failed':
        return ('usage_limited', 'structured_usage_limit') if any(x in error for x in USAGE_MARKERS) else ('failed', 'latest_turn_failed')
    if status in ('interrupted', 'cancelled'): return 'paused', 'latest_turn_interrupted'
    if goal:
        gs = goal.get('status')
        mapping = {'usage_limited':'usage_limited','budget_limited':'budget_limited',
                   'blocked':'blocked','paused':'paused','complete':'complete','active':'pending'}
        if gs in mapping: return mapping[gs], 'formal_goal_' + gs
    if '<heartbeat>' in tail: return 'monitoring', 'heartbeat_cycle'
    if any(x in tail for x in BLOCKED_MARKERS): return 'blocked', 'explicit_blocker'
    if any(x in tail for x in PENDING_MARKERS): return 'pending', 'explicit_pending_phrase'
    if any(x in text for x in COMPLETE_MARKERS): return 'complete', 'explicit_completion_phrase'
    if status == 'completed': return 'complete', 'completed_turn_default'
    if has_goal: return 'pending', 'goal_without_terminal_state'
    return 'unknown', 'no_terminal_evidence'

def compose(state, has_goal, tag, base, max_chars=60):
    icon = {'running':'🔵','usage_limited':'🚩','budget_limited':'⏳','failed':'🔴',
            'blocked':'🔴','pending':'🟡','paused':'⏸️','complete':'✅',
            'monitoring':'🔁','unknown':'⚪'}[state]
    prefix = icon + ' ' + ('🏁 ' if has_goal else '') + (f'[{tag}] ' if tag else '')
    room = max(1, max_chars - len(prefix))
    if len(base) > room:
        base = base[:max(1, room - 1)].rstrip() + '…'
    return prefix + base

def inspect(server, thread, config):
    turn = latest_turn(server, thread['id'])
    goal, has_goal = goal_info(server, thread)
    state, reason = classify(thread, turn, goal, has_goal)
    desired = compose(state, has_goal, project_tag(thread, config), base_title(thread), config.get('maxTitleChars', 60))
    return {'id': thread['id'], 'oldTitle': thread.get('name') or '', 'newTitle': desired,
            'state': state, 'goal': has_goal, 'reason': reason,
            'turnId': (turn or {}).get('id'), 'turnStatus': (turn or {}).get('status')}

def append_ledger(change):
    entry = {'at': datetime.now(timezone.utc).isoformat(), **change}
    with LEDGER_PATH.open('a', encoding='utf-8', newline='\n') as f:
        f.write(json.dumps(entry, ensure_ascii=False) + '\n')

def cycle(server, config, dry_run=False, only_ids=None):
    result = server.call('thread/list', {'limit': config.get('scanLimit', 50),
        'sortKey': 'updated_at', 'sortDirection': 'desc', 'archived': False})
    rows = []
    for thread in result.get('data', []):
        if thread.get('ephemeral'): continue
        if only_ids and thread['id'] not in only_ids: continue
        if not only_ids and thread.get('createdAt', 0) < config.get('manageCreatedAfter', 0): continue
        change = inspect(server, thread, config)
        change['changed'] = change['oldTitle'] != change['newTitle']
        rows.append(change)
        if change['changed'] and not dry_run:
            server.call('thread/name/set', {'threadId': thread['id'], 'name': change['newTitle']})
            append_ledger(change)
    return rows

def acquire_lock():
    ROOT.mkdir(parents=True, exist_ok=True)
    handle = LOCK_PATH.open('a+b')
    try:
        msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
    except OSError:
        handle.close(); return None
    return handle

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--once', action='store_true')
    p.add_argument('--dry-run', action='store_true')
    p.add_argument('--thread-id', action='append')
    args=p.parse_args()
    ROOT.mkdir(parents=True, exist_ok=True)
    config=load_json(CONFIG_PATH, {})
    lock=acquire_lock()
    if not lock:
        print(json.dumps({'status':'already_running'})); return 0
    PID_PATH.write_text(str(os.getpid()), encoding='ascii')
    server=None
    try:
        while True:
            try:
                if server is None:
                    server=AppServer(config)
                rows=cycle(server, config, args.dry_run, set(args.thread_id or []))
                if args.once:
                    print(json.dumps(rows, ensure_ascii=False, indent=2)); return 0
            except Exception as exc:
                log(f'cycle_error {type(exc).__name__}: {exc}')
                if server:
                    server.close()
                    server=None
                if args.once: raise
            time.sleep(config.get('pollSeconds', 10))
    finally:
        if server:
            server.close()
        PID_PATH.unlink(missing_ok=True)
        lock.close()

if __name__ == '__main__':
    raise SystemExit(main())
