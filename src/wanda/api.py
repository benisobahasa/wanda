"""Zero-dependency JSON API (python standard library). Binds to localhost by default.

    wanda serve --port 8080
    curl -s localhost:8080/v1/normalize -d '{"text": "aku ora ngerti"}'

For production use behind your own authentication and TLS. A FastAPI version lives in
wanda.api_fastapi (optional dependency).
"""
from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Optional

from .service import Service

MAX_BODY = 64 * 1024


def make_server(host: str = "127.0.0.1", port: int = 8080, service: Optional[Service] = None, cors: bool = False) -> ThreadingHTTPServer:
    svc = service or Service()

    class Handler(BaseHTTPRequestHandler):
        def _send(self, status: int, body: dict) -> None:
            data = json.dumps(body, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            if cors:
                self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            self._send(*svc.handle("GET", self.path.split("?")[0]))

        def do_POST(self):
            length = int(self.headers.get("Content-Length") or 0)
            if length > MAX_BODY:
                return self._send(413, {"error": "request body too large"})
            try:
                payload = json.loads(self.rfile.read(length) or b"{}")
                if not isinstance(payload, dict):
                    raise ValueError
            except ValueError:
                return self._send(400, {"error": "body must be a JSON object"})
            self._send(*svc.handle("POST", self.path.split("?")[0], payload))

        def do_OPTIONS(self):
            self.send_response(204)
            if cors:
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.end_headers()

        def log_message(self, *args):  # no request logging: texts may be personal
            pass

    return ThreadingHTTPServer((host, port), Handler)


def serve(host: str = "127.0.0.1", port: int = 8080, service: Optional[Service] = None, cors: bool = False) -> None:
    srv = make_server(host, port, service, cors)
    print(f"Wanda API on http://{host}:{port}  (Ctrl+C to stop)")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        srv.server_close()
