"""Boxmaker: an archive of what was refuted, discarded or rejected, kept for recombination.

Discarded material is not waste. A refuted expectation, an option judged not
viable, a hypothesis ACH set aside, a proposal the develop gate rejected — each
carries a reason, and parts of it may fit a later problem (Marco IV.4:
destruction and creation). ``build`` collects them, with the reason and the
record they come from; ``recombine`` turns chosen items into draft claims for a
new ``ante options`` input.

Recombined material enters as ``HYPOTHESIS`` with ``origin: system``, never as
evidence: the claims discipline refuses system-produced evidence (invariant 7),
so a recombined idea must earn its evidence again.

    ante learn box build --out BOX.json --at T [--artifacts DIR ...] [--ledger L] [--state S]
    ante learn box recombine BOX.json --items ID,ID --at T
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from ante.core import canon, io, schema
from ante.core import time as ante_time
from ante.learn import ledger
from ante.strategy import artifact, chain


def build(at: str, directories: list[str] = (), ledger_path: str | None = None,
          state_path: str | None = None) -> dict:
    items = []
    for directory in directories:
        for art in chain.load(directory):
            if art['command'] == 'options':
                for option in art['body'].get('options', []):
                    if not option.get('viable'):
                        items.append({'kind': 'discarded_option', 'text': option['mechanism'],
                                      'reason': option.get('why_not_viable'),
                                      'from': f'{art["case_id"]}:options:{art["artifact_sha256"][:12]}'})
            if art['command'] == 'ach':
                analysis = art['body']['analysis']
                for hypothesis in art['body']['hypotheses']:
                    if hypothesis['id'] in analysis['least_inconsistent']:
                        continue
                    count = analysis['inconsistency_by_source_group'][hypothesis['id']]
                    items.append({'kind': 'rejected_hypothesis', 'text': hypothesis['statement'],
                                  'reason': f'{count} inconsistent source group(s) in ACH',
                                  'from': f'{art["case_id"]}:ach:{art["artifact_sha256"][:12]}'})
    if ledger_path:
        entries = ledger.read(ledger_path)
        decided = ledger.decisions(entries)
        for entry in ledger.reconciliations(entries):
            payload = entry['payload']
            if payload['outcome'] != 'REFUTED':
                continue
            decision = decided[payload['decision']]
            if decision['payload']['synthetic']:
                continue
            frozen = {e['id']: e for e in decision['payload']['artifact']['body']['snapshot']['expectations']}
            expectation = frozen[payload['expectation']]
            items.append({'kind': 'refuted_expectation', 'text': expectation['what_should_change'],
                          'reason': f'refuted: {payload["observed"]}', 'from': f'ledger:{entry["seq"]}'})
    if state_path:
        state = ledger.read(state_path)
        specs = {e['payload']['id']: e['payload']['spec'] for e in state if e['kind'] == 'proposal'}
        for entry in state:
            if entry['kind'] == 'gate' and entry['payload']['decision'] == 'REJECT':
                spec = specs.get(entry['payload']['id'], {})
                items.append({'kind': 'rejected_proposal', 'text': spec.get('hypothesis', entry['payload']['id']),
                              'reason': '; '.join(entry['payload']['reasons']), 'from': f'develop:{entry["seq"]}'})
    for item in items:
        item['id'] = 'box-' + canon.digest({k: item[k] for k in ('kind', 'text', 'from')})[:10]
    return {'kind': 'boxmaker_archive', 'at': ante_time.iso(ante_time.parse(at, 'at')), 'items': items,
            'note': 'Discarded material with its reason. Recombined items enter as HYPOTHESIS, never as evidence.'}


def recombine(box: dict, item_ids: list[str], at: str) -> dict:
    by_id = {item['id']: item for item in box['items']}
    unknown = [i for i in item_ids if i not in by_id]
    if unknown:
        schema.fail('items', f'not in the archive: {", ".join(unknown)}')
    if len(item_ids) < 1:
        schema.fail('items', 'name at least one archive item')
    date = ante_time.iso(ante_time.parse(at, 'at'))[:10]
    claims = [{'id': f'recombined-{item["id"]}',
               'text': f'Recombined from a {item["kind"].replace("_", " ")}: {item["text"]}',
               'status': 'HYPOTHESIS', 'source': {'ref': f'boxmaker:{item["from"]}', 'origin': 'system'},
               'date': date, 'limit': f'Previously set aside because: {item["reason"]}. Needs new evidence.'}
              for item in (by_id[i] for i in item_ids)]
    return {'kind': 'boxmaker_recombination', 'claims': claims,
            'note': 'Paste these claims into an ante options input. They cannot be promoted to EVIDENCE as they are.'}


def add_parser(lsub) -> None:
    box = lsub.add_parser('box', help='archive of refuted, discarded and rejected material; recombination')
    bsub = box.add_subparsers(dest='box_command', required=True)
    b = bsub.add_parser('build')
    b.add_argument('--out', required=True)
    b.add_argument('--artifacts', action='append', default=[])
    b.add_argument('--ledger')
    b.add_argument('--state')
    b.add_argument('--at', required=True)
    r = bsub.add_parser('recombine')
    r.add_argument('box')
    r.add_argument('--items', required=True)
    r.add_argument('--at', required=True)


def main(args) -> int:
    try:
        if args.box_command == 'build':
            result = build(args.at, args.artifacts, args.ledger, args.state)
            Path(args.out).write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
            print(f'boxmaker: {len(result["items"])} item(s) -> {args.out}')
            return 0
        result = recombine(io.load_json(args.box), [i.strip() for i in args.items.split(',') if i.strip()], args.at)
    except (artifact.LineageError, ledger.LedgerError) as exc:
        print(f'LINEAGE {exc}', file=sys.stderr)
        return 3
    except (io.InputError, schema.SchemaError, ante_time.TimeError) as exc:
        print(f'INVALID {exc}', file=sys.stderr)
        return 2
    sys.stdout.write(json.dumps(result, indent=2, ensure_ascii=False) + '\n')
    return 0
