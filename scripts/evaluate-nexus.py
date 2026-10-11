#!/usr/bin/env python3
"""evaluate-nexus.py — join recorded host trials with blind reviewer judgments.

Three variants answer the same case under the same model, inputs and budget:
`single_agent`, `fixed_team`, `nexus_instance`. This tool reports what was
measured. It never synthesizes a result, never ranks the variants, and never
reduces the metrics to one number.

Why two files. Assignment knowledge can bias artifact review. So execution and judgment are recorded separately:

  trials     one row per run: variant, model, inputs, budget, and the costs the
             runner observed (money, tokens, wall time) plus counters the engine
             must instrument consistently across all variants.
  judgments  one row per SUBMISSION: the reviewer's counts, keyed only by an
             opaque submission id. A judgment that names a variant, a case, or a
             reviewer who also ran the trials is rejected.

The join happens after review. Separate files reduce direct label leakage but do
not prove blinding or authenticate reviewer identities, costs or evidence.

Why no composite. The metrics answer different questions and trade against each
other. A fatal defect is not repaid by a lower token count, and a run that is
cheap because it stopped early is not thereby better. Any input carrying a
`score`, `rank` or `overall` field is rejected: ranking is the reader's job,
performed against a stated purpose this tool does not have.

Usage:
  evaluate-nexus.py --runs host-trials.json --judgments host-judgments.json
  evaluate-nexus.py --runs ... --judgments ... --require-paired
"""
import argparse, datetime as dt, json, math, re, statistics, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VARIANTS = {'single_agent', 'fixed_team', 'nexus_instance'}
SUBMISSION_ID = re.compile(r'^[0-9a-f]{16}$')

# Supplied runner counters; instrumentation and accounting need independent verification.
RUN_COUNTERS = ('cost_usd', 'tokens_total', 'wall_time_seconds', 'invalid_decisions', 'rework_cycles')
# Counted by a blind reviewer against the case's expected behavior.
JUDGED_COUNTERS = ('factual_errors', 'fatal_defects', 'constraint_violations')
# Reported as a fraction so a denominator of zero stays visible instead of
# becoming a flattering 100%.
JUDGED_FRACTIONS = ('evidence_coverage',)

TRIAL_FIELDS = {'submission_id', 'case_id', 'trial_id', 'variant', 'model_version', 'host_version',
                'evidence_ref', 'operator', 'inputs_hash', 'budget_policy_ref', 'started_at'} | set(RUN_COUNTERS)
JUDGMENT_FIELDS = {'submission_id', 'reviewer', 'judged_at', 'evidence_ref'} | set(JUDGED_COUNTERS) | set(JUDGED_FRACTIONS)
BANNED = {'score', 'rank', 'overall', 'winner', 'composite', 'verdict'}


def _reject_composite(row, where):
    banned = BANNED & set(row)
    if banned:
        raise ValueError(f'{where} carries ranking field(s) {sorted(banned)}; this protocol '
                         'reports metrics separately and does not rank variants')


def _count(value, name, where):
    if type(value) is not int or value < 0:
        raise ValueError(f'{where}: {name} must be a non-negative integer count')
    return value


def _number(value, name, where):
    if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
        raise ValueError(f'{where}: {name} must be a non-negative finite number')
    return value


def _fraction(value, name, where):
    if not isinstance(value, dict) or set(value) != {'covered', 'required'}:
        raise ValueError(f'{where}: {name} must be {{"covered": n, "required": m}}')
    covered = _count(value['covered'], f'{name}.covered', where)
    required = _count(value['required'], f'{name}.required', where)
    if covered > required:
        raise ValueError(f'{where}: {name}.covered exceeds {name}.required')
    return covered, required


def _rows(rows, name):
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        raise ValueError(f'{name} must be a list of objects')


def _timestamp(value, name):
    try:
        result = dt.datetime.fromisoformat(value.replace('Z', '+00:00'))
    except (ValueError, AttributeError):
        raise ValueError(f'{name} must be an ISO-8601 timestamp') from None
    if result.tzinfo is None:
        raise ValueError(f'{name} must include timezone')
    return result


def load_cases(cases):
    if not isinstance(cases, dict) or not isinstance(cases.get('cases'), list) or not cases['cases']:
        raise ValueError('cases must contain a non-empty cases list')
    result = {}
    for case in cases['cases']:
        if not isinstance(case, dict) or any(not isinstance(case.get(k), str) or not case[k].strip()
                                           for k in ('id', 'scenario', 'expected_behavior')):
            raise ValueError('each case needs id, scenario and expected_behavior')
        if case['id'] in result:
            raise ValueError('duplicate case id')
        result[case['id']] = case
    return result


def load_trials(rows):
    _rows(rows, 'trials')
    seen, trials = set(), {}
    for index, row in enumerate(rows):
        where = f'trials[{index}]'
        _reject_composite(row, where)
        unknown = set(row) - TRIAL_FIELDS
        if unknown:
            raise ValueError(f'{where}: unknown field(s) {sorted(unknown)}')
        missing = TRIAL_FIELDS - set(row)
        if missing:
            raise ValueError(f'{where}: missing field(s) {sorted(missing)}')
        if not isinstance(row['variant'], str) or row['variant'] not in VARIANTS:
            raise ValueError(f"{where}: unknown variant {row['variant']!r}")
        if not isinstance(row['submission_id'], str) or not SUBMISSION_ID.fullmatch(row['submission_id']):
            raise ValueError(f'{where}: submission_id must be 16 hex characters and carry no '
                             'information about the variant that produced it')
        for field in ('case_id', 'trial_id', 'model_version', 'host_version', 'evidence_ref',
                      'operator', 'inputs_hash', 'budget_policy_ref', 'started_at'):
            if not isinstance(row[field], str) or not row[field].strip():
                raise ValueError(f'{where}: missing trial metadata: {field}')
        _timestamp(row['started_at'], f'{where}.started_at')
        key = (row['case_id'], row['trial_id'], row['variant'])
        if key in seen:
            raise ValueError(f'{where}: duplicate case/trial/variant {key}')
        seen.add(key)
        if row['submission_id'] in trials:
            raise ValueError(f"{where}: duplicate submission_id {row['submission_id']}")
        for field in ('cost_usd', 'wall_time_seconds'):
            _number(row[field], field, where)
        for field in ('tokens_total', 'invalid_decisions', 'rework_cycles'):
            _count(row[field], field, where)
        trials[row['submission_id']] = row
    return trials


def load_judgments(rows, trials):
    _rows(rows, 'judgments')
    operators = {r['operator'].strip().casefold() for r in trials.values()}
    judgments = {}
    for index, row in enumerate(rows):
        where = f'judgments[{index}]'
        _reject_composite(row, where)
        leaked = {'variant', 'case_id', 'trial_id', 'model_version'} & set(row)
        if leaked:
            raise ValueError(f'{where} carries {sorted(leaked)}; a judgment that names the variant '
                             'or the case it came from was not made blind')
        unknown = set(row) - JUDGMENT_FIELDS
        if unknown:
            raise ValueError(f'{where}: unknown field(s) {sorted(unknown)}')
        missing = JUDGMENT_FIELDS - set(row)
        if missing:
            raise ValueError(f'{where}: missing field(s) {sorted(missing)}')
        submission = row['submission_id']
        if not isinstance(submission, str) or not SUBMISSION_ID.fullmatch(submission):
            raise ValueError(f'{where}: submission_id must be 16 hex characters')
        if submission in judgments:
            raise ValueError(f'{where}: duplicate judgment for submission {submission}')
        if submission not in trials:
            raise ValueError(f'{where}: judgment for unknown submission {submission}')
        for field in ('reviewer', 'judged_at', 'evidence_ref'):
            if not isinstance(row[field], str) or not row[field].strip():
                raise ValueError(f'{where}: missing judgment metadata: {field}')
        if _timestamp(row['judged_at'], f'{where}.judged_at') < _timestamp(trials[submission]['started_at'], 'started_at'):
            raise ValueError(f'{where}: judgment predates trial')
        if row['reviewer'].strip().casefold() in operators:
            raise ValueError(f"{where}: reviewer {row['reviewer']!r} also ran this trial; a run "
                             'cannot be judged by the person who produced it')
        for field in JUDGED_COUNTERS:
            _count(row[field], field, where)
        for field in JUDGED_FRACTIONS:
            _fraction(row[field], field, where)
        judgments[submission] = row
    return judgments


def evaluate(cases, rows, judgment_rows=None):
    case_ids = set(load_cases(cases))
    trials = load_trials(rows)
    judgments = load_judgments([] if judgment_rows is None else judgment_rows, trials)
    if not rows:
        return {'status': 'NOT_MEASURED',
                'reason': 'No recorded host trials supplied. An empty trial set is not a '
                          'neutral result; nothing about the variants has been measured.',
                'comparisons': [], 'missing_cases': sorted(case_ids)}

    for submission, row in trials.items():
        if row['case_id'] not in case_ids:
            raise ValueError(f"trial {submission}: unknown case {row['case_id']!r}")

    groups = {}
    for row in trials.values():
        groups.setdefault((row['case_id'], row['trial_id']), []).append(row)
    complete, incomplete = {}, {}
    for key, group in groups.items():
        present = {r['variant'] for r in group}
        if present != VARIANTS:
            incomplete[key] = sorted(VARIANTS - present)
            continue
        for field in ('inputs_hash', 'budget_policy_ref', 'model_version', 'host_version'):
            if len({r[field] for r in group}) != 1:
                raise ValueError(f'paired trial {key} differs in {field}; the variants did not '
                                 'answer the same question under the same limits')
        complete[key] = group

    by_variant = {v: [] for v in VARIANTS}
    judged_complete = {k: group for k, group in complete.items()
                       if all(row['submission_id'] in judgments for row in group)}
    execution_report = []
    for variant in sorted(VARIANTS):
        samples = [row for group in complete.values() for row in group if row['variant'] == variant]
        entry = {'variant': variant, 'paired_trials': len(samples)}
        for field in RUN_COUNTERS:
            values = [row[field] for row in samples]
            if values:
                entry[field] = {'median': statistics.median(values), 'min': min(values),
                                'max': max(values), 'total': sum(values)}
        execution_report.append(entry)
    for group in judged_complete.values():
        for row in group:
            by_variant[row['variant']].append(row)

    report = []
    unjudged = sorted(set(trials) - set(judgments))
    for variant, samples in sorted(by_variant.items()):
        entry = {'variant': variant, 'paired_trials': len(samples), 'judged_trials': len(samples)}
        if samples:
            for field in RUN_COUNTERS:
                values = [r[field] for r in samples]
                entry[field] = {'median': statistics.median(values),
                                'min': min(values), 'max': max(values), 'total': sum(values)}
            judged = [judgments[r['submission_id']] for r in samples if r['submission_id'] in judgments]
            entry['judged_trials'] = len(judged)
            if judged:
                for field in JUDGED_COUNTERS:
                    values = [j[field] for j in judged]
                    entry[field] = {'median': statistics.median(values),
                                    'total': sum(values), 'trials_with_any': sum(1 for v in values if v)}
                for field in JUDGED_FRACTIONS:
                    covered = sum(j[field]['covered'] for j in judged)
                    required = sum(j[field]['required'] for j in judged)
                    entry[field] = {'covered': covered, 'required': required,
                                    'ratio': (covered / required) if required else None}
        report.append(entry)

    covered_cases = sorted({k[0] for k in complete})
    result = {
        'status': 'RECORDED_TRIALS' if complete else 'NOT_MEASURED',
        'comparisons': report,
        'execution_comparisons': execution_report,
        'judged_paired_trials': len(judged_complete),
        'comparison_pairs': [{'case_id': k[0], 'trial_id': k[1]} for k in sorted(judged_complete)],
        'fatal_observations': [{'submission_id': sid, 'variant': trials[sid]['variant'],
                                'case_id': trials[sid]['case_id'], 'trial_id': trials[sid]['trial_id'],
                                'fatal_defects': j['fatal_defects']}
                               for sid, j in sorted(judgments.items()) if j['fatal_defects']],
        'paired_trials': len(complete),
        'covered_cases': covered_cases,
        'missing_cases': sorted(case_ids - set(covered_cases)),
        'incomplete_pairs': [{'case_id': k[0], 'trial_id': k[1], 'missing_variants': v}
                             for k, v in sorted(incomplete.items())],
        'unjudged_submissions': sorted(unjudged),
        'limitations': [
            'Descriptive observations. No causal claim, no statistical test, no ranking.',
            'Fatal defects are reported on their own and are never offset by any other metric.',
            'A variant that is cheaper or faster may be so because it did less; read the '
            'cost metrics only together with the judged ones.',
            'Primary comparisons use the same fully judged three-variant pairs for all nine metrics. '
            'Execution-only comparisons use all complete execution pairs and do not imply quality.',
            'Fatal observations include judgments excluded from matched comparisons.',
            'The protocol does not authenticate blinding, preregistration or actual budget enforcement.',
            'Reviewer judgments and evidence references require independent verification.',
        ],
    }
    if incomplete:
        result['limitations'].insert(0, 'Incomplete pairs are excluded from every aggregate; '
                                        'a variant that failed to produce an artifact would '
                                        'otherwise disappear from the comparison it lost.')
    return result


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--cases', default=str(ROOT / 'examples/nexus/evaluation-cases.json'))
    ap.add_argument('--runs', required=True)
    ap.add_argument('--judgments')
    ap.add_argument('--require-paired', action='store_true',
                    help='require at least one fully judged triple, no incomplete pairs and no unjudged submissions')
    args = ap.parse_args()
    try:
        cases = json.loads(Path(args.cases).read_text(encoding='utf-8'))
        runs = json.loads(Path(args.runs).read_text(encoding='utf-8'))
        judgments = json.loads(Path(args.judgments).read_text(encoding='utf-8')) if args.judgments else []
        result = evaluate(cases, runs, judgments)
        print(json.dumps(result, indent=2))
        if args.require_paired and (not result.get('judged_paired_trials')
                                    or result.get('incomplete_pairs')
                                    or result.get('unjudged_submissions')):
            return 1
        return 0
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f'ERROR {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
