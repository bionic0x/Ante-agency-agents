"""Container execution for one admitted run.

The command is built from fixed hardening flags plus values that come from the relay
config and the NEXUS task, never from the person who requested the run. The requester's
instruction reaches the agent only on stdin."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import re
import runpy
import secrets
import subprocess
import threading

from .config import REPO_ROOT, RelayConfig

FORWARDER = REPO_ROOT / "relay" / "container" / "forwarder.py"
SAFE_SEGMENT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
MAX_OUTPUT = 2 * 1024 * 1024
ENGINE_KILL_TIMEOUT = 20
KILL_GRACE_SECONDS = 10


class RunError(RuntimeError):
    pass


def safe_segment(value: str, what: str) -> str:
    if not SAFE_SEGMENT.match(value or "") or value in (".", ".."):
        raise RunError(f"{what} {value!r} is not a safe path segment")
    return value


def agent_profile(slug: str) -> Path:
    _, agents, _ = runpy.run_path(str(REPO_ROOT / "scripts" / "build-catalog.py"))["collect"]()
    for agent in agents:
        if agent["slug"] == slug:
            path = (REPO_ROOT / agent["path"]).resolve()
            if REPO_ROOT not in path.parents:
                raise RunError("agent profile outside the repository")
            return path
    raise RunError(f"agent {slug!r} is not in the canonical catalog")


@dataclass
class RunPaths:
    workspace: Path
    socket_dir: Path
    output: Path

    @property
    def socket(self) -> Path:
        return self.socket_dir / "model.sock"


def prepare(cfg: RelayConfig, run_id: str, task: dict) -> RunPaths:
    run_id = safe_segment(run_id, "run id")
    workspace = cfg.workspaces_dir / workspace_name(task["id"])
    run_dir = cfg.runs_dir / run_id
    socket_dir = run_dir / "sock"
    for d in (cfg.workspaces_dir, cfg.runs_dir, workspace, run_dir, socket_dir):
        d.mkdir(mode=0o700, exist_ok=True)
        os.chmod(d, 0o700)  # nosemgrep: insecure-file-permissions -- owner-only; the rule's 0o644 is looser
    return RunPaths(workspace=workspace, socket_dir=socket_dir, output=run_dir / "output.txt")


def workspace_name(task_id: str) -> str:
    """One persistent workspace per NEXUS task, so retries see earlier work."""
    if SAFE_SEGMENT.match(task_id) and task_id not in (".", ".."):
        return "task-" + task_id
    return "task-" + hashlib.sha256(task_id.encode()).hexdigest()[:24]


def container_name(run_id: str) -> str:
    return f"ante-relay-{safe_segment(run_id, 'run id')}"


def build_command(cfg: RelayConfig, run_id: str, paths: RunPaths, profile: Path, run_token: str) -> list[str]:
    rt = cfg.runtime
    uid, gid = os.getuid(), os.getgid()
    if uid == 0:
        raise RunError("refusing to run agents as root; start the relay as an unprivileged user")
    cmd = [
        rt.engine, "run", "--rm", "-i",
        # Never fetch at run time: the image must already be present, ideally by digest.
        "--pull", "never",
        "--name", container_name(run_id),
        "--network", "none",
        "--read-only",
        "--cap-drop", "ALL",
        "--security-opt", "no-new-privileges",
        "--user", f"{uid}:{gid}",
        "--pids-limit", str(rt.pids),
        "--memory", rt.memory,
        "--memory-swap", rt.memory,
        "--cpus", rt.cpus,
        "--tmpfs", "/tmp:rw,nosuid,nodev,size=512m",
        "--mount", f"type=bind,source={paths.workspace},target=/workspace",
        "--mount", f"type=bind,source={profile},target=/agent/profile.md,readonly",
        "--mount", f"type=bind,source={FORWARDER},target=/relay/forwarder.py,readonly",
        # Connecting to a unix socket needs no write access to its directory.
        "--mount", f"type=bind,source={paths.socket_dir},target=/run/relay,readonly",
        "--workdir", "/workspace",
        "--env", "HOME=/tmp",
        "--env", "ANTHROPIC_BASE_URL=http://127.0.0.1:8787",
        "--env", f"ANTHROPIC_API_KEY={run_token}",
        "--env", "AGENT_PROFILE=/agent/profile.md",
        # In-container deadline: the forwarder kills the agent even if the engine cannot.
        "--env", f"RELAY_DEADLINE_SECONDS={rt.timeout_seconds}",
        "--entrypoint", "python3",
    ]
    if rt.engine == "podman":
        cmd += ["--userns", "keep-id"]
    cmd += [rt.image, "/relay/forwarder.py", "--", *rt.agent_command]
    for value in (str(paths.workspace), str(profile), str(paths.socket_dir)):
        if "," in value:
            raise RunError(f"path contains a comma, which --mount cannot express safely: {value}")
    return cmd


def new_run_token() -> str:
    return "relay-run-" + secrets.token_urlsafe(32)


ENGINE_ENV = ("PATH", "HOME", "XDG_RUNTIME_DIR", "DOCKER_HOST", "DOCKER_CONTEXT", "DOCKER_CONFIG", "CONTAINER_HOST")


def engine_environment() -> dict:
    """The container CLI gets only what it needs to reach its engine, never the model key."""
    return {k: os.environ[k] for k in ENGINE_ENV if k in os.environ}


def engine_is_rootless(engine: str) -> bool | None:
    """True for a rootless engine, False for one running as root, None if unknown."""
    query = {"podman": ["info", "--format", "{{.Host.Security.Rootless}}"],
             "docker": ["info", "--format", "{{json .SecurityOptions}}"]}[engine]
    try:
        out = subprocess.run([engine, *query], capture_output=True, text=True, timeout=30,
                             check=True, env=engine_environment()).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None
    if engine == "podman":
        return {"true": True, "false": False}.get(out.lower())
    return "name=rootless" in out


def image_is_pinned(image: str) -> bool:
    return "@sha256:" in image or image.startswith("sha256:")


def check_engine(cfg: RelayConfig) -> str:
    """Refuse a root-owned engine: access to it is root on the host (audit R-2)."""
    rootless = engine_is_rootless(cfg.runtime.engine)
    if rootless is None:
        raise RunError(f"cannot reach the {cfg.runtime.engine} engine to check how it runs")
    if rootless and cfg.runtime.engine == "docker":
        raise RunError("rootless Docker is not supported (the proxy socket is not reachable "
                       "across its uid mapping); use rootless Podman")
    if not rootless:
        if not cfg.runtime.allow_rootful_engine:
            raise RunError(f"{cfg.runtime.engine} runs as root, and any account that can use it is root on "
                           "this host. Use rootless Podman, or set runtime.allow_rootful_engine to true "
                           "to accept that risk explicitly.")
        return "rootful (explicitly allowed: the relay account is root-equivalent)"
    return "rootless"


class ContainerRun:
    """Runs the container with the instruction on stdin, keeps a bounded output file and
    enforces the wall-clock limit. `stop()` is safe to call from any thread."""

    def __init__(self, cfg: RelayConfig, run_id: str, command: list[str], output: Path):
        self.cfg = cfg
        self.run_id = run_id
        self.command = command
        self.output = output
        self._proc: subprocess.Popen | None = None
        self._stopped = threading.Event()
        self.stop_reason: str | None = None

    def stop(self, reason: str) -> None:
        """Request termination without blocking the caller (a proxy thread or a timer)."""
        if self._stopped.is_set():
            return
        self.stop_reason = reason
        self._stopped.set()
        threading.Thread(target=self._terminate, name=f"relay-stop-{self.run_id}", daemon=True).start()

    def _terminate(self) -> None:
        # Layer 1: ask the engine to kill the container.
        try:
            subprocess.run([self.cfg.runtime.engine, "kill", container_name(self.run_id)],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=ENGINE_KILL_TIMEOUT,
                           check=False, env=engine_environment())
        except (OSError, subprocess.TimeoutExpired):
            pass
        # Layer 2: if the engine could not, end the client so the run is reconciled; the
        # proxy socket is removed with it, so a surviving container has no model access.
        # Layer 3 (inside the container): the forwarder enforces RELAY_DEADLINE_SECONDS.
        proc = self._proc
        if proc is None:
            return
        try:
            proc.wait(timeout=KILL_GRACE_SECONDS)
        except subprocess.TimeoutExpired:
            proc.kill()

    def run(self, instruction: str) -> tuple[int, str]:
        fd = os.open(self.output, os.O_CREAT | os.O_TRUNC | os.O_WRONLY, 0o600)
        written = 0
        digest = hashlib.sha256()
        with os.fdopen(fd, "wb") as sink:
            self._proc = subprocess.Popen(self.command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                          stderr=subprocess.STDOUT, env=engine_environment())
            timer = threading.Timer(self.cfg.runtime.timeout_seconds, self.stop, args=("timeout",))
            timer.daemon = True
            timer.start()
            try:
                assert self._proc.stdin is not None and self._proc.stdout is not None
                try:
                    self._proc.stdin.write(instruction.encode())
                    self._proc.stdin.close()
                except BrokenPipeError:
                    pass
                for chunk in iter(lambda: self._proc.stdout.read(8192), b""):
                    if written < MAX_OUTPUT:
                        part = chunk[: MAX_OUTPUT - written]
                        sink.write(part)
                        digest.update(part)
                        written += len(part)
                code = self._proc.wait()
            finally:
                timer.cancel()
                if self._proc.stdout:
                    self._proc.stdout.close()
        return code, digest.hexdigest()
