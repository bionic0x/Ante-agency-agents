"""ante ach — analysis of competing hypotheses with source dependence made visible.

Marco VIII.4 (Heuer, chapter 8; Dhami et al. 2019 on its limits). The matrix rates
each piece of evidence against each hypothesis — ``C`` consistent, ``I``
inconsistent, ``N`` neutral or not applicable — and the command computes, without
turning ratings into probabilities:

- **source groups**: evidence that shares a source, or declares that it depends
  on other evidence, is one group and counts once (ten reports repeating one
  source are one observation);
- **self-produced evidence**: evidence resting on a claim whose source origin is
  ``system`` is listed but never counted (invariant 7);
- **inconsistency per hypothesis**, raw and by source group (Heuer weighs what
  contradicts a hypothesis, not what agrees with it);
- **diagnosticity**: evidence rated identically against every hypothesis
  discriminates nothing;
- **sensitivity**: evidence whose removal would change the least-inconsistent
  set — the items to corroborate first (VIII.5).

Input fields::

    hypotheses         [{id, statement}]                      at least two
    evidence           [{id, description, claim, source_id, depends_on: [evidence id]}]
    matrix             {evidence id: {hypothesis id: "C" | "I" | "N"}}
    future_indicators  [{hypothesis, indicator}]
    confidence         {verbal, interval: [low, high]}        calibrated language (VIII.10)
"""
from __future__ import annotations

from ante.core import schema
from ante.strategy.base import Command, Result, nonplaceholder

RATINGS = ('C', 'I', 'N')


class _Groups:
    def __init__(self, ids):
        self.parent = {i: i for i in ids}

    def find(self, item):
        while self.parent[item] != item:
            self.parent[item] = self.parent[self.parent[item]]
            item = self.parent[item]
        return item

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[max(ra, rb)] = min(ra, rb)


def _least_inconsistent(hyp_ids, counted, matrix, groups):
    totals = {}
    for h in hyp_ids:
        inconsistent_groups = {groups.find(e) for e in counted if matrix[e][h] == 'I'}
        totals[h] = len(inconsistent_groups)
    best = min(totals.values()) if totals else 0
    return totals, sorted(h for h, v in totals.items() if v == best)


def run(doc, ctx):
    findings = ctx.findings
    hypotheses = schema.array(doc['hypotheses'], 'hypotheses', 2)
    hyp_ids = schema.unique_ids(hypotheses, 'hypotheses')
    for index, h in enumerate(hypotheses):
        schema.exact_keys(h, ('id', 'statement'), f'hypotheses[{index}]')
        nonplaceholder(h['statement'], f'hypotheses[{index}].statement', findings)

    evidence = schema.array(doc['evidence'], 'evidence', 1)
    ev_ids = schema.unique_ids(evidence, 'evidence')
    groups = _Groups(ev_ids)
    by_source: dict[str, str] = {}
    excluded = []
    for index, item in enumerate(evidence):
        path = f'evidence[{index}]'
        schema.exact_keys(item, ('id', 'description', 'claim', 'source_id', 'depends_on'), path)
        nonplaceholder(item['description'], f'{path}.description', findings)
        nonplaceholder(item['source_id'], f'{path}.source_id', findings, 'UNSOURCED_EVIDENCE')
        ctx.refs([item['claim']], f'{path}.claim', 1)
        claim = ctx.claim(item['claim'])
        if claim and claim['source']['origin'] == 'system':
            excluded.append(item['id'])
            findings.warn('SELF_CORROBORATION', f'{path}.claim',
                          'rests on a system-produced claim; listed but not counted')
        for dep in schema.array(item['depends_on'], f'{path}.depends_on'):
            if dep not in ev_ids:
                findings.error('UNKNOWN_EVIDENCE', f'{path}.depends_on', 'depends on evidence not in this matrix')
            else:
                groups.union(item['id'], dep)
        if isinstance(item['source_id'], str):
            if item['source_id'] in by_source:
                groups.union(item['id'], by_source[item['source_id']])
            else:
                by_source[item['source_id']] = item['id']

    matrix = schema.obj(doc['matrix'], 'matrix')
    if set(matrix) != set(ev_ids):
        findings.error('INCOMPLETE_MATRIX', 'matrix', 'every evidence item needs a row')
    for ev, row in matrix.items():
        schema.obj(row, f'matrix.{ev}')
        if set(row) != set(hyp_ids):
            findings.error('INCOMPLETE_MATRIX', f'matrix.{ev}', 'every hypothesis needs a rating')
        for h, rating in row.items():
            schema.enum(rating, RATINGS, f'matrix.{ev}.{h}')
    indicators = schema.array(doc['future_indicators'], 'future_indicators', 1)
    for index, ind in enumerate(indicators):
        schema.exact_keys(ind, ('hypothesis', 'indicator'), f'future_indicators[{index}]')
        if ind['hypothesis'] not in hyp_ids:
            findings.error('UNKNOWN_HYPOTHESIS', f'future_indicators[{index}].hypothesis', 'not a hypothesis id')
        nonplaceholder(ind['indicator'], f'future_indicators[{index}].indicator', findings)
    confidence = schema.exact_keys(doc['confidence'], ('verbal', 'interval'), 'confidence')
    nonplaceholder(confidence['verbal'], 'confidence.verbal', findings)
    interval = schema.array(confidence['interval'], 'confidence.interval', 2)
    if len(interval) != 2:
        schema.fail('confidence.interval', 'exactly [low, high] required')
    low = schema.number(interval[0], 'confidence.interval[0]', 0, 1)
    high = schema.number(interval[1], 'confidence.interval[1]', 0, 1)
    schema.require(low <= high, 'confidence.interval', 'low must not exceed high')
    findings.raise_errors()

    counted = [e for e in ev_ids if e not in excluded]
    raw = {h: sum(1 for e in counted if matrix[e][h] == 'I') for h in hyp_ids}
    by_group, least = _least_inconsistent(hyp_ids, counted, matrix, groups)
    shared = {}
    for e in ev_ids:
        shared.setdefault(groups.find(e), []).append(e)
    shared_groups = sorted((sorted(members) for members in shared.values() if len(members) > 1))
    for members in shared_groups:
        findings.warn('SHARED_SOURCE', 'evidence', f'{", ".join(members)} share a source or depend on each other; counted once')
    non_diagnostic = sorted(e for e in counted if len({matrix[e][h] for h in hyp_ids}) == 1)
    sensitive = []
    for e in counted:
        _, without = _least_inconsistent(hyp_ids, [x for x in counted if x != e], matrix, groups)
        if without != least:
            sensitive.append(e)
    body = {
        'hypotheses': hypotheses, 'evidence': evidence, 'matrix': matrix,
        'future_indicators': indicators, 'confidence': confidence,
        'analysis': {
            'counted_evidence': counted,
            'excluded_self_produced': sorted(excluded),
            'source_groups': shared_groups,
            'inconsistency_raw': raw,
            'inconsistency_by_source_group': by_group,
            'least_inconsistent': least,
            'non_diagnostic': non_diagnostic,
            'sensitive_evidence': sorted(sensitive),
            'interpretation': ('Ratings are judgements, not probabilities. The least-inconsistent set is '
                               'conditional on the matrix; corroborate the sensitive evidence first.'),
        },
    }
    next_decision = ('Corroborate ' + ', '.join(sorted(sensitive)) + ' before relying on the result.'
                     if sensitive else 'Record the leading hypothesis with its confidence and indicators.')
    return Result(body=body, next_decision=next_decision)


COMMAND = Command(name='ach', summary='competing hypotheses, diagnosticity, sensitivity and source dependence',
                  fields=('hypotheses', 'evidence', 'matrix', 'future_indicators', 'confidence'),
                  parents=('frame',), review=True, run=run)
