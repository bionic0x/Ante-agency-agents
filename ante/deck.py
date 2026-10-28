"""``ante deck``: a read-only terminal view of a case.

Shows the artefact chain as a navigable graph — each artefact with its parents,
its claims and their epistemic state — next to the claims that carry the plan
(nodal load), the defensive layers and their independence, shadow trials and
cumulative drift. It is a view: it opens files for reading only and has no
effect. Terminal aesthetic: green on black.

    ante deck --artifacts DIR [--ledger L] [--log S] [--state D] [--at T] [--plain]

Interactive when attached to a terminal (arrows or j/k move, enter toggles
detail, q quits); ``--plain`` prints the same screen once, for logs and tests.
"""
from __future__ import annotations

import json
import sys

from ante.core import time as ante_time
from ante.ice import layers as ice_layers
from ante.learn import jackpot, ledger, stub
from ante.strategy import artifact, chain
from ante.strategy.commands import nodal

MARK = {'EVIDENCE': '■', 'HYPOTHESIS': '◆', 'ASSUMPTION': '○', 'ATTRIBUTED_INTENT': '◇', 'UNKNOWN': '?'}


def model(directory: str, at: str | None = None, ledger_path: str | None = None, log_path: str | None = None,
          state_path: str | None = None) -> dict:
    arts = chain.load(directory)
    when = at or (arts[-1]['at'] if arts else ante_time.iso(ante_time.parse('1970-01-01T00:00:00Z', 'at')))
    by_hash = {a['artifact_sha256']: a for a in arts}
    nodes = []
    for art in arts:
        nodes.append({'command': art['command'], 'at': art['at'], 'sha': art['artifact_sha256'][:12],
                      'verdict': art['verdict'], 'independence': art['independence_level'],
                      'parents': [by_hash[p['artifact_sha256']]['command'] for p in art['parents']],
                      'claims': [(c['id'], c['status']) for c in art['claims']],
                      'warnings': [f['code'] for f in art['findings']], 'next': art['next_decision']})
    load = nodal.assess(arts) if any(a['command'] == 'frame' for a in arts) else None
    shipped = ice_layers.load()
    view = {'case': arts[0]['case_id'] if arts else None, 'at': when, 'nodes': nodes,
            'load_bearing': load['load_bearing_claims'] if load else [], 'blocking': load['blocking'] if load else [],
            'ice': {'layers': [(layer['function'], layer['id']) for layer in shipped],
                    'problems': ice_layers.check(shipped)},
            'shadow': stub.status(log_path)['recommendations'] if log_path else None,
            'drift': None}
    if ledger_path:
        state = ledger.read(state_path) if state_path else []
        result = jackpot.assess(ledger.read(ledger_path), when, state)
        view['drift'] = {'status': result['status'], 'total': result['total'],
                         'threshold': result['thresholds']['cumulative']}
    return view


def render(view: dict, selected: int = 0, detail: bool = False, width: int = 100) -> list[str]:
    bar = '═' * min(width, 100)
    lines = [bar, f" ANTE DECK  case {view['case'] or '—'}  at {view['at']}  (read-only)", bar, ' CHAIN']
    for index, node in enumerate(view['nodes']):
        cursor = '▶' if index == selected else ' '
        claims = ''.join(MARK.get(status, '?') for _, status in node['claims'])
        verdict = f"  [{node['verdict']}]" if node['verdict'] else ''
        parents = f"  ← {', '.join(node['parents'])}" if node['parents'] else ''
        lines.append(f" {cursor} {node['command']:<10} {node['sha']}  {claims:<6}{verdict}{parents}")
        if detail and index == selected:
            for claim_id, status in node['claims']:
                lines.append(f"      {MARK.get(status, '?')} {claim_id}  {status}")
            for code in node['warnings']:
                lines.append(f"      ! {code}")
            lines.append(f"      next: {node['next']}")
    lines += ['', ' LOAD-BEARING CLAIMS (nodal)']
    for row in view['load_bearing']:
        flag = 'BLOCKING' if row['blocking'] else row['required_verification']
        lines.append(f"   {MARK.get(row['status'], '?')} {row['id']:<22} load {row['load']}  {flag}")
    if not view['load_bearing']:
        lines.append('   none')
    lines += ['', ' DEFENCE LAYERS (ice)']
    lines += [f"   {function:<8} {layer_id}" for function, layer_id in view['ice']['layers']]
    lines.append('   independent' if not view['ice']['problems'] else '   ' + '; '.join(view['ice']['problems']))
    lines += ['', ' SHADOW TRIALS']
    shadow = view['shadow']
    lines.append('   no shadow log' if shadow is None else
                 '   ' + (', '.join(f'{k}: {v}' for k, v in sorted(shadow.items())) or 'none') + '  (hidden until reconciled)')
    lines += ['', ' CUMULATIVE DRIFT']
    drift = view['drift']
    lines.append('   no ledger' if drift is None else f"   {drift['total']}/{drift['threshold']}  {drift['status']}")
    lines += [bar, ' ■ evidence ◆ hypothesis ○ assumption ◇ attributed intent    ↑↓ move  ⏎ detail  q quit']
    return lines


def _interactive(view: dict) -> None:   # pragma: no cover - needs a terminal
    import curses

    def loop(screen):
        curses.curs_set(0)
        curses.start_color()
        curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)
        screen.bkgd(' ', curses.color_pair(1))
        selected, detail = 0, False
        while True:
            screen.erase()
            height, width = screen.getmaxyx()
            for row, line in enumerate(render(view, selected, detail, width - 1)[:height - 1]):
                screen.addnstr(row, 0, line, width - 1, curses.color_pair(1))
            screen.refresh()
            key = screen.getch()
            if key in (ord('q'), 27):
                return
            if key in (curses.KEY_DOWN, ord('j')):
                selected = min(selected + 1, max(len(view['nodes']) - 1, 0))
            elif key in (curses.KEY_UP, ord('k')):
                selected = max(selected - 1, 0)
            elif key in (10, 13, curses.KEY_ENTER):
                detail = not detail

    curses.wrapper(loop)


def add_parser(sub) -> None:
    deck = sub.add_parser('deck', help='read-only terminal view of a case: chain, load, defences, shadows, drift')
    deck.add_argument('--artifacts', required=True)
    deck.add_argument('--ledger')
    deck.add_argument('--log')
    deck.add_argument('--state')
    deck.add_argument('--at')
    deck.add_argument('--plain', action='store_true')
    deck.add_argument('--json', action='store_true', help='print the view model as JSON')
    deck.set_defaults(handler=main)


def main(args) -> int:
    try:
        at = ante_time.iso(ante_time.parse(args.at, 'at')) if args.at else None
        view = model(args.artifacts, at, args.ledger, args.log, args.state)
    except (artifact.LineageError, ledger.LedgerError) as exc:
        print(f'LINEAGE {exc}', file=sys.stderr)
        return 3
    except (ValueError, OSError) as exc:
        print(f'INVALID {exc}', file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(view, indent=2, ensure_ascii=False, default=list))
    elif args.plain or not sys.stdout.isatty():
        print('\n'.join(render(view, detail=True)))
    else:
        _interactive(view)
    return 0
