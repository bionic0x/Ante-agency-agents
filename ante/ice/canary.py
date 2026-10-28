"""Canary strings for held-out case packs.

A canary is ``ANTE-CANARY-`` followed by 32 hex digits. ``seed`` writes one into
every text material of a held-out pack **before it is frozen** (a frozen pack's
material cannot change without changing its ``inputs_hash``) and records it in a
registry kept beside the packs, outside the checkout. ``scan`` looks for canaries
in anything the improver produced or touched. The format alone is enough to
detect contamination; the registry only says which pack leaked.

A hit is contamination, not a judgement about intent: the proposal is rejected
and the leak is investigated by a human.
"""
from __future__ import annotations

import json
import re
import secrets
from pathlib import Path

from ante.core import io
from ante.paths import ROOT

PATTERN = re.compile(r'ANTE-CANARY-[0-9a-f]{32}')
PREFIX = 'ANTE-CANARY-'
TEXT_SUFFIXES = ('.md', '.txt', '.json', '.csv', '.yaml', '.yml')
MAX_SCAN_BYTES = 32 * 1024 * 1024


class CanaryError(ValueError):
    pass


def new() -> str:
    return PREFIX + secrets.token_hex(16)


def _outside_checkout(path: Path, root: Path) -> None:
    if path.resolve().is_relative_to(Path(root).resolve()):
        raise CanaryError(f'{path.name}: canary registries and held-out packs live outside the checkout')


def seed(pack_dir: str, registry: str, root: Path = ROOT) -> dict:
    pack_path = Path(pack_dir)
    reg_path = Path(registry)
    _outside_checkout(reg_path, root)
    pack = io.load_json(pack_path / 'pack.json')
    if pack.get('split') != 'held_out':
        raise CanaryError(f'{pack.get("id")}: only held-out packs carry canaries')
    if 'frozen' in pack:
        raise CanaryError(f'{pack["id"]}: already frozen; seed canaries before nexus-casepack.py freeze')
    entries = io.load_json(reg_path) if reg_path.exists() else {'schema_version': 1, 'canaries': []}
    if any(e['pack'] == pack['id'] for e in entries['canaries']):
        raise CanaryError(f'{pack["id"]}: already seeded')
    token = new()
    seeded = []
    for name in pack.get('materials', []):
        target = pack_path / name
        if target.suffix.lower() not in ('.md', '.txt'):
            continue
        text = target.read_text(encoding='utf-8')
        target.write_text(text.rstrip('\n') + f'\n\n<!-- {token} -->\n', encoding='utf-8')
        seeded.append(name)
    if not seeded:
        raise CanaryError(f'{pack["id"]}: no markdown or text material to carry a canary')
    entries['canaries'].append({'pack': pack['id'], 'canary': token, 'materials': seeded})
    reg_path.parent.mkdir(parents=True, exist_ok=True)
    reg_path.write_text(json.dumps(entries, indent=2) + '\n', encoding='utf-8')
    return {'pack': pack['id'], 'materials': seeded}


def _registry(path: str | None) -> dict[str, str]:
    if path is None:
        return {}
    return {e['canary']: e['pack'] for e in io.load_json(path)['canaries']}


def scan_text(text: str, label: str, registry: dict[str, str]) -> list[dict]:
    return [{'where': label, 'canary': match, 'pack': registry.get(match)}
            for match in sorted(set(PATTERN.findall(text)))]


def scan(paths: list[str], registry_path: str | None = None) -> list[dict]:
    """Canary hits in files or directories (recursively, text files only)."""
    registry = _registry(registry_path)
    hits = []
    for given in paths:
        root = Path(given)
        files = sorted(p for p in root.rglob('*') if p.is_file()) if root.is_dir() else [root]
        for path in files:
            if path.stat().st_size > MAX_SCAN_BYTES:
                hits.append({'where': str(path), 'canary': None, 'pack': None, 'problem': 'too large to scan'})
                continue
            hits += scan_text(path.read_bytes().decode('utf-8', 'replace'), str(path), registry)
    return hits
