"""HTTP server for the room. Loopback only; every response carries strict security
headers; every state-changing request needs a session, a CSRF token and a matching Origin."""
from __future__ import annotations

from http import HTTPStatus
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from . import auth
from .auth import AuthError, RateLimiter
from .nexus import AdmissionError
from .service import Conflict, Forbidden, Relay

STATIC = Path(__file__).resolve().parent / "static"
MAX_REQUEST = 64 * 1024
COOKIE = "relay_session"
SECURITY_HEADERS = {
    "Content-Security-Policy": "default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self'; "
                               "connect-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    "Cross-Origin-Opener-Policy": "same-origin",
    "Cross-Origin-Resource-Policy": "same-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
    "Cache-Control": "no-store",
}
STATIC_FILES = {
    "/": ("room.html", "text/html; charset=utf-8"),
    "/join": ("room.html", "text/html; charset=utf-8"),
    "/static/room.js": ("room.js", "text/javascript; charset=utf-8"),
    "/static/room.css": ("room.css", "text/css; charset=utf-8"),
}


class HttpError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status
        self.message = message


def make_handler(relay: Relay, limiter: RateLimiter):
    cfg = relay.cfg

    class Handler(BaseHTTPRequestHandler):
        server_version = "nexus-relay"
        sys_version = ""
        protocol_version = "HTTP/1.1"
        timeout = 30

        def log_message(self, fmt, *args):
            return

        # --- plumbing ------------------------------------------------------------
        def _send(self, status: int, body: bytes, content_type: str, extra: dict | None = None) -> None:
            self.send_response(status)
            for k, v in SECURITY_HEADERS.items():
                self.send_header(k, v)
            if cfg.secure_cookies:
                self.send_header("Strict-Transport-Security", "max-age=31536000")
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            for k, v in (extra or {}).items():
                self.send_header(k, v)
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(body)

        def _json(self, status: int, value, extra: dict | None = None) -> None:
            self._send(status, json.dumps(value).encode(), "application/json", extra)

        def _session_token(self) -> str | None:
            raw = self.headers.get("Cookie")
            if not raw:
                return None
            cookie = SimpleCookie()
            try:
                cookie.load(raw)
            except Exception:
                return None
            return cookie[COOKIE].value if COOKIE in cookie else None

        def _member(self) -> tuple[dict, str | None]:
            member, csrf_hash = auth.session_member(relay.store, self._session_token())
            if member is None:
                raise HttpError(401, "sign in with an invite link")
            return member, csrf_hash

        def _check_write(self, csrf_hash: str | None) -> None:
            if self.headers.get("Origin") != cfg.public_origin:
                raise HttpError(403, "origin not allowed")
            if not auth.csrf_ok(csrf_hash, self.headers.get("X-Relay-CSRF")):
                raise HttpError(403, "missing or invalid CSRF token")

        def _body(self) -> dict:
            if (self.headers.get("Content-Type") or "").split(";")[0].strip() != "application/json":
                raise HttpError(415, "application/json required")
            try:
                length = int(self.headers.get("Content-Length", ""))
            except ValueError:
                raise HttpError(411, "content-length required")
            if not 0 <= length <= MAX_REQUEST:
                raise HttpError(413, "request too large")
            try:
                value = json.loads(self.rfile.read(length) or b"{}")
            except json.JSONDecodeError:
                raise HttpError(400, "invalid JSON")
            if not isinstance(value, dict):
                raise HttpError(400, "JSON object required")
            return value

        def _host_ok(self) -> bool:
            host = self.headers.get("Host", "")
            allowed = {urlsplit(cfg.public_origin).netloc, f"{cfg.host}:{cfg.port}", f"localhost:{cfg.port}"}
            return host in allowed

        def _dispatch(self, method: str) -> None:
            try:
                if not self._host_ok():
                    raise HttpError(421, "unknown host")
                path = urlsplit(self.path).path
                if method in ("GET", "HEAD") and path in STATIC_FILES:
                    name, ctype = STATIC_FILES[path]
                    return self._send(200, (STATIC / name).read_bytes(), ctype)
                if method == "POST" and path == "/api/join":
                    return self._join()
                route = ROUTES.get((method if method != "HEAD" else "GET", path))
                if route is None:
                    raise HttpError(404, "not found")
                member, csrf_hash = self._member()
                if method == "POST":
                    self._check_write(csrf_hash)
                    body = self._body()
                else:
                    body = {k: v[-1] for k, v in parse_qs(urlsplit(self.path).query).items()}
                result = route(self, member, body)
                self._json(200, result if result is not None else {"ok": True})
            except HttpError as exc:
                self._json(exc.status, {"error": exc.message})
            except Forbidden as exc:
                self._json(403, {"error": str(exc)})
            except (Conflict, AdmissionError) as exc:
                self._json(409, {"error": str(exc)})
            except AuthError:
                self._json(401, {"error": "invalid invite"})
            except (ValueError, KeyError) as exc:
                self._json(400, {"error": str(exc).strip("'")})
            except Exception:
                self._json(500, {"error": "internal error"})

        def do_GET(self):
            self._dispatch("GET")

        def do_HEAD(self):
            self._dispatch("HEAD")

        def do_POST(self):
            self._dispatch("POST")

        def do_PUT(self):
            self._json(405, {"error": "method not allowed"})

        do_DELETE = do_PATCH = do_OPTIONS = do_PUT

        # --- routes ------------------------------------------------------------------
        def _join(self) -> None:
            if self.headers.get("Origin") != cfg.public_origin:
                raise HttpError(403, "origin not allowed")
            if not limiter.allow(self.client_address[0]):
                raise HttpError(429, "too many attempts; try again later")
            body = self._body()
            member_id, session, csrf = auth.redeem_invite(relay.store, body.get("token"))
            attrs = "; HttpOnly; SameSite=Strict; Path=/; Max-Age=" + str(int(auth.SESSION_TTL.total_seconds()))
            if cfg.secure_cookies:
                attrs += "; Secure"
            self._json(200, {"csrf": csrf}, {"Set-Cookie": f"{COOKIE}={session}{attrs}"})

    def me(h, member, body):
        return {"member": member}

    def log(h, member, body):
        try:
            after = int(body.get("after", 0))
        except ValueError:
            raise HttpError(400, "after must be an integer")
        return {"entries": relay.store.entries_after(max(0, after))}

    def csrf(h, member, body):
        return {"csrf": auth.rotate_csrf(relay.store, h._session_token())}

    def logout(h, member, body):
        auth.revoke_session(relay.store, h._session_token(), member["id"])
        return {"ok": True}

    ROUTES = {
        ("GET", "/api/me"): me,
        ("GET", "/api/csrf"): csrf,
        ("GET", "/api/log"): log,
        ("GET", "/api/members"): lambda h, m, b: {"members": relay.members(m)},
        ("GET", "/api/plan"): lambda h, m, b: relay.plan(m),
        ("GET", "/api/runs"): lambda h, m, b: {"runs": relay.runs(m)},
        ("GET", "/api/run-output"): lambda h, m, b: {"output": relay.output(m, str(b.get("run_id", "")))},
        ("POST", "/api/logout"): logout,
        ("POST", "/api/messages"): lambda h, m, b: relay.post_message(m, b.get("text")),
        ("POST", "/api/runs/request"): lambda h, m, b: {"run_id": relay.request_run(m, str(b.get("task_id", "")), b.get("instruction"))},
        ("POST", "/api/runs/approve"): lambda h, m, b: {"reserved_cost": relay.approve(m, str(b.get("run_id", "")))},
        ("POST", "/api/runs/decline"): lambda h, m, b: relay.decline(m, str(b.get("run_id", "")), b.get("reason")),
        ("POST", "/api/runs/cancel"): lambda h, m, b: relay.cancel(m, str(b.get("run_id", ""))),
        ("POST", "/api/runs/review"): lambda h, m, b: relay.review(m, str(b.get("run_id", "")), b.get("accepted"),
                                                                   b.get("confirmed_predicates", []), b.get("note")),
        ("POST", "/api/members/invite"): lambda h, m, b: dict(zip(("member_id", "token"),
                                                                  relay.invite(m, str(b.get("name", "")), str(b.get("role", ""))))),
        ("POST", "/api/members/reinvite"): lambda h, m, b: {"token": relay.reinvite(m, str(b.get("member_id", "")))},
        ("POST", "/api/members/disable"): lambda h, m, b: relay.disable(m, str(b.get("member_id", ""))),
    }
    return Handler


class _Server(ThreadingHTTPServer):
    daemon_threads = True

    def handle_error(self, request, client_address):
        """Client disconnects and malformed requests are routine; do not dump tracebacks."""
        import sys
        exc = sys.exc_info()[1]
        if isinstance(exc, (ConnectionError, TimeoutError)):
            return
        super().handle_error(request, client_address)


def serve(relay: Relay) -> ThreadingHTTPServer:
    server = _Server((relay.cfg.host, relay.cfg.port), make_handler(relay, RateLimiter()))
    server.daemon_threads = True
    return server
