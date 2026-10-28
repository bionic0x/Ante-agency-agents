#!/usr/bin/env python3
"""Mechanical extraction of ``scripts/*.py`` into the ``ante`` package, and its proof.

    extraction.py apply  SCRIPT MODULE   move one script; leave a compatibility shim
    extraction.py verify [--base REF]    prove every recorded move is mechanical

A move is mechanical when the package module equals the script at the base
commit after exactly these rewrites, and nothing else:

1. the shebang line is dropped (the package module is not executable);
2. ``ROOT = Path(__file__).resolve().parents[1]`` becomes
   ``from ante.paths import ROOT`` (the expression meant "repository root" only
   for a file one level below the root).

``verify`` re-derives each module from the base commit and compares bytes, and
checks that each shim is exactly the generated shim. Reviewers of a
``protected:`` commit can therefore confirm a move without reading the moved code.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = Path(__file__).with_name('extractions.json')
BASE = '86addea'
ROOT_LINE = 'ROOT = Path(__file__).resolve().parents[1]\n'
ROOT_IMPORT = 'from ante.paths import ROOT\n'


def transform(source: str) -> str:
    lines = source.splitlines(keepends=True)
    if lines and lines[0].startswith('#!'):
        lines = lines[1:]
    count = sum(1 for line in lines if line == ROOT_LINE)
    if count > 1:
        raise SystemExit('more than one ROOT definition; extraction is not mechanical')
    return ''.join(ROOT_IMPORT if line == ROOT_LINE else line for line in lines)


def shim(module: str, docstring_first_line: str) -> str:
    return (
        '#!/usr/bin/env python3\n'
        f'"""Compatibility entry point. Implementation: {module} (see ante/_compat.py).\n\n'
        f'{docstring_first_line}\n"""\n'
        'import sys\n'
        'from pathlib import Path\n\n'
        'sys.path.append(str(Path(__file__).resolve().parents[1]))\n'
        'from ante._compat import adopt  # noqa: E402\n\n'
        f'adopt(globals(), {module!r})\n'
    )


def module_path(module: str) -> Path:
    return ROOT.joinpath(*module.split('.')).with_suffix('.py')


def first_doc_line(source: str) -> str:
    import ast
    doc = ast.get_docstring(ast.parse(source)) or ''
    return doc.strip().splitlines()[0] if doc.strip() else ''


def load_manifest() -> dict:
    if MANIFEST.exists():
        return json.loads(MANIFEST.read_text(encoding='utf-8'))
    return {'base': BASE, 'moves': {}}


def cmd_apply(script: str, module: str) -> int:
    source_path = ROOT / 'scripts' / script
    source = source_path.read_text(encoding='utf-8')
    if source.startswith('#!/usr/bin/env python3\n"""Compatibility entry point.'):
        raise SystemExit(f'{script} is already a shim')
    target = module_path(module)
    target.parent.mkdir(parents=True, exist_ok=True)
    init = target.parent / '__init__.py'
    if not init.exists():
        init.write_text(f'"""{module.rsplit(".", 1)[0]}"""\n', encoding='utf-8')
    target.write_text(transform(source), encoding='utf-8')
    mode = source_path.stat().st_mode
    source_path.write_text(shim(module, first_doc_line(source)), encoding='utf-8')
    source_path.chmod(mode)
    manifest = load_manifest()
    manifest['moves'][script] = module
    MANIFEST.write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    print(f'moved scripts/{script} -> {target.relative_to(ROOT)}')
    return 0


def git_show(ref: str, path: str) -> str:
    return subprocess.run(['git', '-C', str(ROOT), 'show', f'{ref}:{path}'], check=True,
                          capture_output=True, text=True).stdout


def cmd_verify(base: str) -> int:
    manifest = load_manifest()
    failures = 0
    for script, module in sorted(manifest['moves'].items()):
        original = git_show(base, f'scripts/{script}')
        expected_module = transform(original)
        expected_shim = shim(module, first_doc_line(original))
        actual_module = module_path(module).read_text(encoding='utf-8')
        actual_shim = (ROOT / 'scripts' / script).read_text(encoding='utf-8')
        problems = []
        if actual_module != expected_module:
            problems.append(f'{module} differs from scripts/{script}@{base} beyond the two rewrites')
        if actual_shim != expected_shim:
            problems.append(f'scripts/{script} is not the generated shim')
        for problem in problems:
            print(f'FAIL {problem}')
        failures += bool(problems)
    print(f'extraction: {len(manifest["moves"]) - failures}/{len(manifest["moves"])} moves are mechanical')
    return 1 if failures else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    sub = parser.add_subparsers(dest='command', required=True)
    apply = sub.add_parser('apply')
    apply.add_argument('script')
    apply.add_argument('module')
    verify = sub.add_parser('verify')
    verify.add_argument('--base', default=None)
    args = parser.parse_args()
    if args.command == 'apply':
        return cmd_apply(args.script, args.module)
    return cmd_verify(args.base or load_manifest()['base'])


if __name__ == '__main__':
    sys.exit(main())
