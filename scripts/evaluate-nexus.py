#!/usr/bin/env python3
"""Compare explicitly recorded host trials; never synthesize model results.

A complete comparison contains all three variants for each case/trial pair.
Judgments are supplied reviewer observations, not an institutional certificate.
"""
import argparse
import json
import math
from pathlib import Path
import statistics
import sys

VARIANTS = {'single_agent', 'fixed_team', 'nexus_instance'}
METRICS = ('correct_reaction', 'uncertainty_preserved', 'traceable', 'fatal_violation')


def evaluate(cases, rows):
    ids = {c['id'] for c in cases['cases']}
    seen, groups, by = set(), {}, {v: [] for v in VARIANTS}
    if not rows:
        return {'status': 'NOT_MEASURED', 'reason': 'No recorded host trials supplied', 'comparisons': []}
    for row in rows:
        key = (row['case_id'], row['trial_id'], row['variant'])
        if key in seen or row['case_id'] not in ids or row['variant'] not in VARIANTS:
            raise ValueError('duplicate or unknown case/trial/variant')
        seen.add(key)
        for field in ('model_version', 'host_version', 'evidence_ref', 'reviewer', 'inputs_hash', 'budget_policy_ref', 'started_at'):
            if not isinstance(row.get(field), str) or not row[field].strip():
                raise ValueError(f'missing trial metadata: {field}')
        for field in ('cost', 'latency_seconds'):
            value = row[field]
            if type(value) not in (int,float) or not math.isfinite(value) or value < 0:
                raise ValueError('invalid numeric observation')
        if any(type(row.get(m)) is not bool for m in METRICS):
            raise ValueError('reviewer rubric fields must be explicit booleans')
        groups.setdefault(key[:2], []).append(row)
        by[row['variant']].append(row)
    for group in groups.values():
        if {r['variant'] for r in group} != VARIANTS:
            raise ValueError('each case/trial requires all three variants')
        for field in ('inputs_hash', 'budget_policy_ref'):
            if len({r[field] for r in group}) != 1:
                raise ValueError(f'paired trial differs in {field}')
    report = []
    for variant, samples in sorted(by.items()):
        report.append({'variant':variant, 'trials':len(samples),
                       **{m:sum(r[m] for r in samples) for m in METRICS},
                       'median_cost':statistics.median(r['cost'] for r in samples),
                       'median_latency_seconds':statistics.median(r['latency_seconds'] for r in samples)})
    return {'status':'RECORDED_TRIALS', 'comparisons':report,
            'paired_trials':len(groups), 'covered_cases':sorted({k[0] for k in groups}),
            'missing_cases':sorted(ids-{k[0] for k in groups}),
            'limitations':['Descriptive observations; no causal or statistical superiority established.',
                           'Supplied reviewer judgments and evidence require independent verification.',
                           'Fatal violations are reported separately, never compensated by other metrics.']}


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--cases',default=str(Path(__file__).resolve().parents[1]/'examples/nexus/evaluation-cases.json'))
    ap.add_argument('--runs',required=True)
    args=ap.parse_args()
    try:
        print(json.dumps(evaluate(json.loads(Path(args.cases).read_text()),json.loads(Path(args.runs).read_text())),indent=2))
        return 0
    except (OSError,ValueError,KeyError,TypeError) as exc:
        print(f'ERROR {exc}',file=sys.stderr);return 1

if __name__=='__main__':sys.exit(main())
