from __future__ import annotations

import json
import os
from pathlib import Path
import queue
import shutil
import subprocess
import threading
import time

METHODS = {"initialize", "thread/read", "thread/turns/list", "thread/goal/get", "thread/name/set"}


def executable(config: dict) -> str:
    candidates = [config.get("codexExecutable"), os.environ.get("CODEX_CLI_PATH"), shutil.which("codex")]
    if os.name == "nt":
        folder = Path(os.environ.get("LOCALAPPDATA", "")) / "OpenAI/Codex/bin"
        candidates += [str(x) for x in sorted(folder.glob("*/codex.exe"), key=lambda p: p.stat().st_mtime, reverse=True)]
    for candidate in candidates:
        if candidate and Path(candidate).is_file() and Path(candidate).suffix.lower() not in (".cmd", ".bat"):
            return str(candidate)
    raise FileNotFoundError("Set codexExecutable or CODEX_CLI_PATH to the native Codex executable")


class Server:
    def __init__(self, config: dict):
        self.seq = 0; self.responses = queue.Queue()
        self.process = subprocess.Popen([executable(config), "app-server", "--listen", "stdio://"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
            encoding="utf-8", creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        threading.Thread(target=self._read, daemon=True).start()
        self.call("initialize", {"clientInfo": {"name": "thread_state", "version": "0.2.0"},
                                 "capabilities": {"experimentalApi": True}})
        self._send({"method": "initialized"})

    def _read(self):
        for line in self.process.stdout:
            try: self.responses.put(json.loads(line))
            except ValueError: pass
        self.responses.put(None)

    def _send(self, value): self.process.stdin.write(json.dumps(value) + "\n"); self.process.stdin.flush()

    def call(self, method, params):
        if method not in METHODS: raise ValueError("RPC method is not allowed")
        self.seq += 1; current = self.seq
        self._send({"id": current, "method": method, "params": params})
        deadline = time.monotonic() + 5
        while True:
            try: message = self.responses.get(timeout=max(.001, deadline - time.monotonic()))
            except queue.Empty: raise TimeoutError("App Server response timeout") from None
            if message is None: raise RuntimeError("App Server closed output")
            if message.get("id") == current:
                if "error" in message: raise RuntimeError(str(message["error"]))
                return message.get("result", {})
            if time.monotonic() >= deadline: raise TimeoutError("App Server response timeout")

    def close(self):
        if self.process.poll() is None:
            self.process.terminate()
            try: self.process.wait(timeout=2)
            except subprocess.TimeoutExpired: self.process.kill(); self.process.wait(timeout=2)
        self.process.stdin.close(); self.process.stdout.close()

    def __enter__(self): return self
    def __exit__(self, *_): self.close()
