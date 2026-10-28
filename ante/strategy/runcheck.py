"""``ante run RUNBOOK`` — is the case's artefact chain complete for this runbook?

Reads ``strategy_commands`` from ``strategy/runbooks.json`` and checks a directory
of artefacts: every one is intact, they belong to one case, every declared parent
is present, and each required command appears exactly once. It executes nothing.

Exit 0 complete, 1 incomplete, 3 broken lineage.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from ante import doctrine as doctrine_mod
from ante import registry
from ante.core import canon
from ante.strategy import artifact, chain


def check(runbook: dict, directory: Path, doctrine_hash: str | None = None) -> dict:
    required = runbook.get('strategy_commands')
    if not isinstance(required, list) or not required:
        return {'runbook': runbook['slug'], 'complete': False,
                'missing': ['runbook declares no strategy_commands'], 'present': []}
    loaded = chain.load(directory)
    cases = {a['case_id'] for a in loaded}
    counts = {}
    for art in loaded:
        counts[art['command']] = counts.get(art['command'], 0) + 1
    missing = [c for c in required if counts.get(c, 0) == 0]
    repeated = [c for c in required if counts.get(c, 0) > 1]
    decide = [a for a in loaded if a['command'] == 'decide']
    foreign = sorted(a['command'] for a in loaded
                     if doctrine_hash and 'doctrine_sha256' in a['body'] and a['body']['doctrine_sha256'] != doctrine_hash)
    return {
        'runbook': runbook['slug'],
        'case_id': next(iter(cases)) if cases else None,
        'required': required,
        'present': sorted(counts),
        'missing': missing,
        'repeated': repeated,
        'verdict': decide[0]['verdict'] if len(decide) == 1 else None,
        'non_canonical_doctrine': foreign,
        'complete': not missing and not repeated and not foreign,
        'note': 'A complete chain is a record, not an authorisation to act.',
    }


def main(args) -> int:
    runbooks = registry.runbooks()
    if args.runbook not in runbooks:
        print(f'INVALID unknown runbook {args.runbook}', file=sys.stderr)
        return 2
    try:
        doctrine = doctrine_mod.load(args.contracts) if args.contracts else doctrine_mod.load()
        report = check(runbooks[args.runbook], Path(args.artifacts), canon.digest(doctrine.raw))
    except artifact.LineageError as exc:
        print(f'LINEAGE {exc}', file=sys.stderr)
        return 3
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report['complete'] else 1
