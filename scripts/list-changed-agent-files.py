#!/usr/bin/env python3
"""Filter changed repository paths down to canonical agent Markdown files."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import PurePosixPath


def load_divisions(path: str) -> set[str]:
    with open(path, encoding="utf-8") as handle:
        document = json.load(handle)
    divisions = document.get("divisions")
    if not isinstance(divisions, dict) or not divisions:
        raise ValueError("divisions.json must contain a non-empty 'divisions' object")
    return set(divisions)


def is_agent_path(raw_path: str, divisions: set[str]) -> bool:
    path = PurePosixPath(raw_path.strip())
    parts = path.parts
    return (
        len(parts) >= 2
        and parts[0] in divisions
        and path.suffix == ".md"
        and path.name != "README.md"
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Read newline-delimited changed paths on stdin and emit canonical agent Markdown paths."
    )
    parser.add_argument("--divisions", default="divisions.json")
    args = parser.parse_args()

    try:
        divisions = load_divisions(args.divisions)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: cannot load division registry: {exc}", file=sys.stderr)
        return 2

    for line in sys.stdin:
        candidate = line.strip()
        if candidate and is_agent_path(candidate, divisions):
            print(candidate)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
