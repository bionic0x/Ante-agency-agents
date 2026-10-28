"""ante selftest — the institutional self-test applied to this repository.

Marco VIII.13 and ``strategy/INSTITUTIONAL-SELF-TEST.md``. The eight rows are read
from that document's table (one source). Results come only from the dated,
human-recorded entries of an evidence register:

    PASS              dated evidence of the function working in the declared scope
    FAIL              evidence of failure
    NOT_DEMONSTRATED  evidence insufficient — the default; missing evidence is not failure

The command never upgrades a row by itself. It lists, per row, the mechanisms the
repository can show mechanically (``mechanisms``) so the reviewer knows what to
examine, and it publishes every row that is not ``PASS``. There is no score.
CI runs it before a release and prints the result; a row in ``FAIL`` is reported,
not hidden, and does not break the build (the doctrine: CI does not certify these
predicates).

Input fields::

    entries  [{row, scope, evidence_ref, date, result, reviewer, owner, gap, next_trigger}]
             owner may be "UNDESIGNATED"; an agent role name is not an appointment.
"""
from __future__ import annotations

import json
import re

from ante.core import schema
from ante.core import time as ante_time
from ante.paths import ROOT
from ante.strategy.base import Command, Result, nonplaceholder

RESULTS = ('PASS', 'FAIL', 'NOT_DEMONSTRATED')
SELF_TEST = ROOT / 'strategy' / 'INSTITUTIONAL-SELF-TEST.md'
ROW = re.compile(r'^\|\s*(\d)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*$')


def rows() -> list[dict]:
    found = []
    for line in SELF_TEST.read_text(encoding='utf-8').splitlines():
        match = ROW.match(line)
        if match and len(found) < 8 and int(match.group(1)) == len(found) + 1:
            found.append({'row': int(match.group(1)), 'failure': match.group(2),
                          'response': match.group(3), 'test': match.group(4)})
    if len(found) != 8:
        raise schema.SchemaError('INSTITUTIONAL-SELF-TEST.md: the eight-row table could not be read')
    return found


def mechanisms() -> dict[int, list[str]]:
    """What the repository can show mechanically. Never a result."""
    runbooks = json.loads((ROOT / 'strategy/runbooks.json').read_text(encoding='utf-8'))['runbooks']
    with_breach = sum(1 for r in runbooks if r.get('termination_contract', {}).get('on_breach'))
    found = {
        1: ['strategy/STRATEGIC-CONTROL-PLANE.md defines escalation and decision-owner roles'],
        2: ['ante artefacts carry claim status, source, date and limit through every step',
            'scripts/check-strategy-vocabulary.py keeps the five epistemic states in the handoff templates'],
        3: ['ante cohere and ante decide record independence_level; PROCEED requires INDEPENDENT_OPERATOR'],
        4: ['ante decide refuses a record with neither dissent nor the people asked for it'],
        5: [f'{with_breach}/{len(runbooks)} runbooks declare an on_breach clause',
            'ante watch refuses indicators without a response and plans without a stopping threshold'],
        6: [],
        7: ['ante cohere records the plan metrics it relies on'],
        8: ['ante decide records dated expectations with refutation conditions'],
    }
    return found


def run(doc, ctx):
    findings = ctx.findings
    table = rows()
    entries = schema.array(doc['entries'], 'entries')
    now = ante_time.parse(ctx.at, 'at')
    latest: dict[int, dict] = {}
    for index, entry in enumerate(entries):
        path = f'entries[{index}]'
        schema.exact_keys(entry, ('row', 'scope', 'evidence_ref', 'date', 'result', 'reviewer', 'owner', 'gap',
                                  'next_trigger'), path)
        row = schema.integer(entry['row'], f'{path}.row', 1)
        schema.require(row <= 8, f'{path}.row', 'rows are 1 to 8')
        result = schema.enum(entry['result'], RESULTS, f'{path}.result')
        date = ante_time.parse(entry['date'], f'{path}.date')
        if date > now:
            findings.error('FUTURE_EVIDENCE', f'{path}.date', 'dated after the review time')
        nonplaceholder(entry['scope'], f'{path}.scope', findings)
        nonplaceholder(entry['reviewer'], f'{path}.reviewer', findings, 'NO_REVIEWER')
        nonplaceholder(entry['owner'], f'{path}.owner', findings, 'OWNER_NOT_STATED')
        nonplaceholder(entry['next_trigger'], f'{path}.next_trigger', findings)
        if result in ('PASS', 'FAIL'):
            nonplaceholder(entry['evidence_ref'], f'{path}.evidence_ref', findings, 'RESULT_WITHOUT_EVIDENCE')
        if result != 'PASS':
            nonplaceholder(entry['gap'], f'{path}.gap', findings, 'GAP_NOT_STATED')
        previous = latest.get(row)
        if previous is None or ante_time.parse(previous['date'], 'date') <= date:
            latest[row] = entry
    machine = mechanisms()
    report = []
    for row in table:
        entry = latest.get(row['row'])
        report.append({**row, 'result': entry['result'] if entry else 'NOT_DEMONSTRATED',
                       'entry': entry, 'mechanisms': machine[row['row']]})
    published = [r['row'] for r in report if r['result'] != 'PASS']
    body = {'source': 'strategy/INSTITUTIONAL-SELF-TEST.md', 'rows': report,
            'published_gaps': published,
            'reading': 'No score. A PASS describes a capability that decays; the review is repeated per release.'}
    next_decision = ('Release owner: decide how rows ' + ', '.join(map(str, published)) + ' affect the release.'
                     if published else 'Record the next review trigger.')
    return Result(body=body, case_id='institutional-self-test', next_decision=next_decision)


COMMAND = Command(name='selftest', summary='institutional self-test of this repository (eight rows)',
                  fields=('entries',), root=True, run=run)
