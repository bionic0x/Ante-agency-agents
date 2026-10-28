"""``ante ghosts``: expired claims that live artefacts still cite.

A claim can outlive its truth. It may carry ``expires`` (renew it after that
date), or predate a declared change of regime — a new law, a merger, a market
break — after which earlier observations no longer describe the situation.
``ghosts`` reads a case directory and reports every such claim that is still
cited by a **live** artefact (one whose case has no decision record, or whose
decision record has not expired). Each must be renewed with a new dated
statement or withdrawn from the artefacts that cite it.

    ante ghosts --artifacts DIR --at T [--regimes FILE]

``FILE``: ``{"changes": [{"id", "at", "scope", "description"}]}``. Exit 1 when a
ghost is found. In decision records this is ``stale_claims``.
"""
from __future__ import annotations

import json
import sys

from ante.core import io, schema
from ante.core import time as ante_time
from ante.strategy import artifact, chain
from ante.strategy.commands import nodal


def _regimes(path: str | None) -> list[dict]:
    if path is None:
        return []
    doc = io.load_document(path)
    schema.exact_keys(doc, ('changes',), 'regimes')
    changes = []
    for index, change in enumerate(schema.array(doc['changes'], 'changes')):
        where = f'changes[{index}]'
        schema.exact_keys(change, ('id', 'at', 'scope', 'description'), where)
        for key in ('id', 'scope', 'description'):
            schema.text(change[key], f'{where}.{key}')
        changes.append({**change, 'when': ante_time.parse(change['at'], f'{where}.at')})
    return changes


def audit(directory: str, at: str, regimes: list[dict] = ()) -> dict:
    now = ante_time.parse(at, 'at')
    arts = [a for a in chain.load(directory) if ante_time.parse(a['at'], 'at') <= now]
    decides = [a for a in arts if a['command'] == 'decide']
    live = not decides or any(ante_time.parse(d['body']['expires'], 'expires') > now for d in decides)
    graph = nodal.graph(arts)
    statements = {c['id']: (a, c) for a in arts for c in a['claims']}   # latest statement wins (arts sorted by time)
    ghosts = []
    for claim_id, (art, claim) in sorted(statements.items()):
        reasons = []
        if 'expires' in claim and chain.when(claim['expires'], 'expires') <= now:
            reasons.append(f'expired {claim["expires"]}')
        dated = chain.when(claim['date'], 'date')
        for change in regimes:
            if dated < change['when'] <= now:
                reasons.append(f'predates regime change {change["id"]} ({change["at"]}): {change["description"]}')
        cited = graph[claim_id]['cited_by'] if claim_id in graph else []
        if reasons and cited and live:
            ghosts.append({'claim': claim_id, 'status': claim['status'], 'stated_in': art['command'],
                           'date': claim['date'], 'reasons': reasons, 'cited_by': cited,
                           'required': 'renew with a new dated statement, or withdraw it from the citing artefacts'})
    return {'kind': 'stale_claims', 'at': ante_time.iso(now), 'case_id': arts[0]['case_id'] if arts else None,
            'live': live, 'ghosts': ghosts}


def add_parser(sub) -> None:
    parser = sub.add_parser('ghosts', help='expired or pre-regime claims still cited by live artefacts')
    parser.add_argument('--artifacts', required=True)
    parser.add_argument('--at', required=True)
    parser.add_argument('--regimes')
    parser.set_defaults(handler=main)


def main(args) -> int:
    try:
        result = audit(args.artifacts, args.at, _regimes(args.regimes))
    except artifact.LineageError as exc:
        print(f'LINEAGE {exc}', file=sys.stderr)
        return 3
    except (io.InputError, schema.SchemaError, ante_time.TimeError) as exc:
        print(f'INVALID {exc}', file=sys.stderr)
        return 2
    sys.stdout.write(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False) + '\n')
    return 1 if result['ghosts'] else 0
