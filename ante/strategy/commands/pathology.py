"""ante pathology — sweep of the fourteen strategic pathologies.

Marco XV and ``STRATEGIC-CONTROL-PLANE.md §8``. Every pathology in the
``pathologies`` table of ``strategy/contracts.json`` is answered:

    DETECTED       evidence (claim ids) and a false-positive check are required:
                   perseverance is not escalation, reserve is not hesitation (XV)
    NOT_DETECTED   a reason
    NOT_ASSESSED   a reason — an honest gap, never a silent pass

*Denied culmination* is a different mechanism from *level inversion* and from
*escalation of commitment*. Declaring them on the same evidence conflates them
and is refused: culmination is about the marginal sign of further effort,
inversion about which criterion of success governs, escalation about sunk cost
used as a reason.

Input fields::

    pathologies  {pathology id: {status, evidence: [claim id], false_positive_check, note}}
"""
from __future__ import annotations

from ante.core import canon, schema
from ante.strategy.base import Command, Result, nonplaceholder

STATUSES = ('DETECTED', 'NOT_DETECTED', 'NOT_ASSESSED')
SEPARATE_FROM_CULMINATION = ('level_inversion', 'escalation_of_commitment')
CULMINATION = 'denied_culmination'


def run(doc, ctx):
    findings = ctx.findings
    table = {p['id']: p for p in ctx.doctrine.table('pathologies')}
    answers = schema.obj(doc['pathologies'], 'pathologies')
    missing = sorted(set(table) - set(answers))
    unknown = sorted(set(answers) - set(table))
    if missing:
        findings.error('PATHOLOGY_NOT_SWEPT', 'pathologies', f'missing: {", ".join(missing)}')
    if unknown:
        findings.error('UNKNOWN_PATHOLOGY', 'pathologies', f'not in the doctrine table: {", ".join(unknown)}')
    detected = []
    for pid, answer in answers.items():
        path = f'pathologies.{pid}'
        schema.exact_keys(answer, ('status', 'evidence', 'false_positive_check', 'note'), path)
        status = schema.enum(answer['status'], STATUSES, f'{path}.status')
        if status == 'DETECTED':
            ctx.refs(answer['evidence'], f'{path}.evidence', 1)
            nonplaceholder(answer['false_positive_check'], f'{path}.false_positive_check', findings,
                           'NO_FALSE_POSITIVE_CHECK')
            detected.append(pid)
        else:
            ctx.refs(answer['evidence'], f'{path}.evidence')
            nonplaceholder(answer['note'], f'{path}.note', findings, 'UNREASONED_SWEEP')
    culmination = answers.get(CULMINATION)
    if isinstance(culmination, dict) and culmination.get('status') == 'DETECTED':
        culmination_evidence = set(culmination.get('evidence') or [])
        for other in SEPARATE_FROM_CULMINATION:
            answer = answers.get(other)
            if (isinstance(answer, dict) and answer.get('status') == 'DETECTED'
                    and culmination_evidence and set(answer.get('evidence') or []) == culmination_evidence):
                findings.error('CONFLATED_PATHOLOGIES', f'pathologies.{other}',
                               f'{other} and {CULMINATION} rest on identical evidence; they are different mechanisms')

    body = {
        'pathologies': answers,
        'detected': [{'id': pid, 'mechanism': table[pid].get('mechanism'), 'correction': table[pid].get('correction')}
                     for pid in sorted(detected) if pid in table],
        'not_assessed': sorted(pid for pid, a in answers.items() if isinstance(a, dict) and a.get('status') == 'NOT_ASSESSED'),
        'doctrine_sha256': canon.digest(ctx.doctrine.raw),
    }
    next_decision = ('Address ' + ', '.join(sorted(detected)) + ' in the decision conditions (ante decide).'
                     if detected else 'Record the decision (ante decide).')
    return Result(body=body, next_decision=next_decision)


COMMAND = Command(name='pathology', summary='sweep of the fourteen pathologies with false-positive checks',
                  fields=('pathologies',), parents=('frame',), review=True, run=run)
