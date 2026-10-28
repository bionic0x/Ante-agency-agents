"""Reading a case directory of artefacts (shared by run-check, ghosts and deck)."""
from __future__ import annotations

import json
from pathlib import Path

from ante.core import time as ante_time
from ante.strategy import artifact


def load(directory: Path | str) -> list[dict]:
    """Every sealed artefact in ``directory``; one case; every parent present. Raises LineageError."""
    loaded = []
    for path in sorted(Path(directory).glob('*.json')):
        try:
            data = json.loads(path.read_text(encoding='utf-8'))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(data, dict) and 'artifact_sha256' in data and 'command' in data:
            loaded.append(artifact.verify_self(data, path.name))
    if len({a['case_id'] for a in loaded}) > 1:
        raise artifact.LineageError(f'{directory}: artefacts of more than one case')
    hashes = {a['artifact_sha256'] for a in loaded}
    for art in loaded:
        for parent in art['parents']:
            if parent['artifact_sha256'] not in hashes:
                raise artifact.LineageError(f'{art["command"]} names a parent {parent["command"]} that is not present')
    return sorted(loaded, key=lambda a: (ante_time.parse(a['at'], 'at'), a['command']))


def when(value: str, field: str):
    """A claim date (YYYY-MM-DD) or timestamp, as an aware datetime."""
    return ante_time.parse(value + 'T00:00:00Z' if len(value) == 10 else value, field)
