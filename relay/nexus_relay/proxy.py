"""Per-run model proxy on a unix socket.

The container has no network. Its only channel out is this socket, mounted into the run.
The proxy accepts only allowlisted model API paths, requires the per-run token the
container was given, swaps it for the real API key, and enforces the NEXUS reservation
as a hard ceiling:

* Before forwarding, each generation request holds its worst-case cost (an upper bound on
  input tokens plus `max_tokens`) against the reservation, under a lock. Text is bounded
  by request bytes; images and PDFs by `media.input_bound`, since bytes do not bound them. `max_tokens` is
  lowered to what the remaining budget can pay for; a request that cannot fit is refused.
* After the response, the hold is settled at the metered cost. An incomplete response is
  charged at its full hold, never at a partial count.
* The request itself is checked against `policy`: nothing that makes the provider act on
  the network (server tools, remote MCP servers, URL or Files-API sources, containers) or
  change the price per token is forwarded. The container has no network; the provider
  must not become its network either.
* Concurrency, connection count, request size and idle time are all bounded, so a
  container cannot exhaust the relay's threads or memory.
"""
from __future__ import annotations

from http.server import BaseHTTPRequestHandler
import hmac
import http.client
import itertools
import json
import math
import os
from pathlib import Path
import socketserver
import threading
from urllib.parse import urlsplit

from .media import DEFAULT_MAX_IMAGE_TOKENS, DEFAULT_MAX_INPUT_TOKENS, input_bound
from .policy import PolicyViolation, check_betas, check_request

MAX_BODY = 8 * 1024 * 1024
MAX_CONNECTIONS = 8
MAX_IN_FLIGHT = 4
IN_FLIGHT_WAIT_SECONDS = 120
IDLE_TIMEOUT_SECONDS = 30
INPUT_MARGIN_TOKENS = 4096
MIN_THINKING_BUDGET = 1024
GENERATION_PATH = "/v1/messages"
FORWARD_HEADERS = ("content-type", "anthropic-version", "anthropic-beta", "accept")
RESPONSE_HEADERS = ("content-type", "request-id", "anthropic-ratelimit-requests-remaining", "retry-after")
USAGE_KEYS = ("input_tokens", "output_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")


class BudgetExceeded(Exception):
    pass


class Meter:
    """Thread-safe ledger: spent + held never exceeds the reservation when the upstream
    reports usage honestly and input tokens do not exceed the bound given to `hold`
    (by default request bytes plus a margin; the proxy passes `media.input_bound`)."""

    def __init__(self, unit: str, prices: dict, reserved: float, input_margin: int = INPUT_MARGIN_TOKENS):
        self.unit = unit
        self.prices = prices
        self.reserved = float(reserved)
        self.input_margin = input_margin
        self.spent = 0.0
        self.requests = 0
        self.overruns = 0
        self._holds: dict[int, float] = {}
        self._ids = itertools.count(1)
        self._lock = threading.Lock()
        self._closed = False

    def priced(self, model: str | None) -> bool:
        return self.unit == "tokens" or (model is not None and model in self.prices)

    def exhausted(self) -> bool:
        with self._lock:
            return self._closed or self.spent >= self.reserved

    def remaining(self) -> float:
        with self._lock:
            return 0.0 if self._closed else self.reserved - self.spent - sum(self._holds.values())

    def _rates(self, model: str | None) -> tuple[float, float]:
        """(worst-case cost of one input token, cost of one output token)."""
        if self.unit == "tokens":
            return 1.0, 1.0
        price = self.prices[model]
        worst_input = max(price["input"], price.get("cache_write", price["input"]),
                          price.get("cache_read", price["input"]))
        return worst_input / 1_000_000, price["output"] / 1_000_000

    def cost(self, model: str | None, usage: dict) -> float:
        tokens = {k: max(0, int(usage.get(k) or 0)) for k in USAGE_KEYS}
        if self.unit == "tokens":
            return float(sum(tokens.values()))
        price = self.prices[model]
        return (tokens["input_tokens"] * price["input"]
                + tokens["output_tokens"] * price["output"]
                + tokens["cache_creation_input_tokens"] * price.get("cache_write", price["input"])
                + tokens["cache_read_input_tokens"] * price.get("cache_read", price["input"])) / 1_000_000

    def hold(self, model: str | None, body_bytes: int, requested_max: int | None,
             input_tokens: int | None = None) -> tuple[int, int]:
        """Reserve the worst case for one generation request. Returns (hold id, max_tokens
        to forward). Without `input_tokens`, byte length bounds the tokens of the text it
        encodes; callers with images or documents must pass a media-aware bound."""
        in_rate, out_rate = self._rates(model)
        if input_tokens is None:
            input_tokens = body_bytes + self.input_margin
        input_cost = input_tokens * in_rate
        with self._lock:
            if self._closed:
                raise BudgetExceeded("run meter is closed")
            free = self.reserved - self.spent - sum(self._holds.values())
            affordable = math.floor((free - input_cost) / out_rate) if out_rate > 0 else (requested_max or 0)
            if affordable < 1:
                raise BudgetExceeded("run budget cannot cover this request")
            max_tokens = affordable if requested_max is None else min(requested_max, affordable)
            hold_id = next(self._ids)
            self._holds[hold_id] = input_cost + max_tokens * out_rate
            return hold_id, max_tokens

    def settle(self, hold_id: int, model: str | None, usage: dict | None) -> float:
        """Release a hold, charging metered usage, or the full hold if usage is unknown."""
        # Keep the reservation visible while calculating its final cost. Releasing
        # it first lets a concurrent request spend money that is about to be charged.
        charged = self.cost(model, usage) if usage is not None else None
        with self._lock:
            if self._closed:
                return 0.0  # close() already charged the full hold before cost was persisted.
            held = self._holds.pop(hold_id)
            if charged is None:
                charged = held
            if charged > held:
                self.overruns += 1
            self.spent += charged
            self.requests += 1
        return charged

    def close(self) -> None:
        """Freeze final cost, charging outstanding responses conservatively at their holds.

        Proxy handlers are daemon threads and may outlive socket shutdown. They must
        neither release budget nor alter a run's cost after it has been persisted.
        """
        with self._lock:
            if self._closed:
                return
            self._closed = True
            self.spent += sum(self._holds.values())
            self.requests += len(self._holds)
            self._holds.clear()

    def add(self, model: str | None, usage: dict) -> None:
        """Record usage that was not held in advance (test doubles and recovery)."""
        charged = self.cost(model, usage)
        with self._lock:
            self.spent += charged
            self.requests += 1


class _UsageParser:
    """Collects usage from either a JSON body or an SSE stream, chunk by chunk, and
    whether the response reached its final usage report."""

    def __init__(self, streaming: bool):
        self.streaming = streaming
        self.buffer = b""
        self.usage: dict = {}
        self.complete = False

    def feed(self, chunk: bytes) -> None:
        if not self.streaming:
            if len(self.buffer) <= MAX_BODY:
                self.buffer += chunk
            return
        self.buffer += chunk
        while b"\n" in self.buffer:
            line, self.buffer = self.buffer.split(b"\n", 1)
            line = line.strip()
            if line.startswith(b"data:"):
                self._event(line[5:].strip())
        if len(self.buffer) > 1024 * 1024:
            self.buffer = b""

    def _event(self, data: bytes) -> None:
        try:
            event = json.loads(data)
        except (json.JSONDecodeError, UnicodeDecodeError, RecursionError):
            return
        if not isinstance(event, dict):
            return
        message = event.get("message") if isinstance(event.get("message"), dict) else None
        if message:
            self._merge(message.get("usage"))
        self._merge(event.get("usage"))
        if event.get("type") == "message_stop":
            self.complete = True

    def _merge(self, usage) -> None:
        if isinstance(usage, dict):
            for key, value in usage.items():
                if isinstance(value, int) and not isinstance(value, bool):
                    self.usage[key] = max(self.usage.get(key, 0), value)

    def finish(self) -> dict | None:
        if not self.streaming:
            try:
                body = json.loads(self.buffer)
            except (json.JSONDecodeError, UnicodeDecodeError, RecursionError):
                return None
            if isinstance(body, dict) and isinstance(body.get("usage"), dict):
                self._merge(body["usage"])
                self.complete = True
        return dict(self.usage) if self.complete and "output_tokens" in self.usage else None


class _Server(socketserver.ThreadingMixIn, socketserver.UnixStreamServer):
    daemon_threads = True
    allow_reuse_address = False

    def __init__(self, path, handler, max_connections: int):
        self._slots = threading.BoundedSemaphore(max_connections)
        super().__init__(path, handler)

    def process_request(self, request, client_address):
        if not self._slots.acquire(blocking=False):
            self.shutdown_request(request)
            return
        try:
            super().process_request(request, client_address)
        except BaseException:
            self._slots.release()
            raise

    def process_request_thread(self, request, client_address):
        try:
            super().process_request_thread(request, client_address)
        finally:
            self._slots.release()


def _clamp(request: dict, max_tokens: int) -> dict:
    """Lower max_tokens (and an extended-thinking budget, which must stay below it)."""
    request = dict(request)
    request["max_tokens"] = max_tokens
    thinking = request.get("thinking")
    if isinstance(thinking, dict) and isinstance(thinking.get("budget_tokens"), int):
        if thinking["budget_tokens"] >= max_tokens:
            if max_tokens - 1 < MIN_THINKING_BUDGET:
                raise BudgetExceeded("remaining budget is too small for extended thinking")
            request["thinking"] = {**thinking, "budget_tokens": max_tokens - 1}
    return request


class ModelProxy:
    def __init__(self, socket_path: Path, run_token: str, api_key: str, upstream: str,
                 allowed_paths: tuple[str, ...], meter: Meter, connection_factory=None, *,
                 max_connections: int = MAX_CONNECTIONS, max_in_flight: int = MAX_IN_FLIGHT,
                 idle_timeout: float = IDLE_TIMEOUT_SECONDS, extra_request_fields: tuple[str, ...] = (),
                 max_image_tokens: int = DEFAULT_MAX_IMAGE_TOKENS, max_input_tokens: int = DEFAULT_MAX_INPUT_TOKENS):
        self.socket_path = socket_path
        self.run_token = run_token
        self.api_key = api_key
        self.upstream = urlsplit(upstream)
        self.allowed_paths = allowed_paths
        self.extra_request_fields = tuple(extra_request_fields)
        self.max_image_tokens = max_image_tokens
        self.max_input_tokens = max_input_tokens
        self.meter = meter
        self.on_exhausted = None
        self.max_connections = max_connections
        self.idle_timeout = idle_timeout
        self._in_flight = threading.BoundedSemaphore(max_in_flight)
        self._connect = connection_factory or (lambda: http.client.HTTPSConnection(
            self.upstream.hostname, self.upstream.port or 443, timeout=600))
        self._server = None
        self._thread = None

    def start(self) -> None:
        proxy = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.0"
            timeout = proxy.idle_timeout

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
            self._server = _Server(str(self.socket_path), Handler, self.max_connections)
        finally:
            os.umask(old_umask)
        # The container runs as the relay's own uid, so owner-only permissions suffice.
        os.chmod(self.socket_path, 0o600)
        self._thread = threading.Thread(target=self._server.serve_forever, name="relay-model-proxy", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self.meter.close()
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

    def _stop_if_spent(self) -> None:
        if self.meter.exhausted() and self.on_exhausted:
            self.on_exhausted()

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
            self._stop_if_spent()
            return handler._reply(402, "run budget exhausted")
        try:
            length = int(handler.headers.get("content-length", ""))
        except ValueError:
            return handler._reply(411, "content-length required")
        if not 0 < length <= MAX_BODY:
            return handler._reply(413, "request body too large")
        body = handler.rfile.read(length)
        if len(body) != length:
            return handler._reply(400, "truncated body")
        try:
            request = json.loads(body)
        except (json.JSONDecodeError, UnicodeDecodeError, RecursionError):
            return handler._reply(400, "JSON body required")
        if not isinstance(request, dict):
            return handler._reply(400, "JSON object required")
        try:
            check_betas(handler.headers.get("anthropic-beta"))
            check_request(path, request, self.extra_request_fields)
        except (PolicyViolation, RecursionError) as exc:
            return handler._reply(403, f"refused by relay policy: {exc}"[:500])
        model = request.get("model")
        if not isinstance(model, str) or not self.meter.priced(model):
            return handler._reply(403, f"model {model!r} has no configured price")
        generating = path == GENERATION_PATH
        requested_max = request.get("max_tokens")
        if generating and (type(requested_max) is not int or requested_max < 1):
            return handler._reply(400, "max_tokens must be a positive integer")
        if not self._in_flight.acquire(timeout=IN_FLIGHT_WAIT_SECONDS):
            return handler._reply(429, "too many concurrent model requests for this run")
        hold_id = None
        try:
            if generating:
                bound, media = input_bound(request, len(body), self.meter.input_margin,
                                           max_image_tokens=self.max_image_tokens,
                                           max_input_tokens=self.max_input_tokens)
                try:
                    hold_id, max_tokens = self.meter.hold(model, len(body), requested_max, input_tokens=bound)
                    if max_tokens != requested_max:
                        request = _clamp(request, max_tokens)
                        body = json.dumps(request, separators=(",", ":")).encode()
                except BudgetExceeded as exc:
                    if hold_id is not None:
                        self.meter.settle(hold_id, model, {})
                        hold_id = None
                    if media:
                        # Only this request's images or PDFs do not fit; a text request
                        # may still, so refuse it without ending the run.
                        return handler._reply(402, f"{exc}: its images or PDFs are held at their worst case "
                                                   f"(a PDF at the model input limit, {self.max_input_tokens} tokens)")
                    # The reservation cannot pay for another request: end the run now.
                    if self.on_exhausted:
                        self.on_exhausted()
                    return handler._reply(402, str(exc))
            owned, hold_id = hold_id, None  # _forward settles it from here on
            self._forward(handler, forward_target, body, model, request.get("stream") is True, owned)
        finally:
            if hold_id is not None:
                self.meter.settle(hold_id, model, None)
            self._in_flight.release()
            self._stop_if_spent()

    def _forward(self, handler, target: str, body: bytes, model: str, streaming: bool, hold_id: int | None) -> None:
        headers = {k: handler.headers[k] for k in FORWARD_HEADERS if handler.headers.get(k)}
        headers["x-api-key"] = self.api_key
        headers["content-length"] = str(len(body))
        parser = _UsageParser(streaming)
        status = None
        conn = self._connect()
        try:
            conn.request("POST", target, body=body, headers=headers)
            upstream = conn.getresponse()
            status = upstream.status
            handler.send_response(status)
            for name in RESPONSE_HEADERS:
                value = upstream.getheader(name)
                if value:
                    handler.send_header(name, value)
            handler.send_header("Connection", "close")
            handler.end_headers()
            while True:
                chunk = upstream.read1(65536) if hasattr(upstream, "read1") else upstream.read(65536)
                if not chunk:
                    break
                parser.feed(chunk)
                handler.wfile.write(chunk)
                handler.wfile.flush()
        except (OSError, http.client.HTTPException) as exc:
            if status is None:
                try:
                    handler._reply(502, f"upstream error: {type(exc).__name__}")
                except OSError:
                    pass
        finally:
            conn.close()
            if hold_id is not None:
                usage = parser.finish() if status == 200 else ({} if status is not None and status >= 400 else None)
                self.meter.settle(hold_id, model, usage)
