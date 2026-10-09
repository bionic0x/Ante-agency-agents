"""End-to-end isolation check with a real container engine.

    RELAY_E2E=1 RELAY_E2E_IMAGE=python:3.13-slim python3 relay/tests/e2e_container.py

Runs as an unprivileged user with access to docker or podman. The "agent" is a probe
script that tries to break out; the test passes only if every attempt fails and the
model call through the relay proxy succeeds with the real key injected upstream."""
from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import http.client
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import threading
import unittest

RELAY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RELAY))

from nexus_relay import config, proxy, runner  # noqa: E402

PROBE = r'''
import json, os, socket, urllib.request
r = {}
def attempt(name, fn):
    try:
        fn(); r[name] = "allowed"
    except Exception as e:
        r[name] = "blocked:" + type(e).__name__
attempt("internet", lambda: socket.create_connection(("1.1.1.1", 443), timeout=3))
attempt("dns", lambda: socket.getaddrinfo("example.com", 443))
attempt("write_root", lambda: open("/pwned", "w").write("x"))
attempt("write_etc", lambda: open("/etc/pwned", "w").write("x"))
attempt("docker_socket", lambda: socket.socket(socket.AF_UNIX).connect("/var/run/docker.sock"))
attempt("write_socket_dir", lambda: open("/run/relay/planted", "w").write("x"))
r["uid"] = os.getuid()
r["key_seen"] = os.environ.get("ANTHROPIC_API_KEY", "")
r["profile_readable"] = os.path.exists("/agent/profile.md")
attempt("write_profile", lambda: open("/agent/profile.md", "a").write("x"))
r["instruction"] = __import__("sys").stdin.read()
req = urllib.request.Request(os.environ["ANTHROPIC_BASE_URL"] + "/v1/messages",
    data=json.dumps({"model": "m", "max_tokens": 5, "messages": []}).encode(),
    headers={"content-type": "application/json", "x-api-key": os.environ["ANTHROPIC_API_KEY"],
             "anthropic-version": "2023-06-01"})
r["model_call"] = json.loads(urllib.request.urlopen(req, timeout=20).read())["content"]
attempt("other_path", lambda: urllib.request.urlopen(urllib.request.Request(
    os.environ["ANTHROPIC_BASE_URL"] + "/v1/files", data=b"{}",
    headers={"x-api-key": os.environ["ANTHROPIC_API_KEY"], "content-type": "application/json"}), timeout=10))
open("/workspace/result.json", "w").write(json.dumps(r))
print(json.dumps(r))
'''


class Stub(BaseHTTPRequestHandler):
    seen_keys: list = []

    def log_message(self, *a):
        pass

    def do_POST(self):
        self.rfile.read(int(self.headers["content-length"]))
        Stub.seen_keys.append(self.headers.get("x-api-key"))
        body = json.dumps({"model": "m", "content": "pong", "usage": {"input_tokens": 3, "output_tokens": 2}}).encode()
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


@unittest.skipUnless(os.environ.get("RELAY_E2E") == "1", "set RELAY_E2E=1 to run against a real container engine")
class ContainerIsolation(unittest.TestCase):
    def test_probe_cannot_escape_and_model_call_works(self):
        engine = os.environ.get("RELAY_E2E_ENGINE", "docker")
        image = os.environ.get("RELAY_E2E_IMAGE", "python:3.13-slim")
        tmp = Path(tempfile.mkdtemp(prefix="relay-e2e-"))
        os.chmod(tmp, 0o700)
        try:
            raw = {"schema_version": 1, "instance": "i.json", "events": "e.jsonl",
                   "bind": {"host": "127.0.0.1", "port": 8770}, "public_origin": "http://127.0.0.1:8770",
                   "runtime": {"engine": engine, "image": image, "agent_command": ["python3", "-c", PROBE],
                               "timeout_seconds": 120},
                   "model": {"upstream": "https://upstream.invalid", "api_key_env": "UNUSED", "cost_unit": "tokens"}}
            cfg = config.parse(raw, tmp)
            stub = ThreadingHTTPServer(("127.0.0.1", 0), Stub)
            threading.Thread(target=stub.serve_forever, daemon=True).start()
            port = stub.server_address[1]
            paths = runner.prepare(cfg, "e2e1", {"id": "A", "resource_scope": []})
            token = runner.new_run_token()
            meter = proxy.Meter("tokens", {}, 100_000)
            p = proxy.ModelProxy(paths.socket, token, "sk-real-upstream-key", cfg.model.upstream,
                                 cfg.model.allowed_paths, meter,
                                 connection_factory=lambda: http.client.HTTPConnection("127.0.0.1", port, timeout=30))
            p.start()
            try:
                cmd = runner.build_command(cfg, "e2e1", paths, runner.agent_profile("general-strategy-director"), token)
                code, digest = runner.ContainerRun(cfg, "e2e1", cmd, paths.output).run("probe instruction")
            finally:
                p.stop()
                stub.shutdown()
            out = paths.output.read_text()
            self.assertEqual(0, code, out)
            r = json.loads((paths.workspace / "result.json").read_text())
            for name in ("internet", "dns", "write_root", "write_etc", "docker_socket", "write_profile",
                         "other_path", "write_socket_dir"):
                self.assertTrue(r[name].startswith("blocked"), f"{name}: {r[name]}")
            self.assertEqual(os.getuid(), r["uid"])
            self.assertNotEqual(0, r["uid"])
            self.assertEqual(token, r["key_seen"])
            self.assertNotIn("sk-real-upstream-key", out)
            self.assertTrue(r["profile_readable"])
            self.assertEqual("probe instruction", r["instruction"])
            self.assertEqual("pong", r["model_call"])
            self.assertEqual(["sk-real-upstream-key"], Stub.seen_keys)
            self.assertEqual(5, meter.spent)
            print(json.dumps(r, indent=2))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
