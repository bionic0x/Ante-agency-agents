"""nexus-brief.py — the owner's decision brief for a NEXUS instance (Overdrive, Phase 3).

The engine refuses bad closures; it does not tell the owner, in one place, what
is waiting on them and why the instance stands where it does. This brief does,
from the instance and its event log alone. It decides nothing and runs nothing.

    nexus-brief.py INSTANCE_JSON --events EVENTS_JSONL --at ISO_TIME [--json]

Sections, in the order an owner needs them:

  waiting on you   unresolved assertion conflicts, open dissent, holds, closed
                   challenger gates, claims under review, running tasks
  closure          whether `close` and `terminate SUFFICIENT_RESULT` would be
                   admitted now, asked of the engine itself with a probe event
                   that is never recorded
  results          each task's status, agent, model, cost, evidence and asserts
  independence     shared models, shared source roots, plan-linter warnings
  budget           spent, reserve, releases, uncommitted
  record           every owner and reviewer event with its stated reason: the
                   trail that answers "why was this decided"

The Phase 3 kill criterion is an owner who can no longer reconstruct a decision
from the brief and the event history; the record section exists for that test.
"""
from __future__ import annotations

import argparse
import copy
import importlib.util
import json
from pathlib import Path
import runpy
import sys

from ante.paths import ROOT
ENGINE = runpy.run_path(str(ROOT / 'scripts/nexus-instance.py'), run_name='nexus_engine_for_brief')
_spec = importlib.util.spec_from_file_location('lint_for_brief', ROOT / 'scripts/nexus-lint.py')
LINT = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(LINT)

RECORDED = ('decision', 'hold', 'resolve_hold', 'dissent', 'dissent_response', 'resolve_conflict',
            'override_verdict', 'release_reserve', 'claim_revision', 'rebind_claims', 'terminate', 'close')
REASON_FIELDS = ('reason', 'response', 'objection', 'disposition', 'state', 'key', 'value', 'amount',
                 'contingency', 'outcome', 'risk_owner', 'expires')
PROBE_CLOSURE = {k: 'brief probe' for k in ('achieved', 'outstanding', 'accountable', 'on_breach',
                                             'conservation_resources')}


def probe(instance, state, event):
    """Ask the engine whether an owner event would be admitted now, without recording it."""
    try:
        ENGINE['apply'](instance, copy.deepcopy(state), event)
        return {'admitted': True, 'reason': None}
    except (ValueError, KeyError, TypeError) as exc:
        return {'admitted': False, 'reason': str(exc)}


def brief(instance, events, at):
    state = ENGINE['replay'](instance, events)
    plan = ENGINE['plan'](instance, state, at)
    tasks = {t['id']: t for t in instance['tasks']}
    owner = instance['mandate']['owner']
    rows = {r['task_id']: r for r in plan['tasks']}

    waiting = []
    for key, conflict in plan['assertion_conflicts'].items():
        if not conflict['resolved']:
            waiting.append({'kind': 'ASSERTION_CONFLICT', 'key': key, 'next_event': 'resolve_conflict',
                            'detail': {tid: {'agent': tasks[tid]['agent'], 'value': value}
                                       for tid, value in sorted(conflict['values'].items())}})
    by_id = {d['id']: d for d in state['dissent']}
    for did in state['open_dissent']:
        d = by_id[did]
        waiting.append({'kind': 'OPEN_DISSENT', 'id': did, 'next_event': 'dissent_response',
                        'detail': {'issuer': d['issuer'], 'objection': d['objection'],
                                   'risk_owner': d['risk_owner'], 'evidence_refs': d['evidence_refs']}})
    for cid, condition in sorted(state['conditions'].items()):
        waiting.append({'kind': 'HOLD', 'id': cid, 'next_event': 'resolve_hold',
                        'detail': {k: condition.get(k) for k in ('classification', 'task_ids', 'reason')}})
    for pid, gate in sorted(plan['challenger_gates'].items()):
        if not gate['open']:
            waiting.append({'kind': 'CHALLENGER_GATE', 'id': pid, 'next_event':
                            'override_verdict' if gate['status'] == 'VETO' else 'wait for the challenger',
                            'detail': {'status': gate['status'], 'challenger': gate['challenger'],
                                       'verdict': gate['verdict']}})
    for cid in state['review_required']:
        waiting.append({'kind': 'CLAIM_REVIEW', 'id': cid, 'next_event': 'claim_revision or rebind_claims',
                        'detail': {'statement': state['claims'][cid]['statement']}})
    for tid, row in rows.items():
        if row['status'] == 'RUNNING':
            waiting.append({'kind': 'RESULT_PENDING', 'id': tid, 'next_event': 'finish (accept or reject)',
                            'detail': {'agent': tasks[tid]['agent']}})

    probe_base = {'at': at, 'issuer': owner, 'evidence_refs': ['brief-probe'], 'closure': PROBE_CLOSURE}
    closure = {'closed': {'outcome': state.get('termination_outcome', 'SUCCESS'),
                          'closure': state.get('closure')}} if state['closed'] else {
        'close': probe(instance, state, {**probe_base, 'id': 'brief-probe-close', 'type': 'close'}),
        'terminate_sufficient_result': probe(instance, state, {
            **probe_base, 'id': 'brief-probe-terminate', 'type': 'terminate', 'outcome': 'SUFFICIENT_RESULT',
            'reason': 'brief probe'}),
    }

    results = []
    for tid, task in tasks.items():
        p = state['tasks'][tid]
        results.append({'task': tid, 'agent': task['agent'], 'status': p['status'], 'attempts': p['attempts'],
                        'spent': p['spent'], 'model': state['models'].get(tid),
                        'evidence_refs': p.get('evidence_refs', []), 'asserts': state['assertions'].get(tid, {}),
                        'inputs_stale': p['inputs_stale'], 'blockers': rows[tid]['blockers']})

    lint = LINT.lint(instance, ENGINE)
    independence = {'shared_model_tasks': plan['shared_model_tasks'],
                    'shared_source_roots': plan['shared_source_roots'],
                    'plan_warnings': [f for f in lint.get('findings', [])
                                      if f['code'] in ('SINGLE_SOURCE_KEY', 'DEPENDENT_ASSERTERS',
                                                       'SAME_AGENT_ASSERTERS')]}
    record = [{'at': e['at'], 'type': e['type'], 'issuer': e['issuer'],
               **({'task': e['task_id']} if e.get('task_id') else {}),
               **{k: e[k] for k in REASON_FIELDS if k in e},
               **({'evidence_refs': e['evidence_refs']} if e.get('evidence_refs') else {})}
              for e in events if e.get('type') in RECORDED]
    accepted = sum(1 for e in events if e.get('type') == 'finish' and e.get('accepted') is True)
    rejected = sum(1 for e in events if e.get('type') == 'finish' and e.get('accepted') is False)
    return {'instance_id': instance['id'], 'at': at,
            'objective': {k: instance['objective'][k] for k in ('purpose', 'non_object', 'success_condition')},
            'decision_state': state['decision_state'], 'closed': state['closed'],
            'owner': owner, 'reviewers': instance['mandate']['reviewers'],
            'waiting_on_owner': waiting, 'closure': closure, 'results': results,
            'acceptances': {'accepted': accepted, 'rejected': rejected},
            'independence': independence,
            'budget': {k: plan[k] for k in ('spent', 'reserve', 'reserve_released', 'uncommitted_cost')},
            'record': record,
            'note': 'Derived from the instance and event log only; the brief decides nothing.'}


def _value(v):
    return json.dumps(v, ensure_ascii=False) if not isinstance(v, str) else v


def markdown(b):
    out = [f"# Decision brief: {b['instance_id']}", '',
           f"As of {b['at']}. Decision state **{b['decision_state']}**"
           + (' (closed)' if b['closed'] else '') + f". Owner `{b['owner']}`.", '',
           f"**Purpose.** {b['objective']['purpose']}  ",
           f"**Not the goal.** {b['objective']['non_object']}  ",
           f"**Success means.** {b['objective']['success_condition']}", '',
           f"## Waiting on you ({len(b['waiting_on_owner'])})", '']
    if not b['waiting_on_owner']:
        out.append('Nothing is waiting on the owner.')
    for item in b['waiting_on_owner']:
        label = item.get('key') or item.get('id')
        out.append(f"- **{item['kind']}** `{label}` — next: `{item['next_event']}`")
        for k, v in item['detail'].items():
            out.append(f"  - {k}: {_value(v)}")
    out += ['', '## Closure', '']
    if 'closed' in b['closure']:
        done = b['closure']['closed']
        out.append(f"Closed with outcome **{done['outcome']}**.")
        for k, v in (done['closure'] or {}).items():
            out.append(f"- {k}: {_value(v)}")
    else:
        for name, verdict in b['closure'].items():
            out.append(f"- `{name}`: " + ('admitted now' if verdict['admitted'] else f"refused — {verdict['reason']}"))
    out += ['', '## Results', '', '| Task | Agent | Status | Model | Spent | Asserts | Blockers |',
            '|---|---|---|---|---|---|---|']
    for r in b['results']:
        out.append(f"| {r['task']} | {r['agent']} | {r['status']} | {r['model'] or '—'} | {r['spent']} | "
                   f"{_value(r['asserts']) if r['asserts'] else '—'} | {', '.join(r['blockers']) or '—'} |")
    out.append('')
    out.append(f"Acceptances: {b['acceptances']['accepted']} accepted, {b['acceptances']['rejected']} rejected.")
    ind = b['independence']
    out += ['', '## Independence', '']
    if not (ind['shared_model_tasks'] or ind['shared_source_roots'] or ind['plan_warnings']):
        out.append('No shared model, shared source root or assertion-design warning.')
    for model, ids in ind['shared_model_tasks'].items():
        out.append(f"- Tasks {', '.join(ids)} ran on the same model `{model}`; their agreement is not independent.")
    for root, claims in ind['shared_source_roots'].items():
        out.append(f"- Claims {', '.join(claims)} share source root `{root}`.")
    for f in ind['plan_warnings']:
        out.append(f"- {f['code']}: {f['message']}")
    bud = b['budget']
    out += ['', '## Budget', '', f"Spent {bud['spent']}; reserve {bud['reserve']} "
            f"(released {bud['reserve_released']}); uncommitted {bud['uncommitted_cost']}.", '',
            '## Record', '']
    if not b['record']:
        out.append('No owner or reviewer events yet.')
    for e in b['record']:
        fields = '; '.join(f"{k}: {_value(v)}" for k, v in e.items() if k not in ('at', 'type', 'issuer'))
        out.append(f"- {e['at']} `{e['type']}` by `{e['issuer']}`" + (f" — {fields}" if fields else ''))
    out += ['', f"_{b['note']}_"]
    return '\n'.join(out) + '\n'


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('instance')
    ap.add_argument('--events', required=True)
    ap.add_argument('--at', required=True, help='ISO time the brief is computed for (expiry checks)')
    ap.add_argument('--json', action='store_true')
    args = ap.parse_args(argv)
    try:
        instance = json.loads(Path(args.instance).read_text(encoding='utf-8'))
        lines = Path(args.events).read_text(encoding='utf-8').splitlines() if Path(args.events).exists() else []
        events = [json.loads(line) for line in lines if line.strip()]
        result = brief(instance, events, args.at)
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(f'ERROR {exc}', file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, ensure_ascii=False) if args.json else markdown(result), end='')
    return 0


if __name__ == '__main__':
    sys.exit(main())
