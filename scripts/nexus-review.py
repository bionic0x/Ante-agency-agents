#!/usr/bin/env python3
"""nexus-review.py — a blind reviewer's kit: scoring sheets from each pack's rubric.

nexus-blind.py seals artifacts under opaque submission ids. It gives the reviewer
the case outline, but not what the pack says a fatal defect, a factual error or a
required point of evidence is. Without that, counts depend on each reviewer's idea
of the case. This tool closes that gap without unblinding:

  kit      run by the operator, who holds the trials file. For every sealed
           submission it resolves the frozen pack the trial answered and writes a
           scoring sheet listing the pack's rubric, plus the pack's brief,
           constraints and materials. Everything added is identical for the three
           variants of a pack, so nothing in the kit tells them apart.
  collect  run on the returned sheets. Refuses unfilled items or a modified
           artifact, and writes judgments in the format evaluate-nexus.py reads.

    nexus-review.py kit     --sealed REVIEW_DIR --trials FILE --packs ROOT --out KIT_DIR
    nexus-review.py collect --kit KIT_DIR --reviewer NAME --judged-at ISO --out JUDGMENTS
                            [--trials FILE]      # validate against the trials now

The reviewer never needs the trials file. Counts: fatal_defects is the rubric
items marked present plus any additional fatal defect the reviewer names;
factual_errors and constraint_violations are counted against the rubric's
descriptions; evidence_coverage is covered over required rubric points.
Reviewer independence is recorded, not authenticated.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]


def _module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


EVALUATION = _module('evaluation_for_review', ROOT / 'scripts/evaluate-nexus.py')
CASEPACK = _module('casepack_for_review', ROOT / 'scripts/nexus-casepack.py')
SHEETS = 'sheets'
CASES = 'cases'
INSTRUCTIONS = """# Reviewer instructions

You are judging each artifact listed in `index.json` against its case. You do not
know, and should not try to infer, how an artifact was produced.

For every file in `sheets/`:

1. Read the case under `cases/<case>/` (brief, constraints, materials) and the
   artifact named in the sheet.
2. For each `fatal_defects` item set `present` to true or false. If you find a
   fatal defect the rubric does not list, add it to `additional_fatal_defects` as
   a sentence a second reviewer could check.
3. Set `factual_errors.count` and `constraint_violations.count` to whole numbers,
   using the rubric's descriptions; note what you counted.
4. For each `evidence_required` item set `covered` to true or false.

Do not edit artifacts or rubric text. Sheets with an empty item are refused.
"""


class ReviewError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise ReviewError(message)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _packs_by_hash(root):
    packs = {}
    for pack_json in sorted(Path(root).glob('*/pack.json')):
        pack = CASEPACK.verify(pack_json.parent)
        packs[pack['frozen']['inputs_hash']] = (pack_json.parent, pack)
    require(packs, f'{root}: no frozen packs')
    return packs


def sheet_for(submission, pack, case_key):
    rubric = pack['rubric']
    return {'schema_version': 1, 'submission_id': submission['submission_id'],
            'artifact': submission['artifact'], 'artifact_sha256': submission['artifact_sha256'],
            'case': f'{CASES}/{case_key}',
            'fatal_defects': [{'criterion': c, 'present': None} for c in rubric['fatal_defects']],
            'additional_fatal_defects': [],
            'factual_errors': {'criteria': rubric['factual_errors'], 'count': None, 'notes': ''},
            'constraint_violations': {'criteria': rubric['constraint_violations'], 'count': None, 'notes': ''},
            'evidence_required': [{'point': p, 'covered': None} for p in rubric['evidence_required']],
            'notes': ''}


def kit(sealed, trials_path, packs_root, out):
    sealed, out = Path(sealed), Path(out)
    require(not out.exists(), f'{out} already exists; a kit is written once')
    index = json.loads((sealed / 'index.json').read_text(encoding='utf-8'))
    trials = EVALUATION.load_trials(json.loads(Path(trials_path).read_text(encoding='utf-8')))
    packs = _packs_by_hash(packs_root)
    plan, cases = [], {}
    for submission in index['submissions']:
        sid = submission['submission_id']
        require(sid in trials, f'submission {sid} is not in the trials file')
        artifact = sealed / submission['artifact']
        require(artifact.is_file() and sha256(artifact.read_bytes()) == submission['artifact_sha256'],
                f'artifact {submission["artifact"]} is missing or changed since sealing')
        digest = trials[sid]['inputs_hash']
        require(digest in packs, f'no frozen pack under {packs_root} matches submission {sid}')
        pack_dir, pack = packs[digest]
        # An opaque case key: the pack id may name the trap the case is testing.
        case_key = 'case-' + sha256(digest.encode())[:8]
        cases[case_key] = (pack_dir, pack)
        plan.append((submission, sheet_for(submission, pack, case_key)))
    out.mkdir(parents=True)
    shutil.copy2(sealed / 'index.json', out / 'index.json')
    for submission, _ in plan:
        shutil.copy2(sealed / submission['artifact'], out / submission['artifact'])
    for case_key, (pack_dir, pack) in cases.items():
        target = out / CASES / case_key
        (target / 'materials').mkdir(parents=True)
        lines = ['# Case', '', pack['brief'], '', '## Constraints', ''] + [f'- {c}' for c in pack['constraints']]
        lines += ['', '## Permitted evidence', ''] + [f'- {e}' for e in pack['permitted_evidence']]
        lines += ['', '## Required sections of the deliverable', '']
        lines += [f'- `{s}`' for s in pack['output_contract']['required_sections']]
        (target / 'brief.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
        for name in pack['materials']:
            shutil.copy2(pack_dir / name, target / 'materials' / Path(name).name)
    (out / SHEETS).mkdir()
    for submission, sheet in plan:
        (out / SHEETS / f"{submission['submission_id']}.json").write_text(
            json.dumps(sheet, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    (out / 'REVIEWER.md').write_text(INSTRUCTIONS, encoding='utf-8')
    return {'kit': str(out), 'sheets': len(plan), 'cases': len(cases)}


def _boolean(value, where):
    require(type(value) is bool, f'{where}: set true or false')
    return value


def _count(value, where):
    require(type(value) is int and value >= 0, f'{where}: set a whole number of 0 or more')
    return value


def score(sheet, kit_dir):
    sid = sheet.get('submission_id')
    where = f'sheet {sid}'
    artifact = Path(kit_dir) / sheet['artifact']
    require(artifact.is_file() and sha256(artifact.read_bytes()) == sheet['artifact_sha256'],
            f'{where}: artifact missing or edited during review')
    fatal = sum(_boolean(item.get('present'), f"{where} fatal_defects[{i}]")
                for i, item in enumerate(sheet['fatal_defects']))
    extra = sheet.get('additional_fatal_defects', [])
    require(isinstance(extra, list) and all(isinstance(x, str) and x.strip() for x in extra),
            f'{where}: additional_fatal_defects must be sentences')
    covered = sum(_boolean(item.get('covered'), f"{where} evidence_required[{i}]")
                  for i, item in enumerate(sheet['evidence_required']))
    return {'fatal_defects': fatal + len(extra),
            'factual_errors': _count(sheet['factual_errors'].get('count'), f'{where} factual_errors.count'),
            'constraint_violations': _count(sheet['constraint_violations'].get('count'),
                                            f'{where} constraint_violations.count'),
            'evidence_coverage': {'covered': covered, 'required': len(sheet['evidence_required'])}}


def collect(kit_dir, reviewer, judged_at, out, trials_path=None):
    kit_dir, out = Path(kit_dir), Path(out)
    require(isinstance(reviewer, str) and reviewer.strip(), 'reviewer required')
    try:
        stamp = dt.datetime.fromisoformat(judged_at.replace('Z', '+00:00'))
    except (AttributeError, ValueError):
        raise ReviewError('judged_at must be an ISO-8601 time') from None
    require(stamp.tzinfo is not None, 'judged_at needs a timezone')
    index = json.loads((kit_dir / 'index.json').read_text(encoding='utf-8'))
    expected = {s['submission_id'] for s in index['submissions']}
    sheets = {p.stem: p for p in sorted((kit_dir / SHEETS).glob('*.json'))}
    require(set(sheets) == expected, f'sheets and sealed submissions differ: missing '
            f'{sorted(expected - set(sheets))}, unexpected {sorted(set(sheets) - expected)}')
    rows, problems = [], []
    for sid, path in sheets.items():
        raw = path.read_bytes()
        sheet = json.loads(raw)
        try:
            require(sheet.get('submission_id') == sid, f'sheet {path.name} names another submission')
            counts = score(sheet, kit_dir)
        except ReviewError as exc:
            problems.append(str(exc)); continue
        rows.append({'submission_id': sid, 'reviewer': reviewer.strip(), 'judged_at': judged_at,
                     'evidence_ref': f'review-sheet:{sid}#sha256:{sha256(raw)}', **counts})
    require(not problems, 'incomplete review: ' + '; '.join(problems))
    if trials_path:
        EVALUATION.load_judgments(rows, EVALUATION.load_trials(json.loads(Path(trials_path).read_text())))
    require(not out.exists(), f'{out} already exists')
    out.write_text(json.dumps(rows, indent=2) + '\n', encoding='utf-8')
    return {'judgments': len(rows), 'out': str(out)}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='command', required=True)
    k = sub.add_parser('kit')
    for flag in ('--sealed', '--trials', '--packs', '--out'):
        k.add_argument(flag, required=True)
    c = sub.add_parser('collect')
    for flag in ('--kit', '--reviewer', '--judged-at', '--out'):
        c.add_argument(flag, required=True)
    c.add_argument('--trials')
    args = ap.parse_args(argv)
    try:
        if args.command == 'kit':
            result = kit(args.sealed, args.trials, args.packs, args.out)
        else:
            result = collect(args.kit, args.reviewer, args.judged_at, args.out, args.trials)
        print(json.dumps(result, indent=2))
        return 0
    except (ReviewError, CASEPACK.PackError, ValueError, OSError, KeyError) as exc:
        print(f'ERROR {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
