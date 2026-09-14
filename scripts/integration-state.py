#!/usr/bin/env python3
"""Cache verified input/output hashes so installation never reuses stale adapters."""
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def digest(paths):
    h = hashlib.sha256()
    for path in sorted(paths):
        h.update(path.relative_to(ROOT).as_posix().encode())
        h.update(b"\0")
        h.update(path.read_bytes())
        h.update(b"\0")
    return h.hexdigest()


def main():
    mode, tool = sys.argv[1:]
    tools = json.loads((ROOT / "tools.json").read_text())["tools"]
    if mode not in ("check", "record") or tool not in tools:
        raise ValueError("expected check|record and a registered tool")
    divisions = json.loads((ROOT / "divisions.json").read_text())["divisions"]
    inputs = [ROOT / p for p in ("divisions.json", "tools.json")]
    for directory in [*divisions, "scripts", "strategy"]:
        inputs.extend(p for p in (ROOT / directory).rglob("*")
                      if p.is_file() and p.suffix in (".md", ".py", ".sh", ".json", ".yaml"))
    outputs = [p for p in (ROOT / "integrations" / tool).rglob("*")
               if p.is_file() and p.name != "README.md" and "__pycache__" not in p.parts]
    if not outputs:
        return 1
    state = {"inputs": digest(inputs), "outputs": digest(outputs)}
    stamp = ROOT / ".cache" / "integration-state" / (tool + ".json")
    if mode == "record":
        stamp.parent.mkdir(parents=True, exist_ok=True)
        stamp.write_text(json.dumps(state) + "\n")
        return 0
    return 0 if stamp.is_file() and json.loads(stamp.read_text()) == state else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, KeyError) as exc:
        print(f"integration state: {exc}", file=sys.stderr)
        sys.exit(1)
