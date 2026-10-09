"""NEXUS Relay tests. Standard library only: python3 -m unittest discover -s relay/tests"""
from __future__ import annotations

import hashlib
import http.client
import io
import json
import os
from pathlib import Path
import shutil
import socket
import sqlite3
import sys
import tempfile
import threading
import time
import unittest
from unittest import mock

RELAY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RELAY))

from nexus_relay import auth, config, nexus, proxy, runner, server, service, store  # noqa: E402
from nexus_relay.cli import verify  # noqa: E402

EXAMPLE = RELAY / "examples" / "relay-pilot.instance.json"
OWNER = json.loads(EXAMPLE.read_text())["mandate"]["owner"]


def raw_config(tmp: Path, **over) -> dict:
    raw = {
        "schema_version": 1,
        "instance": str(tmp / "instance.json"),
        "events": str(tmp / "events.jsonl"),
        "bind": {"host": "127.0.0.1", "port": 8770},
        "public_origin": "http://127.0.0.1:8770",
        "runtime": {"engine": "docker", "image": "agent:test", "agent_command": ["agent"]},
        "model": {"upstream": "https://api.example.test", "api_key_env": "RELAY_TEST_KEY", "cost_unit": "tokens"},
    }
    raw.update(over)
    return raw


class Env(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="relay-test-"))
        os.chmod(self.tmp, 0o700)
        shutil.copy(EXAMPLE, self.tmp / "instance.json")
        self.cfg = config.parse(raw_config(self.tmp), self.tmp)
        self.store = store.Store(self.cfg.db_path)
        self.contract = nexus.Contract(self.cfg.instance_path, self.cfg.events_path)

    def tearDown(self):
        self.store.close()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def instance(self) -> dict:
        return json.loads(self.cfg.instance_path.read_text())

    def write_instance(self, value: dict) -> None:
        self.cfg.instance_path.write_text(json.dumps(value))

    def member(self, name: str, role: str) -> dict:
        member_id = auth.create_member(self.store, name, role, "test")
        return {"id": member_id, "name": name, "role": role}


# --- config ----------------------------------------------------------------------------
class ConfigTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_refuses_non_loopback_bind(self):
        for host in ("0.0.0.0", "192.168.1.10", "::"):
            with self.subTest(host=host), self.assertRaisesRegex(config.ConfigError, "loopback"):
                config.parse(raw_config(self.tmp, bind={"host": host, "port": 8770}), self.tmp)

    def test_refuses_plain_http_public_origin_off_loopback(self):
        with self.assertRaisesRegex(config.ConfigError, "TLS"):
            config.parse(raw_config(self.tmp, public_origin="http://relay.example.com"), self.tmp)
        cfg = config.parse(raw_config(self.tmp, public_origin="https://box.tail.ts.net"), self.tmp)
        self.assertTrue(cfg.secure_cookies)

    def test_refuses_unknown_keys_and_unsafe_values(self):
        with self.assertRaisesRegex(config.ConfigError, "unknown keys"):
            config.parse(raw_config(self.tmp, extra=True), self.tmp)
        bad_rt = {"engine": "docker", "image": "--privileged", "agent_command": ["x"]}
        with self.assertRaisesRegex(config.ConfigError, "image"):
            config.parse(raw_config(self.tmp, runtime=bad_rt), self.tmp)
        with self.assertRaisesRegex(config.ConfigError, "unknown keys"):
            config.parse(raw_config(self.tmp, runtime={**bad_rt, "image": "ok", "privileged": True}), self.tmp)

    def test_usd_requires_prices_and_https_upstream(self):
        with self.assertRaisesRegex(config.ConfigError, "prices"):
            config.parse(raw_config(self.tmp, model={"upstream": "https://a.test", "api_key_env": "K", "cost_unit": "usd"}), self.tmp)
        with self.assertRaisesRegex(config.ConfigError, "https"):
            config.parse(raw_config(self.tmp, model={"upstream": "http://a.test", "api_key_env": "K", "cost_unit": "tokens"}), self.tmp)

    def test_load_refuses_group_readable_files(self):
        os.chmod(self.tmp, 0o755)
        with self.assertRaisesRegex(config.ConfigError, "permissions"):
            config.load(self.tmp)


# --- store -------------------------------------------------------------------------------
class StoreTests(Env):
    def test_chain_verifies_and_is_append_only(self):
        with self.store.tx() as db:
            self.store.append(db, "message", "m1", {"text": "hello"})
            self.store.append(db, "message", "m1", {"text": "again"})
        self.assertEqual(2, self.store.verify_chain())
        with self.assertRaises(sqlite3.DatabaseError):
            with self.store.tx() as db:
                db.execute("UPDATE log SET payload = '{}' WHERE seq = 1")
        with self.assertRaises(sqlite3.DatabaseError):
            with self.store.tx() as db:
                db.execute("DELETE FROM log")

    def test_tampering_is_detected(self):
        with self.store.tx() as db:
            self.store.append(db, "message", "m1", {"text": "original"})
        raw = sqlite3.connect(self.cfg.db_path)
        raw.execute("DROP TRIGGER log_no_update")
        raw.execute("""UPDATE log SET payload = '{"text":"forged"}' WHERE seq = 1""")
        raw.commit()
        raw.close()
        with self.assertRaisesRegex(store.ChainError, "does not match"):
            self.store.verify_chain()

    def test_database_file_is_private(self):
        self.assertEqual(0o600, os.stat(self.cfg.db_path).st_mode & 0o777)


# --- auth -----------------------------------------------------------------------------------
class AuthTests(Env):
    def test_invite_is_single_use_and_never_stored_raw(self):
        m = self.member("ana", "operator")
        token = auth.create_invite(self.store, m["id"], "test")
        self.assertNotIn(token.encode(), self.cfg.db_path.read_bytes())
        member_id, session, csrf = auth.redeem_invite(self.store, token)
        self.assertEqual(m["id"], member_id)
        with self.assertRaises(auth.AuthError):
            auth.redeem_invite(self.store, token)
        found, csrf_hash = auth.session_member(self.store, session)
        self.assertEqual("ana", found["name"])
        self.assertTrue(auth.csrf_ok(csrf_hash, csrf))
        self.assertFalse(auth.csrf_ok(csrf_hash, "wrong"))

    def test_expired_invite_is_refused(self):
        m = self.member("ana", "operator")
        with mock.patch.object(auth, "INVITE_TTL", auth.dt.timedelta(seconds=-1)):
            token = auth.create_invite(self.store, m["id"], "test")
        with self.assertRaises(auth.AuthError):
            auth.redeem_invite(self.store, token)

    def test_disabling_a_member_kills_sessions_and_invites(self):
        m = self.member("ana", "operator")
        _, session, _ = auth.redeem_invite(self.store, auth.create_invite(self.store, m["id"], "t"))
        pending = auth.create_invite(self.store, m["id"], "t")
        auth.disable_member(self.store, m["id"], "owner")
        self.assertEqual((None, None), auth.session_member(self.store, session))
        with self.assertRaises(auth.AuthError):
            auth.redeem_invite(self.store, pending)

    def test_only_one_owner_and_owner_cannot_be_disabled(self):
        owner = self.member(OWNER, "owner")
        with self.assertRaisesRegex(ValueError, "already has its owner"):
            self.member("second", "owner")
        with self.assertRaisesRegex(ValueError, "owner cannot be disabled"):
            auth.disable_member(self.store, owner["id"], "x")

    def test_rate_limiter(self):
        limiter = auth.RateLimiter(per_client=2, global_limit=3, window_seconds=60)
        self.assertTrue(limiter.allow("a"))
        self.assertTrue(limiter.allow("a"))
        self.assertFalse(limiter.allow("a"))
        self.assertTrue(limiter.allow("b"))
        self.assertFalse(limiter.allow("c"))


# --- NEXUS admission ------------------------------------------------------------------------
class NexusTests(Env):
    def test_instance_must_be_local_relay(self):
        inst = self.instance()
        inst["mandate"]["scope"] = "offline-analysis"
        self.write_instance(inst)
        with self.assertRaisesRegex(nexus.AdmissionError, "local-relay"):
            self.contract.start("r1", "A", OWNER)

    def test_engine_refuses_blocked_and_unauthorised_starts(self):
        with self.assertRaisesRegex(nexus.AdmissionError, "DEPENDENCY:A"):
            self.contract.start("r1", "C", OWNER)
        with self.assertRaisesRegex(nexus.AdmissionError, "issuer"):
            self.contract.start("r2", "A", "someone-else")
        self.assertFalse(self.cfg.events_path.exists())

    def test_hold_blocks_the_task(self):
        inst = self.instance()
        inst["open_conditions"] = [{"id": "H1", "classification": "PENDING_EVIDENCE", "task_ids": ["A"], "reason": "waiting"}]
        self.write_instance(inst)
        with self.assertRaisesRegex(nexus.AdmissionError, "HOLD:H1"):
            self.contract.start("r1", "A", OWNER)

    def test_start_reserves_and_finish_requires_every_predicate(self):
        reserved = self.contract.start("r1", "A", OWNER)
        self.assertEqual(150000, reserved)
        with self.assertRaisesRegex(nexus.AdmissionError, "predicates"):
            self.contract.finish("r1", "A", OWNER, 10, True, ["ev"], [])
        self.contract.finish("r1", "A", OWNER, 10, True, ["ev"], ["contract_met"])
        state = self.contract.state()[1]
        self.assertEqual("SUCCEEDED", state["tasks"]["A"]["status"])
        self.assertEqual(10, state["spent"])
        nexus.engine()["replay"](self.instance(), self.contract.events())

    def test_events_file_is_private(self):
        self.contract.start("r1", "A", OWNER)
        self.assertEqual(0o600, os.stat(self.cfg.events_path).st_mode & 0o777)


# --- runner -----------------------------------------------------------------------------------
class RunnerTests(Env):
    def test_command_is_hardened_and_carries_no_key(self):
        os.environ["RELAY_TEST_KEY"] = "sk-real-secret"
        try:
            paths = runner.prepare(self.cfg, "r_1", {"id": "A", "resource_scope": ["x"]})
            profile = runner.agent_profile("general-strategy-director")
            with mock.patch.object(runner.os, "getuid", return_value=1000), mock.patch.object(runner.os, "getgid", return_value=1000):
                cmd = runner.build_command(self.cfg, "r_1", paths, profile, "relay-run-token")
        finally:
            del os.environ["RELAY_TEST_KEY"]
        joined = " ".join(cmd)
        for flag in ("--network none", "--read-only", "--cap-drop ALL", "--security-opt no-new-privileges",
                     "--user 1000:1000", "--pids-limit", "--memory 4g", "--rm"):
            self.assertIn(flag, joined)
        self.assertNotIn("sk-real-secret", joined)
        self.assertNotIn("--privileged", joined)
        self.assertNotIn("docker.sock", joined)
        self.assertIn("ANTHROPIC_API_KEY=relay-run-token", cmd)
        self.assertEqual(0o700, os.stat(paths.workspace).st_mode & 0o777)

    def test_refuses_root(self):
        paths = runner.prepare(self.cfg, "r_1", {"id": "A", "resource_scope": []})
        with mock.patch.object(runner.os, "getuid", return_value=0):
            with self.assertRaisesRegex(runner.RunError, "root"):
                runner.build_command(self.cfg, "r_1", paths, runner.agent_profile("general-strategy-director"), "t")

    def test_unsafe_names_never_reach_paths(self):
        with self.assertRaises(runner.RunError):
            runner.prepare(self.cfg, "../escape", {"id": "A", "resource_scope": []})
        self.assertTrue(runner.workspace_name("../../etc").startswith("task-"))
        self.assertNotIn("/", runner.workspace_name("../../etc"))
        with self.assertRaisesRegex(runner.RunError, "catalog"):
            runner.agent_profile("../../../etc/passwd")

    def test_engine_gets_no_model_key(self):
        with mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk", "RELAY_TEST_KEY": "sk", "PATH": "/bin"}):
            env = runner.engine_environment()
        self.assertEqual({"PATH": "/bin"}, {k: v for k, v in env.items() if k in ("PATH", "ANTHROPIC_API_KEY", "RELAY_TEST_KEY")})


# --- proxy ------------------------------------------------------------------------------------
class FakeUpstream:
    """Stand-in for the model API. Thread-safe; records forwarded bodies and peak concurrency."""

    def __init__(self, status=200, body=b"", headers=None, delay=0.0, usage=None):
        self.status, self.headers, self.delay = status, headers or {"content-type": "application/json"}, delay
        self.body = body if usage is None else json.dumps({"usage": usage}).encode()
        self.requests = []
        self.inflight = self.peak = 0
        self.lock = threading.Lock()

    def __call__(self):
        outer = self

        class Conn:
            def request(self, method, path, body=None, headers=None):
                with outer.lock:
                    outer.requests.append((method, path, body, dict(headers)))

            def getresponse(self):
                with outer.lock:
                    outer.inflight += 1
                    outer.peak = max(outer.peak, outer.inflight)
                time.sleep(outer.delay)
                with outer.lock:
                    outer.inflight -= 1

                class Resp:
                    status = outer.status
                    _buf = io.BytesIO(outer.body)

                    def getheader(self, name):
                        return outer.headers.get(name)

                    def read1(self, n):
                        return self._buf.read(n)
                return Resp()

            def close(self):
                pass
        return Conn()

    def forwarded(self, i=0) -> dict:
        return json.loads(self.requests[i][2])


def unix_post(sock_path: Path, path: str, body: dict, headers: dict) -> tuple[int, bytes]:
    payload = json.dumps(body).encode()
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.connect(str(sock_path))
    lines = [f"POST {path} HTTP/1.0", f"Content-Length: {len(payload)}", "Content-Type: application/json"]
    lines += [f"{k}: {v}" for k, v in headers.items()]
    s.sendall(("\r\n".join(lines) + "\r\n\r\n").encode() + payload)
    data = b""
    while chunk := s.recv(65536):
        data += chunk
    s.close()
    head, _, rest = data.partition(b"\r\n\r\n")
    return int(head.split()[1]), rest


TOKEN = {"x-api-key": "run-token"}


def msg(max_tokens=100, **extra) -> dict:
    return {"model": "m", "max_tokens": max_tokens, "messages": [], **extra}


class ProxyTests(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="rp-", dir="/tmp"))
        self.sock = self.dir / "m.sock"

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def make(self, upstream, reserved=1_000_000.0, unit="tokens", prices=None, margin=0, **kw):
        meter = proxy.Meter(unit, prices or {}, reserved, input_margin=margin)
        p = proxy.ModelProxy(self.sock, "run-token", "sk-real", "https://api.example.test",
                             ("/v1/messages", "/v1/messages/count_tokens"),
                             meter, connection_factory=upstream, **kw)
        p.start()
        self.addCleanup(p.stop)
        return p, meter

    # identity and routing
    def test_swaps_token_for_key_and_meters_json_usage(self):
        up = FakeUpstream(usage={"input_tokens": 10, "output_tokens": 5})
        p, meter = self.make(up)
        status, _ = unix_post(self.sock, "/v1/messages", msg(), {**TOKEN, "anthropic-version": "2023-06-01", "Cookie": "x=1"})
        self.assertEqual(200, status)
        headers = up.requests[0][3]
        self.assertEqual("sk-real", headers["x-api-key"])
        self.assertNotIn("Cookie", headers)
        self.assertEqual(15, meter.spent)
        self.assertEqual(0, meter.remaining() - (meter.reserved - 15))
        self.assertEqual(0o600, os.stat(self.sock).st_mode & 0o777)

    def test_refuses_wrong_token_and_paths(self):
        up = FakeUpstream(body=b"{}")
        self.make(up)
        self.assertEqual(401, unix_post(self.sock, "/v1/messages", msg(), {"x-api-key": "sk-guess"})[0])
        self.assertEqual(403, unix_post(self.sock, "/v1/files", msg(), TOKEN)[0])
        self.assertEqual(403, unix_post(self.sock, "/v1/messages/../files", msg(), TOKEN)[0])
        self.assertEqual(403, unix_post(self.sock, "//evil.test/v1/messages", msg(), TOKEN)[0])
        self.assertEqual(403, unix_post(self.sock, "https://evil.test/v1/messages", msg(), TOKEN)[0])
        self.assertEqual([], up.requests)

    def test_query_string_is_forwarded_to_the_fixed_upstream_path(self):
        up = FakeUpstream(usage={"input_tokens": 1, "output_tokens": 1})
        self.make(up)
        self.assertEqual(200, unix_post(self.sock, "/v1/messages?beta=true", msg(), TOKEN)[0])
        self.assertEqual("/v1/messages?beta=true", up.requests[0][1])

    def test_generation_requires_max_tokens(self):
        up = FakeUpstream(usage={"input_tokens": 1, "output_tokens": 1})
        self.make(up)
        for bad in ({"model": "m"}, msg(max_tokens=0), msg(max_tokens=True), msg(max_tokens="5")):
            self.assertEqual(400, unix_post(self.sock, "/v1/messages", bad, TOKEN)[0])
        self.assertEqual([], up.requests)

    # metering
    def test_meters_streaming_usage(self):
        sse = (b'event: message_start\ndata: {"type":"message_start","message":{"model":"m","usage":{"input_tokens":20,"output_tokens":1}}}\n\n'
               b'event: message_delta\ndata: {"type":"message_delta","usage":{"output_tokens":7}}\n\n'
               b'event: message_stop\ndata: {"type":"message_stop"}\n\n')
        p, meter = self.make(FakeUpstream(body=sse, headers={"content-type": "text/event-stream"}))
        status, body = unix_post(self.sock, "/v1/messages", msg(stream=True), TOKEN)
        self.assertEqual(200, status)
        self.assertEqual(sse, body)
        self.assertEqual(27, meter.spent)

    def test_incomplete_stream_is_charged_its_full_hold(self):
        sse = b'event: message_start\ndata: {"type":"message_start","message":{"usage":{"input_tokens":20,"output_tokens":1}}}\n\n'
        p, meter = self.make(FakeUpstream(body=sse, headers={"content-type": "text/event-stream"}))
        payload = msg(max_tokens=500, stream=True)
        unix_post(self.sock, "/v1/messages", payload, TOKEN)
        self.assertEqual(len(json.dumps(payload)) + 500, meter.spent)

    def test_upstream_errors_are_not_charged(self):
        p, meter = self.make(FakeUpstream(status=529, body=b'{"type":"error"}'))
        self.assertEqual(529, unix_post(self.sock, "/v1/messages", msg(), TOKEN)[0])
        self.assertEqual(0, meter.spent)
        self.assertEqual(meter.reserved, meter.remaining())

    def test_count_tokens_is_not_held(self):
        up = FakeUpstream(body=b'{"input_tokens": 12}')
        p, meter = self.make(up, reserved=1)
        self.assertEqual(200, unix_post(self.sock, "/v1/messages/count_tokens", {"model": "m", "messages": []}, TOKEN)[0])
        self.assertEqual(0, meter.spent)

    def test_usd_refuses_unpriced_models(self):
        up = FakeUpstream(usage={"input_tokens": 1_000_000, "output_tokens": 0})
        p, meter = self.make(up, reserved=1000, unit="usd", prices={"priced": {"input": 3, "output": 15}})
        self.assertEqual(403, unix_post(self.sock, "/v1/messages", {**msg(), "model": "other"}, TOKEN)[0])
        self.assertEqual(200, unix_post(self.sock, "/v1/messages", {**msg(), "model": "priced"}, TOKEN)[0])
        self.assertAlmostEqual(3.0, meter.spent)

    # R-1: the reservation is a hard ceiling under concurrency
    def test_concurrent_requests_never_exceed_the_reservation(self):
        # Each response really spends what it may: the old proxy let 20 of these through
        # against a 1000-token reservation (spent 5000).
        up = FakeUpstream(delay=0.3, usage={"input_tokens": 40, "output_tokens": 200})
        stops = []
        p, meter = self.make(up, reserved=1000)
        p.on_exhausted = lambda: stops.append(1)
        results = []

        def call():
            try:
                results.append(unix_post(self.sock, "/v1/messages", msg(max_tokens=200), TOKEN)[0])
            except (OSError, IndexError):
                results.append("dropped")
        threads = [threading.Thread(target=call) for _ in range(20)]
        [t.start() for t in threads]
        [t.join() for t in threads]
        self.assertLessEqual(meter.spent, meter.reserved)
        self.assertLessEqual(up.peak, proxy.MAX_IN_FLIGHT)
        self.assertIn(402, results)
        self.assertTrue(stops, "the run must be stopped once the budget cannot cover a request")
        self.assertEqual(0, meter.overruns)

    # R-3: max_tokens is lowered to what the budget can pay for
    def test_max_tokens_is_clamped_to_the_remaining_budget(self):
        up = FakeUpstream(usage={"input_tokens": 1, "output_tokens": 1})
        p, meter = self.make(up, reserved=1000)
        payload = msg(max_tokens=64000)
        self.assertEqual(200, unix_post(self.sock, "/v1/messages", payload, TOKEN)[0])
        forwarded = up.forwarded()["max_tokens"]
        self.assertLessEqual(len(json.dumps(payload)) + forwarded, 1000)
        self.assertGreater(forwarded, 0)

    def test_thinking_budget_follows_the_clamp_or_is_refused(self):
        up = FakeUpstream(usage={"input_tokens": 1, "output_tokens": 1})
        p, meter = self.make(up, reserved=5000)
        thinking = {"type": "enabled", "budget_tokens": 30000}
        self.assertEqual(200, unix_post(self.sock, "/v1/messages", msg(max_tokens=64000, thinking=thinking), TOKEN)[0])
        sent = up.forwarded()
        self.assertLess(sent["thinking"]["budget_tokens"], sent["max_tokens"])
        p2_dir = Path(tempfile.mkdtemp(prefix="rp-", dir="/tmp"))
        self.addCleanup(shutil.rmtree, p2_dir, True)
        meter2 = proxy.Meter("tokens", {}, 900, input_margin=0)
        p2 = proxy.ModelProxy(p2_dir / "m.sock", "run-token", "sk", "https://a.test", ("/v1/messages",), meter2,
                              connection_factory=up)
        p2.start()
        self.addCleanup(p2.stop)
        self.assertEqual(402, unix_post(p2_dir / "m.sock", "/v1/messages", msg(max_tokens=64000, thinking=thinking), TOKEN)[0])
        self.assertEqual(0, meter2.spent)

    def test_budget_exhaustion_stops_the_run(self):
        up = FakeUpstream(usage={"input_tokens": 60, "output_tokens": 60})
        p, meter = self.make(up, reserved=400)
        stopped = threading.Event()
        p.on_exhausted = stopped.set
        statuses = [unix_post(self.sock, "/v1/messages", msg(max_tokens=100), TOKEN)[0] for _ in range(5)]
        self.assertIn(402, statuses)
        self.assertTrue(stopped.is_set())
        self.assertLessEqual(meter.spent, 400)

    # R-4: the container cannot exhaust relay threads or memory
    def test_idle_and_excess_connections_are_bounded(self):
        up = FakeUpstream(usage={"input_tokens": 1, "output_tokens": 1})
        p, meter = self.make(up, idle_timeout=0.5)
        before = threading.active_count()
        socks = []
        for _ in range(100):
            s = socket.socket(socket.AF_UNIX)
            s.connect(str(self.sock))
            socks.append(s)
        time.sleep(0.3)
        self.assertLessEqual(threading.active_count() - before, proxy.MAX_CONNECTIONS + 1)
        time.sleep(1.0)
        for s in socks:
            s.close()
        self.assertEqual(200, unix_post(self.sock, "/v1/messages", msg(), TOKEN)[0])

    def test_oversized_body_is_refused(self):
        up = FakeUpstream(usage={"input_tokens": 1, "output_tokens": 1})
        self.make(up)
        s = socket.socket(socket.AF_UNIX)
        s.connect(str(self.sock))
        s.sendall(f"POST /v1/messages HTTP/1.0\r\nContent-Length: {proxy.MAX_BODY + 1}\r\nx-api-key: run-token\r\n\r\n".encode())
        self.assertIn(b" 413 ", s.recv(4096))
        s.close()
        self.assertEqual([], up.requests)


# --- service -------------------------------------------------------------------------------------
class FakeRun:
    instances = []

    def __init__(self, cfg, run_id, command, output):
        self.run_id, self.command, self.output = run_id, command, output
        self.stop_reason = None
        FakeRun.instances.append(self)

    def stop(self, reason):
        self.stop_reason = reason

    def run(self, instruction):
        self.output.write_text("result for: " + instruction)
        return 0, hashlib.sha256(self.output.read_bytes()).hexdigest()


class FakeProxy:
    def __init__(self, socket_path, token, key, upstream, paths, meter):
        self.meter = meter
        self.on_exhausted = None

    def start(self):
        self.meter.add("m", {"input_tokens": 100, "output_tokens": 50})

    def stop(self):
        pass


class ServiceTests(Env):
    def setUp(self):
        super().setUp()
        uid = mock.patch.object(runner.os, "getuid", return_value=1000)
        uid.start()
        self.addCleanup(uid.stop)
        self.relay = service.Relay(self.cfg, self.store, self.contract, runner_factory=FakeRun,
                                   proxy_factory=FakeProxy, api_key="sk-test")
        self.owner = self.member(OWNER, "owner")
        self.op = self.member("ana", "operator")
        self.viewer = self.member("bo", "viewer")

    def wait_state(self, run_id, state, timeout=10):
        deadline = time.time() + timeout
        while time.time() < deadline:
            if self.store.run(run_id)["state"] == state:
                return
            time.sleep(0.02)
        self.fail(f"run did not reach {state}: {self.store.run(run_id)['state']}")

    def test_roles_are_enforced(self):
        with self.assertRaises(service.Forbidden):
            self.relay.request_run(self.viewer, "A", "do it")
        run_id = self.relay.request_run(self.op, "A", "do it")
        with self.assertRaises(service.Forbidden):
            self.relay.approve(self.op, run_id)
        with self.assertRaises(service.Forbidden):
            self.relay.invite(self.op, "eve", "operator")
        with self.assertRaises(service.Forbidden):
            self.relay.review(self.op, run_id, True, ["contract_met"], "ok")

    def test_full_lifecycle_is_admitted_metered_and_verifiable(self):
        run_id = self.relay.request_run(self.op, "A", "analyse")
        reserved = self.relay.approve(self.owner, run_id)
        self.assertEqual(150000, reserved)
        self.wait_state(run_id, "completed")
        row = self.store.run(run_id)
        self.assertEqual(150, row["actual_cost"])
        self.assertIsNone(row["error"])
        with self.assertRaisesRegex(service.Conflict, "predicates"):
            self.relay.review(self.owner, run_id, True, [], "missing predicates")
        self.relay.review(self.owner, run_id, True, ["contract_met"], "meets the contract")
        self.assertEqual("accepted", self.store.run(run_id)["state"])
        events = self.contract.events()
        self.assertEqual(["start", "finish"], [e["type"] for e in events])
        self.assertEqual(150, events[1]["actual_cost"])
        self.assertTrue(events[1]["evidence_refs"][0].startswith("relay-output:sha256:"))
        self.assertEqual([], verify(self.cfg))

    def test_refused_start_runs_nothing(self):
        FakeRun.instances.clear()
        run_id = self.relay.request_run(self.op, "C", "needs A and B first")
        with self.assertRaisesRegex(service.Conflict, "DEPENDENCY"):
            self.relay.approve(self.owner, run_id)
        self.assertEqual("failed_to_start", self.store.run(run_id)["state"])
        self.assertEqual([], FakeRun.instances)
        self.assertEqual([], self.contract.events())

    def test_double_approval_cannot_start_twice(self):
        run_id = self.relay.request_run(self.op, "A", "once")
        self.relay.approve(self.owner, run_id)
        with self.assertRaises(service.Conflict):
            self.relay.approve(self.owner, run_id)
        self.assertEqual(1, sum(e["type"] == "start" for e in self.contract.events()))
        self.wait_state(run_id, "completed")

    def test_unit_mismatch_is_refused(self):
        inst = self.instance()
        inst["budget"]["unit"] = "usd"
        self.write_instance(inst)
        run_id = self.relay.request_run(self.op, "A", "x")
        with self.assertRaisesRegex(service.Conflict, "unit"):
            self.relay.approve(self.owner, run_id)

    def test_owner_name_must_match_mandate(self):
        self.store.close()
        shutil.rmtree(self.tmp)
        self.setUp_without_owner()
        impostor = self.member("not-the-owner", "owner")
        run_id = self.relay.request_run(impostor, "A", "x")
        with self.assertRaisesRegex(service.Forbidden, "mandate owner"):
            self.relay.approve(impostor, run_id)

    def setUp_without_owner(self):
        Env.setUp(self)
        self.relay = service.Relay(self.cfg, self.store, self.contract, runner_factory=FakeRun,
                                   proxy_factory=FakeProxy, api_key="sk-test")

    def test_recover_charges_the_reservation(self):
        run_id = self.relay.request_run(self.op, "A", "x")
        with self.store.tx() as db:
            db.execute("UPDATE runs SET state='approved' WHERE id=?", (run_id,))
        self.contract.start(run_id, "A", OWNER)
        self.assertEqual([run_id], self.relay.recover())
        row = self.store.run(run_id)
        self.assertEqual("completed", row["state"])
        self.assertEqual(150000, row["actual_cost"])
        self.relay.review(self.owner, run_id, False, [], "interrupted")
        self.assertEqual([], verify(self.cfg))

    def test_running_as_root_fails_the_run_safely(self):
        with mock.patch.object(runner.os, "getuid", return_value=0):
            run_id = self.relay.request_run(self.op, "A", "x")
            self.relay.approve(self.owner, run_id)
            self.wait_state(run_id, "completed")
        row = self.store.run(run_id)
        self.assertIn("root", row["error"])
        with self.assertRaises(service.Conflict):
            self.relay.review(self.owner, run_id, True, ["contract_met"], "cannot accept a failed run")
        self.relay.review(self.owner, run_id, False, [], "failed")
        self.assertEqual([], verify(self.cfg))

    def test_message_limits(self):
        with self.assertRaises(ValueError):
            self.relay.post_message(self.viewer, "x" * (service.MAX_MESSAGE + 1))
        with self.assertRaises(ValueError):
            self.relay.post_message(self.viewer, "   ")
        self.relay.post_message(self.viewer, "<script>alert(1)</script>")


# --- HTTP server ---------------------------------------------------------------------------------
class ServerTests(Env):
    def setUp(self):
        super().setUp()
        sock = socket.socket()
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
        sock.close()
        self.cfg = config.parse(raw_config(self.tmp, bind={"host": "127.0.0.1", "port": port},
                                           public_origin=f"http://127.0.0.1:{port}"), self.tmp)
        self.relay = service.Relay(self.cfg, self.store, self.contract, runner_factory=FakeRun,
                                   proxy_factory=FakeProxy, api_key="sk-test")
        self.httpd = server.serve(self.relay)
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()
        self.port = port
        self.origin = f"http://127.0.0.1:{port}"
        owner_id = auth.create_member(self.store, OWNER, "owner", "t")
        self.owner_invite = auth.create_invite(self.store, owner_id, "t")

    def tearDown(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        super().tearDown()

    def req(self, method, path, body=None, headers=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        h = {"Host": f"127.0.0.1:{self.port}"}
        h.update(headers or {})
        data = None
        if body is not None:
            data = json.dumps(body).encode()
            h.setdefault("Content-Type", "application/json")
        conn.request(method, path, body=data, headers=h)
        resp = conn.getresponse()
        payload = resp.read()
        conn.close()
        return resp, payload

    def login(self):
        resp, payload = self.req("POST", "/api/join", {"token": self.owner_invite}, {"Origin": self.origin})
        self.assertEqual(200, resp.status, payload)
        cookie = resp.getheader("Set-Cookie")
        return cookie.split(";")[0], json.loads(payload)["csrf"], cookie

    def test_security_headers_and_static_page(self):
        resp, body = self.req("GET", "/")
        self.assertEqual(200, resp.status)
        csp = resp.getheader("Content-Security-Policy")
        self.assertIn("script-src 'self'", csp)
        self.assertNotIn("unsafe-inline", csp)
        self.assertIn("frame-ancestors 'none'", csp)
        self.assertEqual("nosniff", resp.getheader("X-Content-Type-Options"))
        self.assertNotIn(b"<script>", body.replace(b'<script src="/static/room.js" defer></script>', b""))

    def test_ui_never_uses_inner_html(self):
        js = (RELAY / "nexus_relay" / "static" / "room.js").read_text()
        for sink in ("innerHTML", "outerHTML", "insertAdjacentHTML", "document.write", "eval(", "new Function"):
            self.assertNotIn(sink, js.replace("Never use innerHTML", ""))

    def test_api_requires_session(self):
        resp, _ = self.req("GET", "/api/log")
        self.assertEqual(401, resp.status)

    def test_join_sets_hardened_cookie_and_is_single_use(self):
        cookie, csrf, raw = self.login()
        self.assertIn("HttpOnly", raw)
        self.assertIn("SameSite=Strict", raw)
        resp, _ = self.req("POST", "/api/join", {"token": self.owner_invite}, {"Origin": self.origin})
        self.assertEqual(401, resp.status)
        resp, payload = self.req("GET", "/api/me", headers={"Cookie": cookie})
        self.assertEqual(OWNER, json.loads(payload)["member"]["name"])

    def test_writes_need_origin_and_csrf(self):
        cookie, csrf, _ = self.login()
        body = {"text": "hi"}
        resp, _ = self.req("POST", "/api/messages", body, {"Cookie": cookie, "X-Relay-CSRF": csrf})
        self.assertEqual(403, resp.status)
        resp, _ = self.req("POST", "/api/messages", body, {"Cookie": cookie, "Origin": "https://evil.test", "X-Relay-CSRF": csrf})
        self.assertEqual(403, resp.status)
        resp, _ = self.req("POST", "/api/messages", body, {"Cookie": cookie, "Origin": self.origin})
        self.assertEqual(403, resp.status)
        resp, _ = self.req("POST", "/api/messages", body, {"Cookie": cookie, "Origin": self.origin, "X-Relay-CSRF": csrf})
        self.assertEqual(200, resp.status)

    def test_rejects_unknown_host_header(self):
        resp, _ = self.req("GET", "/", headers={"Host": "attacker.test"})
        self.assertEqual(421, resp.status)

    def test_join_is_rate_limited(self):
        statuses = [self.req("POST", "/api/join", {"token": "x" * 43}, {"Origin": self.origin})[0].status for _ in range(12)]
        self.assertIn(429, statuses)

    def test_internal_errors_do_not_leak(self):
        cookie, csrf, _ = self.login()
        with mock.patch.object(self.relay, "runs", side_effect=RuntimeError("secret detail /home/x")):
            resp, payload = self.req("GET", "/api/runs", headers={"Cookie": cookie})
        self.assertEqual(500, resp.status)
        self.assertNotIn(b"secret", payload)


if __name__ == "__main__":
    unittest.main()
