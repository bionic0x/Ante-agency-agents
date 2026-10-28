#!/usr/bin/env python3
"""Characterization harness: the behavioural contract of the Ante Foundation refactor.

Each case in ``cases.json`` runs one existing CLI exactly as a user would
(``python3 scripts/<name>.py ...``) and records exit status, stdout, stderr and,
optionally, files the command writes. The recordings in ``golden/`` were taken
at the base commit, before any code moved. After the refactor the same scripts
run as thin wrappers over ``ante/`` and must reproduce every recording byte for
byte (after the declared normalisation of the repository root and the per-case
temporary directory).

    run.py check            compare every case with its recording (default)
    run.py check --only ID  one case
    run.py record           write recordings that do not exist yet
    run.py list             list cases and whether each has a recording

Recordings are the contract. ``record`` never overwrites an existing recording:
a recording that no longer matches is a behaviour change, and a behaviour change
belongs in its own pull request with its own reviewed rebaseline (delete the
file in that PR, re-record, and say why). Exit 0 when all cases match, 1 on any
mismatch or missing recording, 2 on harness misuse.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CASES = HERE / 'cases.json'
GOLDEN = HERE / 'golden'
FIXTURES = HERE / 'fixtures'
TIMEOUT = 120
ENV_KEEP = ('PATH', 'HOME', 'SYSTEMROOT')


def load_cases() -> list[dict]:
    with CASES.open(encoding='utf-8') as handle:
        data = json.load(handle)
    cases = data['cases']
    ids = [case['id'] for case in cases]
    duplicates = sorted({i for i in ids if ids.count(i) > 1})
    if duplicates:
        raise SystemExit(f'duplicate case ids: {duplicates}')
    return cases


def expand(token: str, tmp: Path) -> str:
    return (token.replace('{ROOT}', str(ROOT))
                 .replace('{TMP}', str(tmp))
                 .replace('{FIX}', str(FIXTURES)))


def normalise(text: str, tmp: Path) -> str:
    # Longest first: the temporary directory may live under the root.
    for path, label in sorted(((str(tmp), '<TMP>'), (str(ROOT), '<ROOT>')),
                              key=lambda item: -len(item[0])):
        text = text.replace(path, label)
    return text


def clean_env() -> dict[str, str]:
    env = {key: os.environ[key] for key in ENV_KEEP if key in os.environ}
    env.update({'LC_ALL': 'C.UTF-8', 'LANG': 'C.UTF-8', 'TZ': 'UTC',
                'PYTHONHASHSEED': '0', 'PYTHONDONTWRITEBYTECODE': '1',
                'PYTHONIOENCODING': 'utf-8', 'NO_COLOR': '1'})
    return env


def execute(case: dict) -> dict:
    tmp = Path(tempfile.mkdtemp(prefix='ante-char-'))
    try:
        for name, source in case.get('setup_copy', {}).items():
            src = Path(expand(source, tmp))
            dst = tmp / name
            if src.is_dir():
                shutil.copytree(src, dst)
            else:
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
        argv = [sys.executable, str(ROOT / 'scripts' / case['script'])]
        argv += [expand(token, tmp) for token in case.get('args', [])]
        stdin = case.get('stdin')
        proc = subprocess.run(argv, cwd=ROOT, env=clean_env(), timeout=TIMEOUT,
                              input=stdin.encode() if stdin is not None else None,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        result = {
            'exit': proc.returncode,
            'stdout': normalise(proc.stdout.decode('utf-8', 'replace'), tmp),
            'stderr': normalise(proc.stderr.decode('utf-8', 'replace'), tmp),
            'files': {},
        }
        for rel in case.get('capture', []):
            path = tmp / rel
            if path.is_file():
                result['files'][rel] = normalise(path.read_text('utf-8', 'replace'), tmp)
            else:
                result['files'][rel] = None
        return result
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def golden_path(case_id: str) -> Path:
    return GOLDEN / f'{case_id}.json'


def digest(result: dict) -> str:
    blob = json.dumps(result, sort_keys=True, ensure_ascii=False).encode()
    return hashlib.sha256(blob).hexdigest()


def first_difference(expected: str, actual: str) -> str:
    for number, (left, right) in enumerate(zip(expected.splitlines(), actual.splitlines()), 1):
        if left != right:
            return f'line {number}: expected {left[:160]!r} got {right[:160]!r}'
    return f'length differs: expected {len(expected)} chars, got {len(actual)}'


def compare(expected: dict, actual: dict) -> list[str]:
    problems = []
    if expected['exit'] != actual['exit']:
        problems.append(f"exit: expected {expected['exit']} got {actual['exit']}")
    for stream in ('stdout', 'stderr'):
        if expected[stream] != actual[stream]:
            problems.append(f'{stream}: ' + first_difference(expected[stream], actual[stream]))
    for rel, content in expected.get('files', {}).items():
        got = actual['files'].get(rel)
        if content != got:
            if content is None or got is None:
                problems.append(f'file {rel}: presence differs')
            else:
                problems.append(f'file {rel}: ' + first_difference(content, got))
    return problems


def cmd_record(cases: list[dict]) -> int:
    GOLDEN.mkdir(exist_ok=True)
    written = skipped = unstable = 0
    for case in cases:
        target = golden_path(case['id'])
        if target.exists():
            skipped += 1
            continue
        first, second = execute(case), execute(case)
        if digest(first) != digest(second):
            print(f'UNSTABLE {case["id"]}: two runs differ; not recorded', file=sys.stderr)
            unstable += 1
            continue
        record = {'case': case['id'], **first}
        target.write_text(json.dumps(record, indent=2, ensure_ascii=False, sort_keys=True) + '\n',
                          encoding='utf-8')
        written += 1
    print(f'recorded {written}, kept {skipped} existing, {unstable} unstable')
    return 1 if unstable else 0


def cmd_check(cases: list[dict], only: str | None) -> int:
    selected = [case for case in cases if only in (None, case['id'])]
    if only and not selected:
        print(f'unknown case: {only}', file=sys.stderr)
        return 2
    failures = 0
    for case in selected:
        target = golden_path(case['id'])
        if not target.exists():
            print(f'MISSING {case["id"]}: no recording')
            failures += 1
            continue
        expected = json.loads(target.read_text(encoding='utf-8'))
        problems = compare(expected, execute(case))
        if problems:
            failures += 1
            print(f'FAIL {case["id"]}')
            for problem in problems:
                print(f'     {problem}')
    passed = len(selected) - failures
    print(f'characterization: {passed}/{len(selected)} cases match their recording')
    return 1 if failures else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('command', nargs='?', default='check', choices=['check', 'record', 'list'])
    parser.add_argument('--only')
    args = parser.parse_args()
    cases = load_cases()
    if args.command == 'record':
        if args.only:
            parser.error('record takes no --only; it writes every missing recording')
        return cmd_record(cases)
    if args.command == 'list':
        for case in cases:
            mark = 'recorded' if golden_path(case['id']).exists() else 'MISSING'
            print(f'{case["id"]:<48} {mark}')
        return 0
    return cmd_check(cases, args.only)


if __name__ == '__main__':
    sys.exit(main())
