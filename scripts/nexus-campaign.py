#!/usr/bin/env python3
"""nexus-campaign.py — the Phase 1 exit of NEXUS Overdrive, decided before it is run.

strategy/NEXUS-OVERDRIVE.md fixes the exit and the kill rule of Phase 1. This tool
fixes them in code, so the decision cannot be redrafted after the results are seen:

  exit    >= 6 frozen held-out packs, none written or frozen by an improver;
          all three variants, >= 2 trials each per pack, one model, one budget
          policy, live host only, every submission blind-judged
  kill    if nexus_instance does not have fewer fatal defects in total than
          fixed_team on those packs, Phase 2 does not speed up the control plane:
          REDIRECT to improving fixed teams and profiles

    nexus-campaign.py plan   --held-out ROOT --improver NAME --model ID --policy ID
                             [--policies FILE] [--trials FILE] --operator NAME --out DIR
    nexus-campaign.py status --held-out ROOT --improver NAME --trials FILE [--judgments FILE]
    nexus-campaign.py throughput --held-out ROOT --improver NAME \\
                             --baseline-trials F --baseline-judgments F \\
                             --candidate-trials F --candidate-judgments F

Phase 2 (throughput) runs the same campaign twice: the baseline with the
sequential schedule, the candidate with `plan --schedule parallel`. `throughput`
returns ADOPT_PARALLEL only if both campaigns are complete on the same packs,
model and budget policy, the Phase 1 rule did not redirect, the median
nexus_instance wall time fell, and its fatal defects and constraint violations
did not rise. Otherwise KEEP_SEQUENTIAL, or INCOMPLETE. An increase in fatal
defects must be rerun once; if it survives, Phase 2 is killed (charter).

`plan` lists the runs still missing, the exact commands to execute them, and the
spend ceiling those commands are allowed. It spends nothing. `status` reports
INCOMPLETE (with every missing item), PROCEED_TO_PHASE_2 or REDIRECT.

Limits: six packs do not support a claim of superiority; the kill rule is a
pre-registered decision convention, not a significance test. Labels, counters and
reviewer independence are taken from the records, not authenticated.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import shlex
import sys

ROOT = Path(__file__).resolve().parents[1]
MIN_PACKS = 6
TRIALS_PER_VARIANT = 2
VARIANTS = ('single_agent', 'fixed_team', 'nexus_instance')
FAKE_HOST = 'fake-executor'


def _module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


EVALUATION = _module('evaluation_for_campaign', ROOT / 'scripts/evaluate-nexus.py')
CASEPACK = _module('casepack_for_campaign', ROOT / 'scripts/nexus-casepack.py')
TRIAL = _module('trial_for_campaign', ROOT / 'scripts/nexus-trial.py')


class CampaignError(ValueError):
    pass


def held_out_packs(root, improvers):
    """Frozen held-out packs, and the reasons any of them cannot count."""
    if not improvers:
        raise CampaignError('name at least one improver; independence cannot be checked without one')
    # A published pack cannot be an unseen test. This is a *location guard*, not
    # proof that an external copy was secret or that the reviewer is independent.
    # Resolve symlinks before checking so an alias into this checkout cannot pass.
    pack_root = Path(root).resolve()
    checkout = ROOT.resolve()
    if pack_root == checkout or checkout in pack_root.parents:
        return {}, ['held-out packs under the public repository checkout are exposed; '
                    'use a separate evaluator-controlled, access-restricted corpus '
                    '(published sample packs cannot establish a blind result)']
    packs, problems = {}, []
    for pack_json in sorted(Path(root).glob('*/pack.json')):
        try:
            pack = CASEPACK.verify(pack_json.parent)
        except CASEPACK.PackError as exc:
            problems.append(f'{pack_json.parent.name}: {exc}'); continue
        if pack['split'] != 'held_out':
            continue
        written = {pack['author'], pack['frozen']['frozen_by']} & set(improvers)
        if written:
            problems.append(f"{pack['id']}: written or frozen by improver {sorted(written)}; it cannot count")
            continue
        packs[pack['frozen']['inputs_hash']] = {'id': pack['id'], 'dir': pack_json.parent,
                                               'case_id': pack['case_ref'], 'author': pack['author']}
    return packs, problems


def trial_name(pack_id, n):
    """Trials pair on (case_id, trial_id); two packs may share a case, so the id carries the pack."""
    return f'{pack_id}-t{n}'


def _rows(trials_path):
    path = Path(trials_path) if trials_path else None
    return json.loads(path.read_text(encoding='utf-8')) if path and path.exists() else []


def _done(rows, packs):
    """(pack hash, variant) -> trial ids recorded for it."""
    done = {}
    for row in rows:
        if row.get('inputs_hash') in packs:
            done.setdefault((row['inputs_hash'], row['variant']), set()).add(row['trial_id'])
    return done


def plan(root, improvers, model, policy_id, policies, trials_path, operator, out, schedule='sequential'):
    if schedule not in TRIAL.SCHEDULES:
        raise CampaignError(f'schedule must be one of {TRIAL.SCHEDULES}')
    packs, problems = held_out_packs(root, improvers)
    policy = TRIAL.load_policy(policies, policy_id)
    done = _done(_rows(trials_path), packs)
    trials_path = trials_path or str(Path(out) / 'trials.json')
    held = TRIAL.trials_schedule(trials_path)
    if held not in (None, schedule):
        raise CampaignError(f'{trials_path} holds {held} trials; a {schedule} campaign needs its own trials file')
    runs = []
    for digest, pack in sorted(packs.items(), key=lambda kv: kv[1]['id']):
        for variant in VARIANTS:
            for n in range(1, TRIALS_PER_VARIANT + 1):
                trial_id = trial_name(pack['id'], n)
                if trial_id in done.get((digest, variant), set()):
                    continue
                command = ['python3', 'scripts/nexus-trial.py', 'run', '--pack', str(pack['dir']), '--variant', variant,
                           '--trial-id', trial_id, '--model', model, '--policy', policy_id, '--policies', str(policies),
                           '--operator', operator, '--runs', str(Path(out) / 'runs'),
                           '--artifacts', str(Path(out) / 'artifacts'), '--trials', trials_path, '--executor', 'claude', '--schedule', schedule]
                runs.append({'pack': pack['id'], 'variant': variant, 'trial_id': trial_id, 'command': shlex.join(command)})
    return {
        'schedule': schedule,
        'held_out_packs': len(packs), 'packs_needed': max(0, MIN_PACKS - len(packs)), 'problems': problems,
        'runs_missing': len(runs), 'runs': runs,
        'spend_ceiling_usd': round(len(runs) * policy['max_cost_usd'], 2),
        'spend_note': ('budget is checked before each model call, so a run can exceed max_cost_usd by its last '
                       'call; NEXUS runs also pause for owner acceptance, which is not charged as wall time'),
        'spends_nothing': 'plan only prints commands; each run is started by an operator',
    }


def status(root, improvers, trials_path, judgments_path=None):
    packs, problems = held_out_packs(root, improvers)
    missing = list(problems)
    if len(packs) < MIN_PACKS:
        missing.append(f'{len(packs)} independent held-out packs; the exit needs {MIN_PACKS}')
    rows = [r for r in _rows(trials_path) if r.get('inputs_hash') in packs]
    judgments = _rows(judgments_path)
    if any(r['host_version'] == FAKE_HOST for r in rows):
        missing.append('fake-executor rows are not evidence; the exit needs live trials')
    for field in ('model_version', 'budget_policy_ref'):
        values = sorted({r[field] for r in rows})
        if len(values) > 1:
            missing.append(f'more than one {field} ({values}); the exit needs one')
    done = _done(rows, packs)
    for digest, pack in sorted(packs.items(), key=lambda kv: kv[1]['id']):
        for variant in VARIANTS:
            have = len(done.get((digest, variant), set()))
            if have < TRIALS_PER_VARIANT:
                missing.append(f"{pack['id']}: {variant} has {have} of {TRIALS_PER_VARIANT} trials")
    report = None
    if rows:
        cases = json.loads((ROOT / 'examples/nexus/evaluation-cases.json').read_text())
        report = EVALUATION.evaluate(cases, rows, judgments)
        if report.get('incomplete_pairs'):
            missing.append(f"{len(report['incomplete_pairs'])} trial groups lack a variant")
        if report.get('unjudged_submissions'):
            missing.append(f"{len(report['unjudged_submissions'])} submissions are not blind-judged")
    result = {'held_out_packs': len(packs), 'authors': sorted({p['author'] for p in packs.values()}),
              'trial_rows': len(rows), 'missing': missing}
    if missing:
        return {'decision': 'INCOMPLETE', **result}
    fatal = {e['variant']: e['fatal_defects']['total'] for e in report['comparisons']}
    result['fatal_defects_total'] = fatal
    if fatal['nexus_instance'] < fatal['fixed_team']:
        result['decision'] = 'PROCEED_TO_PHASE_2'
        result['reason'] = 'nexus_instance avoided more fatal defects than fixed_team on independent held-out packs'
    else:
        result['decision'] = 'REDIRECT'
        result['reason'] = ('nexus_instance did not avoid more fatal defects than fixed_team; do not speed up the '
                            'control plane. Improve fixed teams and profiles under the same gate.')
    result['limits'] = 'Pre-registered decision convention on few packs; not a significance test.'
    return result


def throughput(root, improvers, baseline, candidate):
    """Phase 2 exit: does the parallel schedule cut wall time without more fatal defects?"""
    missing, report = [], {}
    for label, (trials_path, judgments_path), schedule in (('baseline', baseline, 'sequential'),
                                                           ('candidate', candidate, 'parallel')):
        held = TRIAL.trials_schedule(trials_path)
        if held != schedule:
            missing.append(f'{label} trials must be a {schedule} campaign (found {held})')
        result = status(root, improvers, trials_path, judgments_path)
        missing.extend(f'{label}: {m}' for m in result.get('missing', []))
        report[label] = result
    if missing:
        return {'decision': 'INCOMPLETE', 'missing': missing}
    packs, _ = held_out_packs(root, improvers)
    cases = json.loads((ROOT / 'examples/nexus/evaluation-cases.json').read_text())
    entries, rows = {}, {}
    for label, (trials_path, judgments_path) in (('baseline', baseline), ('candidate', candidate)):
        rows[label] = [r for r in _rows(trials_path) if r.get('inputs_hash') in packs]
        evaluated = EVALUATION.evaluate(cases, rows[label], _rows(judgments_path))
        entries[label] = next(e for e in evaluated['comparisons'] if e['variant'] == 'nexus_instance')
    for field in ('model_version', 'budget_policy_ref'):
        b = {r[field] for r in rows['baseline']}; c = {r[field] for r in rows['candidate']}
        if b != c:
            return {'decision': 'INCOMPLETE', 'missing': [f'baseline and candidate differ in {field}']}
    measured = {label: {'median_wall_time_seconds': e['wall_time_seconds']['median'],
                        'fatal_defects_total': e['fatal_defects']['total'],
                        'constraint_violations_total': e['constraint_violations']['total']}
                for label, e in entries.items()}
    b, c = measured['baseline'], measured['candidate']
    reasons = []
    if report['baseline']['decision'] == 'REDIRECT':
        reasons.append('Phase 1 redirected: nexus_instance did not avoid more fatal defects than fixed_team, '
                       'so the control plane is not to be sped up')
    if not c['median_wall_time_seconds'] < b['median_wall_time_seconds']:
        reasons.append('median nexus_instance wall time did not fall')
    if c['fatal_defects_total'] > b['fatal_defects_total']:
        reasons.append('fatal defects rose; rerun the candidate campaign once, and if the increase survives, '
                       'Phase 2 is killed')
    if c['constraint_violations_total'] > b['constraint_violations_total']:
        reasons.append('constraint violations rose')
    return {'decision': 'KEEP_SEQUENTIAL' if reasons else 'ADOPT_PARALLEL', 'reasons': reasons,
            'nexus_instance': measured, 'phase1_decision': report['baseline']['decision'],
            'limits': 'Pre-registered decision convention on few packs; not a significance test.'}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='command', required=True)
    for name in ('plan', 'status', 'throughput'):
        p = sub.add_parser(name)
        p.add_argument('--held-out', required=True)
        p.add_argument('--improver', action='append', required=True)
        if name != 'throughput':
            p.add_argument('--trials', required=(name == 'status'))
    for flag in ('--baseline-trials', '--baseline-judgments', '--candidate-trials', '--candidate-judgments'):
        sub.choices['throughput'].add_argument(flag, required=True)
    p = sub.choices['plan']
    for flag in ('--model', '--policy', '--operator', '--out'):
        p.add_argument(flag, required=True)
    p.add_argument('--policies', default=str(ROOT / 'examples/nexus/budget-policies.json'))
    p.add_argument('--schedule', choices=TRIAL.SCHEDULES, default='sequential')
    sub.choices['status'].add_argument('--judgments')
    args = ap.parse_args(argv)
    try:
        if args.command == 'plan':
            result = plan(args.held_out, args.improver, args.model, args.policy, args.policies, args.trials,
                          args.operator, args.out, args.schedule)
            code = 0
        elif args.command == 'throughput':
            result = throughput(args.held_out, args.improver, (args.baseline_trials, args.baseline_judgments),
                                (args.candidate_trials, args.candidate_judgments))
            code = 0 if result['decision'] != 'INCOMPLETE' else 1
        else:
            result = status(args.held_out, args.improver, args.trials, args.judgments)
            code = 0 if result['decision'] != 'INCOMPLETE' else 1
        print(json.dumps(result, indent=2))
        return code
    except (CampaignError, TRIAL.TrialError, CASEPACK.PackError, ValueError, OSError, KeyError) as exc:
        print(f'ERROR {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
