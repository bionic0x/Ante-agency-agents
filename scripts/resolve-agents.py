#!/usr/bin/env python3
"""Resolve catalog IDs, display names and runbooks to adapter slugs (stdlib only)."""
import argparse
import re
import runpy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def slugify(value):
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--agent", action="append", default=[])
    parser.add_argument("--division", action="append", default=[])
    parser.add_argument("--agents-file")
    parser.add_argument("--runbook")
    parser.add_argument("--list-runbooks", action="store_true")
    args = parser.parse_args()
    divisions, agents, runbooks = runpy.run_path(str(ROOT / "scripts/build-catalog.py"))["collect"]()
    if args.list_runbooks:
        for rb in runbooks:
            print(f"{rb['slug']}\t{rb['title']}")
        return

    aliases = {}
    rendered = {}
    for agent in agents:
        slug = slugify(agent["name"])
        if not slug or slug in rendered:
            parser.error(f"duplicate or empty adapter slug: {slug!r}")
        rendered[slug] = agent
        for key in {slug, agent["slug"], slugify(agent["name"])}:
            aliases.setdefault(key, set()).add(slug)

    selected = set()
    for div in args.division:
        if div not in divisions:
            parser.error(f"Unknown division {div!r}")
        selected.update(s for s, a in rendered.items() if a["division"] == div)
    requests = [(a, "--agent") for a in args.agent]
    if args.agents_file:
        for line in Path(args.agents_file).read_text(encoding="utf-8-sig").splitlines():
            line = line.split("#", 1)[0].strip()
            if line:
                requests.append((line, f"agents-file {args.agents_file!r}"))
    if args.runbook:
        matches = [rb for rb in runbooks if rb["slug"] == args.runbook]
        if len(matches) != 1:
            parser.error(f"Unknown runbook {args.runbook!r}; use --list runbooks")
        rb = matches[0]
        for rel in [rb["doc"], *rb["required_artifacts"]]:
            if not (ROOT / rel).is_file():
                parser.error(f"runbook {args.runbook!r}: missing {rel}")
        requests.extend((a, f"runbook {args.runbook!r}") for g in rb["roster"] for a in g["agents"])
    for value, origin in requests:
        matches = aliases.get(slugify(value), set())
        if len(matches) != 1:
            parser.error(f"{'Unknown' if not matches else 'Ambiguous'} agent {value!r} in {origin}")
        selected.update(matches)
    if not selected:
        parser.error("agent selection is empty; no files will be installed")
    print("\n".join(sorted(selected)))


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
