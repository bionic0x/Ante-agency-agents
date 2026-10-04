#!/usr/bin/env python3
"""nexus-routing.py — select execution targets by level, vector and factor.

NEXUS already carries two of the three dimensions this router needs. Every task
declares a `level` validated against the five canonical planes, and
`option_analysis` compares factors without weighted scores. The third dimension
was missing in two places: `vector` was free text that nothing checked, and the
engine had no notion of an execution target at all — zero provider or model
references in 430 lines, because it plans and replays but never executes.

This router closes both. It answers one question per task: given the plane the
task belongs to, the vector it contributes along, and the requirements it
declares, which observed execution targets are admissible?

What it refuses to do:

  - It never ranks providers. Admissibility first: a target that cannot meet a
    declared requirement is excluded, not scored lower. Then the undominated set
    and the dominance edges, with each edge's evidence basis — the same
    discipline nexus-options.py already applies to options.
  - It never selects an unobserved model. strategy/providers.json ships five
    providers and zero verified models on purpose: a catalog written from memory
    is stale the week it merges. A model becomes selectable when an observation
    supplies its id, host, limits and valid_until, and expires when that passes.
  - It never treats provider diversity as a benefit. Spreading work across
    vendors is justified by a requirement no single observed target meets, or by
    a measured difference under the evaluation protocol. Otherwise it is cost and
    maintenance with no evidenced return.

Usage:
  nexus-routing.py coverage INSTANCE            # which vectors the instance carries
  nexus-routing.py route INSTANCE [--observations FILE] [--at ISO8601]
"""
import argparse, datetime as dt, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VOCAB = json.loads((ROOT / 'strategy/contracts.json').read_text(encoding='utf-8'))
VECTORS = json.loads((ROOT / 'strategy/vectors.json').read_text(encoding='utf-8'))
PROVIDERS = json.loads((ROOT / 'strategy/providers.json').read_text(encoding='utf-8'))

TIERS = PROVIDERS['capability_tiers']
ORDERED_TIERS = {'reasoning_depth': TIERS['reasoning_depth'],
                 'context_class': TIERS['context_class'],
                 'tool_use': TIERS['tool_use']}


def parse_time(value, field):
    try:
        parsed = dt.datetime.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f'{field} is not ISO-8601: {value!r}') from exc
    if parsed.tzinfo is None:
        raise ValueError(f'{field} must carry a timezone offset')
    return parsed


def load_observations(path, at):
    """Model observations. Absent, malformed or expired -> the model is not selectable."""
    if path is None:
        return [], ['no observation file supplied']
    try:
        raw = Path(path).read_text(encoding='utf-8')
    except OSError as exc:
        return [], [f'observation file unreadable — NOT_OBSERVED: {exc}']
    if not raw.strip():
        return [], ['observation file is empty — NOT_OBSERVED']
    try:
        rows = json.loads(raw)
    except json.JSONDecodeError as exc:
        return [], [f'observation file is invalid JSON — NOT_OBSERVED: {exc}']
    if not isinstance(rows, list):
        return [], ['observation file must contain a JSON array — NOT_OBSERVED']
    required = PROVIDERS['model_observation_contract']['required']
    live, notes = [], []
    for index, row in enumerate(rows):
        where = f'observations[{index}]'
        if not isinstance(row, dict):
            notes.append(f'{where}: NOT_OBSERVED — entry must be an object')
            continue
        missing = [f for f in required if f not in row or row[f] in (None, '', [])]
        if missing:
            notes.append(f'{where}: NOT_OBSERVED — missing {sorted(missing)}')
            continue
        if row['provider'] not in PROVIDERS['providers']:
            notes.append(f"{where}: unknown provider {row['provider']!r}")
            continue
        observed_at = parse_time(row['observed_at'], f'{where}.observed_at')
        valid_until = parse_time(row['valid_until'], f'{where}.valid_until')
        if observed_at > at:
            notes.append(f"{where}: future-dated observation for {row['model_id']}")
            continue
        if valid_until <= at:
            notes.append(f"{where}: EXPIRED — {row['model_id']} valid_until {row['valid_until']}")
            continue
        live.append(row)
    return live, notes


def meets(capabilities, requirement, key):
    """Ordered tiers compare by rank; unordered ones must match exactly."""
    have, want = capabilities.get(key), requirement[key]
    if have is None:
        return False
    if key in ORDERED_TIERS:
        order = ORDERED_TIERS[key]
        if have not in order or want not in order:
            return False
        return order.index(have) >= order.index(want)
    if key == 'modality':
        return set(want if isinstance(want, list) else [want]).issubset(set(have if isinstance(have, list) else [have]))
    return have == want


def admissible(task, targets):
    """Split targets into admissible and excluded, with the reason for each exclusion."""
    requirement = task.get('execution', {}).get('requires', {})
    pinned = task.get('execution', {}).get('provider')
    ok, excluded = [], []
    for target in targets:
        reasons = []
        if pinned and target['provider'] != pinned:
            reasons.append(f"instance pins provider {pinned!r}")
        for key in requirement:
            if key not in TIERS:
                reasons.append(f'unknown requirement {key!r}')
            elif not meets(target['capabilities'], requirement, key):
                reasons.append(f"{key}: needs {requirement[key]!r}, target declares "
                               f"{target['capabilities'].get(key)!r}")
        # A task's `cost_limit` is a budget allowance in the instance's own unit, not a
        # price per 1k tokens. Comparing the two excludes every target for a unit
        # mismatch, so the ceiling is only applied when the task states it in the
        # observation's own unit.
        limit = task.get('execution', {}).get('max_cost_per_1k_output')
        declared = target.get('declared_cost_per_1k_output')
        if limit is not None and declared is not None and declared > limit:
            reasons.append(f'declared output cost {declared} exceeds the task ceiling {limit} '
                           'per 1k output tokens')
        (excluded if reasons else ok).append(
            {'model_id': target['model_id'], 'provider': target['provider'],
             **({'reasons': reasons} if reasons else {})})
    return ok, excluded


def dominance(targets):
    """Undominated set on declared cost and context. No weights, no ranking."""
    by_id = {t['model_id']: t for t in targets}
    edges, dominated = [], set()
    for a in targets:
        for b in targets:
            if a is b:
                continue
            cheaper = a['declared_cost_per_1k_output'] <= b['declared_cost_per_1k_output']
            roomier = a['context_window'] >= b['context_window']
            strict = (a['declared_cost_per_1k_output'] < b['declared_cost_per_1k_output']
                      or a['context_window'] > b['context_window'])
            if cheaper and roomier and strict:
                dominated.add(b['model_id'])
                edges.append({'dominates': a['model_id'], 'over': b['model_id'],
                              'basis': 'declared cost and context only',
                              'measured': False})
    return {'undominated': sorted(t['model_id'] for t in by_id.values()
                                  if t['model_id'] not in dominated),
            'dominance': edges}


def coverage(instance):
    """Which registered vectors the instance carries, and which required ones it lacks."""
    present = sorted({t['vector'] for t in instance.get('tasks', [])})
    unknown = [v for v in present if v not in VECTORS['vectors']]
    rules = VECTORS['coverage_rules']
    required = list(rules['required_always'])
    if instance.get('budget'):
        required += rules['required_when_budgeted']
    if any(t.get('acceptance_predicates') for t in instance.get('tasks', [])):
        required += rules['required_when_predicates_declared']
    if instance.get('contested'):
        required += rules['required_when_contested']
    if instance.get('affects_third_parties'):
        required += rules['required_when_affects_third_parties']
    required = sorted(set(required))
    return {'present': present, 'unknown_vectors': unknown,
            'required': required, 'missing': sorted(set(required) - set(present)),
            'kinds': {v: VECTORS['vectors'][v]['contribution'] for v in present
                      if v in VECTORS['vectors']},
            'note': 'A missing vector is a gap in the instance, never a satisfied requirement.'}


def route(instance, observations_path=None, at=None):
    at = at or dt.datetime.now(dt.timezone.utc)
    targets, notes = load_observations(observations_path, at)
    rows = []
    for task in instance.get('tasks', []):
        if task['level'] not in VOCAB['levels']:
            raise ValueError(f"task {task['id']}: unknown level {task['level']!r}")
        if task['vector'] not in VECTORS['vectors']:
            raise ValueError(f"task {task['id']}: unknown vector {task['vector']!r}; "
                             f"registered vectors are {sorted(VECTORS['vectors'])}")
        ok, excluded = admissible(task, targets)
        entry = {'task_id': task['id'], 'level': task['level'], 'vector': task['vector'],
                 'contribution': VECTORS['vectors'][task['vector']]['contribution'],
                 'characteristic_failure': VECTORS['vectors'][task['vector']]['failure_mode'],
                 'admissible': ok, 'excluded': excluded}
        if not targets:
            entry['selection'] = 'NO_OBSERVED_TARGET'
        elif not ok:
            entry['selection'] = 'NO_ADMISSIBLE_TARGET'
        else:
            entry['selection'] = 'ADMISSIBLE_SET'
            entry.update(dominance([t for t in targets
                                    if t['model_id'] in {o['model_id'] for o in ok}]))
        rows.append(entry)
    return {'status': 'ROUTED' if targets else 'MODELS_NOT_OBSERVED',
            'coverage': coverage(instance), 'tasks': rows, 'observation_notes': notes,
            'limitations': [
                'Admissibility only. No ranking, no weighted score, no claim that one '
                'provider performs better.',
                'Dominance uses declared cost and context from the operator\'s own '
                'observations; it is not measured performance.',
                'Provider diversity is not a benefit in itself: justify it by a requirement '
                'no single observed target meets, or by a measured difference.',
                'An unobserved or expired model is not selectable; that is a gap to close, '
                'not a reason to fall back to a guess.']}


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('command', choices=['route', 'coverage'])
    ap.add_argument('instance')
    ap.add_argument('--observations')
    ap.add_argument('--at')
    args = ap.parse_args()
    try:
        instance = json.loads(Path(args.instance).read_text(encoding='utf-8'))
        at = parse_time(args.at, '--at') if args.at else None
        result = (coverage(instance) if args.command == 'coverage'
                  else route(instance, args.observations, at))
        print(json.dumps(result, indent=2))
        return 0
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print(f'ERROR {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
