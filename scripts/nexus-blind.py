#!/usr/bin/env python3
"""nexus-blind.py — build a review packet with direct pipeline labels removed.

Blinding that relies on a reviewer not looking is not blinding. Two things
defeat it in practice, and both are mechanical:

  the filename   `nexus-instance-level-inversion.md` announces the variant
                 before the artifact is opened.
  the artifact   a run that narrates its own pipeline ("delegating to the
                 orchestrator", "as a single agent I will…") announces it in
                 the first paragraph.

`seal` addresses the first by copying every artifact to an opaque submission id
and emitting the packet in shuffled order. It addresses the second by scanning
for tells and refusing to seal a packet that contains them, as a screening step. Preserve the original artifacts: redactions need a uniform,
preregistered procedure. No keyword scan can guarantee blinded review.

The variant assignment stays in the trials file, which the reviewer never
receives. evaluate-nexus.py joins the two after the judgments are sealed.

Usage:
  nexus-blind.py seal --trials host-trials.json --artifacts runs/ --out review/
  nexus-blind.py seal ... --allow-tells      # record them instead of refusing
"""
import argparse, hashlib, importlib.util, json, os, random, re, shutil, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('nexus_evaluation', ROOT / 'scripts/evaluate-nexus.py')
evaluation = importlib.util.module_from_spec(spec)
spec.loader.exec_module(evaluation)

# Words that identify the pipeline that produced an artifact. Matched case-
# insensitively on word boundaries so ordinary prose ("a single agent may…")
# is caught too: in a review packet that phrase is a tell whatever its intent.
TELLS = [r'nexus', r'single[\s_-]?agent', r'fixed[\s_-]?team', r'orchestrat\w*',
         r'sub-?agent', r'variant', r'delegat\w*']
TELL_RE = re.compile('|'.join(f'({t})' for t in TELLS), re.IGNORECASE)


def submission_id(case_id, trial_id, variant, salt):
    """Reproducible pseudonym; use a private, high-entropy salt. Not proof of anonymity."""
    digest = hashlib.sha256(f'{salt}\0{case_id}\0{trial_id}\0{variant}'.encode()).hexdigest()
    return digest[:16]


def scan(text):
    found = {}
    for match in TELL_RE.finditer(text):
        word = match.group(0).lower()
        found[word] = found.get(word, 0) + 1
    return found


def seal(trials_path, artifacts_dir, out_dir, allow_tells=False, seed=None, cases_path=None):
    trials = json.loads(Path(trials_path).read_text(encoding='utf-8'))
    validated = evaluation.load_trials(trials)
    if not validated:
        raise ValueError('no trials to seal')
    case_path = Path(cases_path) if cases_path else ROOT / 'examples/nexus/evaluation-cases.json'
    cases = evaluation.load_cases(json.loads(case_path.read_text(encoding='utf-8')))
    artifacts, out = Path(artifacts_dir).resolve(), Path(out_dir).absolute()
    if out.exists() or out.is_symlink():
        raise ValueError(f'{out} already exists; packets must use a new destination')
    # Validate every artifact and prepare the bytes before publishing any packet.
    packet, leaks, files = [], {}, {}
    for row in validated.values():
        sid = row['submission_id']
        if row['case_id'] not in cases:
            raise ValueError(f"unknown case {row['case_id']!r}")
        case = cases[row['case_id']]
        source = artifacts / f'{sid}.md'
        if source.is_symlink() or not source.resolve().is_relative_to(artifacts):
            raise ValueError(f'artifact must be a regular file inside artifacts directory: {sid}')
        if not source.is_file():
            raise ValueError(f'missing artifact for submission {sid}: {source}')
        data = source.read_bytes()
        found = scan(data.decode('utf-8'))
        if found:
            leaks[sid] = found
        files[f'{sid}.md'] = data
        packet.append({'submission_id': sid, 'case_scenario': case['scenario'],
                       'expected_behavior': case['expected_behavior'], 'artifact': f'{sid}.md',
                       'artifact_sha256': hashlib.sha256(data).hexdigest()})
    if leaks and not allow_tells:
        detail = '; '.join(f'{sid}: {sorted(words)}' for sid, words in sorted(leaks.items()))
        raise ValueError('known self-narration defeats the blind: ' + detail +
                         '. Preserve the original artifact; record an unblinded review or '
                         'apply a preregistered redaction protocol. --allow-tells records the leak.')
    random.Random(seed).shuffle(packet)
    index = {'schema_version': 1, 'submissions': packet,
             'reviewer_instructions':
                 'Judge each artifact against the supplied case and expected behavior. '
                 'Record counts by submission id without pipeline labels or rankings.',
             'known_tells': leaks or None,
             'blinding_status': 'KNOWN_TELLS' if leaks else 'NOT_INDEPENDENTLY_VERIFIED',
             'limitations': 'Opaque names and a keyword scan cannot guarantee blinding. '
                            'Use a separate reviewer workspace; keep trials and salt private.'}
    out.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix='.nexus-review-', dir=out.parent))
    try:
        for name, data in files.items():
            (staging / name).write_bytes(data)
        (staging / 'index.json').write_text(json.dumps(index, indent=2) + '\n', encoding='utf-8')
        # Atomic reservation: do not replace even a concurrently created empty directory.
        out.mkdir()
        try:
            for source in staging.iterdir():
                os.replace(source, out / source.name)
        except BaseException:
            shutil.rmtree(out)
            raise
    finally:
        shutil.rmtree(staging, ignore_errors=True)
    return {'sealed': len(packet), 'out': str(out), 'tells_recorded': bool(leaks)}


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('command', choices=['seal', 'submission-id'])
    ap.add_argument('--trials')
    ap.add_argument('--artifacts')
    ap.add_argument('--cases', help='case material and expected behavior for the reviewer')
    ap.add_argument('--out')
    ap.add_argument('--allow-tells', action='store_true')
    ap.add_argument('--seed', type=int, default=None)
    ap.add_argument('--case'); ap.add_argument('--trial')
    ap.add_argument('--variant'); ap.add_argument('--salt')
    args = ap.parse_args()
    try:
        if args.command == 'submission-id':
            if not all([args.case, args.trial, args.variant, args.salt]):
                ap.error('submission-id requires --case --trial --variant --salt')
            print(submission_id(args.case, args.trial, args.variant, args.salt))
            return 0
        if not all([args.trials, args.artifacts, args.out]):
            ap.error('seal requires --trials --artifacts --out')
        print(json.dumps(seal(args.trials, args.artifacts, args.out,
                              args.allow_tells, args.seed, args.cases), indent=2))
        return 0
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f'ERROR {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
