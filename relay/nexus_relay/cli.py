"""Command line: init, invite, serve, verify."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

from . import auth
from .config import CONFIG_NAME, ConfigError, load, model_api_key, parse
from .nexus import AdmissionError, Contract, engine
from .service import Relay
from .store import ChainError, Store

DEFAULT_DIR = Path(os.environ.get("NEXUS_RELAY_HOME", "~/.ante-relay")).expanduser()


def _write_private(path: Path, text: str) -> None:
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write(text)


def cmd_init(args) -> int:
    if os.getuid() == 0:
        print("refusing to initialise as root; use an unprivileged account", file=sys.stderr)
        return 2
    data_dir = args.data_dir.expanduser().resolve()
    if (data_dir / CONFIG_NAME).exists():
        print(f"{data_dir} is already initialised", file=sys.stderr)
        return 2
    instance_path = args.instance.expanduser().resolve()
    contract = Contract(instance_path, args.events.expanduser().resolve())
    try:
        instance, _ = contract.state()
    except AdmissionError as exc:
        print(f"instance rejected: {exc}", file=sys.stderr)
        return 2
    raw = {
        "schema_version": 1,
        "instance": str(instance_path),
        "events": str(args.events.expanduser().resolve()),
        "bind": {"host": "127.0.0.1", "port": args.port},
        "public_origin": args.public_origin or f"http://127.0.0.1:{args.port}",
        "runtime": {"engine": args.engine, "image": args.image,
                    "agent_command": ["sh", "-c", "exec claude -p --dangerously-skip-permissions "
                                      "--append-system-prompt \"$(cat \"$AGENT_PROFILE\")\""],
                    "memory": "4g", "cpus": "2", "pids": 512, "timeout_seconds": 1800},
        "model": {"upstream": "https://api.anthropic.com", "api_key_env": "ANTHROPIC_API_KEY",
                  "cost_unit": "tokens"},
    }
    parse(raw, data_dir)  # fail before touching the filesystem
    data_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(data_dir, 0o700)
    _write_private(data_dir / CONFIG_NAME, json.dumps(raw, indent=2) + "\n")
    store = Store(data_dir / "relay.db")
    owner = instance["mandate"]["owner"]
    member_id = auth.create_member(store, owner, "owner", "init")
    token = auth.create_invite(store, member_id, "init")
    store.close()
    print(f"Initialised {data_dir}")
    print(f"Owner sign-in link (single use, 24 h): {raw['public_origin']}/join#{token}")
    print("Edit relay.json for the container image and agent command before `serve`.")
    return 0


def cmd_invite(args) -> int:
    cfg = load(args.data_dir)
    store = Store(cfg.db_path)
    row = store.one("SELECT id, role FROM members WHERE name = ? AND disabled_at IS NULL", (args.name,))
    if row is None:
        print(f"no active member named {args.name!r}", file=sys.stderr)
        return 2
    token = auth.create_invite(store, row["id"], "cli")
    print(f"{cfg.public_origin}/join#{token}")
    return 0


def cmd_serve(args) -> int:
    if os.getuid() == 0:
        print("refusing to serve as root", file=sys.stderr)
        return 2
    cfg = load(args.data_dir)
    api_key = model_api_key(cfg)
    store = Store(cfg.db_path)
    store.verify_chain()
    contract = Contract(cfg.instance_path, cfg.events_path)
    contract.state()
    relay = Relay(cfg, store, contract, api_key=api_key)
    for run_id in relay.recover():
        print(f"recovered interrupted run {run_id}; review it to reconcile its cost", file=sys.stderr)
    from .server import serve
    server = serve(relay)
    print(f"NEXUS Relay listening on http://{cfg.host}:{cfg.port} (public origin {cfg.public_origin})")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


def verify(cfg) -> list[str]:
    problems = []
    store = Store(cfg.db_path)
    try:
        count = store.verify_chain()
    except ChainError as exc:
        return [str(exc)]
    contract = Contract(cfg.instance_path, cfg.events_path)
    try:
        instance = contract.instance()
        events = contract.events()
        engine()["replay"](instance, events)
    except (AdmissionError, ValueError, KeyError, TypeError) as exc:
        problems.append(f"NEXUS replay failed: {exc}")
        events = []
    ids = {e.get("id") for e in events}
    for row in store.query("SELECT id, state FROM runs"):
        started = f"relay-{row['id']}-start" in ids
        finished = f"relay-{row['id']}-finish" in ids
        if row["state"] in ("running", "completed", "accepted", "rejected") and not started:
            problems.append(f"run {row['id']} is {row['state']} but has no NEXUS start event")
        if row["state"] in ("accepted", "rejected") and not finished:
            problems.append(f"run {row['id']} is {row['state']} but has no NEXUS finish event")
        if row["state"] in ("requested", "declined", "failed_to_start") and started:
            problems.append(f"run {row['id']} is {row['state']} but NEXUS recorded a start")
    if not problems:
        print(f"log chain intact ({count} entries); NEXUS replay accepted {len(events)} events")
    return problems


def cmd_verify(args) -> int:
    problems = verify(load(args.data_dir))
    for p in problems:
        print(f"FAIL: {p}", file=sys.stderr)
    return 1 if problems else 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="nexus-relay", description="Contract-admitted, container-isolated agent runs.")
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DIR)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("init", help="create the data directory, config and owner sign-in link")
    p.add_argument("--instance", type=Path, required=True, help="NEXUS instance JSON with mandate.scope local-relay")
    p.add_argument("--events", type=Path, required=True, help="NEXUS events JSONL (created if missing)")
    p.add_argument("--port", type=int, default=8770)
    p.add_argument("--public-origin", help="https origin of your TLS tunnel, e.g. https://box.tailnet.ts.net")
    p.add_argument("--engine", choices=("docker", "podman"), default="podman")
    p.add_argument("--image", default="ante-relay-agent:latest")
    p.set_defaults(func=cmd_init)
    p = sub.add_parser("invite", help="print a new single-use sign-in link for an existing member")
    p.add_argument("name")
    p.set_defaults(func=cmd_invite)
    sub.add_parser("serve", help="run the relay").set_defaults(func=cmd_serve)
    sub.add_parser("verify", help="check the log chain and replay the NEXUS events").set_defaults(func=cmd_verify)
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except (ConfigError, AdmissionError, ChainError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
