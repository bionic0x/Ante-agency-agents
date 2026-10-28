"""ante nodal — the claims that carry the plan.

Marco VIII.5: verification effort should grow with irreversibility, impact and
causal dependence — "a low-visibility assumption can sustain the calendar, the
allocation and the estimate of the adversary's reaction; if it falls, it drags the
whole plan". ``nodal`` reads the whole artefact chain supplied with ``--from``,
builds the dependency graph between claims and the inferences that cite them,
and reports the **load-bearing claims**.

- **Load** of a claim: the number of distinct inference sites across the chain
  that cite it (``basis``, ``evidence``, ``assumptions``, ``claim`` fields),
  excluding the artefact that states it.
- **Irreversibility**: the least reversible viable option in the ``options``
  artefact; without one it is treated as low (``unknown``).
- **Required verification**: ``load × weight`` (weight 1 for high reversibility,
  1.5 medium, 2 low or unknown). At 4 or more the claim must be **corroborated**;
  at 2 or more it must be **checked**; below, routine.

A claim that must be corroborated but stands as ``ASSUMPTION`` or
``ATTRIBUTED_INTENT`` is **blocking**: ``decide`` refuses ``PROCEED`` until it is
corroborated (re-run ``nodal`` after the upgrade) or accepted as a named risk in
the decision (``accepted_risks``).

Input: only the envelope (``at``, ``claims``). A claim restated in nodal's own
``claims`` (for example an assumption now corroborated by an external source)
replaces the earlier statement in the graph. Lineage: ``frame`` plus every
other artefact of the case that should be examined.
"""
from __future__ import annotations

from ante.core import time as ante_time
from ante.strategy.base import Command, Result

REF_KEYS = ('basis', 'evidence', 'assumptions', 'claim')
WEIGHTS = {'high': 1.0, 'medium': 1.5, 'low': 2.0, 'unknown': 2.0}
CORROBORATE, CHECK = 4.0, 2.0
UNVERIFIED = ('ASSUMPTION', 'ATTRIBUTED_INTENT')


def _sites(value, path, known, found):
    if isinstance(value, dict):
        for key, item in value.items():
            here = f'{path}.{key}' if path else key
            if key in REF_KEYS:
                refs = [item] if isinstance(item, str) else item if isinstance(item, list) else []
                for ref in refs:
                    if isinstance(ref, str) and ref in known:
                        found.append((ref, here))
            _sites(item, here, known, found)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _sites(item, f'{path}[{index}]', known, found)


def graph(parents: list[dict], own_claims: list[dict] = ()) -> dict:
    """Claims by id with their latest status and the inference sites that cite them.

    Citations inside an artefact that states the claim are not counted: an
    artefact citing its own claim adds no dependency beyond the statement.
    """
    ordered = sorted(parents, key=lambda p: (ante_time.parse(p['at'], 'at'), p['command'], p['artifact_sha256']))
    statements = [(p['artifact_sha256'], p['command'], c) for p in ordered for c in p['claims']]
    statements += [(None, 'nodal', c) for c in own_claims]
    claims, stated_by = {}, {}
    for sha, command, claim in statements:   # the latest statement of an id wins; nodal's own claims last
        source = claim['source'] if isinstance(claim['source'], dict) else {}
        claims[claim['id']] = {'status': claim['status'], 'origin': source.get('origin'),
                               'stated_in': command, 'cited_by': []}
        stated_by.setdefault(claim['id'], set()).add(sha)
    for parent in ordered:
        found = []
        _sites(parent['body'], '', set(claims), found)
        for claim_id, site in found:
            label = f'{parent["command"]}:{site}'
            entry = claims[claim_id]
            if parent['artifact_sha256'] not in stated_by[claim_id] and label not in entry['cited_by']:
                entry['cited_by'].append(label)
    return claims


def irreversibility(parents: list[dict]) -> str:
    options = [p for p in parents if p['command'] == 'options']
    if not options:
        return 'unknown'
    levels = [o['reversibility'] for o in options[-1]['body'].get('options', []) if o.get('viable')]
    for level in ('low', 'medium', 'high'):
        if level in levels:
            return level
    return 'unknown'


def assess(parents: list[dict], own_claims: list[dict] = ()) -> dict:
    claims = graph(parents, own_claims)
    level = irreversibility(parents)
    weight = WEIGHTS[level]
    rows = []
    for claim_id, entry in sorted(claims.items()):
        load = len(entry['cited_by'])
        score = load * weight
        required = 'corroborate' if score >= CORROBORATE else 'check' if score >= CHECK else 'routine'
        rows.append({'id': claim_id, 'status': entry['status'], 'origin': entry['origin'],
                     'stated_in': entry['stated_in'], 'load': load, 'score': score,
                     'required_verification': required, 'cited_by': entry['cited_by'],
                     'blocking': required == 'corroborate' and entry['status'] in UNVERIFIED})
    rows.sort(key=lambda r: (-r['score'], r['id']))
    return {'irreversibility': level, 'weight': weight,
            'thresholds': {'corroborate': CORROBORATE, 'check': CHECK},
            'artefacts_examined': sorted(f'{p["command"]}:{p["artifact_sha256"][:12]}' for p in parents),
            'load_bearing_claims': [r for r in rows if r['required_verification'] != 'routine'],
            'routine_claims': [r['id'] for r in rows if r['required_verification'] == 'routine'],
            'blocking': [r['id'] for r in rows if r['blocking']]}


def run(doc, ctx):
    body = assess(ctx.lineage.parents, ctx.claims)
    for claim_id in body['blocking']:
        ctx.findings.warn('LOAD_BEARING_UNVERIFIED', claim_id,
                          'carries the plan unverified: corroborate it or accept it as a named risk in decide')
    if body['irreversibility'] == 'unknown':
        ctx.findings.warn('IRREVERSIBILITY_UNKNOWN', 'options', 'no options artefact; treated as low reversibility')
    if body['blocking']:
        next_decision = ('Corroborate ' + ', '.join(body['blocking']) + ' and re-run nodal, or accept them as '
                         'named risks in decide; PROCEED is refused until then.')
    else:
        next_decision = 'No load-bearing claim stands unverified; carry the checks listed into watch.'
    return Result(body=body, next_decision=next_decision)


COMMAND = Command(name='nodal', summary='load-bearing claims across the artefact chain (VIII.5)', fields=(),
                  parents=('frame',), run=run)
