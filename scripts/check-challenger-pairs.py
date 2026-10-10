#!/usr/bin/env python3
"""check-challenger-pairs.py — keep proposer/challenger pairs intact across the catalog.

strategy/challenger-pairs.json names agents whose work must be independently
judged before it influences anything else (P8 in strategy/NEXUS-INSTANCE.md).
The engine enforces the verdict gate inside an instance. This check enforces what
the engine cannot see, at the catalog level:

  1. the registry is well formed: known agents, two different agents per pair,
     no agent playing both roles across pairs, known excluded runbooks;
  2. every runbook that rosters a proposer also rosters its challenger, so the
     pair is always installed and activated together;
  3. no runbook listed in a pair's `excluded_runbooks` rosters either agent;
  4. each agent file names its counterpart, so the separation of duties is also
     stated where the agent reads it.

It does not authenticate a verdict, judge its quality, or stop a host from
running the proposer outside NEXUS.
"""
import json
from pathlib import Path
import runpy
import sys

ROOT = Path(__file__).resolve().parents[1]


def check(registry, agents, runbooks):
    errors = []
    slugs = {a['slug']: a for a in agents}
    books = {r['slug']: r for r in runbooks}
    if registry.get('schema_version') != 1:
        errors.append('challenger-pairs.json: schema_version must be 1')
    decisions = set(json.loads((ROOT / 'strategy/contracts.json').read_text())['decision_states'])
    favourable = registry.get('favourable_verdicts')
    if not isinstance(favourable, list) or not favourable or not set(favourable) <= decisions:
        errors.append('favourable_verdicts must be a non-empty subset of the canonical decision states')
    pairs = registry.get('pairs')
    if not isinstance(pairs, list) or not pairs:
        return errors + ['pairs must be a non-empty array']
    roles, ids = {}, set()
    for pair in pairs:
        pid = pair.get('id', '<no id>')
        if pid in ids:
            errors.append(f'duplicate pair id {pid}')
        ids.add(pid)
        proposer, challenger = pair.get('proposer'), pair.get('challenger')
        for role, slug in (('proposer', proposer), ('challenger', challenger)):
            if slug not in slugs:
                errors.append(f'{pid}: {role} {slug!r} is not a catalog agent')
            elif roles.setdefault(slug, role) != role:
                errors.append(f'{pid}: {slug} is a proposer in one pair and a challenger in another')
        if proposer == challenger:
            errors.append(f'{pid}: proposer and challenger must differ')
        if not str(pair.get('rationale', '')).strip():
            errors.append(f'{pid}: rationale required')
        excluded = pair.get('excluded_runbooks', [])
        if not isinstance(excluded, list):
            errors.append(f'{pid}: excluded_runbooks must be an array')
            excluded = []
        for slug in excluded:
            if slug not in books:
                errors.append(f'{pid}: excluded runbook {slug!r} does not exist')
        for book in runbooks:
            roster = {a for g in book['roster'] for a in g['agents']}
            if proposer in roster and challenger not in roster:
                errors.append(f'runbook {book["slug"]} rosters {proposer} without its challenger {challenger}')
            if book['slug'] in excluded and roster & {proposer, challenger}:
                errors.append(f'runbook {book["slug"]} is excluded for pair {pid} but rosters it')
        for slug, other in ((proposer, challenger), (challenger, proposer)):
            if slug in slugs and other in slugs:
                body = (ROOT / slugs[slug]['path']).read_text(encoding='utf-8')
                if Path(slugs[other]['path']).name not in body:
                    errors.append(f'{slugs[slug]["path"]} does not link its counterpart {slugs[other]["path"]}')
    return errors


def main():
    registry = json.loads((ROOT / 'strategy/challenger-pairs.json').read_text(encoding='utf-8'))
    _, agents, runbooks = runpy.run_path(str(ROOT / 'scripts/build-catalog.py'))['collect']()
    errors = check(registry, agents, runbooks)
    for error in errors:
        print(f'ERROR {error}')
    if errors:
        print(f'FAILED: {len(errors)} challenger-pair error(s)')
        return 1
    print(f'PASSED: {len(registry["pairs"])} challenger pair(s) intact across {len(runbooks)} runbooks')
    return 0


if __name__ == '__main__':
    sys.exit(main())
