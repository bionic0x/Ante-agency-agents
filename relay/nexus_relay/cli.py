"""Command line: init, invite, serve, verify."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

from . import auth, evidence
from .config import CONFIG_NAME, ConfigError, load, model_api_key, parse
from .nexus import AdmissionError, Contract, engine
from .runner import RunError, check_engine, image_is_pinned
from .service import Relay
from .store import CHAIN_KEY_ENV, ChainError, Store, chain_key_from_env

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
                    # --bare: no hooks, CLAUDE.md discovery, auto-memory or keychain, and auth only
                    # from ANTHROPIC_API_KEY (the per-run token). Nothing the workspace contains can
                    # reconfigure the agent (audit R-6). Permissions are bypassed because the
                    # container, not the agent, is the security boundary.
                    "agent_command": ["sh", "-c", "exec claude -p --bare --strict-mcp-config "
                                      "--dangerously-skip-permissions "
                                      "--append-system-prompt \"$(cat \"$AGENT_PROFILE\")\""],
                    "memory": "4g", "cpus": "2", "pids": 512, "timeout_seconds": 1800},
        "model": {"upstream": "https://api.anthropic.com", "api_key_env": "ANTHROPIC_API_KEY",
                  "cost_unit": "tokens"},
    }
    parse(raw, data_dir)  # fail before touching the filesystem
    data_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(data_dir, 0o700)
    _write_private(data_dir / CONFIG_NAME, json.dumps(raw, indent=2) + "\n")
    store = Store(data_dir / "relay.db", chain_key=chain_key_from_env())
    owner = instance["mandate"]["owner"]
    member_id = auth.create_member(store, owner, "owner", "init")
    token = auth.create_invite(store, member_id, "init")
    store.close()
    print(f"Initialised {data_dir}")
    print(f"Owner sign-in link (single use, 24 h): {raw['public_origin']}/join#{token}")
    print("Edit relay.json for the container image and agent command before `serve`.")
    if not store_keyed_hint():
        print(f"Warning: {CHAIN_KEY_ENV} is not set, so the room log is tamper-evident only against "
              "careless edits. Set it (32+ bytes, kept outside this machine's disk) for a keyed log.")
    return 0


def store_keyed_hint() -> bool:
    return chain_key_from_env() is not None


def cmd_invite(args) -> int:
    cfg = load(args.data_dir)
    store = Store(cfg.db_path, chain_key=chain_key_from_env())
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
    try:
        engine_mode = check_engine(cfg)
    except RunError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    api_key = model_api_key(cfg)
    store = Store(cfg.db_path, chain_key=chain_key_from_env())
    try:
        store.verify_chain()
    except ChainError as exc:
        if not (args.adopt_chain_key and "not keyed" in str(exc)):
            raise
        store.verify_chain(adopt_key=True)
        with store.tx() as db:
            store.append(db, "chain.keyed", "cli", {"note": "log is keyed from this entry on"})
        print("The log is keyed from now on. Entries before this point are only as trustworthy as "
              "the anchors you recorded for them.", file=sys.stderr)
    if not image_is_pinned(cfg.runtime.image):
        print(f"Warning: runtime.image {cfg.runtime.image!r} is a mutable tag; pin it as name@sha256:<digest> "
              "so a re-tag cannot change what agents run.", file=sys.stderr)
    if not store.keyed:
        print(f"Warning: {CHAIN_KEY_ENV} is not set; the room log is not keyed.", file=sys.stderr)
    contract = Contract(cfg.instance_path, cfg.events_path)
    contract.state()
    relay = Relay(cfg, store, contract, api_key=api_key)
    for run_id in relay.recover():
        print(f"recovered interrupted run {run_id}; review it to reconcile its cost", file=sys.stderr)
    from .server import serve
    server = serve(relay)
    print(f"NEXUS Relay listening on http://{cfg.host}:{cfg.port} (public origin {cfg.public_origin}); "
          f"engine: {cfg.runtime.engine}, {engine_mode}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


def verify(cfg, expect_head: str | None = None) -> list[str]:
    store = Store(cfg.db_path, chain_key=chain_key_from_env())
    try:
        return _verify(cfg, store, expect_head)
    finally:
        store.close()


def _verify(cfg, store, expect_head: str | None) -> list[str]:
    problems = []
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
    if expect_head:
        try:
            seq_text, digest = expect_head.split(":", 1)
            seq = int(seq_text)
        except ValueError:
            return [f"--expect-head must be SEQ:HASH as printed by `anchor`, got {expect_head!r}"]
        actual = store.hash_at(seq)
        if actual != digest:
            problems.append(f"anchor mismatch at seq {seq}: recorded {digest}, log has {actual}")
    for e in events:
        if e.get("type") != "finish":
            continue
        for ref in e.get("evidence_refs", []):
            if isinstance(ref, str) and ref.startswith("relay-log:sha256:") and not store.has_hash(ref.split(":", 2)[2]):
                problems.append(f"NEXUS event {e.get('id')} cites a log entry that is not in the chain")
    ids = {e.get("id") for e in events}
    finishes = {e.get("id"): e for e in events if e.get("type") == "finish"}
    for row in store.query("SELECT * FROM runs"):
        started = f"relay-{row['id']}-start" in ids
        finished = f"relay-{row['id']}-finish" in ids
        if row["state"] in ("running", "completed", "accepted", "rejected") and not started:
            problems.append(f"run {row['id']} is {row['state']} but has no NEXUS start event")
        if row["state"] in ("accepted", "rejected") and not finished:
            problems.append(f"run {row['id']} is {row['state']} but has no NEXUS finish event")
        if finished and row["state"] not in ("accepted", "rejected"):
            problems.append(f"run {row['id']} has a NEXUS finish but its relay state is {row['state']}; "
                            "reconcile the interrupted review before retrying")
        if row["state"] in ("requested", "declined", "failed_to_start") and started:
            problems.append(f"run {row['id']} is {row['state']} but NEXUS recorded a start")
        if row["state"] not in ("completed", "accepted", "rejected"):
            continue
        # Evidence is checked against the chained completion entry; the runs table is only an
        # index and must agree with it (a consistent edit of file and row must not pass).
        try:
            logged = store.run_completion(row["id"])
        except ChainError as exc:
            problems.append(f"run {row['id']}: {exc}")
            continue
        problems.extend(f"run {row['id']}: {p}" for p in evidence.record_problems(row, logged))
        if logged is None:
            continue
        for problem in evidence.artifact_problems(cfg.runs_dir / row["id"], logged.get("artifact_digest"),
                                                  logged.get("workspace_digest")):
            problems.append(f"run {row['id']}: {problem}")
        finish = finishes.get(f"relay-{row['id']}-finish")
        if finish is not None:
            refs = set(finish.get("evidence_refs") or [])
            for prefix, field in (("relay-output", "artifact_digest"), ("relay-workspace", "workspace_digest")):
                cited = {r.split(":", 2)[2] for r in refs if isinstance(r, str) and r.startswith(prefix + ":sha256:")}
                expected = {logged[field]} if logged.get(field) else set()
                if cited != expected:
                    problems.append(f"run {row['id']}: NEXUS finish cites a {prefix} digest that differs "
                                    "from the chained run.completed entry")
    if not problems:
        print(f"log chain intact ({count} entries); NEXUS replay accepted {len(events)} events")
    return problems


def cmd_anchor(args) -> int:
    cfg = load(args.data_dir)
    store = Store(cfg.db_path, chain_key=chain_key_from_env())
    try:
        store.verify_chain()
        seq, digest = store.head()
    finally:
        store.close()
    print(f"{seq}:{digest}")
    print("Record this somewhere the relay account cannot write (a signed commit, a ticket, paper); "
          "`verify --expect-head` checks it later.", file=sys.stderr)
    return 0


def cmd_verify(args) -> int:
    problems = verify(load(args.data_dir), args.expect_head)
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
    p = sub.add_parser("serve", help="run the relay")
    p.add_argument("--adopt-chain-key", action="store_true",
                   help=f"start keying an existing unkeyed log with {CHAIN_KEY_ENV}")
    p.set_defaults(func=cmd_serve)
    p = sub.add_parser("verify", help="check the log chain and replay the NEXUS events")
    p.add_argument("--expect-head", help="SEQ:HASH recorded earlier with `anchor`")
    p.set_defaults(func=cmd_verify)
    sub.add_parser("anchor", help="print the current log head to record outside this machine").set_defaults(func=cmd_anchor)
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except (ConfigError, AdmissionError, ChainError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
