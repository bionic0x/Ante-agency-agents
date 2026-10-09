"""Per-run model proxy on a unix socket.

The container has no network. Its only channel out is this socket, mounted into the run.
The proxy accepts only allowlisted model API paths, requires the per-run token the
container was given, swaps it for the real API key, meters usage from the response and
refuses further requests once the NEXUS reservation is spent."""
from __future__ import annotations

from http.server import BaseHTTPRequestHandler
import hmac
import http.client
import json
import os
from pathlib import Path
import socketserver
import threading
from urllib.parse import urlsplit

MAX_BODY = 32 * 1024 * 1024
FORWARD_HEADERS = ("content-type", "anthropic-version", "anthropic-beta", "accept")
RESPONSE_HEADERS = ("content-type", "request-id", "anthropic-ratelimit-requests-remaining", "retry-after")


class Meter:
    def __init__(self, unit: str, prices: dict, reserved: float):
        self.unit = unit
        self.prices = prices
        self.reserved = reserved
        self.spent = 0.0
        self.requests = 0
        self._lock = threading.Lock()

    def exhausted(self) -> bool:
        with self._lock:
            return self.spent >= self.reserved

    def priced(self, model: str | None) -> bool:
        return self.unit == "tokens" or (model is not None and model in self.prices)

    def add(self, model: str | None, usage: dict) -> None:
        tokens = {k: int(usage.get(k) or 0) for k in
                  ("input_tokens", "output_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")}
        if self.unit == "tokens":
            cost = float(sum(tokens.values()))
        else:
            price = self.prices[model]
            cost = (tokens["input_tokens"] * price["input"]
                    + tokens["output_tokens"] * price["output"]
                    + tokens["cache_creation_input_tokens"] * price.get("cache_write", price["input"])
                    + tokens["cache_read_input_tokens"] * price.get("cache_read", price["input"])) / 1_000_000
        with self._lock:
            self.spent += cost
            self.requests += 1


class _UsageParser:
    """Collects usage from either a JSON body or an SSE stream, chunk by chunk."""

    def __init__(self, streaming: bool):
        self.streaming = streaming
        self.buffer = b""
        self.usage: dict = {}
        self.model: str | None = None

    def feed(self, chunk: bytes) -> None:
        self.buffer += chunk
        if not self.streaming:
            return
        while b"\n" in self.buffer:
            line, self.buffer = self.buffer.split(b"\n", 1)
            line = line.strip()
            if line.startswith(b"data:"):
                self._event(line[5:].strip())

    def _event(self, data: bytes) -> None:
        try:
            event = json.loads(data)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return
        if not isinstance(event, dict):
            return
        message = event.get("message") if isinstance(event.get("message"), dict) else None
        if message:
            self.model = message.get("model") or self.model
            self._merge(message.get("usage"))
        self._merge(event.get("usage"))

    def _merge(self, usage) -> None:
        if isinstance(usage, dict):
            for key, value in usage.items():
                if isinstance(value, int):
                    self.usage[key] = max(self.usage.get(key, 0), value)

    def finish(self) -> None:
        if not self.streaming:
            try:
                body = json.loads(self.buffer)
            except (json.JSONDecodeError, UnicodeDecodeError):
                return
            if isinstance(body, dict):
                self.model = body.get("model") or self.model
                self._merge(body.get("usage"))


class _Server(socketserver.ThreadingMixIn, socketserver.UnixStreamServer):
    daemon_threads = True
    allow_reuse_address = False


class ModelProxy:
    def __init__(self, socket_path: Path, run_token: str, api_key: str, upstream: str,
                 allowed_paths: tuple[str, ...], meter: Meter, connection_factory=None):
        self.socket_path = socket_path
        self.run_token = run_token
        self.api_key = api_key
        self.upstream = urlsplit(upstream)
        self.allowed_paths = allowed_paths
        self.meter = meter
        self.on_exhausted = None
        self._connect = connection_factory or (lambda: http.client.HTTPSConnection(
            self.upstream.hostname, self.upstream.port or 443, timeout=600))
        self._server = None
        self._thread = None

    def start(self) -> None:
        proxy = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.0"

            def log_message(self, *args):
                return

            def _reply(self, status: int, message: str) -> None:
                body = json.dumps({"type": "error", "error": {"type": "relay_proxy", "message": message}}).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_GET(self):
                self._reply(405, "method not allowed")

            do_PUT = do_DELETE = do_PATCH = do_HEAD = do_OPTIONS = do_GET

            def do_POST(self):
                proxy._handle(self)

        self.socket_path.parent.mkdir(parents=True, exist_ok=True)
        old_umask = os.umask(0o077)
        try:
            self._server = _Server(str(self.socket_path), Handler)
        finally:
            os.umask(old_umask)
        # The container runs as the relay's own uid, so owner-only permissions suffice.
        os.chmod(self.socket_path, 0o600)
        self._thread = threading.Thread(target=self._server.serve_forever, name="relay-model-proxy", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        if self._server:
            self._server.shutdown()
            self._server.server_close()
            self._server = None
        try:
            self.socket_path.unlink()
        except FileNotFoundError:
            pass

    def _authorised(self, handler) -> bool:
        presented = handler.headers.get("x-api-key") or ""
        auth = handler.headers.get("authorization") or ""
        if not presented and auth.lower().startswith("bearer "):
            presented = auth[7:]
        return bool(presented) and hmac.compare_digest(presented.encode(), self.run_token.encode())

    def _handle(self, handler) -> None:
        target = handler.path
        parts = urlsplit(target)
        if not target.startswith("/") or target.startswith("//") or parts.scheme or parts.netloc \
                or parts.path not in self.allowed_paths or parts.fragment:
            return handler._reply(403, "path not allowed by relay")
        path = parts.path
        forward_target = path + (f"?{parts.query}" if parts.query else "")
        if not self._authorised(handler):
            return handler._reply(401, "invalid run token")
        if self.meter.exhausted():
            if self.on_exhausted:
                self.on_exhausted()
            return handler._reply(402, "run budget exhausted")
        try:
            length = int(handler.headers.get("content-length", ""))
        except ValueError:
            return handler._reply(411, "content-length required")
        if not 0 < length <= MAX_BODY:
            return handler._reply(413, "request body too large")
        body = handler.rfile.read(length)
        try:
            request = json.loads(body)
        except json.JSONDecodeError:
            return handler._reply(400, "JSON body required")
        model = request.get("model") if isinstance(request, dict) else None
        if not self.meter.priced(model):
            return handler._reply(403, f"model {model!r} has no configured price")
        streaming = bool(isinstance(request, dict) and request.get("stream"))
        headers = {k: handler.headers[k] for k in FORWARD_HEADERS if handler.headers.get(k)}
        headers["x-api-key"] = self.api_key
        headers["content-length"] = str(len(body))
        conn = self._connect()
        try:
            conn.request("POST", forward_target, body=body, headers=headers)
            upstream = conn.getresponse()
            handler.send_response(upstream.status)
            for name in RESPONSE_HEADERS:
                value = upstream.getheader(name)
                if value:
                    handler.send_header(name, value)
            handler.send_header("Connection", "close")
            handler.end_headers()
            parser = _UsageParser(streaming)
            while True:
                chunk = upstream.read1(65536) if hasattr(upstream, "read1") else upstream.read(65536)
                if not chunk:
                    break
                parser.feed(chunk)
                handler.wfile.write(chunk)
                handler.wfile.flush()
            parser.finish()
            if path == "/v1/messages" and upstream.status == 200:
                self.meter.add(model, parser.usage)
                if self.meter.exhausted() and self.on_exhausted:
                    self.on_exhausted()
        except (OSError, http.client.HTTPException) as exc:
            try:
                handler._reply(502, f"upstream error: {type(exc).__name__}")
            except OSError:
                pass
        finally:
            conn.close()
