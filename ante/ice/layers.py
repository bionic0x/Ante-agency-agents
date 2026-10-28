"""Functional independence of the ICE layers."""
from __future__ import annotations

import sys
from itertools import combinations
from pathlib import Path

from ante.core import io

LAYERS = Path(__file__).with_name('layers.json')
FUNCTIONS = ('detect', 'absorb', 'contain', 'recover', 'learn')


def load(path: Path | str = LAYERS) -> list[dict]:
    return io.load_json(path)['layers']


def check(layers: list[dict]) -> list[str]:
    """Problems: a missing function, or two layers sharing data or an assumption."""
    problems = []
    present = [layer['function'] for layer in layers]
    for function in FUNCTIONS:
        if function not in present:
            problems.append(f'no layer performs {function}')
    for function in set(present):
        if present.count(function) > 1:
            problems.append(f'{function} is claimed by more than one layer; give each a distinct function')
    for a, b in combinations(layers, 2):
        shared = sorted(set(a['data']) & set(b['data']))
        if shared:
            problems.append(f'{a["id"]} and {b["id"]} read the same data: {", ".join(shared)}')
        assumed = sorted(set(a['assumptions']) & set(b['assumptions']))
        if assumed:
            problems.append(f'{a["id"]} and {b["id"]} rest on the same assumption: {"; ".join(assumed)}')
    return problems


def main(args) -> int:
    layers = load(args.layers) if getattr(args, 'layers', None) else load()
    problems = check(layers)
    for layer in layers:
        print(f"{layer['function']:<8} {layer['id']:<28} data: {', '.join(layer['data'])}")
    for problem in problems:
        print(f'FAIL {problem}', file=sys.stderr)
    if not problems:
        print(f'ice: {len(layers)} layers, one per function, no shared data or assumption')
    return 1 if problems else 0
