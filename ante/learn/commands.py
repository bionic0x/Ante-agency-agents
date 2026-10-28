"""``ante learn``: record decisions, reconcile outcomes, calibrate, propose patterns.

Learning here means updating versioned data — calibration, candidate patterns —
from dated predictions reconciled with what happened. It does not retrain models
or rewrite doctrine, and nothing it produces changes routing, thresholds or
profiles by itself: those changes go through ``ante develop`` and a human merge.

    ante learn record DECIDE.json --ledger L --at T [--runbook R] [--agent A] [--synthetic]
    ante learn reconcile OBSERVATIONS.json --ledger L --at T
    ante learn calibrate --ledger L --at T [--min-sample N] [--out FILE]
    ante learn patterns  --ledger L --at T [--min-group N] [--out FILE]
    ante learn verify    --ledger L

When too few decisions have been reconciled, the honest output is that nothing
has been learned yet: ``INSUFFICIENT_SAMPLE``, not a number.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from ante import registry
from ante.core import canon, io, schema
from ante.core import time as ante_time
from ante.learn import apophenia, ledger
from ante.strategy import artifact

OUTCOMES = ('CONFIRMED', 'REFUTED', 'INCONCLUSIVE', 'NOT_YET_OBSERVABLE')
DECISIVE = ('CONFIRMED', 'REFUTED')
BINS = ((0.0, 0.2), (0.2, 0.4), (0.4, 0.6), (0.6, 0.8), (0.8, 1.0001))
SCHEMA_VERSION = 1


class LearnError(ValueError):
    pass


def _at(value: str) -> str:
    return ante_time.iso(ante_time.parse(value, 'at'))


def record(decide_path: str, ledger_path: str, at: str, runbook: str | None, agent: str | None,
           synthetic: bool) -> dict:
    art = artifact.load_parent(decide_path)
    if art['command'] != 'decide':
        raise LearnError('only decide artefacts are recorded as decisions')
    if runbook is not None and runbook not in registry.runbooks():
        raise LearnError(f'unknown runbook {runbook}')
    entries = ledger.read(ledger_path)
    if art['artifact_sha256'] in ledger.decisions(entries):
        raise LearnError('this decision is already in the ledger')
    if ante_time.parse(at, 'at') < ante_time.parse(art['at'], 'decision.at'):
        raise LearnError('a decision cannot be recorded before it was taken')
    payload = {'artifact': art, 'runbook': runbook, 'agent': agent, 'synthetic': synthetic}
    return ledger.append(ledger_path, 'decision', payload, at)


def reconcile(doc_path: str, ledger_path: str, at: str) -> list[dict]:
    doc = io.load_document(doc_path)
    schema.exact_keys(doc, ('observations',), 'input', ('at',))
    entries = ledger.read(ledger_path)
    decided = ledger.decisions(entries)
    now = ante_time.parse(at, 'at')
    payloads = []
    for index, obs in enumerate(schema.array(doc['observations'], 'observations', 1)):
        path = f'observations[{index}]'
        schema.exact_keys(obs, ('decision', 'expectation', 'outcome', 'observed', 'source', 'observed_at'), path)
        entry = decided.get(obs['decision'])
        if entry is None:
            schema.fail(f'{path}.decision', 'no decision with this artefact hash in the ledger')
        expectations = {e['id']: e for e in entry['payload']['artifact']['body']['expectations']}
        if obs['expectation'] not in expectations:
            schema.fail(f'{path}.expectation', 'not an expectation of that decision')
        outcome = schema.enum(obs['outcome'], OUTCOMES, f'{path}.outcome')
        schema.text(obs['observed'], f'{path}.observed')
        source = schema.exact_keys(obs['source'], ('ref', 'origin'), f'{path}.source')
        schema.text(source['ref'], f'{path}.source.ref')
        schema.enum(source['origin'], ('external', 'owner', 'system'), f'{path}.source.origin')
        observed_at = ante_time.parse(obs['observed_at'], f'{path}.observed_at')
        decided_at = ante_time.parse(entry['payload']['artifact']['at'], 'decision.at')
        horizon = ante_time.parse(expectations[obs['expectation']]['horizon'], 'horizon')
        schema.require(observed_at <= now, f'{path}.observed_at', 'dated after the reconciliation time')
        schema.require(observed_at >= decided_at, f'{path}.observed_at',
                       'an observation before the decision is not its outcome')
        if outcome in DECISIVE and source['origin'] == 'system':
            schema.fail(f'{path}.source.origin', 'a system-produced source cannot confirm or refute (invariant 7)')
        if outcome == 'NOT_YET_OBSERVABLE' and now >= horizon:
            schema.fail(f'{path}.outcome', 'the horizon has passed; record what was observed or INCONCLUSIVE')
        payloads.append({'decision': obs['decision'], 'expectation': obs['expectation'], 'outcome': outcome,
                         'observed': obs['observed'], 'source': source,
                         'observed_at': ante_time.iso(observed_at),
                         'decision_entry': entry['entry_hash']})
    return [ledger.append(ledger_path, 'reconciliation', payload, at) for payload in payloads]


def _latest_outcomes(entries: list[dict]) -> dict[tuple[str, str], dict]:
    latest = {}
    for entry in ledger.reconciliations(entries):
        latest[(entry['payload']['decision'], entry['payload']['expectation'])] = entry
    return latest


def _midpoint(expectation: dict) -> float:
    low, high = expectation['probability']['interval']
    return (low + high) / 2


def calibrate(ledger_path: str, at: str, min_sample: int) -> dict:
    if min_sample < 1:
        raise LearnError('the minimum sample must be at least 1')
    entries = ledger.read(ledger_path)
    decided = ledger.decisions(entries)
    latest = _latest_outcomes(entries)
    excluded = {'synthetic': 0, 'not_decisive': 0, 'unreconciled': 0}
    rows = []
    for sha, entry in sorted(decided.items()):
        payload = entry['payload']
        for expectation in payload['artifact']['body']['expectations']:
            outcome = latest.get((sha, expectation['id']))
            if payload['synthetic']:
                excluded['synthetic'] += 1
                continue
            if outcome is None:
                excluded['unreconciled'] += 1
                continue
            if outcome['payload']['outcome'] not in DECISIVE:
                excluded['not_decisive'] += 1
                continue
            rows.append({'runbook': payload['runbook'] or 'unlabelled', 'agent': payload['agent'] or 'unlabelled',
                         'kind': expectation.get('kind', 'unlabelled'), 'p': _midpoint(expectation),
                         'o': 1 if outcome['payload']['outcome'] == 'CONFIRMED' else 0})
    groups = []
    for dimension in ('all', 'runbook', 'agent', 'kind'):
        keys = sorted({'all'} if dimension == 'all' else {r[dimension] for r in rows})
        for key in keys:
            members = rows if dimension == 'all' else [r for r in rows if r[dimension] == key]
            groups.append(_calibration_group(dimension, key, members, min_sample))
    return {'schema_version': SCHEMA_VERSION, 'kind': 'calibration', 'at': _at(at),
            'ledger_head': entries[-1]['entry_hash'] if entries else ledger.GENESIS,
            'min_sample': min_sample, 'decisive_predictions': len(rows), 'excluded': excluded, 'groups': groups,
            'method': 'Brier score on the midpoint of each declared interval; CONFIRMED = 1, REFUTED = 0.'}


def _calibration_group(dimension: str, key: str, rows: list[dict], min_sample: int) -> dict:
    base = {'dimension': dimension, 'key': key, 'n': len(rows)}
    if len(rows) < min_sample:
        return {**base, 'result': 'INSUFFICIENT_SAMPLE', 'brier': None,
                'reason': f'{len(rows)} decisive predictions; {min_sample} declared as the minimum'}
    brier = sum((r['p'] - r['o']) ** 2 for r in rows) / len(rows)
    curve = []
    for low, high in BINS:
        members = [r for r in rows if low <= r['p'] < high]
        curve.append({'bin': [low, min(high, 1.0)], 'n': len(members),
                      'mean_forecast': round(sum(r['p'] for r in members) / len(members), 6) if members else None,
                      'observed_rate': round(sum(r['o'] for r in members) / len(members), 6) if members else None})
    return {**base, 'result': 'MEASURED', 'brier': round(brier, 6), 'reliability': curve}


def patterns(ledger_path: str, at: str, min_group: int, seed: int = 20261028) -> dict:
    entries = ledger.read(ledger_path)
    decided = ledger.decisions(entries)
    latest = _latest_outcomes(entries)
    samples, genealogy = [], {}
    excluded = {'synthetic': 0, 'no_decisive_outcome': 0, 'self_sourced_only': 0}
    for sha, entry in sorted(decided.items()):
        payload = entry['payload']
        if payload['synthetic']:
            excluded['synthetic'] += 1
            continue
        outcomes = [latest[(sha, e['id'])] for e in payload['artifact']['body']['expectations']
                    if (sha, e['id']) in latest and latest[(sha, e['id'])]['payload']['outcome'] in DECISIVE]
        if not outcomes:
            excluded['no_decisive_outcome'] += 1
            continue
        independent = [o for o in outcomes if o['payload']['source']['origin'] != 'system']
        if not independent:
            excluded['self_sourced_only'] += 1
            continue
        body = payload['artifact']['body']
        features = {f'verdict:{body["verdict"]}', f'review:{body["review_independence"]}'}
        features |= {f'pathology:{p}' for p in body['detected_pathologies']}
        if payload['runbook']:
            features.add(f'runbook:{payload["runbook"]}')
        refuted = 1 if any(o['payload']['outcome'] == 'REFUTED' for o in independent) else 0
        samples.append((features, refuted))
        for feature in features:
            genealogy.setdefault(feature, []).append(
                {'decision_entry': entry['entry_hash'], 'outcome_entries': [o['entry_hash'] for o in independent]})
    all_features = sorted({f for present, _ in samples for f in present})
    verdicts, tested = apophenia.guard(samples, all_features, seed=seed, min_group=min_group)
    proposals = [{**v.as_dict(), 'kind': 'refutation_rate_difference', 'sources': genealogy[v.feature],
                  'status': 'PROPOSAL', 'note': 'Correlation in the ledger; a human decides whether it means anything.'}
                 for v in verdicts if v.passes]
    return {'schema_version': SCHEMA_VERSION, 'kind': 'patterns', 'at': _at(at),
            'ledger_head': entries[-1]['entry_hash'] if entries else ledger.GENESIS,
            'decisions_used': len(samples), 'excluded': excluded, 'features_seen': len(all_features),
            'features_tested': tested, 'seed': seed, 'min_group': min_group,
            'tested': [v.as_dict() for v in verdicts], 'proposals': proposals,
            'learned_anything': bool(proposals)}


def _emit(value: dict, out: str | None) -> None:
    text = json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + '\n'
    if out:
        Path(out).parent.mkdir(parents=True, exist_ok=True)
        Path(out).write_text(text, encoding='utf-8')
        print(f'{value["kind"]} -> {out} ({canon.sha256_hex(text)})')
    else:
        sys.stdout.write(text)


def add_parser(sub) -> None:
    learn = sub.add_parser('learn', help='decision ledger, reconciliation, calibration, patterns')
    lsub = learn.add_subparsers(dest='learn_command', required=True)
    rec = lsub.add_parser('record', help='append a decide artefact to the ledger')
    rec.add_argument('decide')
    rec.add_argument('--runbook')
    rec.add_argument('--agent')
    rec.add_argument('--synthetic', action='store_true', help='fixture data; excluded from calibration and patterns')
    rcn = lsub.add_parser('reconcile', help='record observed outcomes of dated expectations')
    rcn.add_argument('observations')
    cal = lsub.add_parser('calibrate', help='Brier score and reliability, or INSUFFICIENT_SAMPLE')
    cal.add_argument('--min-sample', type=int, default=30)
    cal.add_argument('--out')
    pat = lsub.add_parser('patterns', help='candidate patterns that survive the apophenia guard')
    pat.add_argument('--min-group', type=int, default=3)
    pat.add_argument('--out')
    ver = lsub.add_parser('verify', help='verify the ledger chain')
    for p in (rec, rcn, cal, pat, ver):
        p.add_argument('--ledger', required=True)
    for p in (rec, rcn, cal, pat):
        p.add_argument('--at', required=True)
    learn.set_defaults(handler=main)


def main(args) -> int:
    try:
        if args.learn_command == 'record':
            entry = record(args.decide, args.ledger, args.at, args.runbook, args.agent, args.synthetic)
            print(f'decision recorded: seq {entry["seq"]} {entry["entry_hash"]}')
        elif args.learn_command == 'reconcile':
            added = reconcile(args.observations, args.ledger, args.at)
            print(f'{len(added)} reconciliation(s) recorded; head {added[-1]["entry_hash"]}')
        elif args.learn_command == 'calibrate':
            _emit(calibrate(args.ledger, args.at, args.min_sample), args.out)
        elif args.learn_command == 'patterns':
            _emit(patterns(args.ledger, args.at, args.min_group), args.out)
        else:
            entries = ledger.read(args.ledger)
            print(f'ledger intact: {len(entries)} entries, head {entries[-1]["entry_hash"] if entries else ledger.GENESIS}')
    except (artifact.LineageError, ledger.LedgerError) as exc:
        print(f'LINEAGE {exc}', file=sys.stderr)
        return 3
    except (LearnError, io.InputError, schema.SchemaError, ante_time.TimeError) as exc:
        print(f'INVALID {exc}', file=sys.stderr)
        return 2
    return 0
