#!/usr/bin/env python3
"""Verify and synchronize generated adapters with granular per-agent state.

State v2 records each source hash and the concrete output hashes it owns.
Per-agent tools can then rebuild only changed/new/corrupted agents, while roster
and plugin tools deliberately fall back to a clean full rebuild. ``check`` is
strictly read-only; ``sync`` is the only mode that mutates generated outputs.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
STATE_VERSION = 2
IGNORED_OUTPUT_NAMES = {"README.md"}
CONVERTED_IDENTITY_FORMAT = "identity"


class StateError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def stable_hash(parts: list[tuple[str, bytes]]) -> str:
    h = hashlib.sha256()
    for label, data in sorted(parts):
        h.update(label.encode("utf-8"))
        h.update(b"\0")
        h.update(data)
        h.update(b"\0")
    return h.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise StateError(f"{path.relative_to(ROOT)} must contain a JSON object")
    return value


def registries() -> tuple[dict[str, Any], dict[str, Any]]:
    divisions_doc = load_json(ROOT / "divisions.json")
    tools_doc = load_json(ROOT / "tools.json")
    divisions = divisions_doc.get("divisions")
    tools = tools_doc.get("tools")
    if not isinstance(divisions, dict) or not divisions:
        raise StateError("divisions.json has no non-empty 'divisions' object")
    if not isinstance(tools, dict) or not tools:
        raise StateError("tools.json has no non-empty 'tools' object")
    return divisions, tools


def ensure_converted_tool(tool: str, tools: dict[str, Any]) -> dict[str, Any]:
    if tool not in tools:
        raise StateError(f"unknown registered tool: {tool}")
    spec = tools[tool]
    if spec.get("format") == CONVERTED_IDENTITY_FORMAT:
        raise StateError(f"tool '{tool}' installs source agents directly and has no generated integration")
    return spec


def normalize_scalar(value: str) -> str:
    value = value.strip(" \t")
    if len(value) >= 2 and value[0] == value[-1] == '"':
        value = value[1:-1].replace(r'\"', '"').replace(r"\\", "\\")
    elif len(value) >= 2 and value[0] == value[-1] == "'":
        value = value[1:-1].replace("''", "'")
    return value


def first_frontmatter_field(path: Path, field: str) -> str:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except UnicodeDecodeError as exc:
        raise StateError(f"{path.relative_to(ROOT)} is not UTF-8: {exc}") from exc
    if not lines or lines[0] != "---":
        return ""
    prefix = field + ": "
    found: str | None = None
    for line in lines[1:]:
        if line == "---":
            break
        if found is not None:
            if line.startswith((" ", "\t")):
                continuation = line.lstrip(" \t")
                if continuation:
                    found += " " + continuation
                    continue
            return normalize_scalar(found)
        if line.startswith(prefix):
            found = line[len(prefix) :]
    return normalize_scalar(found) if found is not None else ""


def slugify(value: str) -> str:
    out: list[str] = []
    pending_separator = False
    for char in value:
        if "A" <= char <= "Z":
            char = char.lower()
        if ("a" <= char <= "z") or ("0" <= char <= "9"):
            if pending_separator and out:
                out.append("-")
            out.append(char)
            pending_separator = False
        else:
            pending_separator = True
    return "".join(out)


def source_agents(divisions: dict[str, Any]) -> dict[str, dict[str, str]]:
    agents: dict[str, dict[str, str]] = {}
    for division in divisions:
        base = ROOT / division
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*.md")):
            name = first_frontmatter_field(path, "name")
            if not name:
                continue
            rel = path.relative_to(ROOT).as_posix()
            agents[rel] = {
                "source_hash": sha256_file(path),
                "name": name,
                "slug": slugify(name),
                "division": division,
            }
    return agents


def renderer_hash(tool: str, spec: dict[str, Any], divisions: dict[str, Any]) -> str:
    paths = [
        ROOT / "scripts" / "convert-engine.sh",
        ROOT / "scripts" / "lib.sh",
        ROOT / "scripts" / "registry.py",
    ]
    if tool == "hermes":
        paths.append(ROOT / "scripts" / "build-hermes-plugin.py")
    parts = [(path.relative_to(ROOT).as_posix(), path.read_bytes()) for path in paths]
    parts.append(("tool-spec", json.dumps(spec, sort_keys=True, separators=(",", ":")).encode("utf-8")))
    parts.append(("division-keys", json.dumps(list(divisions), separators=(",", ":")).encode("utf-8")))
    return stable_hash(parts)


def output_relpaths(tool: str, spec: dict[str, Any], slug: str) -> list[str]:
    fmt = spec.get("format")
    root = Path("integrations") / tool
    if fmt == "codex-toml":
        paths = [root / "agents" / f"{slug}.toml"]
    elif fmt in {"gemini-md", "opencode-md", "qwen-md", "zcode-md"}:
        paths = [root / "agents" / f"{slug}.md"]
    elif fmt == "cursor-mdc":
        paths = [root / "rules" / f"{slug}.mdc"]
    elif fmt == "skill-md":
        rendered_slug = f"{spec.get('slugPrefix', '')}{slug}"
        paths = [root / rendered_slug / "SKILL.md"]
    elif fmt == "openclaw-workspace":
        paths = [root / slug / name for name in ("SOUL.md", "AGENTS.md", "IDENTITY.md")]
    elif fmt == "kimi-agent":
        paths = [root / slug / "agent.yaml", root / slug / "system.md"]
    elif fmt == "vibe-toml":
        paths = [root / "agents" / f"{slug}.toml", root / "prompts" / f"{slug}.md"]
    else:
        raise StateError(f"tool '{tool}' format '{fmt}' is not per-agent renderable")
    return [path.as_posix() for path in paths]


def actual_tool_outputs(tool: str) -> dict[str, str]:
    root = ROOT / "integrations" / tool
    if not root.is_dir():
        return {}
    outputs: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.name in IGNORED_OUTPUT_NAMES or "__pycache__" in path.parts:
            continue
        outputs[path.relative_to(ROOT).as_posix()] = sha256_file(path)
    return outputs


def build_state(tool: str) -> tuple[dict[str, Any], list[str], dict[str, str]]:
    divisions, tools = registries()
    spec = ensure_converted_tool(tool, tools)
    kind = spec.get("installKind")
    agents = source_agents(divisions)
    actual = actual_tool_outputs(tool)
    render_hash = renderer_hash(tool, spec, divisions)

    if kind == "per-agent":
        sources: dict[str, Any] = {}
        owners: dict[str, str] = {}
        expected: set[str] = set()
        missing: list[str] = []
        for source, record in agents.items():
            outputs: dict[str, str] = {}
            relpaths = output_relpaths(tool, spec, record["slug"])
            for rel in relpaths:
                previous = owners.get(rel)
                if previous is not None:
                    raise StateError(
                        f"ambiguous output ownership for {rel}: {previous} and {source}"
                    )
                owners[rel] = source
                expected.add(rel)
                if rel in actual:
                    outputs[rel] = actual[rel]
                else:
                    missing.append(rel)
            sources[source] = {
                "source_hash": record["source_hash"],
                "slug": record["slug"],
                "outputs": outputs,
            }
        extras = {rel: digest for rel, digest in actual.items() if rel not in expected}
        return {
            "version": STATE_VERSION,
            "tool": tool,
            "install_kind": kind,
            "renderer_hash": render_hash,
            "sources": sources,
        }, sorted(missing), extras

    source_parts = [
        (source, record["source_hash"].encode("ascii")) for source, record in agents.items()
    ]
    state = {
        "version": STATE_VERSION,
        "tool": tool,
        "install_kind": kind,
        "renderer_hash": render_hash,
        "sources_hash": stable_hash(source_parts),
        "outputs": actual,
    }
    missing = [] if actual else [f"integrations/{tool}/<generated-output>"]
    return state, missing, {}


def state_path(tool: str) -> Path:
    override = os.environ.get("AGENCY_INTEGRATION_STATE_DIR")
    root = Path(override) if override else ROOT / ".cache" / "integration-state"
    if not root.is_absolute():
        root = ROOT / root
    return root / f"{tool}.json"


def load_saved(tool: str) -> dict[str, Any] | None:
    path = state_path(tool)
    if not path.is_file():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def write_state(tool: str, state: dict[str, Any]) -> None:
    path = state_path(tool)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    temp.write_text(
        json.dumps(state, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    temp.replace(path)


def status(tool: str) -> tuple[bool, list[str]]:
    current, missing, extras = build_state(tool)
    saved = load_saved(tool)
    reasons: list[str] = []
    if saved is None:
        reasons.append("no verified state")
    elif saved.get("version") != STATE_VERSION:
        reasons.append("state schema changed")
    else:
        if saved.get("renderer_hash") != current.get("renderer_hash"):
            reasons.append("renderer contract changed")
        if saved != current and "renderer contract changed" not in reasons:
            if current.get("install_kind") == "per-agent":
                old_sources = saved.get("sources", {}) if isinstance(saved.get("sources"), dict) else {}
                new_sources = current.get("sources", {})
                changed = set(old_sources) ^ set(new_sources)
                for source in set(old_sources) & set(new_sources):
                    if old_sources[source] != new_sources[source]:
                        changed.add(source)
                if changed:
                    reasons.append(f"{len(changed)} agent source/output record(s) changed")
            else:
                reasons.append("aggregate input/output state changed")
    if missing:
        reasons.append(f"{len(missing)} expected output(s) missing")
    if extras:
        reasons.append(f"{len(extras)} unexpected output(s) present")
    return not reasons, reasons


def safe_remove(rel: str, tool: str) -> None:
    root = (ROOT / "integrations" / tool).resolve()
    path = (ROOT / rel).resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise StateError(f"refusing to remove output outside integrations/{tool}: {rel}") from exc
    if path.name in IGNORED_OUTPUT_NAMES:
        raise StateError(f"refusing to remove protected output: {rel}")
    if path.is_file() or path.is_symlink():
        path.unlink()
    parent = path.parent
    while parent != root and parent.is_dir():
        try:
            parent.rmdir()
        except OSError:
            break
        parent = parent.parent


def full_convert(tool: str) -> None:
    completed = subprocess.run(
        ["bash", str(ROOT / "scripts" / "convert-engine.sh"), "--tool", tool],
        cwd=ROOT,
        check=False,
    )
    if completed.returncode:
        raise StateError(f"full conversion failed for {tool} ({completed.returncode})")


def stage_changed_outputs(
    tool: str,
    spec: dict[str, Any],
    divisions: dict[str, Any],
    agents: dict[str, dict[str, str]],
    changed: list[str],
) -> dict[str, bytes]:
    if not changed:
        return {}
    with tempfile.TemporaryDirectory(prefix=f"agency-{tool}-incremental-") as tmp_name:
        stage_root = Path(tmp_name) / "repo"
        scripts = stage_root / "scripts"
        scripts.mkdir(parents=True)
        shutil.copy2(ROOT / "scripts" / "convert-engine.sh", scripts / "convert.sh")
        shutil.copy2(ROOT / "scripts" / "lib.sh", scripts / "lib.sh")
        shutil.copy2(ROOT / "scripts" / "registry.py", scripts / "registry.py")
        shutil.copy2(ROOT / "tools.json", stage_root / "tools.json")

        used_divisions = sorted({agents[source]["division"] for source in changed})
        subset = {division: divisions[division] for division in used_divisions}
        (stage_root / "divisions.json").write_text(
            json.dumps({"divisions": subset}, separators=(",", ":")) + "\n",
            encoding="utf-8",
        )
        for source in changed:
            target = stage_root / source
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / source, target)

        out = Path(tmp_name) / "rendered"
        completed = subprocess.run(
            ["bash", str(scripts / "convert.sh"), "--tool", tool, "--out", str(out)],
            cwd=stage_root,
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
        )
        if completed.returncode:
            raise StateError(
                f"incremental renderer failed for {tool} ({completed.returncode}): {completed.stderr.strip()}"
            )

        staged: dict[str, bytes] = {}
        for source in changed:
            for rel in output_relpaths(tool, spec, agents[source]["slug"]):
                relative = Path(rel).relative_to("integrations")
                rendered = out / relative
                if not rendered.is_file():
                    raise StateError(f"incremental renderer did not produce expected output: {rel}")
                staged[rel] = rendered.read_bytes()
        return staged


def install_staged_outputs(staged: dict[str, bytes]) -> None:
    for rel, data in staged.items():
        path = ROOT / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_name(path.name + ".tmp")
        temp.write_bytes(data)
        temp.replace(path)


def sync(tool: str, force: bool = False) -> str:
    divisions, tools = registries()
    spec = ensure_converted_tool(tool, tools)
    kind = spec.get("installKind")
    saved = load_saved(tool)
    current, _missing, extras = build_state(tool)

    can_incremental = (
        not force
        and kind == "per-agent"
        and isinstance(saved, dict)
        and saved.get("version") == STATE_VERSION
        and saved.get("install_kind") == "per-agent"
        and saved.get("renderer_hash") == current.get("renderer_hash")
        and isinstance(saved.get("sources"), dict)
    )

    if not can_incremental:
        full_convert(tool)
        fresh, missing, extras_after = build_state(tool)
        if missing or extras_after:
            raise StateError(
                f"full conversion for {tool} left {len(missing)} missing and {len(extras_after)} unexpected outputs"
            )
        write_state(tool, fresh)
        reason = "forced" if force else "no compatible granular state or aggregate tool"
        return f"full rebuild ({reason})"

    agents = source_agents(divisions)
    old_sources: dict[str, Any] = saved["sources"]
    new_sources: dict[str, Any] = current["sources"]
    removed = sorted(set(old_sources) - set(new_sources))
    changed: list[str] = []

    for source in sorted(new_sources):
        old = old_sources.get(source)
        new = new_sources[source]
        if old is None or old.get("source_hash") != new.get("source_hash") or old.get("slug") != new.get("slug"):
            changed.append(source)
            continue
        expected = output_relpaths(tool, spec, new["slug"])
        old_outputs = old.get("outputs", {}) if isinstance(old.get("outputs"), dict) else {}
        if set(old_outputs) != set(expected):
            changed.append(source)
            continue
        for rel in expected:
            path = ROOT / rel
            if not path.is_file() or sha256_file(path) != old_outputs.get(rel):
                changed.append(source)
                break

    staged = stage_changed_outputs(tool, spec, divisions, agents, changed)

    for source in removed + changed:
        old = old_sources.get(source)
        if isinstance(old, dict) and isinstance(old.get("outputs"), dict):
            for rel in old["outputs"]:
                safe_remove(rel, tool)
    for rel in extras:
        safe_remove(rel, tool)
    install_staged_outputs(staged)

    fresh, missing, extras_after = build_state(tool)
    if missing or extras_after:
        raise StateError(
            f"incremental conversion for {tool} left {len(missing)} missing and {len(extras_after)} unexpected outputs"
        )
    write_state(tool, fresh)
    return f"incremental rebuild ({len(changed)} changed/new, {len(removed)} removed)"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("check", "record", "sync", "explain"))
    parser.add_argument("tool")
    parser.add_argument("--force", action="store_true", help="force sync to perform a clean full rebuild")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    _divisions, tools = registries()
    ensure_converted_tool(args.tool, tools)

    if args.mode == "check":
        ok, _reasons = status(args.tool)
        return 0 if ok else 1
    if args.mode == "explain":
        ok, reasons = status(args.tool)
        if ok:
            print(f"{args.tool}: current")
        else:
            for reason in reasons:
                print(f"{args.tool}: {reason}")
        return 0
    if args.mode == "record":
        state, missing, extras = build_state(args.tool)
        if missing or extras:
            raise StateError(
                f"cannot record {args.tool}: {len(missing)} missing and {len(extras)} unexpected outputs"
            )
        write_state(args.tool, state)
        return 0

    print(f"{args.tool}: {sync(args.tool, force=args.force)}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, StateError) as exc:
        print(f"integration state: {exc}", file=sys.stderr)
        raise SystemExit(1)
