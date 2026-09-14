#!/usr/bin/env python3
"""Read canonical repository registries without duplicating their key sets in shell.

Usage:
    python3 scripts/registry.py divisions [path]
    python3 scripts/registry.py tools [path]

Keys are emitted in JSON insertion order, one per line. The registries themselves
remain the source of truth; this helper only gives Bash 3.2-compatible scripts a
small, deterministic bridge to them.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRIES = {
    "divisions": ROOT / "divisions.json",
    "tools": ROOT / "tools.json",
}


def main(argv: list[str]) -> int:
    if len(argv) not in (2, 3) or argv[1] not in REGISTRIES:
        print("usage: registry.py divisions|tools [registry.json]", file=sys.stderr)
        return 2

    section = argv[1]
    path = Path(argv[2]) if len(argv) == 3 else REGISTRIES[section]
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        entries = data[section]
    except (OSError, json.JSONDecodeError, KeyError, TypeError) as exc:
        print(f"registry: {path}: {exc}", file=sys.stderr)
        return 1

    if not isinstance(entries, dict) or not entries:
        print(f"registry: {path}: '{section}' must be a non-empty object", file=sys.stderr)
        return 1

    for key in entries:
        if not isinstance(key, str) or not key:
            print(f"registry: {path}: invalid empty/non-string key", file=sys.stderr)
            return 1
        print(key)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
