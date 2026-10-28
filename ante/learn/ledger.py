"""The decision ledger: append-only JSON lines, chained by hash.

Each line is an entry::

    {seq, at, kind, payload, prev_hash, entry_hash}

``entry_hash`` is the canonical hash of the other five fields; ``prev_hash`` is
the previous line's ``entry_hash`` (64 zeros for the first). Reading the ledger
verifies the whole chain; an edited, removed or reordered line breaks it.

Kinds:
    decision        a sealed ``decide`` artefact, frozen as it was (the snapshot
                    later evaluation compares against — Marco I.10), plus labels
                    (runbook, agent) and ``synthetic``
    reconciliation  an observed outcome for one dated expectation
    note            free records (e.g. a model revision) that never count as evidence

Nothing rewrites an entry: a correction is a new entry that refers to the old one.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from ante.core import canon, io
from ante.core import time as ante_time

GENESIS = '0' * 64
KINDS = ('decision', 'reconciliation', 'note')
FIELDS = ('seq', 'at', 'kind', 'payload', 'prev_hash', 'entry_hash')


class LedgerError(ValueError):
    """The ledger is unreadable or its chain is broken."""


def _hash(seq: int, at: str, kind: str, payload: Any, prev_hash: str) -> str:
    return canon.digest({'seq': seq, 'at': at, 'kind': kind, 'payload': payload, 'prev_hash': prev_hash})


def read(path: Path | str) -> list[dict]:
    target = Path(path)
    if not target.exists():
        return []
    entries = []
    prev = GENESIS
    for number, line in enumerate(target.read_text(encoding='utf-8').splitlines(), 1):
        if not line.strip():
            raise LedgerError(f'{target.name}: blank line {number}')
        try:
            entry = io.parse_json(line, f'{target.name}:{number}')
        except io.InputError as exc:
            raise LedgerError(str(exc)) from None
        if not isinstance(entry, dict) or set(entry) != set(FIELDS):
            raise LedgerError(f'{target.name}:{number}: not a ledger entry')
        if entry['seq'] != number or entry['prev_hash'] != prev:
            raise LedgerError(f'{target.name}:{number}: chain broken (sequence or previous hash)')
        expected = _hash(entry['seq'], entry['at'], entry['kind'], entry['payload'], entry['prev_hash'])
        if entry['entry_hash'] != expected:
            raise LedgerError(f'{target.name}:{number}: content does not match its hash')
        entries.append(entry)
        prev = entry['entry_hash']
    return entries


def append(path: Path | str, kind: str, payload: Any, at: str, kinds: tuple[str, ...] = KINDS) -> dict:
    if kind not in kinds:
        raise LedgerError(f'unknown entry kind {kind}')
    at = ante_time.iso(ante_time.parse(at, 'at'))
    target = Path(path)
    entries = read(target)
    if entries and ante_time.parse(entries[-1]['at'], 'at') > ante_time.parse(at, 'at'):
        raise LedgerError('entries are appended in time order; this one is dated before the last')
    seq = len(entries) + 1
    prev = entries[-1]['entry_hash'] if entries else GENESIS
    entry = {'seq': seq, 'at': at, 'kind': kind, 'payload': payload, 'prev_hash': prev,
             'entry_hash': _hash(seq, at, kind, payload, prev)}
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open('a', encoding='utf-8') as handle:
        handle.write(json.dumps(entry, sort_keys=True, ensure_ascii=False, separators=(',', ':')) + '\n')
        handle.flush()
        os.fsync(handle.fileno())
    return entry


def decisions(entries: list[dict]) -> dict[str, dict]:
    """Decision entries keyed by the decide artefact hash."""
    return {e['payload']['artifact']['artifact_sha256']: e for e in entries if e['kind'] == 'decision'}


def reconciliations(entries: list[dict]) -> list[dict]:
    return [e for e in entries if e['kind'] == 'reconciliation']
