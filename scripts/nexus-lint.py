#!/usr/bin/env python3
"""nexus-lint.py — check a NEXUS instance's plan before the owner adopts it (Overdrive, Phase 2).

The engine refuses an invalid instance. A valid instance can still be a poor
plan: work that cannot run in parallel because two tasks claim one resource, task
limits that can only be met by eating into the reserve, or a shared assertion key
that no independent task can contradict, so a disagreement could never surface.

    nexus-lint.py INSTANCE_JSON [--strict]

Reports the plan's shape (critical path, depth, widest level) and findings:

  ERROR  INVALID_INSTANCE       the engine refuses the instance
  WARN   SERIALIZED_RESOURCE    independent tasks share a resource scope; the
                                parallel schedule runs them one after another
  WARN   BUDGET_HEADROOM        the sum of task cost limits exceeds the ordinary
                                budget (cost limit minus reserve)
  WARN   SINGLE_SOURCE_KEY      only one task asserts a key; no conflict can surface
  WARN   DEPENDENT_ASSERTERS    tasks asserting a key depend on one another; the
                                later one sees the earlier answer
  WARN   SAME_AGENT_ASSERTERS   the same agent asserts a key twice
  WARN   MULTIPLE_SINKS         more than one final task; the deliverable is a
                                concatenation, not a synthesis

Exit status 1 on ERROR, or on WARN with --strict. The linter reads the plan only;
it does not run, accept or judge anything.
"""
from __future__ import annotations

import argparse
import itertools
import json
from pathlib import Path
import runpy
import sys

ROOT = Path(__file__).resolve().parents[1]


def _engine():
    return runpy.run_path(str(ROOT / 'scripts/nexus-instance.py'), run_name='nexus_engine_for_lint')


def ancestors(tasks, tid, seen=None):
    seen = set() if seen is None else seen
    for parent in tasks[tid].get('depends_on', []):
        if parent not in seen:
            seen.add(parent)
            ancestors(tasks, parent, seen)
    return seen


def shape(tasks):
    """Depth of each task (longest chain to it), the critical path and the widest level."""
    depth = {}

    def visit(tid):
        if tid not in depth:
            parents = tasks[tid].get('depends_on', [])
            depth[tid] = 1 + max((visit(p) for p in parents), default=0)
        return depth[tid]

    for tid in tasks:
        visit(tid)
    end = max(tasks, key=lambda t: (depth[t], t))
    path = [end]
    while tasks[path[-1]].get('depends_on'):
        path.append(max(tasks[path[-1]]['depends_on'], key=lambda p: (depth[p], p)))
    levels = {}
    for tid, d in depth.items():
        levels.setdefault(d, []).append(tid)
    consumed = {p for t in tasks.values() for p in t.get('depends_on', [])}
    return {'tasks': len(tasks), 'depth': depth[end], 'critical_path': list(reversed(path)),
            'levels': {str(d): sorted(ids) for d, ids in sorted(levels.items())},
            'widest_level': max(len(ids) for ids in levels.values()),
            'sinks': sorted(t for t in tasks if t not in consumed)}


def lint(instance, engine=None):
    engine = engine or _engine()
    findings = []
    try:
        engine['validate'](instance)
    except (ValueError, KeyError, TypeError) as exc:
        return {'instance_id': instance.get('id') if isinstance(instance, dict) else None, 'status': 'ERRORS',
                'findings': [{'severity': 'ERROR', 'code': 'INVALID_INSTANCE', 'tasks': [], 'message': str(exc)}]}
    tasks = {t['id']: t for t in instance['tasks']}
    plan_shape = shape(tasks)

    def warn(code, ids, message):
        findings.append({'severity': 'WARN', 'code': code, 'tasks': sorted(ids), 'message': message})

    related = lambda a, b: a in ancestors(tasks, b) or b in ancestors(tasks, a)
    for a, b in itertools.combinations(sorted(tasks), 2):
        shared = set(tasks[a]['resource_scope']) & set(tasks[b]['resource_scope'])
        if shared and not related(a, b):
            warn('SERIALIZED_RESOURCE', [a, b], f'{a} and {b} are independent but share {sorted(shared)}; '
                 'the engine admits one at a time, so the parallel schedule cannot overlap them')
    budget = instance['budget']
    ordinary = budget['cost_limit'] - budget['reserve']
    limits = sum(t['cost_limit'] for t in tasks.values())
    if limits > ordinary:
        warn('BUDGET_HEADROOM', list(tasks), f'task cost limits sum to {limits}, above the ordinary budget of '
             f'{ordinary} ({budget["cost_limit"]} minus reserve {budget["reserve"]}); retries can only be paid '
             'by an owner releasing reserve')
    keys = {}
    for tid, task in tasks.items():
        for key in task.get('asserts', []):
            keys.setdefault(key, []).append(tid)
    for key, ids in sorted(keys.items()):
        if len(ids) == 1:
            warn('SINGLE_SOURCE_KEY', ids, f'only {ids[0]} asserts {key!r}; no independent result can contradict it')
            continue
        for a, b in itertools.combinations(sorted(ids), 2):
            if related(a, b):
                warn('DEPENDENT_ASSERTERS', [a, b], f'{a} and {b} both assert {key!r} but one depends on the other; '
                     'their agreement is not independent')
            if tasks[a]['agent'] == tasks[b]['agent']:
                warn('SAME_AGENT_ASSERTERS', [a, b], f"{a} and {b} assert {key!r} with the same agent "
                     f"{tasks[a]['agent']!r}; agreement may be one profile agreeing with itself")
    if len(plan_shape['sinks']) > 1:
        warn('MULTIPLE_SINKS', plan_shape['sinks'], 'more than one final task; the deliverable concatenates them '
             'instead of integrating them')
    return {'instance_id': instance['id'], 'status': 'WARNINGS' if findings else 'CLEAN',
            'shape': plan_shape, 'findings': findings}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('instance')
    ap.add_argument('--strict', action='store_true', help='exit 1 on warnings too')
    args = ap.parse_args(argv)
    try:
        instance = json.loads(Path(args.instance).read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError) as exc:
        print(f'ERROR {exc}', file=sys.stderr)
        return 1
    result = lint(instance)
    print(json.dumps(result, indent=2))
    if result['status'] == 'ERRORS' or (args.strict and result['status'] == 'WARNINGS'):
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
