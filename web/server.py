#!/usr/bin/env python3
"""Local NestAgent web console using only Python stdlib."""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
import socket
import sys
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 18080
NOT_FOUND = "not found"


def _ensure_project_root() -> Path:
    root = Path(__file__).resolve().parents[1]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    os.environ.setdefault("NESTAGENT_ROOT", str(root))
    return root


PROJECT_ROOT = _ensure_project_root()
STATIC_ROOT = Path(__file__).resolve().parent / "static"


def _port_available(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind((host, port))
        except OSError:
            return False
    return True


def choose_port(host: str, requested: int) -> int:
    """Return requested port if free, or the next free high port."""
    if requested == 0:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind((host, 0))
            return int(sock.getsockname()[1])

    if _port_available(host, requested):
        return requested

    for port in range(max(requested + 1, 18081), 65000):
        if _port_available(host, port):
            return port
    raise RuntimeError("no available TCP port found")


class NestAgentHandler(BaseHTTPRequestHandler):
    server_version = "NestAgentWeb/0.1"

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/":
            self._serve_static("index.html")
            return
        if parsed.path.startswith("/static/"):
            self._serve_static(parsed.path.removeprefix("/static/"))
            return
        if parsed.path == "/api/ready":
            self._send_json(self._harness().readiness())
            return
        if parsed.path == "/api/tools":
            self._send_json(self._harness().registry.list_specs())
            return
        if parsed.path == "/api/models":
            from llm.ollama_client import OllamaClient

            try:
                client = OllamaClient(self._settings().ollama)
                self._send_json({"models": client.list_models()})
            except Exception as exc:  # noqa: BLE001 - API boundary returns errors as JSON.
                self._send_json({"error": str(exc)}, HTTPStatus.BAD_GATEWAY)
            return
        self._send_json({"error": NOT_FOUND}, HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path != "/api/run":
            self._send_json({"error": NOT_FOUND}, HTTPStatus.NOT_FOUND)
            return

        try:
            payload = self._read_json()
            request = str(payload.get("request", "")).strip()
            use_planner = bool(payload.get("use_planner", True))
            if not request:
                self._send_json({"error": "request is required"}, HTTPStatus.BAD_REQUEST)
                return
            result = self._harness().run(request, use_planner=use_planner)
            self._send_json(result)
        except json.JSONDecodeError:
            self._send_json({"error": "invalid JSON"}, HTTPStatus.BAD_REQUEST)
        except Exception as exc:  # noqa: BLE001 - keep UI usable during harness errors.
            self._send_json({"error": str(exc)}, HTTPStatus.INTERNAL_SERVER_ERROR)

    def log_message(self, fmt: str, *args: Any) -> None:
        print(f"[web] {self.address_string()} - {fmt % args}")

    def _settings(self):
        from config.settings import load_settings

        return load_settings()

    def _harness(self):
        from harness.engine import Harness

        return Harness(self._settings())

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length)
        return json.loads(raw.decode("utf-8")) if raw else {}

    def _send_json(
        self, payload: Any, status: HTTPStatus = HTTPStatus.OK
    ) -> None:
        body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _serve_static(self, rel_path: str) -> None:
        target = (STATIC_ROOT / rel_path).resolve()
        try:
            target.relative_to(STATIC_ROOT.resolve())
        except ValueError:
            self._send_json({"error": "invalid path"}, HTTPStatus.BAD_REQUEST)
            return
        if not target.exists() or not target.is_file():
            self._send_json({"error": NOT_FOUND}, HTTPStatus.NOT_FOUND)
            return

        content = target.read_bytes()
        content_type = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)


def main() -> int:
    parser = argparse.ArgumentParser(description="NestAgent web console")
    parser.add_argument("--host", default=os.environ.get("NESTAGENT_WEB_HOST", DEFAULT_HOST))
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("NESTAGENT_WEB_PORT", str(DEFAULT_PORT))),
        help="Use 0 for a fully dynamic port.",
    )
    args = parser.parse_args()

    port = choose_port(args.host, args.port)
    if port != args.port and args.port != 0:
        print(f"Port {args.port} is busy; using {port} instead.")

    server = ThreadingHTTPServer((args.host, port), NestAgentHandler)
    print(f"NestAgent web console: http://{args.host}:{port}")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping NestAgent web console.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
