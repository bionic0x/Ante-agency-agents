"""Uneven future: a register of weak signals, kept as leading indicators.

Where and when a capability or a conduct was first observed, with its
provenance. A signal is not a prediction: it says that something exists
somewhere, not that it will spread. ``export`` turns the signals observed by a
decision time into ``HYPOTHESIS`` claims for ``frame`` or ``react`` inputs, with
the first observation and its limit stated; they carry no probability.

    ante signals add SPEC.json --register R --at T
    ante signals export --register R --at T [--topic TEXT]

SPEC: ``{id, observed, topic, first_observed_at, where, source: {ref, origin}, note}``.
The register is hash-chained; a signal is never edited, only followed by another.
"""
from __future__ import annotations

import json
import sys

from ante.core import io, schema
from ante.core import time as ante_time
from ante.learn import ledger

KINDS = ('signal',)
KEYS = ('id', 'observed', 'topic', 'first_observed_at', 'where', 'source', 'note')


class SignalError(ValueError):
    pass


def add(spec_path: str, register: str, at: str) -> dict:
    spec = io.load_document(spec_path)
    schema.exact_keys(spec, KEYS, 'signal')
    for key in ('id', 'observed', 'topic', 'where', 'note'):
        schema.text(spec[key], f'signal.{key}')
    source = schema.exact_keys(spec['source'], ('ref', 'origin'), 'signal.source')
    schema.text(source['ref'], 'signal.source.ref')
    schema.enum(source['origin'], ('external', 'owner', 'system'), 'signal.source.origin')
    first = ante_time.parse(spec['first_observed_at'], 'signal.first_observed_at')
    if first > ante_time.parse(at, 'at'):
        raise SignalError('a signal cannot be registered before it was observed')
    entries = ledger.read(register)
    if any(e['kind'] != 'signal' for e in entries):
        raise SignalError('this file is not a signal register')
    if any(e['payload']['id'] == spec['id'] for e in entries):
        raise SignalError(f'signal {spec["id"]} already registered; register a follow-up with a new id')
    return ledger.append(register, 'signal', {**spec, 'first_observed_at': ante_time.iso(first)}, at, kinds=KINDS)


def export(register: str, at: str, topic: str | None = None) -> dict:
    now = ante_time.parse(at, 'at')
    claims = []
    for entry in ledger.read(register):
        signal = entry['payload']
        if ante_time.parse(entry['at'], 'at') > now:
            continue
        if topic and topic.lower() not in signal['topic'].lower():
            continue
        claims.append({'id': f'signal-{signal["id"]}',
                       'text': f'{signal["observed"]} — first observed {signal["first_observed_at"][:10]} '
                               f'at {signal["where"]}.',
                       'status': 'HYPOTHESIS', 'source': dict(signal['source']),
                       'date': signal['first_observed_at'][:10],
                       'limit': 'A weak signal: it shows the capability or conduct exists somewhere; it does not '
                                'predict that it will spread. Use as a leading indicator in react or watch.'})
    return {'kind': 'leading_indicators', 'at': ante_time.iso(now), 'claims': claims}


def add_parser(sub) -> None:
    sig = sub.add_parser('signals', help='weak-signal register; exported as HYPOTHESIS claims, never predictions')
    ssub = sig.add_subparsers(dest='signals_command', required=True)
    a = ssub.add_parser('add')
    a.add_argument('spec')
    e = ssub.add_parser('export')
    e.add_argument('--topic')
    for p in (a, e):
        p.add_argument('--register', required=True)
        p.add_argument('--at', required=True)
    sig.set_defaults(handler=main)


def main(args) -> int:
    try:
        if args.signals_command == 'add':
            entry = add(args.spec, args.register, args.at)
            print(f'signal registered: seq {entry["seq"]} {entry["entry_hash"]}')
            return 0
        sys.stdout.write(json.dumps(export(args.register, args.at, args.topic), indent=2, ensure_ascii=False) + '\n')
        return 0
    except ledger.LedgerError as exc:
        print(f'LINEAGE {exc}', file=sys.stderr)
        return 3
    except (SignalError, io.InputError, schema.SchemaError, ante_time.TimeError) as exc:
        print(f'INVALID {exc}', file=sys.stderr)
        return 2
