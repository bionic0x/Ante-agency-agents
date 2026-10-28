"""ante cohere — the seven coherence tests, non-additive.

Marco XIV, ``STRATEGIC-CONTROL-PLANE.md §5`` and the SDR template §8. Each test
gets a status and, when it is not a clean pass, a triage class:

    status   PASS | CONDITIONAL | FAIL | NOT_APPLICABLE
    class    FATAL_DEFECT | ACCEPTED_RISK | PENDING_EVIDENCE

    FAIL          → FATAL_DEFECT
    CONDITIONAL   → ACCEPTED_RISK (owner and reason) or PENDING_EVIDENCE (date or trigger)
    NOT_APPLICABLE→ a stated reason; never allowed where the doctrine table forbids it
                    (Epistemic and Exit)

Nothing is summed. The artefact states which decision outputs remain admissible:
one fatal defect removes PROCEED and PROCEED_WITH_CONDITIONS regardless of how
many tests pass; pending evidence removes them too (invariant 1: with incomplete
evidence the output is HOLD).

The tests come from the ``coherence_tests`` table of ``strategy/contracts.json``;
without that table the command refuses to run (decision D-004).

Input fields::

    tests  {test id: {status, reason, evidence: [claim id],
                      finding: {class, owner?, reason?, due?, trigger?} | null}}
    plan_metrics  [text]   metrics the plan relies on

Misuse analysis (``ante street``): a plan metric that no ``street`` artefact in
the lineage analyses keeps the interactive test from passing — a ``PASS`` is
recorded as ``CONDITIONAL`` with pending evidence (trigger: the missing
analysis), which leaves ``HOLD``, ``REDESIGN`` or ``REJECT``.
"""
from __future__ import annotations

from ante.core import canon, schema
from ante.core import time as ante_time
from ante.strategy.base import Command, Result, nonplaceholder
from ante.strategy.commands.street import covers

STATUSES = ('PASS', 'CONDITIONAL', 'FAIL', 'NOT_APPLICABLE')
CLASSES = ('FATAL_DEFECT', 'ACCEPTED_RISK', 'PENDING_EVIDENCE')
ALL_DECISIONS = ('PROCEED', 'PROCEED_WITH_CONDITIONS', 'HOLD', 'REDESIGN', 'REJECT')


def admissible(classes: set[str]) -> list[str]:
    if 'FATAL_DEFECT' in classes:
        return ['REDESIGN', 'REJECT']
    if 'PENDING_EVIDENCE' in classes:
        return ['HOLD', 'REDESIGN', 'REJECT']
    if 'ACCEPTED_RISK' in classes:
        return ['PROCEED_WITH_CONDITIONS', 'HOLD', 'REDESIGN', 'REJECT']
    return list(ALL_DECISIONS)


def run(doc, ctx):
    findings = ctx.findings
    table = ctx.doctrine.table('coherence_tests')
    by_id = {t['id']: t for t in table}
    tests = schema.obj(doc['tests'], 'tests')
    missing = sorted(set(by_id) - set(tests))
    unknown = sorted(set(tests) - set(by_id))
    if missing:
        findings.error('TEST_NOT_ANSWERED', 'tests', f'missing: {", ".join(missing)}')
    if unknown:
        findings.error('UNKNOWN_TEST', 'tests', f'not in the doctrine table: {", ".join(unknown)}')
    classes = set()
    for test_id, entry in tests.items():
        path = f'tests.{test_id}'
        schema.exact_keys(entry, ('status', 'reason', 'evidence', 'finding'), path)
        status = schema.enum(entry['status'], STATUSES, f'{path}.status')
        nonplaceholder(entry['reason'], f'{path}.reason', findings, 'UNREASONED_RESULT')
        ctx.refs(entry['evidence'], f'{path}.evidence', 0 if status == 'NOT_APPLICABLE' else 1)
        finding = entry['finding']
        rule = by_id.get(test_id, {})
        if status == 'NOT_APPLICABLE' and rule and not rule.get('not_applicable_allowed', False):
            findings.error('NOT_APPLICABLE_FORBIDDEN', f'{path}.status',
                           f'{test_id} can never be declared not applicable')
        if status in ('PASS', 'NOT_APPLICABLE'):
            if finding is not None:
                schema.fail(f'{path}.finding', f'no finding for status {status}')
            continue
        schema.obj(finding, f'{path}.finding')
        cls = schema.enum(finding.get('class'), CLASSES, f'{path}.finding.class')
        if status == 'FAIL' and cls != 'FATAL_DEFECT':
            findings.error('FAIL_NOT_FATAL', f'{path}.finding.class', 'a failed test is a fatal defect')
        if status == 'CONDITIONAL' and cls == 'FATAL_DEFECT':
            findings.error('CONDITIONAL_FATAL', f'{path}.status', 'a fatal defect is a FAIL, not CONDITIONAL')
        if cls == 'ACCEPTED_RISK':
            schema.exact_keys(finding, ('class', 'owner', 'reason'), f'{path}.finding')
            nonplaceholder(finding['owner'], f'{path}.finding.owner', findings, 'RISK_WITHOUT_OWNER')
            nonplaceholder(finding['reason'], f'{path}.finding.reason', findings)
        elif cls == 'PENDING_EVIDENCE':
            schema.exact_keys(finding, ('class',), f'{path}.finding', ('due', 'trigger'))
            if 'due' not in finding and 'trigger' not in finding:
                findings.error('PENDING_WITHOUT_DATE', f'{path}.finding', 'pending evidence needs a date or a trigger')
            if 'due' in finding:
                ante_time.parse(finding['due'], f'{path}.finding.due')
            if 'trigger' in finding:
                nonplaceholder(finding['trigger'], f'{path}.finding.trigger', findings)
        else:
            schema.exact_keys(finding, ('class', 'reason'), f'{path}.finding')
            nonplaceholder(finding['reason'], f'{path}.finding.reason', findings)
        classes.add(cls)

    metrics = schema.array(doc['plan_metrics'], 'plan_metrics')
    for index, metric in enumerate(metrics):
        nonplaceholder(metric, f'plan_metrics[{index}]', findings)
    street = ctx.lineage.one('street')
    uncovered = [m for m in metrics if isinstance(m, str) and not covers(street, m)]
    interactive = tests.get('interactive')
    if uncovered and isinstance(interactive, dict):
        trigger = 'ante street misuse analysis of: ' + '; '.join(uncovered)
        findings.warn('MISUSE_ANALYSIS_MISSING', 'tests.interactive',
                      'plan metrics without misuse analysis: ' + '; '.join(uncovered))
        if interactive.get('status') == 'PASS':
            tests = dict(tests, interactive={
                'status': 'CONDITIONAL', 'evidence': interactive['evidence'],
                'reason': f"{interactive['reason']} [recorded as CONDITIONAL: no misuse analysis of the plan's metrics]",
                'finding': {'class': 'PENDING_EVIDENCE', 'trigger': trigger}})
            classes.add('PENDING_EVIDENCE')

    body = {
        'tests': tests,
        'plan_metrics': metrics,
        'misuse_analysis': {'street': street['artifact_sha256'] if street else None, 'uncovered_metrics': uncovered},
        'doctrine_sha256': canon.digest(ctx.doctrine.raw),
        'classes': sorted(classes),
        'admissible_verdicts': admissible(classes),
        'reading': 'Non-additive: one fatal defect removes PROCEED and PROCEED_WITH_CONDITIONS.',
    }
    return Result(body=body, next_decision='Sweep the fourteen pathologies (ante pathology), then decide.')


COMMAND = Command(name='cohere', summary='seven coherence tests with triage; admissible verdicts',
                  fields=('tests', 'plan_metrics'), parents=('frame',), review=True, run=run)
