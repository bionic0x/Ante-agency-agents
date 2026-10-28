"""Canonical doctrine tables, loaded from ``strategy/contracts.json`` only.

There is one source. Code never carries its own copy of an enum: every name the
package checks against is read from the file the protected evaluator also reads.

Tables that ``contracts.json`` does not yet contain (the seven coherence tests
and the fourteen pathologies — decision D-004) raise ``MissingTable`` instead of
falling back to a list written in code.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from ante.paths import CONTRACTS


class MissingTable(LookupError):
    pass


@dataclass(frozen=True)
class Doctrine:
    raw: dict

    def table(self, name: str):
        if name not in self.raw:
            raise MissingTable(f'strategy/contracts.json has no "{name}" table (see foundation/DECISIONS.md D-004)')
        return self.raw[name]

    @property
    def epistemic_states(self) -> tuple[str, ...]:
        return tuple(self.table('epistemic_states'))

    @property
    def decision_states(self) -> tuple[str, ...]:
        return tuple(self.table('decision_states'))

    @property
    def levels(self) -> tuple[str, ...]:
        return tuple(self.table('levels'))

    @property
    def runbook_modes(self) -> tuple[str, ...]:
        return tuple(self.table('runbook_modes'))

    def has(self, name: str) -> bool:
        return name in self.raw


@lru_cache(maxsize=4)
def _load(path: str) -> Doctrine:
    return Doctrine(json.loads(Path(path).read_text(encoding='utf-8')))


def load(path: Path | str = CONTRACTS) -> Doctrine:
    return _load(str(path))
