#!/usr/bin/env python3
"""nexus-improve.py — the self-improvement gate (NEXUS Overdrive).

The agency may propose changes to itself. A self-improving system fails in a
characteristic way: it improves the measure instead of the work. This gate
admits a proposal only when both of these hold, and it never merges anything:

  paths    the proposal does not modify the protected evaluator listed in
           strategy/overdrive-protected.json, nor any held-out case pack
  compare  on held-out packs, the candidate is no worse than the baseline on
           every metric beyond its declared tolerance, has no more fatal
           defects (zero tolerance), and is strictly better on at least one

There is no composite score: a fatal defect cannot be bought back with tokens.

    nexus-improve.py paths   --base REF --head REF [--repo DIR]
    nexus-improve.py compare --variant V --held-out PACK_ROOT --tolerances FILE --improver NAME \\
                             --baseline-trials F --baseline-judgments F \\
                             --candidate-trials F --candidate-judgments F
    nexus-improve.py gate    (all of the above)

Exit status 0 means PROPOSE (the proposal may become a pull request for a human
to review and merge); 1 means REJECT or error. Labels, reviewer independence and
the reported counters are taken from the records, not authenticated here.
"""
from __future__ import annotations

import argparse
import fnmatch
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
POLICY = 'strategy/overdrive-protected.json'
LOWER_IS_BETTER = ('cost_usd', 'tokens_total', 'wall_time_seconds', 'invalid_decisions', 'rework_cycles',
                   'factual_errors', 'fatal_defects', 'constraint_violations')
HIGHER_IS_BETTER = ('evidence_coverage',)
METRICS = LOWER_IS_BETTER + HIGHER_IS_BETTER


def _module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


EVALUATION = _module('evaluation_for_improve', ROOT / 'scripts/evaluate-nexus.py')
CASEPACK = _module('casepack_for_improve', ROOT / 'scripts/nexus-casepack.py')


class GateError(ValueError):
    pass


# --- paths -------------------------------------------------------------------------------

def _git(repo, *args):
    proc = subprocess.run(['git', '-C', str(repo), *args], capture_output=True, text=True)
    if proc.returncode != 0:
        raise GateError(f"git {' '.join(args)} failed: {proc.stderr.strip()}")
    return proc.stdout


def _protected_patterns(repo, ref):
    return json.loads(_git(repo, 'show', f'{ref}:{POLICY}'))['protected']


def _held_out_dirs(repo, ref):
    dirs = set()
    for name in _git(repo, 'ls-tree', '-r', '--name-only', ref, '--', 'examples/nexus/casepacks').splitlines():
        if name.endswith('/pack.json'):
            try:
                pack = json.loads(_git(repo, 'show', f'{ref}:{name}'))
            except json.JSONDecodeError:
                continue
            if pack.get('split') == 'held_out':
                dirs.add(name[:-len('pack.json')])
    return dirs


def check_paths(base, head, repo=ROOT):
    """Violations: protected or held-out paths changed between base and head.

    The policy is read from the BASE revision: a proposal cannot loosen the rule
    it is being judged by.
    """
    changed = [p for p in _git(repo, 'diff', '--name-only', '--no-renames', f'{base}...{head}').splitlines() if p]
    patterns = _protected_patterns(repo, base)
    held_out = _held_out_dirs(repo, base) | _held_out_dirs(repo, head)
    violations = []
    for path in changed:
        rule = next((p for p in patterns if fnmatch.fnmatchcase(path, p)), None)
        if rule:
            violations.append({'path': path, 'reason': f'protected by {rule}'})
        elif any(path.startswith(d) for d in held_out):
            violations.append({'path': path, 'reason': 'held-out case pack'})
    return {'changed': changed, 'violations': violations}


# --- compare -----------------------------------------------------------------------------

def _evaluate(trials_path, judgments_path):
    cases = json.loads((ROOT / 'examples/nexus/evaluation-cases.json').read_text())
    trials = json.loads(Path(trials_path).read_text())
    judgments = json.loads(Path(judgments_path).read_text())
    report = EVALUATION.evaluate(cases, trials, judgments)
    if not report.get('judged_paired_trials') or report.get('incomplete_pairs') or report.get('unjudged_submissions'):
        raise GateError(f'{trials_path}: every trial must be part of a complete, fully judged triple')
    return trials, report


def _held_out_hashes(pack_root, improvers=()):
    # Same mechanical exposure guards as nexus-campaign.py: a proposal judged on
    # public or copied cases has not been judged on unseen evidence.
    located = CASEPACK.exposure(pack_root)
    if located:
        raise GateError(located[0])
    published = CASEPACK.published_materials()
    hashes = {}
    for pack_json in sorted(Path(pack_root).glob('*/pack.json')):
        pack = CASEPACK.verify(pack_json.parent)
        if pack['split'] == 'held_out':
            copied = CASEPACK.exposure(pack_root, pack_json.parent, pack, published)
            if copied:
                raise GateError(copied[0])
            hashes[pack['frozen']['inputs_hash']] = pack['id']
            written = {pack['author'], pack['frozen']['frozen_by']} & set(improvers)
            if written:
                raise GateError(f"{pack['id']}: held-out pack written or frozen by the improver ({sorted(written)}); "
                                'the improver cannot be judged on cases it wrote')
    if not hashes:
        raise GateError(f'{pack_root}: no frozen held-out packs; the gate cannot run on development evidence')
    return hashes


def _value(entry, metric):
    if metric == 'fatal_defects':
        return entry[metric]['total']
    if metric == 'evidence_coverage':
        return entry[metric]['ratio']
    return entry[metric]['median']


def compare(variant, held_out_root, tolerances, baseline, candidate, improvers=()):
    """Pareto non-regression on held-out packs for one variant. Returns (decision, reasons, table)."""
    if variant not in EVALUATION.VARIANTS:
        raise GateError(f'unknown variant {variant!r}')
    if set(tolerances) - set(METRICS):
        raise GateError(f'unknown tolerance metric(s) {sorted(set(tolerances) - set(METRICS))}')
    if any(type(v) not in (int, float) or v < 0 for v in tolerances.values()):
        raise GateError('tolerances must be non-negative fractions')
    held_out = _held_out_hashes(held_out_root, improvers)
    reports = {}
    for label, (trials_path, judgments_path) in (('baseline', baseline), ('candidate', candidate)):
        trials, report = _evaluate(trials_path, judgments_path)
        hashes = {row['inputs_hash'] for row in trials}
        if hashes != set(held_out):
            raise GateError(f'{label} trials must cover exactly the held-out packs '
                            f'(missing {sorted(set(held_out) - hashes)}, not held out {sorted(hashes - set(held_out))})')
        reports[label] = (trials, report)
    for field in ('model_version', 'budget_policy_ref'):
        b = {r[field] for r in reports['baseline'][0]}; c = {r[field] for r in reports['candidate'][0]}
        if b != c:
            raise GateError(f'baseline and candidate differ in {field} ({sorted(b)} vs {sorted(c)}); '
                            'that compares models or budgets, not the proposal')
    entries = {label: next(e for e in report['comparisons'] if e['variant'] == variant)
               for label, (_, report) in reports.items()}
    reasons, improved, table = [], [], []
    for metric in METRICS:
        before, after = _value(entries['baseline'], metric), _value(entries['candidate'], metric)
        tolerance = 0 if metric == 'fatal_defects' else tolerances.get(metric, 0)
        row = {'metric': metric, 'baseline': before, 'candidate': after, 'tolerance': tolerance}
        table.append(row)
        if before is None or after is None:
            reasons.append(f'{metric}: no denominator on one side; cannot compare'); continue
        if metric in LOWER_IS_BETTER:
            limit = before * (1 + tolerance) if before else tolerance
            if after > limit:
                reasons.append(f'{metric}: {after} worse than {before} beyond tolerance {tolerance}')
            elif after < before:
                improved.append(metric)
        else:
            if after < before * (1 - tolerance):
                reasons.append(f'{metric}: {after} worse than {before} beyond tolerance {tolerance}')
            elif after > before:
                improved.append(metric)
    if not reasons and not improved:
        reasons.append('no metric improved; a change with no measured benefit is not an improvement')
    return ('PROPOSE' if not reasons else 'REJECT'), reasons, {'improved': improved, 'metrics': table}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='command', required=True)
    for name in ('paths', 'compare', 'gate'):
        p = sub.add_parser(name)
        if name in ('paths', 'gate'):
            p.add_argument('--base', required=True); p.add_argument('--head', required=True)
            p.add_argument('--repo', default=str(ROOT))
        if name in ('compare', 'gate'):
            for flag in ('--variant', '--held-out', '--tolerances', '--baseline-trials', '--baseline-judgments',
                         '--candidate-trials', '--candidate-judgments'):
                p.add_argument(flag, required=True)
            p.add_argument('--improver', action='append', required=True,
                           help='author label of the proposal (repeatable); held-out packs it wrote are refused')
    args = ap.parse_args(argv)
    try:
        result = {}
        decision = 'PROPOSE'
        if args.command in ('paths', 'gate'):
            result['paths'] = check_paths(args.base, args.head, args.repo)
            if result['paths']['violations']:
                decision = 'REJECT'
        if args.command in ('compare', 'gate'):
            tolerances = json.loads(Path(args.tolerances).read_text())
            verdict, reasons, table = compare(args.variant, args.held_out, tolerances,
                                              (args.baseline_trials, args.baseline_judgments),
                                              (args.candidate_trials, args.candidate_judgments), args.improver)
            result['compare'] = {'decision': verdict, 'reasons': reasons, **table}
            if verdict != 'PROPOSE':
                decision = 'REJECT'
        result['decision'] = decision
        result['note'] = 'PROPOSE permits a pull request for human review; this gate never merges.'
        print(json.dumps(result, indent=2))
        return 0 if decision == 'PROPOSE' else 1
    except (GateError, CASEPACK.PackError, ValueError, OSError, KeyError) as exc:
        print(f'ERROR {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
