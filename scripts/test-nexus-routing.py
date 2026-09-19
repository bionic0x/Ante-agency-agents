#!/usr/bin/env python3
"""Regression tests for vector coverage and execution-target routing.

The router's value is what it refuses: an unobserved model, an expired one, a
target that misses a declared requirement, and — above all — picking a winner
when nothing dominates. These tests are mostly about those refusals.
"""
import datetime as dt, importlib.util, json, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('routing', ROOT / 'scripts' / 'nexus-routing.py')
r = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r)

NOW = dt.datetime(2026, 9, 19, 12, 0, tzinfo=dt.timezone.utc)
failures = []


def check(cond, msg):
    if not cond:
        failures.append(msg)


def observation(model_id, provider='anthropic', depth='extended', tools='enforced',
                window=200000, out_cost=15, valid_days=7, **over):
    row = {'model_id': model_id, 'provider': provider,
           'observed_at': (NOW - dt.timedelta(days=1)).isoformat(),
           'valid_until': (NOW + dt.timedelta(days=valid_days)).isoformat(),
           'evidence_ref': 'ev', 'host': 'h', 'host_version': '1',
           'capabilities': {'reasoning_depth': depth, 'context_class': 'large',
                            'modality': ['text'], 'tool_use': tools,
                            'determinism_need': 'repeatable'},
           'context_window': window, 'declared_cost_per_1k_input': 1,
           'declared_cost_per_1k_output': out_cost}
    row.update(over)
    return row


def instance(tasks, **over):
    inst = {'tasks': tasks}
    inst.update(over)
    return inst


def task(tid='T1', level='strategic', vector='causal', **over):
    t = {'id': tid, 'level': level, 'vector': vector}
    t.update(over)
    return t


def routed(inst, rows):
    with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False) as fh:
        json.dump(rows, fh)
        path = fh.name
    try:
        return r.route(inst, path, at=NOW)
    finally:
        Path(path).unlink(missing_ok=True)


def main():
    # No observations at all is not "no constraint" — nothing is selectable.
    out = r.route(instance([task()]), None, at=NOW)
    check(out['status'] == 'MODELS_NOT_OBSERVED', f"empty registry must be MODELS_NOT_OBSERVED, got {out['status']}")
    check(out['tasks'][0]['selection'] == 'NO_OBSERVED_TARGET', 'a task with no target must say so')

    # An expired observation is dropped and named, never used.
    out = routed(instance([task()]), [observation('stale', valid_days=-1)])
    check(out['tasks'][0]['selection'] == 'NO_OBSERVED_TARGET', 'an expired model must not be selectable')
    check(any('EXPIRED' in n for n in out['observation_notes']), 'expiry must be reported')

    # An incomplete observation is NOT_OBSERVED, with the missing field named.
    bad = observation('partial'); bad['evidence_ref'] = ''
    out = routed(instance([task()]), [bad])
    check(any('evidence_ref' in n for n in out['observation_notes']),
          'the missing observation field must be named')

    # A future-dated observation is refused.
    future = observation('future')
    future['observed_at'] = (NOW + dt.timedelta(days=1)).isoformat()
    out = routed(instance([task()]), [future])
    check(any('future-dated' in n for n in out['observation_notes']), 'future-dated must be refused')

    # Capability shortfall excludes with a specific reason, never a lower score.
    t = task(execution={'requires': {'reasoning_depth': 'extended'}})
    out = routed(instance([t]), [observation('shallow-one', depth='standard')])
    entry = out['tasks'][0]
    check(entry['selection'] == 'NO_ADMISSIBLE_TARGET', 'a shortfall must exclude, not rank')
    check('reasoning_depth' in entry['excluded'][0]['reasons'][0], 'the reason must name the requirement')

    # Ordered tiers: a higher tier satisfies a lower requirement.
    t = task(execution={'requires': {'reasoning_depth': 'standard'}})
    out = routed(instance([t]), [observation('deep', depth='extended')])
    check(out['tasks'][0]['selection'] == 'ADMISSIBLE_SET', 'extended must satisfy a standard requirement')

    # A pinned provider excludes the others by instance decision.
    t = task(execution={'provider': 'openai'})
    out = routed(instance([t]), [observation('a', provider='anthropic'), observation('b', provider='openai')])
    check([x['model_id'] for x in out['tasks'][0]['admissible']] == ['b'], 'a pinned provider must bind')

    # The cost ceiling is applied in the observation's own unit, and only when stated.
    t = task(cost_limit=3)
    out = routed(instance([t]), [observation('pricey', out_cost=15)])
    check(out['tasks'][0]['selection'] == 'ADMISSIBLE_SET',
          "a task budget must not be compared against a per-1k price")
    t = task(execution={'max_cost_per_1k_output': 3})
    out = routed(instance([t]), [observation('pricey', out_cost=15)])
    check(out['tasks'][0]['selection'] == 'NO_ADMISSIBLE_TARGET', 'a stated ceiling must exclude')

    # No winner when nothing dominates: cheaper-but-smaller vs pricier-but-roomier.
    out = routed(instance([task()]),
                 [observation('roomy', window=200000, out_cost=15),
                  observation('cheap', provider='openai', window=100000, out_cost=5)])
    entry = out['tasks'][0]
    check(sorted(entry['undominated']) == ['cheap', 'roomy'],
          f"neither should dominate, got {entry['undominated']}")
    check(entry['dominance'] == [], 'no dominance edge when the trade-off is real')
    check(not any(k in entry for k in ('score', 'rank', 'best', 'winner')),
          'the router must not rank targets')

    # Dominance only when one target is better on both and strictly better on one.
    out = routed(instance([task()]),
                 [observation('worse', window=100000, out_cost=15),
                  observation('better', provider='openai', window=200000, out_cost=5)])
    entry = out['tasks'][0]
    check(entry['undominated'] == ['better'], f"clear dominance expected, got {entry['undominated']}")
    check(entry['dominance'][0]['measured'] is False, 'declared dominance is never measured superiority')

    # An unregistered vector is refused by the router, not silently routed.
    try:
        r.route(instance([task(vector='made-up')]), None, at=NOW)
        failures.append('an unregistered vector must be refused')
    except ValueError as exc:
        check('unknown vector' in str(exc), f'the refusal must name the vector, got {exc}')

    # Coverage names gaps instead of assuming them satisfied.
    cov = r.coverage(instance([task(vector='causal')], budget={'cost_limit': 1}))
    check('termination' in cov['missing'] and 'resource' in cov['missing'],
          f"required vectors must be reported missing, got {cov['missing']}")
    check(cov['kinds']['causal'] == 'sequential', 'the contribution kind must come from the registry')

    # The shipped example instance must route without error and carry known vectors.
    example = json.loads((ROOT / 'examples/nexus/strategic-decision.instance.json').read_text())
    cov = r.coverage(example)
    check(cov['unknown_vectors'] == [], f"example uses unregistered vectors: {cov['unknown_vectors']}")

    # The checked-in provider registry declares providers and zero verified models.
    providers = json.loads((ROOT / 'strategy/providers.json').read_text())
    check(providers['status'] == 'MODELS_NOT_OBSERVED', 'the baseline must claim no observed models')
    check(sum(len(p['models']) for p in providers['providers'].values()) == 0,
          'shipping a model catalog written from memory is exactly what this registry refuses')

    for f in failures:
        print(f'  FAIL {f}')
    print(f'\nResults: {"FAILED" if failures else "PASSED"} ({len(failures)} failures)')
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())
