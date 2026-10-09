"""Strict relay configuration. Unknown keys and unsafe values are errors, never defaults."""
from __future__ import annotations

from dataclasses import dataclass
import ipaddress
import json
import os
from pathlib import Path
import re
import stat
from urllib.parse import urlsplit

REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIG_NAME = "relay.json"
DEFAULT_MODEL_PATHS = ("/v1/messages", "/v1/messages/count_tokens")
_SIZE_RE = re.compile(r"^[1-9][0-9]*[kmg]$")
_CPUS_RE = re.compile(r"^(?:[1-9][0-9]*)(?:\.[0-9]+)?$|^0\.[0-9]*[1-9][0-9]*$")


class ConfigError(ValueError):
    pass


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ConfigError(message)


def _keys(obj: dict, allowed: set[str], required: set[str], where: str) -> None:
    _require(isinstance(obj, dict), f"{where}: object required")
    unknown = set(obj) - allowed
    _require(not unknown, f"{where}: unknown keys {sorted(unknown)}")
    missing = required - set(obj)
    _require(not missing, f"{where}: missing keys {sorted(missing)}")


def _text(value, where: str) -> str:
    _require(isinstance(value, str) and value.strip() != "", f"{where}: non-empty text required")
    return value


@dataclass(frozen=True)
class RuntimeConfig:
    engine: str
    image: str
    agent_command: tuple[str, ...]
    memory: str
    cpus: str
    pids: int
    timeout_seconds: int
    allow_rootful_engine: bool = False


@dataclass(frozen=True)
class ModelConfig:
    upstream: str
    api_key_env: str
    cost_unit: str
    prices: dict
    allowed_paths: tuple[str, ...]


@dataclass(frozen=True)
class RelayConfig:
    data_dir: Path
    instance_path: Path
    events_path: Path
    host: str
    port: int
    public_origin: str
    runtime: RuntimeConfig
    model: ModelConfig

    @property
    def db_path(self) -> Path:
        return self.data_dir / "relay.db"

    @property
    def workspaces_dir(self) -> Path:
        return self.data_dir / "workspaces"

    @property
    def runs_dir(self) -> Path:
        return self.data_dir / "runs"

    @property
    def secure_cookies(self) -> bool:
        return self.public_origin.startswith("https://")


def _loopback(host: str) -> bool:
    if host == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def _origin(value: str) -> str:
    _text(value, "public_origin")
    parts = urlsplit(value)
    _require(parts.scheme in ("http", "https") and parts.netloc != "", "public_origin: http(s) origin required")
    _require(parts.path in ("", "/") and not parts.query and not parts.fragment and "@" not in parts.netloc,
             "public_origin: scheme://host[:port] only")
    if parts.scheme == "http":
        _require(_loopback(parts.hostname or ""), "public_origin: plain http is allowed only for loopback; use a TLS tunnel")
    return f"{parts.scheme}://{parts.netloc}"


def _upstream(value: str) -> str:
    parts = urlsplit(_text(value, "model.upstream"))
    _require(parts.scheme == "https" and parts.hostname, "model.upstream: https URL required")
    _require(parts.path in ("", "/") and not parts.query and "@" not in parts.netloc, "model.upstream: origin only")
    return f"https://{parts.netloc}"


def check_private(path: Path, *, directory: bool) -> None:
    """Refuse group/other access: these files hold sessions, invites and the event chain."""
    mode = stat.S_IMODE(path.stat().st_mode)
    _require(mode & 0o077 == 0, f"{path}: permissions {oct(mode)} allow other users; expected {'0700' if directory else '0600'}")


def parse(raw: dict, data_dir: Path) -> RelayConfig:
    _keys(raw, {"schema_version", "instance", "events", "bind", "public_origin", "runtime", "model"},
          {"schema_version", "instance", "events", "bind", "public_origin", "runtime", "model"}, "config")
    _require(raw["schema_version"] == 1, "config: schema_version must be 1")

    bind = raw["bind"]
    _keys(bind, {"host", "port"}, {"host", "port"}, "bind")
    _require(_loopback(_text(bind["host"], "bind.host")), "bind.host: only loopback addresses are allowed; expose through a TLS tunnel")
    _require(type(bind["port"]) is int and 1024 <= bind["port"] <= 65535, "bind.port: 1024-65535")

    rt = raw["runtime"]
    _keys(rt, {"engine", "image", "agent_command", "memory", "cpus", "pids", "timeout_seconds", "allow_rootful_engine"},
          {"engine", "image", "agent_command"}, "runtime")
    _require(rt["engine"] in ("docker", "podman"), "runtime.engine: docker or podman")
    image = _text(rt["image"], "runtime.image")
    _require(not image.startswith("-"), "runtime.image: invalid")
    command = rt["agent_command"]
    _require(isinstance(command, list) and command and all(isinstance(c, str) and c for c in command),
             "runtime.agent_command: non-empty list of strings")
    memory = rt.get("memory", "4g")
    _require(isinstance(memory, str) and bool(_SIZE_RE.match(memory)), "runtime.memory: e.g. 4g")
    cpus = rt.get("cpus", "2")
    _require(isinstance(cpus, str) and bool(_CPUS_RE.match(cpus)), "runtime.cpus: e.g. 2 or 1.5")
    pids = rt.get("pids", 512)
    _require(type(pids) is int and 32 <= pids <= 4096, "runtime.pids: 32-4096")
    timeout = rt.get("timeout_seconds", 1800)
    _require(type(timeout) is int and 30 <= timeout <= 6 * 3600, "runtime.timeout_seconds: 30-21600")
    rootful = rt.get("allow_rootful_engine", False)
    _require(type(rootful) is bool, "runtime.allow_rootful_engine: boolean")

    model = raw["model"]
    _keys(model, {"upstream", "api_key_env", "cost_unit", "prices", "allowed_paths"},
          {"upstream", "api_key_env", "cost_unit"}, "model")
    _require(model["cost_unit"] in ("tokens", "usd"), "model.cost_unit: tokens or usd")
    prices = model.get("prices", {})
    _require(isinstance(prices, dict), "model.prices: object")
    for name, price in prices.items():
        _keys(price, {"input", "output", "cache_write", "cache_read"}, {"input", "output"}, f"model.prices.{name}")
        _require(all(isinstance(v, (int, float)) and v >= 0 for v in price.values()), f"model.prices.{name}: non-negative numbers")
    if model["cost_unit"] == "usd":
        _require(bool(prices), "model.prices: required when cost_unit is usd")
    paths = tuple(model.get("allowed_paths", DEFAULT_MODEL_PATHS))
    _require(all(isinstance(p, str) and p.startswith("/v1/") and ".." not in p for p in paths) and paths,
             "model.allowed_paths: /v1/ paths only")

    instance = Path(_text(raw["instance"], "instance")).expanduser()
    events = Path(_text(raw["events"], "events")).expanduser()
    if not instance.is_absolute():
        instance = (data_dir / instance).resolve()
    if not events.is_absolute():
        events = (data_dir / events).resolve()

    return RelayConfig(
        data_dir=data_dir,
        instance_path=instance,
        events_path=events,
        host=bind["host"],
        port=bind["port"],
        public_origin=_origin(raw["public_origin"]),
        runtime=RuntimeConfig(rt["engine"], image, tuple(command), memory, cpus, pids, timeout, rootful),
        model=ModelConfig(_upstream(model["upstream"]), _text(model["api_key_env"], "model.api_key_env"),
                          model["cost_unit"], prices, paths),
    )


def load(data_dir: Path) -> RelayConfig:
    data_dir = data_dir.expanduser().resolve()
    _require(data_dir.is_dir(), f"{data_dir}: not initialised; run `nexus-relay init`")
    check_private(data_dir, directory=True)
    path = data_dir / CONFIG_NAME
    check_private(path, directory=False)
    try:
        raw = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        raise ConfigError(f"{path}: invalid JSON ({exc})") from exc
    return parse(raw, data_dir)


def model_api_key(cfg: RelayConfig) -> str:
    key = os.environ.get(cfg.model.api_key_env, "")
    _require(key.strip() != "", f"{cfg.model.api_key_env} is not set; the relay needs it for the model proxy")
    return key.strip()
