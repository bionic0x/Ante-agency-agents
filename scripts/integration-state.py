#!/usr/bin/env python3
"""Verify and synchronize generated adapters with granular per-agent state.

State v2 records source hashes and concrete output hashes for per-agent tools.
When a valid v2 state exists and the renderer contract is unchanged, ``sync``
reconverts only changed/new/corrupted agents and prunes outputs belonging to
renamed or deleted sources. Roster/plugin tools, first runs, and renderer
contract changes deliberately fall back to a clean full rebuild.

``check`` remains read-only. ``record`` remains available for callers that have
already converted a tool. ``explain`` reports why a check would fail.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
STATE_VERSION = 2
IGNORED_OUTPUT_NAMES = {"README.md"}


class StateError(RuntimeError):
    pass


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def stable_hash_parts(parts: list[tuple[str, bytes]]) -> str:
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


def normalize_scalar(value: str) -> str:
    value = value.strip(" \t")
    if len(value) >= 2 and value[0] == value[-1] == '"':
        value = value[1:-1].replace(r'\"', '"').replace(r"\\", "\\")
    elif len(value) >= 2 and value[0] == value[-1] == "'":
        value = value[1:-1].replace("''", "'")
    return value


def first_frontmatter_field(path: Path, field: str) -> str:
    """Mirror the small frontmatter subset parsed by scripts/lib.sh get_field."""
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
    """Mirror lib.sh's ASCII-only slug contract exactly."""
    out: list[str] = []
    separator = False
    for char in value:
        if "A" <= char <= "Z":
            char = char.lower()
        if ("a" <= char <= "z") or ("0" <= char <= "9"):
            if separator and out:
                out.append("-")
            out.append(char)
            separator = False
        else:
            separator = True
    return "".join(out)


def source_agents(divisions: dict[str, Any]) -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    for division in divisions:
        base = ROOT / division
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*.md")):
            name = first_frontmatter_field(path, "name")
            if not name:
                continue
            rel = path.relative_to(ROOT).as_posix()
            result[rel] = {
                "source_hash": sha256_file(path),
                "name": name,
                "slug": slugify(name),
            }
    return result


def renderer_hash(tool: str, spec: dict[str, Any], divisions: dict[str, Any]) -> str:
    paths = [ROOT / "scripts/convert.sh", ROOT / "scripts/lib.sh", ROOT / "scripts/registry.py"]
    if tool == "hermes":
        paths.append(ROOT / "scripts/build-hermes-plugin.py")
    parts = [(p.relative_to(ROOT).as_posix(), p.read_bytes()) for p in paths]
    parts.append(("tool-spec", json.dumps(spec, sort_keys=True, separators=(",", ":")).encode()))
    # Only division membership affects discovery; explanatory metadata does not.
    parts.append(("division-keys", json.dumps(list(divisions), separators=(",", ":")).encode()))
    return stable_hash_parts(parts)


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
        raise StateError(f"tool '{tool}' format '{fmt}' has no per-agent output mapping")
    return [p.as_posix() for p in paths]


def actual_tool_outputs(tool: str) -> dict[str, str]:
    root = ROOT / "integrations" / tool
    if not root.is_dir():
        return {}
    result: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.name in IGNORED_OUTPUT_NAMES or "__pycache__" in path.parts:
            continue
        result[path.relative_to(ROOT).as_posix()] = sha256_file(path)
    return result


def build_state(tool: str) -> tuple[dict[str, Any], list[str], dict[str, str]]:
    divisions, tools = registries()
    if tool not in tools:
        raise StateError(f"unknown registered tool: {tool}")
    spec = tools[tool]
    kind = spec.get("installKind")
    agents = source_agents(divisions)
    actual = actual_tool_outputs(tool)
    render_hash = renderer_hash(tool, spec, divisions)

    if kind == "per-agent":
        sources: dict[str, Any] = {}
        expected_paths: set[str] = set()
        missing: list[str] = []
        for source, record in agents.items():
            outputs: dict[str, str] = {}
            for rel in output_relpaths(tool, spec, record["slug"]):
                expected_paths.add(rel)
                if rel not in actual:
                    missing.append(rel)
                else:
                    outputs[rel] = actual[rel]
            sources[source] = {
                "source_hash": record["source_hash"],
                "slug": record["slug"],
                "outputs": outputs,
            }
        extras = {path: digest for path, digest in actual.items() if path not in expected_paths}
        state = {
            "version": STATE_VERSION,
            "tool": tool,
            "install_kind": kind,
            "renderer_hash": render_hash,
            "sources": sources,
        }
        return state, sorted(missing), extras

    # Roster/plugin outputs are aggregate by design. They retain a full-source
    # digest because one changed agent can alter the single combined artifact.
    source_parts = [(path, bytes.fromhex(record["source_hash"])) for path, record in agents.items()]
    state = {
        "version": STATE_VERSION,
        "tool": tool,
        "install_kind": kind,
        "renderer_hash": render_hash,
        "sources_hash": stable_hash_parts(source_parts),
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
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(state, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
    temp.replace(path)


def status(tool: str) -> tuple[bool, list[str], dict[str, Any]]:
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
        if saved != current:
            if current.get("install_kind") == "per-agent" and saved.get("renderer_hash") == current.get("renderer_hash"):
                old_sources = saved.get("sources", {}) if isinstance(saved.get("sources"), dict) else {}
                new_sources = current.get("sources", {})
                changed = set(old_sources) ^ set(new_sources)
                for source in set(old_sources) & set(new_sources):
                    if old_sources[source] != new_sources[source]:
                        changed.add(source)
                if changed:
                    reasons.append(f"{len(changed)} agent source/output record(s) changed")
            elif "renderer contract changed" not in reasons:
                reasons.append("aggregate input/output state changed")
    if missing:
        reasons.append(f"{len(missing)} expected output(s) missing")
    if extras:
        reasons.append(f"{len(extras)} unexpected output(s) present")
    return not reasons, reasons, current


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
    completed = subprocess.run([str(ROOT / "scripts/convert.sh"), "--tool", tool], cwd=ROOT)
    if completed.returncode:
        raise StateError(f"full conversion failed for {tool} ({completed.returncode})")


def incremental_convert(tool: str, sources: list[str]) -> None:
    for source in sources:
        completed = subprocess.run(
            [str(ROOT / "scripts/convert.sh"), "--tool", tool, "--source", source],
            cwd=ROOT,
        )
        if completed.returncode:
            raise StateError(f"incremental conversion failed for {tool}: {source}")


def sync(tool: str, force: bool = False) -> str:
    divisions, tools = registries()
    if tool not in tools:
        raise StateError(f"unknown registered tool: {tool}")
    spec = tools[tool]
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

    # Remove outputs owned by deleted/renamed/changed old records first so slug
    # changes cannot leave stale adapters behind. Remove unowned extras as well.
    for source in removed + changed:
        old = old_sources.get(source)
        if isinstance(old, dict) and isinstance(old.get("outputs"), dict):
            for rel in old["outputs"]:
                safe_remove(rel, tool)
    for rel in extras:
        safe_remove(rel, tool)

    incremental_convert(tool, changed)
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
    if args.tool not in tools:
        raise StateError(f"unknown registered tool: {args.tool}")

    if args.mode == "check":
        ok, _reasons, _current = status(args.tool)
        return 0 if ok else 1
    if args.mode == "explain":
        ok, reasons, _current = status(args.tool)
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

    result = sync(args.tool, force=args.force)
    print(f"{args.tool}: {result}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, StateError) as exc:
        print(f"integration state: {exc}", file=sys.stderr)
        raise SystemExit(1)
