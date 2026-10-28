"""The ``ante`` command line.

    ante <command> INPUT [--at ISO8601] [--from ARTEFACT ...] [--out DIR]
    ante run RUNBOOK --artifacts DIR
    ante commands

Exit status for strategy commands: 0 the artefact was produced (whatever its
verdict, HOLD included); 2 invalid input or a doctrinal rejection; 3 broken
lineage. Nothing here calls a model, opens the network or acts in the world.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from ante import doctrine as doctrine_mod
from ante.core import io, schema
from ante.core import time as ante_time
from ante.strategy import artifact, base
from ante.strategy.commands import COMMANDS

EXIT_OK, EXIT_INVALID, EXIT_LINEAGE = 0, 2, 3


def _write(art: dict, out: Path | None) -> None:
    text = json.dumps(art, indent=2, ensure_ascii=False, sort_keys=True) + '\n'
    if out is None:
        sys.stdout.write(text)
        return
    out.mkdir(parents=True, exist_ok=True)
    name = art['command']
    (out / f'{name}.json').write_text(text, encoding='utf-8')
    (out / f'{name}.md').write_text(artifact.to_markdown(art), encoding='utf-8')
    print(f'{name}: {art["verdict"] or "artefact"} {art["artifact_sha256"]} -> {out / (name + ".json")}')


def _draft(command, args) -> int:
    from ante.strategy import draft
    try:
        if args.at is None:
            schema.fail('at', '--at is required with --draft-with')
        at = ante_time.iso(ante_time.parse(args.at, 'at'))
        lineage = artifact.Lineage.from_paths(args.parents)
        result = draft.draft(command, args.input, lineage.parents, args.draft_with, args.model, at)
    except artifact.LineageError as exc:
        print(f'LINEAGE {exc}', file=sys.stderr)
        return EXIT_LINEAGE
    except (draft.DraftError, io.InputError, schema.SchemaError, ante_time.TimeError) as exc:
        print(f'INVALID {exc}', file=sys.stderr)
        return EXIT_INVALID
    text = json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True) + '\n'
    if args.out:
        out = Path(args.out)
        out.mkdir(parents=True, exist_ok=True)
        (out / f'{command.name}.draft.json').write_text(text, encoding='utf-8')
        print(f'{command.name}: unsigned draft -> {out / (command.name + ".draft.json")}')
    else:
        sys.stdout.write(text)
    return EXIT_OK


def _strategy(command, args) -> int:
    if args.draft_with:
        return _draft(command, args)
    try:
        doc = io.load_document(args.input)
        doctrine = doctrine_mod.load(args.contracts) if args.contracts else doctrine_mod.load()
        art = base.execute(command, doc, args.at, args.parents, doctrine)
    except artifact.LineageError as exc:
        print(f'LINEAGE {exc}', file=sys.stderr)
        return EXIT_LINEAGE
    except artifact.Rejected as exc:
        for finding in exc.findings:
            print(f"ERROR {finding['code']} {finding['path']}: {finding['message']}", file=sys.stderr)
        return EXIT_INVALID
    except (io.InputError, schema.SchemaError, ante_time.TimeError, doctrine_mod.MissingTable) as exc:
        print(f'INVALID {exc}', file=sys.stderr)
        return EXIT_INVALID
    _write(art, Path(args.out) if args.out else None)
    return EXIT_OK


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog='ante', description=__doc__.split('\n\n')[0],
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest='command', required=True, metavar='COMMAND')
    for command in COMMANDS.values():
        p = sub.add_parser(command.name, help=command.summary, description=command.summary)
        p.add_argument('input', help='input document (.json, .yaml, .yml)')
        p.add_argument('--at', help='decision time, ISO-8601 with offset (else the input\'s "at")')
        p.add_argument('--from', dest='parents', action='append', default=[], metavar='ARTEFACT',
                       help='an earlier artefact of the same case (repeatable)')
        p.add_argument('--out', help='directory for <command>.json and <command>.md (else JSON on stdout)')
        p.add_argument('--contracts', help=argparse.SUPPRESS)
        p.add_argument('--draft-with', metavar='PROVIDER',
                       help='have a model draft this input from a brief; writes an unsigned draft, never an artefact')
        p.add_argument('--model', help='model id for --draft-with')
        p.set_defaults(handler=lambda args, c=command: _strategy(c, args))
    lister = sub.add_parser('commands', help='list the strategy commands')
    lister.set_defaults(handler=lambda args: _list())
    from ante.strategy import runcheck
    runner = sub.add_parser('run', help='check that a runbook\'s artefact chain is complete (executes nothing)')
    runner.add_argument('runbook')
    runner.add_argument('--artifacts', required=True, help='directory holding the case artefacts')
    runner.add_argument('--contracts', help=argparse.SUPPRESS)
    runner.set_defaults(handler=runcheck.main)
    return parser


def _list() -> int:
    for command in COMMANDS.values():
        print(f'{command.name:<10} {command.summary}')
    return EXIT_OK


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.handler(args)


if __name__ == '__main__':
    sys.exit(main())
