#!/usr/bin/env python3
"""Validate and inventory agent `tools` frontmatter declarations.

The source format consumed by lib.sh/get_field and the Qwen/ZCode renderers is a
single comma-separated scalar. Tool names and their security semantics are
closed over scripts/agent-tools.json: adding a runtime capability therefore
requires an explicit reviewed registry change before any agent may request it.
"""
from __future__ import annotations

import argparse
import collections
import json
import re
import sys
from pathlib import Path

import yaml

TOOL_TOKEN_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_.:/*-]*$")
EXPECTED_CLASSES = ["read", "network-read", "write", "execute"]
REQUIRED_TOOL_FIELDS = {"class", "mutates", "external_io", "description"}


def load_divisions(root: Path) -> list[str]:
    doc = json.loads((root / "divisions.json").read_text(encoding="utf-8"))
    divisions = doc.get("divisions")
    if not isinstance(divisions, dict) or not divisions:
        raise ValueError("divisions.json must contain a non-empty 'divisions' object")
    return list(divisions)


def load_tool_policy(root: Path) -> tuple[list[str], dict[str, dict[str, object]]]:
    doc = json.loads((root / "scripts" / "agent-tools.json").read_text(encoding="utf-8"))
    if doc.get("schema_version") != 1:
        raise ValueError("agent-tools.json schema_version must be 1")
    classes = doc.get("classes")
    if classes != EXPECTED_CLASSES:
        raise ValueError(f"agent-tools.json classes must be {EXPECTED_CLASSES!r} in privilege order")
    tools = doc.get("tools")
    if not isinstance(tools, dict) or not tools:
        raise ValueError("agent-tools.json must contain a non-empty 'tools' object")

    for name, spec in tools.items():
        if not isinstance(name, str) or not TOOL_TOKEN_RE.fullmatch(name):
            raise ValueError(f"invalid registered tool name: {name!r}")
        if not isinstance(spec, dict):
            raise ValueError(f"tool {name}: policy must be an object")
        keys = set(spec)
        if keys != REQUIRED_TOOL_FIELDS:
            missing = sorted(REQUIRED_TOOL_FIELDS - keys)
            extra = sorted(keys - REQUIRED_TOOL_FIELDS)
            raise ValueError(f"tool {name}: policy fields mismatch; missing={missing}, extra={extra}")
        if spec["class"] not in classes:
            raise ValueError(f"tool {name}: unknown privilege class {spec['class']!r}")
        if not isinstance(spec["mutates"], bool) or not isinstance(spec["external_io"], bool):
            raise ValueError(f"tool {name}: mutates/external_io must be booleans")
        if not isinstance(spec["description"], str) or not spec["description"].strip():
            raise ValueError(f"tool {name}: description must be a non-empty string")

    return classes, tools


def agent_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for division in load_divisions(root):
        directory = root / division
        if not directory.is_dir():
            continue
        files.extend(path for path in directory.rglob("*.md") if path.name != "README.md")
    return sorted(files)


def frontmatter(path: Path) -> dict[str, object]:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    if not lines or lines[0] != "---":
        raise ValueError("missing opening frontmatter fence")
    try:
        end = lines.index("---", 1)
    except ValueError as exc:
        raise ValueError("missing closing frontmatter fence") from exc
    try:
        data = yaml.safe_load("\n".join(lines[1:end]))
    except yaml.YAMLError as exc:
        raise ValueError(f"invalid YAML frontmatter: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("frontmatter must be a YAML mapping")
    return data


def parse_tools(raw: object) -> list[str]:
    if raw is None:
        return []
    if not isinstance(raw, str):
        raise ValueError("'tools' must be a single comma-separated YAML scalar")
    if "\n" in raw or "\r" in raw:
        raise ValueError("'tools' must be a single-line scalar")
    if not raw.strip():
        raise ValueError("'tools' must not be empty when present")

    tokens = [token.strip() for token in raw.split(",")]
    if any(not token for token in tokens):
        raise ValueError("'tools' contains an empty token")
    invalid = [token for token in tokens if not TOOL_TOKEN_RE.fullmatch(token)]
    if invalid:
        raise ValueError(f"invalid tool token(s): {', '.join(invalid)}")
    duplicates = sorted(token for token, count in collections.Counter(tokens).items() if count > 1)
    if duplicates:
        raise ValueError(f"duplicate tool token(s): {', '.join(duplicates)}")
    return tokens


def validate_registered_tools(tokens: list[str], policy: dict[str, dict[str, object]]) -> None:
    unknown = sorted(set(tokens) - set(policy), key=str.casefold)
    if unknown:
        raise ValueError(
            "unregistered tool token(s): " + ", ".join(unknown) +
            "; add reviewed semantics to scripts/agent-tools.json first"
        )


def effective_class(tokens: list[str], classes: list[str], policy: dict[str, dict[str, object]]) -> str:
    if not tokens:
        return "none"
    rank = {name: index for index, name in enumerate(classes)}
    return max((str(policy[token]["class"]) for token in tokens), key=rank.__getitem__)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--inventory", action="store_true")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    errors: list[str] = []
    token_files: dict[str, list[str]] = collections.defaultdict(list)
    class_files: dict[str, list[str]] = collections.defaultdict(list)
    declarations = 0

    try:
        files = agent_files(root)
        classes, policy = load_tool_policy(root)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: cannot load privilege schema: {exc}", file=sys.stderr)
        return 2

    for path in files:
        rel = path.relative_to(root).as_posix()
        try:
            metadata = frontmatter(path)
            if "tools" not in metadata:
                class_files["none"].append(rel)
                continue
            declarations += 1
            tokens = parse_tools(metadata.get("tools"))
            validate_registered_tools(tokens, policy)
            for token in tokens:
                token_files[token].append(rel)
            class_files[effective_class(tokens, classes, policy)].append(rel)
        except (OSError, UnicodeError, ValueError) as exc:
            errors.append(f"{rel}: {exc}")

    for error in errors:
        print(f"ERROR {error}")

    if args.inventory:
        print(f"Agent files: {len(files)}")
        print(f"Agents declaring tools: {declarations}")
        print(f"Registered tool tokens: {len(policy)}")
        print(f"Observed tool tokens: {len(token_files)}")
        for token in sorted(policy, key=str.casefold):
            spec = policy[token]
            print(
                f"TOOL {token}\t{len(token_files.get(token, []))}\t"
                f"class={spec['class']}\tmutates={str(spec['mutates']).lower()}\t"
                f"external_io={str(spec['external_io']).lower()}"
            )
        for class_name in ["none", *classes]:
            print(f"CLASS {class_name}\t{len(class_files.get(class_name, []))}")
        for rel in class_files.get("execute", []):
            print(f"EXECUTE {rel}")

    print(
        f"Privilege schema: {len(files)} agents scanned; {declarations} tools declarations; "
        f"{len(token_files)} observed/{len(policy)} registered tokens; {len(errors)} error(s)."
    )
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
