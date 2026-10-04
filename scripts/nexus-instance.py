#!/usr/bin/env python3
"""Deterministic NEXUS planner and event replay. Never executes a tool or agent.

All authority/evidence records are supplied assertions. The host must authenticate
and enforce them before live action. Replay validates contracts, not truth.
"""
from __future__ import annotations
import argparse
import copy
import datetime as dt
import hashlib
import json
import math
import os
from pathlib import Path
import runpy
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
VOCAB = json.loads((ROOT / 'strategy/contracts.json').read_text())
# `level` was validated against the five canonical planes from the start; `vector`
# was accepted as free text, so the multi-vector dimension was a convention nothing
# checked. strategy/vectors.json closes it.
VECTORS = json.loads((ROOT / 'strategy/vectors.json').read_text())['vectors']


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def text(value, field):
    require(isinstance(value, str) and bool(value.strip()), f'{field}: non-empty text required')
    return value


def strings(value, field, nonempty=False):
    require(isinstance(value, list) and all(isinstance(x, str) and x.strip() for x in value), f'{field}: string array required')
    require(len(value) == len(set(value)), f'{field}: duplicate values')
    require(not nonempty or bool(value), f'{field}: empty array')
    return value


def number(value, field):
    require(type(value) in (int, float) and math.isfinite(value) and value >= 0, f'{field}: finite nonnegative number required')
    return value


def when(value):
    require(isinstance(value, str), 'ISO timestamp text required')
    try:
        date = dt.datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError:
        raise ValueError('ISO timestamp required')
    require(date.tzinfo is not None, 'timestamp needs timezone')
    return date


def indexed(items, label):
    require(isinstance(items, list), f'{label}: array required')
    result = {}
    for item in items:
        require(isinstance(item, dict), f'{label}: object required')
        key = text(item.get('id'), f'{label}.id')
        require(key not in result, f'{label}: duplicate id {key}')
        result[key] = item
    return result


def acyclic(nodes, field):
    active, done = set(), set()
    def visit(key):
        require(key in nodes, f'unknown dependency {key}')
        require(key not in active, f'cycle at {key}')
        if key in done:
            return
        active.add(key)
        for parent in strings(nodes[key].get(field, []), field):
            visit(parent)
        active.remove(key)
        done.add(key)
    for key in nodes:
        visit(key)


def validate_claim(claim):
    require(claim.get('status') in VOCAB['epistemic_states'], 'unknown epistemic state')
    require(type(claim.get('revision')) is int and claim['revision'] > 0, 'claim revision must be positive integer')
    for field in ('statement', 'scope'):
        text(claim.get(field), field)
    strings(claim.get('source_refs'), 'source_refs')
    strings(claim.get('source_roots'), 'source_roots')
    strings(claim.get('depends_on', []), 'claim dependencies')
    if claim['status'] == 'EVIDENCE':
        require(bool(claim['source_refs']) and bool(claim['source_roots']), 'EVIDENCE needs source and lineage')
    when(claim['expires'])


def claim_ancestry(claims, cid):
    """Include every premise: a shared conclusion cannot erase a scoped source."""
    found, pending = set(), [cid]
    while pending:
        current = pending.pop()
        if current not in found:
            found.add(current)
            pending.extend(claims[current].get('depends_on', []))
    return found


def expired(instance, at):
    return when(at) >= min(when(instance['mandate']['expires']), when(instance['budget']['deadline']))


def validate(instance):
    require(isinstance(instance, dict) and instance.get('schema_version') == 1, 'instance schema_version must be 1')
    text(instance.get('id'), 'id')
    _, agents, runbooks = runpy.run_path(str(ROOT / 'scripts/build-catalog.py'))['collect']()
    books = {r['slug']: r for r in runbooks}
    require(instance.get('runbook_ref') in books, 'unknown runbook')
    roster = {a for g in books[instance['runbook_ref']]['roster'] for a in g['agents']}
    catalog = {a['slug'] for a in agents}
    require(instance.get('doctrine_sha256') == hashlib.sha256((ROOT / 'strategy/GENERAL-STRATEGY-DOCTRINE.md').read_bytes()).hexdigest(), 'doctrine changed; review/rebase instance')
    mandate = instance['mandate']
    for field in ('owner', 'authority_ref', 'scope'):
        text(mandate.get(field), f'mandate.{field}')
    require(mandate['scope'] == 'offline-analysis', 'this runner supports offline-analysis only')
    when(mandate['expires'])
    strings(mandate['reviewers'], 'reviewers', True)
    objective = instance['objective']
    for field in ('id', 'purpose', 'non_object', 'success_condition'):
        text(objective.get(field), f'objective.{field}')
    require(objective['purpose'] != objective['non_object'], 'purpose equals non-object')
    strings(objective['constraints'], 'constraints', True)
    require(instance.get('decision_state') in VOCAB['decision_states'], 'unknown decision state')
    budget = instance['budget']
    text(budget.get('unit'), 'budget.unit')
    number(budget['cost_limit'], 'cost_limit'); number(budget['reserve'], 'reserve')
    require(budget['reserve'] <= budget['cost_limit'], 'reserve exceeds total budget')
    when(budget['deadline'])
    claims = indexed(instance['claims'], 'claims')
    for claim in claims.values():
        validate_claim(claim)
    acyclic(claims, 'depends_on')
    tasks = indexed(instance['tasks'], 'tasks')
    require(bool(tasks), 'instance requires at least one task')
    for task in tasks.values():
        require(task['agent'] in roster & catalog, 'task agent must belong to canonical runbook roster')
        require(task['level'] in VOCAB['levels'], 'unknown task level')
        text(task['vector'], 'vector')
        require(task['vector'] in VECTORS, 'unknown task vector')
        require(task['purpose_ref'] == objective['id'], 'orphan task purpose')
        text(task['mechanism'], 'mechanism')
        text(task['evidence_scope'], 'evidence_scope')
        text(task['retry_rationale'], 'retry_rationale')
        number(task['cost_limit'], 'task cost_limit')
        require(type(task['attempt_limit']) is int and task['attempt_limit'] > 0, 'invalid attempt_limit')
        strings(task['acceptance_predicates'], 'acceptance_predicates', True)
        strings(task['resource_scope'], 'resource_scope')
        require(isinstance(task['claim_revisions'], dict), 'claim_revisions must be an object')
        for cid, revision in task['claim_revisions'].items():
            require(cid in claims and type(revision) is int and revision == claims[cid]['revision'], 'unknown/stale initial claim revision')
            require(all(claims[parent]['scope'] in ('shared', task['evidence_scope'])
                        for parent in claim_ancestry(claims, cid)), 'cross-scope evidence reuse in claim ancestry')
    acyclic(tasks, 'depends_on')
    require(isinstance(instance.get('open_conditions', []), list), 'open_conditions must be an array')
    for condition in instance.get('open_conditions', []):
        text(condition['id'], 'condition id')
        require(condition['classification'] in ('PENDING_EVIDENCE', 'ACCEPTED_RISK', 'FATAL_DEFECT'), 'unknown condition class')
        for tid in strings(condition['task_ids'], 'condition task_ids', True):
            require(tid in tasks, 'condition has unknown task')
    if 'option_analysis' in instance:
        runpy.run_path(str(ROOT / 'scripts/nexus-options.py'))['analyze'](instance['option_analysis'])
    return instance


def initial(instance):
    validate(instance)
    return {'instance_hash': digest(instance), 'decision_state': instance['decision_state'],
            'tasks': {t['id']: {'status': 'PENDING', 'attempts': 0, 'spent': 0, 'reserved': 0,
                              'result_revision': 0, 'dependency_revisions': {}, 'inputs_stale': False,
                              'claim_revisions': copy.deepcopy(t['claim_revisions'])} for t in instance['tasks']},
            'claims': copy.deepcopy(indexed(instance['claims'], 'claims')),
            'conditions': copy.deepcopy(indexed(instance.get('open_conditions', []), 'conditions')),
            'review_required': [], 'spent': 0, 'closed': False, 'dissent': [], 'events': {}, 'last_at': None}


def blockers(instance, state, tid, at):
    task = indexed(instance['tasks'], 'tasks')[tid]
    reasons = []
    if state['closed']: reasons.append('INSTANCE_CLOSED')
    if state['decision_state'] in ('REJECT', 'REDESIGN'): reasons.append(state['decision_state'])
    if state['decision_state'] == 'HOLD' and not state['conditions']: reasons.append('GLOBAL_HOLD')
    if expired(instance, at): reasons.append('EXPIRED')
    progress = state['tasks'][tid]
    if progress['inputs_stale']: reasons.append('TASK_INPUT_REVIEW')
    for c in state['conditions'].values():
        if tid in c['task_ids']: reasons.append('HOLD:' + c['id'])
    for parent in task.get('depends_on', []):
        if state['tasks'][parent]['status'] != 'SUCCEEDED': reasons.append('DEPENDENCY:' + parent)
        elif blockers(instance, state, parent, at): reasons.append('DEPENDENCY_REVIEW:' + parent)
        if parent in progress['dependency_revisions'] and progress['dependency_revisions'][parent] != state['tasks'][parent]['result_revision']:
            reasons.append('DEPENDENCY_REVISION:' + parent)
    def claim_expired(cid):
        c = state['claims'][cid]
        return when(c['expires']) <= when(at) or any(claim_expired(parent) for parent in c.get('depends_on', []))
    for cid, revision in state['tasks'][tid]['claim_revisions'].items():
        claim = state['claims'][cid]
        if claim['revision'] != revision or cid in state['review_required']: reasons.append('CLAIM_REVIEW:' + cid)
        if claim_expired(cid): reasons.append('CLAIM_EXPIRED:' + cid)
        for parent in claim_ancestry(state['claims'], cid):
            if state['claims'][parent]['scope'] not in ('shared', task['evidence_scope']): reasons.append('CLAIM_SCOPE:' + parent)
    if state['tasks'][tid]['spent'] > task['cost_limit']: reasons.append('TASK_COST_OVERRUN')
    if state['spent'] > instance['budget']['cost_limit'] - instance['budget']['reserve']: reasons.append('BUDGET_OVERRUN')
    return sorted(set(reasons))


def descendants(claims, cid):
    found = set()
    while True:
        new = {k for k, c in claims.items() if cid in c.get('depends_on', []) or found.intersection(c.get('depends_on', []))}
        if new <= found: return found
        found |= new


def apply(instance, prior, event):
    state = copy.deepcopy(prior)
    eid = text(event.get('id'), 'event.id')
    h = digest(event)
    if eid in state['events']:
        require(state['events'][eid] == h, 'conflicting duplicate event')
        return state
    for field in ('at', 'type'):
        require(field in event, f'event.{field} required')
    at = event['at']; when(at)
    require(state['last_at'] is None or when(at) >= when(state['last_at']), 'out-of-order event')
    require(not state['closed'], 'closed instance requires a new reviewed instance')
    kind = event['type']; issuer = text(event.get('issuer'), 'issuer')
    owner = instance['mandate']['owner']; reviewers = instance['mandate']['reviewers']
    tasks = indexed(instance['tasks'], 'tasks')
    tid = event.get('task_id')
    if tid is not None: require(tid in tasks, 'unknown task')
    if kind in ('start', 'finish'):
        require(tid is not None, 'task_id required')
        require(issuer in (owner, tasks[tid]['agent']), 'event issuer not assigned to task')
        task, progress = tasks[tid], state['tasks'][tid]
        if kind == 'start':
            require(progress['status'] in ('PENDING', 'FAILED'), 'task not startable')
            require(not blockers(instance, state, tid, at), 'task blocked: ' + ','.join(blockers(instance, state, tid, at)))
            require(progress['attempts'] < task['attempt_limit'], 'attempt budget exhausted')
            reserved = number(event['reserved_cost'], 'reserved_cost')
            committed = state['spent'] + sum(t['reserved'] for t in state['tasks'].values())
            require(committed + reserved <= instance['budget']['cost_limit'] - instance['budget']['reserve'], 'reserve boundary exceeded')
            require(progress['spent'] + reserved <= task['cost_limit'], 'task cost budget exceeded')
            for other, p in state['tasks'].items():
                require(p['status'] != 'RUNNING' or not set(task['resource_scope']).intersection(tasks[other]['resource_scope']), 'shared resource already owned')
            progress.update(status='RUNNING', attempts=progress['attempts'] + 1, reserved=reserved)
            progress['dependency_revisions'] = {parent: state['tasks'][parent]['result_revision']
                                                for parent in task.get('depends_on', [])}
        else:
            require(progress['status'] == 'RUNNING', 'task not running')
            cost = number(event['actual_cost'], 'actual_cost')
            require(type(event['accepted']) is bool, 'accepted must be boolean')
            evidence = strings(event['evidence_refs'], 'evidence_refs')
            if event['accepted']:
                require(bool(evidence), 'acceptance needs evidence')
                results = event.get('predicate_results')
                require(isinstance(results, dict) and set(results) == set(task['acceptance_predicates']) and all(v is True for v in results.values()), 'acceptance predicates must all pass')
            # Record actual overruns; do not erase expenditure to preserve a green gate.
            progress['spent'] += cost; state['spent'] += cost; progress['reserved'] = 0
            progress['status'] = 'SUCCEEDED' if event['accepted'] else 'FAILED'
            progress['evidence_refs'] = evidence
            if event['accepted']: progress['result_revision'] += 1
    elif kind == 'hold':
        require(issuer in [owner, *reviewers], 'hold requires named owner/reviewer')
        c = event['condition']; text(c['id'], 'condition id')
        require(c['id'] not in state['conditions'], 'condition already exists')
        require(c['classification'] in ('PENDING_EVIDENCE', 'ACCEPTED_RISK', 'FATAL_DEFECT'), 'unknown condition class')
        require(all(t in tasks for t in strings(c['task_ids'], 'task_ids', True)), 'unknown held task')
        text(c['reason'], 'condition reason')
        state['conditions'][c['id']] = copy.deepcopy(c)
    elif kind == 'resolve_hold':
        require(issuer == owner, 'only named owner can resolve a hold')
        require(event.get('condition_id') in state['conditions'], 'unknown or already resolved condition')
        c = state['conditions'][event['condition_id']]
        require(c['classification'] != 'FATAL_DEFECT', 'fatal defect requires redesign, not risk acceptance')
        strings(event['evidence_refs'], 'evidence_refs', True); text(event['reason'], 'resolution reason')
        del state['conditions'][c['id']]
    elif kind == 'decision':
        require(issuer == owner, 'only named owner can change decision')
        require(event['state'] in VOCAB['decision_states'], 'unknown decision state')
        require(not any(c['classification'] == 'FATAL_DEFECT' for c in state['conditions'].values()) or event['state'] in ('HOLD', 'REDESIGN', 'REJECT'), 'fatal defect prevents proceed')
        text(event['reason'], 'decision reason')
        state['decision_state'] = event['state']
    elif kind == 'claim_revision':
        require(issuer in [owner, *reviewers], 'claim revision requires owner/reviewer')
        new = event['claim']
        require(isinstance(new, dict) and new.get('id') in state['claims'], 'claim revision must target an existing claim')
        old = state['claims'][new['id']]
        validate_claim(new); require(new['revision'] == old['revision'] + 1, 'nonsequential claim revision')
        text(event['reason'], 'revision reason')
        if old['status'] != 'EVIDENCE' and new['status'] == 'EVIDENCE':
            require(bool(set(new['source_refs']) - set(old['source_refs'])), 'promotion requires new evidence')
        updated = copy.deepcopy(state['claims']); updated[new['id']] = copy.deepcopy(new); acyclic(updated, 'depends_on')
        require(not set(new.get('depends_on', [])).intersection(state['review_required']), 'claim depends on unresolved review')
        state['claims'] = updated
        state['review_required'] = sorted((set(state['review_required']) - {new['id']}) | descendants(updated, new['id']))
    elif kind == 'rebind_claims':
        require(issuer in [owner, *reviewers] and tid is not None, 'rebinding requires owner/reviewer and task')
        require(state['tasks'][tid]['status'] != 'RUNNING', 'cannot rebind running task')
        revisions = event['claim_revisions']; require(isinstance(revisions, dict), 'revisions must be object')
        require(set(revisions) == set(state['tasks'][tid]['claim_revisions']), 'cannot drop/add task claims while rebinding')
        for cid, rev in revisions.items():
            require(rev == state['claims'][cid]['revision'] and cid not in state['review_required'], 'claim still requires review')
            require(all(state['claims'][parent]['scope'] in ('shared', tasks[tid]['evidence_scope'])
                        for parent in claim_ancestry(state['claims'], cid)), 'cross-scope evidence reuse in claim ancestry')
        text(event['reason'], 'rebinding reason')
        state['tasks'][tid]['claim_revisions'] = copy.deepcopy(revisions)
        state['tasks'][tid]['status'] = 'PENDING'
        state['tasks'][tid]['inputs_stale'] = False
        state['tasks'][tid]['dependency_revisions'] = {}
        # Retain accounting and prior results, but never silently reuse consumers.
        # Running consumers must still finish to reconcile their actual cost.
        for child in descendants(tasks, tid):
            if state['tasks'][child]['status'] != 'PENDING':
                state['tasks'][child]['inputs_stale'] = True
    elif kind == 'dissent':
        require(issuer in [owner, *reviewers], 'unknown dissent reviewer')
        text(event['objection'], 'objection'); text(event['risk_owner'], 'risk_owner')
        strings(event['evidence_refs'], 'evidence_refs', True)
        state['dissent'].append(copy.deepcopy(event))
    elif kind == 'terminate':
        require(issuer == owner, 'termination requires named owner')
        require(event['outcome'] in ('SUFFICIENT_RESULT', 'FAILURE', 'EXPIRED', 'REDESIGN', 'REJECT'), 'unknown termination outcome')
        require(not any(p['status'] == 'RUNNING' for p in state['tasks'].values()), 'reconcile running tasks before termination')
        if event['outcome'] == 'SUFFICIENT_RESULT':
            # Sufficiency cannot compensate a fatal defect or overwrite a negative decision.
            require(not any(c['classification'] == 'FATAL_DEFECT' for c in state['conditions'].values()), 'fatal defect prevents sufficient-result termination')
            require(state['decision_state'] not in ('REJECT', 'REDESIGN'), 'decision state requires REJECT/REDESIGN termination, not sufficient result')
        for field in ('achieved', 'outstanding', 'accountable', 'on_breach', 'conservation_resources'):
            text(event['closure'][field], field)
        strings(event['evidence_refs'], 'evidence_refs', True)
        text(event['reason'], 'termination reason')
        state['termination_outcome'] = event['outcome']
        state['closure'] = copy.deepcopy(event['closure']); state['closed'] = True
        for p in state['tasks'].values():
            if p['status'] in ('PENDING', 'FAILED'): p['status'] = 'CANCELLED'
    elif kind == 'close':
        require(issuer == owner, 'closure requires named owner')
        require(not expired(instance, at), 'EXPIRED mandate or deadline prevents success closure')
        require(bool(state['tasks']), 'success closure requires at least one task')
        require(not state['conditions'] and not state['review_required'], 'unresolved closure conditions')
        require(state['decision_state'] in ('PROCEED', 'PROCEED_WITH_CONDITIONS'), 'decision prevents success closure')
        require(all(p['status'] == 'SUCCEEDED' and not blockers(instance, state, t, at) for t, p in state['tasks'].items()), 'incomplete/stale work prevents success closure')
        for field in ('achieved', 'outstanding', 'accountable', 'on_breach', 'conservation_resources'):
            text(event['closure'][field], field)
        strings(event['evidence_refs'], 'evidence_refs', True)
        state['closure'] = copy.deepcopy(event['closure']); state['closed'] = True
    else:
        raise ValueError('unknown event type')
    state['events'][eid] = h; state['last_at'] = at
    return state


def replay(instance, events, checkpoint=None):
    state = initial(instance)
    if checkpoint is not None:
        require(checkpoint.get('instance_hash') == digest(instance), 'checkpoint belongs to another instance')
        # Require the complete event history; reconstruct rather than trust a mutable projection.
    checkpoint_seen = checkpoint is None or checkpoint == state
    for event in events:
        state = apply(instance, state, event)
        checkpoint_seen |= checkpoint is not None and state == checkpoint
    require(checkpoint_seen, 'checkpoint does not match a prefix of this event history')
    return state


def plan(instance, state, at):
    rows = []
    for task in instance['tasks']:
        p = state['tasks'][task['id']]
        reasons = blockers(instance, state, task['id'], at)
        if p['attempts'] >= task['attempt_limit'] and p['status'] != 'SUCCEEDED': reasons.append('ATTEMPT_BUDGET')
        rows.append({'task_id': task['id'], 'agent': task['agent'], 'level': task['level'], 'vector': task['vector'],
                     'status': p['status'], 'blockers': reasons,
                     'ready': not reasons and p['status'] in ('PENDING', 'FAILED')})
    roots = {}
    for cid, claim in state['claims'].items():
        for root in claim['source_roots']: roots.setdefault(root, []).append(cid)
    option_comparison = runpy.run_path(str(ROOT / 'scripts/nexus-options.py'))['analyze'](instance['option_analysis']) if 'option_analysis' in instance else None
    return {'option_comparison': option_comparison, 'instance_id': instance['id'], 'decision_state': state['decision_state'], 'tasks': rows,
            'spent': state['spent'], 'reserve': instance['budget']['reserve'],
            'uncommitted_cost': instance['budget']['cost_limit'] - instance['budget']['reserve'] - state['spent'] - sum(p['reserved'] for p in state['tasks'].values()),
            'shared_source_roots': {k: v for k, v in roots.items() if len(v) > 1},
            'execution_authority': False, 'mode': 'OFFLINE_CONTRACT_REPLAY'}


def atomic_write(path, value):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(dir=path.parent, prefix='.' + path.name)
    try:
        with os.fdopen(fd, 'w') as out:
            json.dump(value, out, indent=2, allow_nan=False); out.write('\n'); out.flush(); os.fsync(out.fileno())
        os.replace(temp, path)
    finally:
        if os.path.exists(temp): os.unlink(temp)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('command', choices=['validate', 'plan', 'replay'])
    ap.add_argument('instance'); ap.add_argument('--events'); ap.add_argument('--checkpoint')
    ap.add_argument('--output'); ap.add_argument('--at')
    args = ap.parse_args()
    try:
        instance = json.loads(Path(args.instance).read_text())
        events = [json.loads(line) for line in Path(args.events).read_text().splitlines() if line.strip()] if args.events else []
        checkpoint = json.loads(Path(args.checkpoint).read_text()) if args.checkpoint else None
        state = replay(instance, events, checkpoint)
        if args.command == 'validate': result = {'status': 'VALID', 'instance_hash': digest(instance), 'execution_authority': False}
        elif args.command == 'plan':
            require(args.at is not None, 'plan requires --at for reproducible expiry checks')
            result = plan(instance, state, args.at)
        else: result = state
        if args.output: atomic_write(args.output, result)
        else: print(json.dumps(result, indent=2, allow_nan=False))
        return 0
    except (ValueError, OSError, KeyError, TypeError, RecursionError) as exc:
        print(f'ERROR {exc}', file=sys.stderr); return 1

if __name__ == '__main__':
    sys.exit(main())
