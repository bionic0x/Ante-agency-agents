"""Shadow trials: a candidate runs beside real decisions, without effect.

A candidate profile, runbook or routing produces its own recommendation for a
real recorded decision. The recommendation goes to a separate shadow log — a
hash-chained file that is never the decision ledger — dated, and hidden: no
command shows it while the decision's expectations are unreconciled, so it
cannot reach the person deciding. When ``learn reconcile`` brings outcomes, the
shadow and the real forecasts are compared on the same expectations. Adoption
can only be proposed (through ``ante develop``) after ``MIN_HISTORY`` compared
predictions, and never happens here.

Isolation, by construction and by test:

- shadow entries are not artefacts: ``--from`` refuses them, ``ante run`` does
  not count them, ``learn record`` refuses them;
- a shadow log is refused if it is a decision ledger, and a ledger is refused as a
  shadow log;
- a shadow recommendation is refused once its decision has any reconciled
  outcome (no hindsight), and the decision's own snapshot never mentions it.

    ante stub record SPEC.json --log S --ledger L --at T
    ante stub compare --log S --ledger L --at T [--min-history N]
    ante stub status  --log S

In decision records this is ``shadow_trial``.
"""
from __future__ import annotations

import json
import sys

from ante.core import canon, io, schema
from ante.core import time as ante_time
from ante.learn import ledger

KINDS = ('shadow',)
CANDIDATE_KINDS = ('profile', 'runbook', 'routing')
MIN_HISTORY = 30
VERDICTS = ('PROCEED', 'PROCEED_WITH_CONDITIONS', 'HOLD', 'REDESIGN', 'REJECT')


class StubError(ValueError):
    pass


def _log(path: str) -> list[dict]:
    entries = ledger.read(path)
    if any(e['kind'] != 'shadow' for e in entries):
        raise StubError('this file is a decision ledger, not a shadow log; shadow output never enters it')
    return entries


def record(spec_path: str, log_path: str, ledger_path: str, at: str) -> dict:
    from pathlib import Path
    if Path(log_path).resolve() == Path(ledger_path).resolve():
        raise StubError('the shadow log and the decision ledger must be different files')
    spec = io.load_document(spec_path)
    schema.exact_keys(spec, ('candidate', 'decision', 'verdict', 'predictions', 'rationale'), 'shadow')
    cand = schema.exact_keys(spec['candidate'], ('id', 'kind', 'ref', 'sha256'), 'shadow.candidate')
    schema.text(cand['id'], 'shadow.candidate.id')
    schema.enum(cand['kind'], CANDIDATE_KINDS, 'shadow.candidate.kind')
    schema.text(cand['ref'], 'shadow.candidate.ref')
    schema.text(cand['sha256'], 'shadow.candidate.sha256')
    schema.enum(spec['verdict'], VERDICTS, 'shadow.verdict')
    schema.text(spec['rationale'], 'shadow.rationale')
    entries = _log(log_path)
    real = ledger.read(ledger_path)
    if any(e['kind'] == 'shadow' for e in real):
        raise StubError('the decision ledger contains shadow entries; isolation already broken')
    decision = ledger.decisions(real).get(spec['decision'])
    if decision is None:
        raise StubError('no recorded decision with this artefact hash')
    if any(e['payload']['decision'] == spec['decision'] for e in ledger.reconciliations(real)):
        raise StubError('this decision already has reconciled outcomes; a shadow recommendation now is hindsight')
    if any(e['payload']['decision'] == spec['decision'] and e['payload']['candidate']['id'] == cand['id']
           for e in entries):
        raise StubError('this candidate already recorded a recommendation for this decision')
    expectations = {e['id'] for e in decision['payload']['artifact']['body']['snapshot']['expectations']}
    predictions = schema.array(spec['predictions'], 'shadow.predictions')
    for index, item in enumerate(predictions):
        path = f'shadow.predictions[{index}]'
        schema.exact_keys(item, ('expectation', 'interval'), path)
        if item['expectation'] not in expectations:
            schema.fail(f'{path}.expectation', 'not an expectation of that decision')
        interval = schema.array(item['interval'], f'{path}.interval', 2)
        low = schema.number(interval[0], f'{path}.interval[0]', 0, 1)
        high = schema.number(interval[1], f'{path}.interval[1]', 0, 1)
        schema.require(len(interval) == 2 and low <= high, f'{path}.interval', '[low, high] required')
    payload = {'shadow_trial': True, 'candidate': cand, 'decision': spec['decision'], 'verdict': spec['verdict'],
               'predictions': predictions, 'rationale': spec['rationale'], 'spec_sha256': canon.digest(spec)}
    return ledger.append(log_path, 'shadow', payload, at, kinds=KINDS)


def compare(log_path: str, ledger_path: str, at: str, min_history: int = MIN_HISTORY) -> dict:
    shadows = _log(log_path)
    real = ledger.read(ledger_path)
    decided = ledger.decisions(real)
    latest = {}
    for entry in ledger.reconciliations(real):
        latest[(entry['payload']['decision'], entry['payload']['expectation'])] = entry['payload']['outcome']
    by_candidate = {}
    for entry in shadows:
        payload = entry['payload']
        decision = decided.get(payload['decision'])
        if decision is None or decision['payload']['synthetic']:
            continue
        frozen = {e['id']: e for e in decision['payload']['artifact']['body']['snapshot']['expectations']}
        rows = by_candidate.setdefault(payload['candidate']['id'], [])
        for prediction in payload['predictions']:
            outcome = latest.get((payload['decision'], prediction['expectation']))
            if outcome not in ('CONFIRMED', 'REFUTED'):
                continue   # hidden until reconciled
            observed = 1 if outcome == 'CONFIRMED' else 0
            shadow_p = sum(prediction['interval']) / 2
            real_p = sum(frozen[prediction['expectation']]['probability']['interval']) / 2
            rows.append(((shadow_p - observed) ** 2, (real_p - observed) ** 2))
    candidates = []
    for cid, rows in sorted(by_candidate.items()):
        base = {'candidate': cid, 'compared_predictions': len(rows)}
        if len(rows) < min_history:
            candidates.append({**base, 'result': 'INSUFFICIENT_HISTORY', 'shadow_brier': None, 'real_brier': None,
                               'eligible_for_proposal': False})
            continue
        shadow_brier = sum(r[0] for r in rows) / len(rows)
        real_brier = sum(r[1] for r in rows) / len(rows)
        candidates.append({**base, 'result': 'MEASURED', 'shadow_brier': round(shadow_brier, 6),
                           'real_brier': round(real_brier, 6), 'eligible_for_proposal': shadow_brier < real_brier})
    return {'kind': 'shadow_trial', 'at': ante_time.iso(ante_time.parse(at, 'at')), 'min_history': min_history,
            'candidates': candidates,
            'note': 'Eligibility only permits an ante develop proposal; a shadow candidate is never adopted here.'}


def status(log_path: str) -> dict:
    entries = _log(log_path)
    counts = {}
    for entry in entries:
        counts[entry['payload']['candidate']['id']] = counts.get(entry['payload']['candidate']['id'], 0) + 1
    return {'kind': 'shadow_trial_status', 'recommendations': counts,
            'note': 'Recommendations stay hidden until their decisions are reconciled (ante stub compare).'}


def add_parser(sub) -> None:
    stub = sub.add_parser('stub', help='shadow trials of candidate profiles, runbooks or routing; no effect')
    ssub = stub.add_subparsers(dest='stub_command', required=True)
    rec = ssub.add_parser('record')
    rec.add_argument('spec')
    cmp_ = ssub.add_parser('compare')
    cmp_.add_argument('--min-history', type=int, default=MIN_HISTORY)
    st = ssub.add_parser('status')
    for p in (rec, cmp_, st):
        p.add_argument('--log', required=True)
    for p in (rec, cmp_):
        p.add_argument('--ledger', required=True)
        p.add_argument('--at', required=True)
    stub.set_defaults(handler=main)


def main(args) -> int:
    try:
        if args.stub_command == 'record':
            entry = record(args.spec, args.log, args.ledger, args.at)
            print(f'shadow recommendation recorded (hidden until reconciled): seq {entry["seq"]}')
            return 0
        result = compare(args.log, args.ledger, args.at, args.min_history) if args.stub_command == 'compare' \
            else status(args.log)
    except ledger.LedgerError as exc:
        print(f'LINEAGE {exc}', file=sys.stderr)
        return 3
    except (StubError, io.InputError, schema.SchemaError, ante_time.TimeError) as exc:
        print(f'INVALID {exc}', file=sys.stderr)
        return 2
    sys.stdout.write(json.dumps(result, indent=2, sort_keys=True) + '\n')
    return 0
