"""Frozen reviewer profiles: pinned by hash, read-only to the learning and development loops."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

from ante.core import canon
from ante.paths import ROOT

REGISTRY = 'ante/constructs/frozen.json'
CONSTRUCTS_DIR = 'ante/constructs'


class ConstructError(ValueError):
    pass


def load(root: Path = ROOT, ref: str | None = None) -> list[dict]:
    """The frozen reviewers, from the working tree or from a git revision."""
    if ref is None:
        raw = (Path(root) / REGISTRY).read_text(encoding='utf-8')
    else:
        proc = subprocess.run(['git', '-C', str(root), 'show', f'{ref}:{REGISTRY}'], capture_output=True, text=True)
        if proc.returncode != 0:
            return []
        raw = proc.stdout
    return json.loads(raw)['frozen_reviewers']


def paths(root: Path = ROOT, ref: str | None = None) -> tuple[str, ...]:
    return tuple(entry['path'] for entry in load(root, ref)) + (REGISTRY,)


def verify(root: Path = ROOT) -> list[dict]:
    """Drift between each frozen profile and its pinned hash."""
    drift = []
    for entry in load(root):
        target = Path(root) / entry['path']
        if not target.is_file():
            drift.append({'id': entry['id'], 'path': entry['path'], 'problem': 'missing'})
            continue
        actual = canon.sha256_hex(target.read_bytes())
        if actual != entry['sha256']:
            drift.append({'id': entry['id'], 'path': entry['path'], 'problem': 'hash differs',
                          'pinned': entry['sha256'], 'actual': actual})
    return drift


def guard_write(target: Path | str, root: Path = ROOT) -> None:
    """Refuse a write by the learning or development loop into a construct."""
    resolved = Path(target).resolve()
    base = Path(root).resolve()
    if resolved.is_relative_to(base / CONSTRUCTS_DIR):
        raise ConstructError(f'{resolved.name}: constructs are read-only to ante learn and ante develop')
    frozen = {(base / p).resolve() for p in paths(root)}
    if resolved in frozen:
        raise ConstructError(f'{resolved.name} is a frozen reviewer; ante learn and ante develop cannot write to it')


def is_frozen_agent(slug: str | None, root: Path = ROOT) -> bool:
    return slug is not None and any(entry['id'] == slug for entry in load(root))


def add_parser(sub) -> None:
    parser = sub.add_parser('constructs', help='frozen reviewer profiles: list, or verify their pinned hashes')
    parser.add_argument('action', choices=('list', 'verify'))
    parser.set_defaults(handler=main)


def main(args) -> int:
    if args.action == 'list':
        for entry in load():
            print(f"{entry['id']:<34} {entry['sha256'][:12]}  {entry['path']}")
        return 0
    drift = verify()
    for item in drift:
        print(f"DRIFT {item['id']}: {item['problem']} ({item['path']})")
    if drift:
        print('A frozen reviewer changed. Update its hash only in a human-authored protected: commit.')
        return 1
    print(f'constructs: {len(load())} frozen reviewer(s) match their pinned hash')
    return 0
