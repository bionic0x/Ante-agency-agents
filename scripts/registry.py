#!/usr/bin/env python3
"""Read canonical repository registries without duplicating key sets in shell.

Examples:
    python3 scripts/registry.py divisions [path]
    python3 scripts/registry.py tools [path]
    python3 scripts/registry.py tools [path] --converted
    python3 scripts/registry.py tools [path] --install-kind per-agent
    python3 scripts/registry.py tool-field <tool> <field> [path]

Division keys retain JSON insertion order. Tool keys are ordered by their
canonical ``order`` field (then key as a deterministic tie-breaker), so CLI/TUI
consumers do not carry a second ordering policy.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REGISTRIES = {
    "divisions": ROOT / "divisions.json",
    "tools": ROOT / "tools.json",
}
VALID_INSTALL_KINDS = {"per-agent", "roster", "plugin"}


class RegistryError(RuntimeError):
    pass


def load_section(section: str, path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        entries = data[section]
    except (OSError, json.JSONDecodeError, KeyError, TypeError) as exc:
        raise RegistryError(f"{path}: {exc}") from exc

    if not isinstance(entries, dict) or not entries:
        raise RegistryError(f"{path}: '{section}' must be a non-empty object")
    for key, value in entries.items():
        if not isinstance(key, str) or not key:
            raise RegistryError(f"{path}: invalid empty/non-string key")
        if not isinstance(value, dict):
            raise RegistryError(f"{path}: entry '{key}' must be an object")
    return entries


def ordered_tools(entries: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    rows: list[tuple[int, str, dict[str, Any]]] = []
    seen_orders: dict[int, str] = {}
    for key, spec in entries.items():
        order = spec.get("order")
        if not isinstance(order, int) or isinstance(order, bool) or order < 1:
            raise RegistryError(f"tools.json: tool '{key}' must have a positive integer 'order'")
        previous = seen_orders.get(order)
        if previous is not None:
            raise RegistryError(
                f"tools.json: duplicate order {order} for '{previous}' and '{key}'"
            )
        seen_orders[order] = key
        rows.append((order, key, spec))
    rows.sort(key=lambda row: (row[0], row[1]))
    return [(key, spec) for _order, key, spec in rows]


def registry_path(section: str, explicit: str | None) -> Path:
    return Path(explicit) if explicit else REGISTRIES[section]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    divisions = sub.add_parser("divisions", help="emit division keys")
    divisions.add_argument("path", nargs="?")

    tools = sub.add_parser("tools", help="emit tool keys in canonical order")
    tools.add_argument("path", nargs="?")
    tools.add_argument("--converted", action="store_true", help="exclude identity/source tools")
    tools.add_argument("--install-kind", choices=sorted(VALID_INSTALL_KINDS))

    field = sub.add_parser("tool-field", help="emit one field from one registered tool")
    field.add_argument("tool")
    field.add_argument("field")
    field.add_argument("path", nargs="?")
    return parser


def main(argv: list[str]) -> int:
    args = build_parser().parse_args(argv[1:])

    if args.command == "divisions":
        entries = load_section("divisions", registry_path("divisions", args.path))
        for key in entries:
            print(key)
        return 0

    if args.command == "tools":
        entries = load_section("tools", registry_path("tools", args.path))
        for key, spec in ordered_tools(entries):
            if args.converted and spec.get("format") == "identity":
                continue
            if args.install_kind and spec.get("installKind") != args.install_kind:
                continue
            print(key)
        return 0

    entries = load_section("tools", registry_path("tools", args.path))
    if args.tool not in entries:
        raise RegistryError(f"tools.json: unknown tool '{args.tool}'")
    value = entries[args.tool].get(args.field)
    if value is None:
        raise RegistryError(f"tools.json: tool '{args.tool}' has no field '{args.field}'")
    if isinstance(value, (dict, list)):
        print(json.dumps(value, separators=(",", ":"), sort_keys=True))
    elif isinstance(value, bool):
        print("true" if value else "false")
    else:
        print(value)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv))
    except RegistryError as exc:
        print(f"registry: {exc}", file=sys.stderr)
        raise SystemExit(1)
