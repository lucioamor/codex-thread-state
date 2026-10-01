"""Opt-in loopback-only appearance panel. No model calls or background poller."""
from __future__ import annotations

import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import secrets
from urllib.parse import urlsplit
import webbrowser

from .appearance import Appearance

ASSETS = Path(__file__).with_name("web")


class PanelServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, port=0, appearance=None):
        self.appearance = appearance or Appearance()
        self.token = secrets.token_urlsafe(32)
        super().__init__(("127.0.0.1", port), Handler)
        self.origin = f"http://127.0.0.1:{self.server_port}"
        self.url = f"{self.origin}/#{self.token}"


class Handler(BaseHTTPRequestHandler):
    def setup(self):
        super().setup()
        self.connection.settimeout(10)

    def log_message(self, *_):
        pass

    def respond(self, status, payload, kind="application/json; charset=utf-8"):
        data = json.dumps(payload, ensure_ascii=False).encode() if isinstance(payload, dict) else payload
        self.send_response(status)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; "
                         "img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'")
        self.end_headers()
        self.wfile.write(data)

    def authorized(self, api=False):
        if self.headers.get("Host") != urlsplit(self.server.origin).netloc:
            self.respond(403, {"error": "Host não permitido."}); return False
        origin = self.headers.get("Origin")
        if origin and origin != self.server.origin:
            self.respond(403, {"error": "Origem não permitida."}); return False
        if api and not hmac.compare_digest(self.headers.get("X-Thread-State-Token", ""), self.server.token):
            self.respond(403, {"error": "Abra o link gerado pelo comando panel."}); return False
        return True

    def do_GET(self):
        path = urlsplit(self.path).path
        if not self.authorized(api=path.startswith("/api/")): return
        if path == "/api/state":
            try: self.respond(200, self.server.appearance.state())
            except (ValueError, OSError): self.respond(500, {"error": "Não foi possível ler as preferências."})
            return
        files = {"/": ("index.html", "text/html"), "/app.js": ("app.js", "text/javascript"),
                 "/styles.css": ("styles.css", "text/css")}
        if path not in files:
            self.respond(404, {"error": "Página não encontrada."}); return
        filename, kind = files[path]
        self.respond(200, (ASSETS / filename).read_bytes(), kind + "; charset=utf-8")

    def do_POST(self):
        if not self.authorized(api=True): return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 65536 or self.headers.get_content_type() != "application/json":
                self.respond(400, {"error": "Pedido inválido."}); return
            payload = json.loads(self.rfile.read(length))
            if not isinstance(payload, dict): raise ValueError("Pedido inválido.")
            path = urlsplit(self.path).path
            if path == "/api/preview": result = self.server.appearance.preview(payload.get("settings"))
            elif path == "/api/settings": result = self.server.appearance.save(payload.get("settings"), payload.get("revision"))
            elif path == "/api/undo": result = self.server.appearance.undo(payload.get("revision"))
            else:
                self.respond(404, {"error": "Ação não encontrada."}); return
            self.respond(200, result)
        except (ValueError, TypeError, KeyError) as exc:
            self.respond(400, {"error": str(exc) or "Pedido inválido."})
        except OSError:
            self.respond(500, {"error": "Não foi possível salvar. As preferências anteriores foram preservadas quando possível."})


def serve(port=0, open_browser=False):
    with PanelServer(port) as server:
        print(json.dumps({"url": server.url, "mode": "local", "stop": "Ctrl+C"}), flush=True)
        if open_browser: webbrowser.open(server.url)
        try: server.serve_forever()
        except KeyboardInterrupt: pass
    return 0
