#!/usr/bin/env python3
"""Bounded live-execution pilot for NEXUS.

The pilot composes three existing authorities without replacing any of them:
  * nexus-instance.py decides which task is ready;
  * nexus-routing.py decides which observed targets are admissible;
  * an operator authorization decides whether a live model call may occur.

One `step` executes at most one task. It appends a NEXUS `start` event and stores
an execution record, then stops in AWAITING_ACCEPTANCE. A separate `accept`
operation appends the NEXUS `finish` event. This separation is deliberate:
COMPLETED by a model host is not the same claim as accepted by the NEXUS task
contract. `replay` never calls a provider.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import uuid

ROOT = Path(__file__).resolve().parents[1]


def _module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ENGINE = _module('nexus_instance_for_pilot', ROOT / 'scripts' / 'nexus-instance.py')
ROUTER = _module('nexus_routing_for_pilot', ROOT / 'scripts' / 'nexus-routing.py')
ANTHROPIC = _module('nexus_anthropic_for_pilot', ROOT / 'scripts' / 'nexus-anthropic.py')


class PilotError(ValueError):
    pass


def parse_time(value, field):
    try:
        parsed = dt.datetime.fromisoformat(value.replace('Z', '+00:00'))
    except (AttributeError, ValueError) as exc:
        raise PilotError(f'{field} must be ISO-8601 text') from exc
    if parsed.tzinfo is None:
        raise PilotError(f'{field} must carry a timezone offset')
    return parsed


def load_json(path, label='JSON'):
    try:
        value = json.loads(Path(path).read_text(encoding='utf-8'))
    except OSError as exc:
        raise PilotError(f'{label} cannot be read: {exc}') from exc
    except json.JSONDecodeError as exc:
        raise PilotError(f'{label} is not valid JSON: {exc}') from exc
    return value


def load_events(path):
    target = Path(path)
    if not target.exists():
        return []
    rows = []
    for number, line in enumerate(target.read_text(encoding='utf-8').splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise PilotError(f'events line {number} is not valid JSON: {exc}') from exc
        if not isinstance(row, dict):
            raise PilotError(f'events line {number} must be an object')
        rows.append(row)
    return rows


def append_event(path, event):
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open('a', encoding='utf-8') as fh:
        fh.write(json.dumps(event, sort_keys=True, ensure_ascii=False) + '\n')
        fh.flush(); os.fsync(fh.fileno())


def _text(value, field):
    if not isinstance(value, str) or not value.strip():
        raise PilotError(f'{field} must be non-empty text')
    return value


def validate_authority(record, instance, at):
    required = {
        'schema_version', 'instance_id', 'authority_ref', 'operator', 'provider',
        'issued_at', 'not_before', 'expires', 'task_ids', 'allow_external_actions',
        'instance_cost_unit', 'reserved_costs'
    }
    if not isinstance(record, dict):
        raise PilotError('authority must be an object')
    missing = sorted(required - set(record))
    if missing:
        raise PilotError(f'authority missing fields: {missing}')
    if type(record['schema_version']) is not int or record['schema_version'] != 1:
        raise PilotError('authority schema_version must be 1')
    if record['instance_id'] != instance['id']:
        raise PilotError('authority belongs to another instance')
    expected = instance['mandate']['authority_ref']
    if _text(record['authority_ref'], 'authority_ref') != expected:
        raise PilotError('authority_ref does not match the instance mandate')
    _text(record['operator'], 'operator')
    if record['provider'] != 'anthropic':
        raise PilotError('this pilot supports provider anthropic only')
    issued = parse_time(record['issued_at'], 'issued_at')
    not_before = parse_time(record['not_before'], 'not_before')
    expires = parse_time(record['expires'], 'expires')
    if issued > at:
        raise PilotError('authority is future-dated')
    if not_before > at:
        raise PilotError('authority is not active yet')
    if expires <= at:
        raise PilotError('authority has expired')
    if not (issued <= not_before < expires):
        raise PilotError('authority time window is incoherent')
    task_ids = record['task_ids']
    known = {task['id'] for task in instance['tasks']}
    if not isinstance(task_ids, list) or not task_ids or not all(isinstance(x, str) and x for x in task_ids):
        raise PilotError('authority.task_ids must be a non-empty string array')
    if len(task_ids) != len(set(task_ids)):
        raise PilotError('authority.task_ids contains duplicates')
    if not set(task_ids) <= known:
        raise PilotError('authority names unknown tasks')
    if record['allow_external_actions'] is not False:
        raise PilotError('this pilot requires allow_external_actions=false')
    if record['instance_cost_unit'] != instance['budget']['unit']:
        raise PilotError('authority.instance_cost_unit does not match the instance budget unit')
    reserved = record['reserved_costs']
    tasks = _task_map(instance)
    if not isinstance(reserved, dict) or set(reserved) != set(task_ids):
        raise PilotError('authority.reserved_costs must map exactly the authorized task_ids')
    for task_id, value in reserved.items():
        if type(value) not in (int, float) or value < 0:
            raise PilotError(f'authority.reserved_costs[{task_id!r}] must be nonnegative')
        if value > tasks[task_id]['cost_limit']:
            raise PilotError(f'authority reservation for {task_id} exceeds that task cost_limit')
    return record


def _task_map(instance):
    return {task['id']: task for task in instance['tasks']}


def _route_one(instance, task_id, observations_path, at, requested_model=None):
    result = ROUTER.route(instance, observations_path, at=at)
    entry = next(row for row in result['tasks'] if row['task_id'] == task_id)
    if entry['selection'] != 'ADMISSIBLE_SET':
        raise PilotError(f"routing rejected task {task_id}: {entry['selection']}")
    candidates = list(entry.get('undominated', []))
    if requested_model is not None:
        if requested_model not in {row['model_id'] for row in entry['admissible']}:
            raise PilotError(f'model {requested_model!r} is not admissible for task {task_id}')
        return requested_model, entry, result
    if len(candidates) != 1:
        raise PilotError(f'SELECTION_AMBIGUOUS: task {task_id} has undominated targets {candidates}')
    return candidates[0], entry, result


def _target_row(observations_path, model_id, at):
    targets, notes = ROUTER.load_observations(observations_path, at)
    matches = [row for row in targets if row['model_id'] == model_id]
    if len(matches) != 1:
        raise PilotError(f'selected model {model_id!r} does not resolve to exactly one live observation; notes={notes}')
    return matches[0]


def _evidence_payload(state, task, records_root):
    dependencies = []
    for parent in task.get('depends_on', []):
        refs = state['tasks'][parent].get('evidence_refs', [])
        for ref in refs:
            if isinstance(ref, str) and ref.startswith('sha256:'):
                dependencies.append({'task_id': parent, 'evidence_ref': ref, 'execution_output': None})
                continue
            path = Path(ref)
            if not path.is_absolute():
                path = ROOT / path
            row = None
            try:
                if path.is_file():
                    row = json.loads(path.read_text(encoding='utf-8'))
            except (OSError, json.JSONDecodeError):
                row = None
            dependencies.append({
                'task_id': parent,
                'evidence_ref': ref,
                'execution_output': row.get('output') if isinstance(row, dict) else None,
            })
    return dependencies


def build_packet(instance, state, task, records_root):
    claims = {claim['id']: claim for claim in instance['claims']}
    bound = [claims[cid] for cid in task.get('claim_revisions', {})]
    return {
        'schema_version': 1,
        'instance_id': instance['id'],
        'runbook_ref': instance['runbook_ref'],
        'decision_state': state['decision_state'],
        'objective': instance['objective'],
        'task': task,
        'claims': bound,
        'dependencies': _evidence_payload(state, task, records_root),
        'execution_boundary': {
            'external_actions': False,
            'purpose': 'Produce analytical evidence for this task only; host completion is not task acceptance.',
        },
    }


def _packet_sha(packet):
    return hashlib.sha256(
        json.dumps(packet, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()
    ).hexdigest()


def _record_path(records_root, instance_id, task_id, record_id):
    for value, field in ((instance_id, 'instance_id'), (task_id, 'task_id'), (record_id, 'record_id')):
        _text(value, field)
        if value in ('.', '..') or any(char not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-' for char in value):
            raise PilotError(f'{field} contains path-unsafe characters')
    return Path(records_root) / instance_id / task_id / f'{record_id}.json'


def _evidence_path(ref):
    path = Path(ref)
    return path if path.is_absolute() else ROOT / path


def _portable_ref(path):
    resolved = Path(path).resolve()
    try:
        return str(resolved.relative_to(ROOT))
    except ValueError:
        return str(resolved)


def verify_execution_evidence(state):
    """Verify every pilot content hash before replay or further execution."""
    for task_id, progress in state['tasks'].items():
        refs = progress.get('evidence_refs', [])
        hashes = [ref[7:] for ref in refs
                  if isinstance(ref, str) and ref.startswith('sha256:')]
        if not hashes:
            continue
        paths = [ref for ref in refs
                 if isinstance(ref, str) and not ref.startswith('sha256:')]
        if len(hashes) != 1 or len(paths) != 1 or len(hashes[0]) != 64:
            raise PilotError(f'task {task_id}: malformed content-bound execution evidence')
        path = _evidence_path(paths[0])
        if not path.is_file():
            raise PilotError(f'task {task_id}: execution evidence file is missing: {paths[0]}')
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != hashes[0]:
            raise PilotError(
                f'task {task_id}: execution evidence hash mismatch '
                f'(recorded {hashes[0][:12]}…, actual {actual[:12]}…)'
            )


def _save_record(path, record):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(dir=path.parent, prefix='.' + path.name)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as fh:
            json.dump(record, fh, indent=2, ensure_ascii=False); fh.write('\n'); fh.flush(); os.fsync(fh.fileno())
        os.replace(temp, path)
    finally:
        if os.path.exists(temp): os.unlink(temp)


def status(instance, state, at):
    if state['closed']:
        return 'CLOSED'
    if any(row['status'] == 'RUNNING' for row in state['tasks'].values()):
        return 'AWAITING_ACCEPTANCE'
    if all(row['status'] == 'SUCCEEDED' for row in state['tasks'].values()):
        return 'AWAITING_TERMINATION'
    planned = ENGINE.plan(instance, state, at.isoformat())
    if any(row['ready'] for row in planned['tasks']):
        return 'READY'
    return 'BLOCKED'


def step(instance, observations_path, authority, events_path, records_root,
         at=None, requested_model=None, execute_fn=None):
    at = at or dt.datetime.now(dt.timezone.utc)
    ENGINE.validate(instance)
    validate_authority(authority, instance, at)
    events = load_events(events_path)
    state = ENGINE.replay(instance, events)
    verify_execution_evidence(state)
    current = status(instance, state, at)
    if current != 'READY':
        return {'status': current, 'instance_id': instance['id'], 'execution_authority': False}
    plan = ENGINE.plan(instance, state, at.isoformat())
    ready = [row for row in plan['tasks'] if row['ready']]
    # Deterministic serial pilot: instance order wins, never provider score/rank.
    order = {task['id']: index for index, task in enumerate(instance['tasks'])}
    ready.sort(key=lambda row: order[row['task_id']])
    chosen = ready[0]
    task_id = chosen['task_id']
    if task_id not in authority['task_ids']:
        raise PilotError(f'operator authority does not include task {task_id}')
    task = _task_map(instance)[task_id]
    model_id, route_entry, route_result = _route_one(instance, task_id, observations_path, at, requested_model)
    target = _target_row(observations_path, model_id, at)
    if target['provider'] != 'anthropic':
        raise PilotError(f"selected provider {target['provider']!r} has no adapter in this pilot")

    start = {
        'id': 'pilot-start-' + uuid.uuid4().hex,
        'at': at.isoformat(), 'type': 'start', 'issuer': task['agent'],
        'task_id': task_id, 'reserved_cost': authority['reserved_costs'][task_id],
    }
    # Apply before persisting: engine remains the authority on task readiness.
    next_state = ENGINE.apply(instance, state, start)
    append_event(events_path, start)
    packet = build_packet(instance, next_state, task, records_root)
    expected_packet_sha = _packet_sha(packet)
    execute_fn = execute_fn or ANTHROPIC.execute
    try:
        record = execute_fn(
            packet=packet, agent_id=task['agent'], model_id=model_id,
            authority_ref=authority['authority_ref'], operator=authority['operator'],
            policy_expires=authority['expires'],
        )
    except Exception as exc:
        # The start event remains durable. Persist the failure so an operator can
        # explicitly reject/finish the attempt instead of stranding an opaque RUNNING task.
        record = {
            'record_id': uuid.uuid4().hex[:16], 'instance_id': instance['id'],
            'task_id': task_id, 'agent_id': task['agent'], 'provider': 'anthropic',
            'model_id': model_id, 'authority_ref': authority['authority_ref'],
            'operator': authority['operator'], 'started_at': at.isoformat(),
            'finished_at': dt.datetime.now(dt.timezone.utc).isoformat(),
            'outcome': 'FAILED', 'error': str(exc), 'cost_usd': None,
            'tokens_total': None, 'wall_time_seconds': None, 'evidence_ref': None,
            'level': task['level'], 'vector': task['vector'], 'permission_denials': [],
            'packet_sha256': expected_packet_sha, 'output': '',
            'limitations': ['Provider execution failed after the engine start event was durably recorded; reject/finish this attempt before retrying.'],
        }
    if record.get('instance_id') != instance['id'] or record.get('task_id') != task_id:
        raise PilotError('adapter returned a record bound to another instance/task')
    if (record.get('provider') != target['provider'] or record.get('model_id') != model_id
            or record.get('agent_id') != task['agent']
            or record.get('authority_ref') != authority['authority_ref']
            or record.get('level') != task['level'] or record.get('vector') != task['vector']):
        record['outcome'] = 'FAILED'
        record['error'] = 'EXECUTION_TARGET_MISMATCH: adapter record does not match the routed task/provider/model/authority'
    if record.get('packet_sha256') != expected_packet_sha:
        record['outcome'] = 'FAILED'
        record['error'] = 'EXECUTION_PACKET_MISMATCH: adapter record is not bound to the packet that was executed'
    if record.get('outcome') == 'COMPLETED' and record.get('host_version') != target['host_version']:
        record['outcome'] = 'FAILED'
        record['error'] = (
            f"HOST_VERSION_DRIFT: observation used {target['host_version']!r}, "
            f"execution used {record.get('host_version')!r}; observe again before retrying"
        )
        record.setdefault('limitations', []).append(
            'The routed observation is version-bound; a host-version change invalidates it for live execution.'
        )
    path = _record_path(records_root, instance['id'], task_id, record['record_id'])
    _save_record(path, record)
    return {
        'status': 'AWAITING_ACCEPTANCE',
        'instance_id': instance['id'], 'task_id': task_id,
        'provider': target['provider'], 'model_id': model_id,
        'execution_record': str(path),
        'route': route_entry,
        'routing_limitations': route_result['limitations'],
        'execution_authority': False,
        'note': ('Host COMPLETED is evidence only. Append a separate finish decision with accept/reject before another task can run.'
                 if record.get('outcome') == 'COMPLETED' else
                 'Provider execution failed. The start event and failure record are durable; reject/finish this attempt before retrying.'),
    }


def accept(instance, events_path, execution_record, accepted, actual_cost,
           issuer, predicate_results=None, at=None):
    at = at or dt.datetime.now(dt.timezone.utc)
    ENGINE.validate(instance)
    record = load_json(execution_record, 'execution record')
    if record.get('instance_id') != instance['id']:
        raise PilotError('execution record belongs to another instance')
    if accepted and record.get('outcome') != 'COMPLETED':
        raise PilotError('a failed provider execution cannot be accepted')
    task_id = _text(record.get('task_id'), 'execution_record.task_id')
    tasks = _task_map(instance)
    if task_id not in tasks:
        raise PilotError('execution record names an unknown task')
    state = ENGINE.replay(instance, load_events(events_path))
    verify_execution_evidence(state)
    if state['tasks'][task_id]['status'] != 'RUNNING':
        raise PilotError(f'task {task_id} is not RUNNING')
    task = tasks[task_id]
    if (record.get('agent_id') != task['agent'] or record.get('provider') != 'anthropic'
            or record.get('authority_ref') != instance['mandate']['authority_ref']
            or record.get('level') != task['level'] or record.get('vector') != task['vector']):
        raise PilotError('execution record does not match the running task/provider/authority')
    expected_packet_sha = _packet_sha(build_packet(instance, state, task, Path(execution_record).parent))
    if record.get('packet_sha256') != expected_packet_sha:
        raise PilotError('execution record packet_sha256 does not match the running task packet')
    if type(actual_cost) not in (int, float) or actual_cost < 0:
        raise PilotError('actual_cost must be a finite nonnegative number in the instance budget unit')
    evidence_path = Path(execution_record)
    evidence_ref = _portable_ref(evidence_path)
    evidence_sha = hashlib.sha256(evidence_path.read_bytes()).hexdigest()
    event = {
        'id': 'pilot-finish-' + uuid.uuid4().hex,
        'at': at.isoformat(), 'type': 'finish', 'issuer': issuer,
        'task_id': task_id, 'actual_cost': actual_cost,
        'accepted': bool(accepted), 'evidence_refs': [evidence_ref, 'sha256:' + evidence_sha],
    }
    if accepted:
        expected = tasks[task_id]['acceptance_predicates']
        if not isinstance(predicate_results, dict) or set(predicate_results) != set(expected) or not all(v is True for v in predicate_results.values()):
            raise PilotError(f'accepted finish requires every predicate true: {expected}')
        event['predicate_results'] = predicate_results
    ENGINE.apply(instance, state, event)
    append_event(events_path, event)
    replayed = ENGINE.replay(instance, load_events(events_path))
    return {
        'status': status(instance, replayed, at),
        'task_id': task_id, 'accepted': bool(accepted),
        'execution_authority': False,
    }


def replay(instance, events_path):
    state = ENGINE.replay(instance, load_events(events_path))
    verify_execution_evidence(state)
    return {'status': 'REPLAYED', 'state': state, 'execution_authority': False}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest='command', required=True)
    step_ap = sub.add_parser('step')
    step_ap.add_argument('instance'); step_ap.add_argument('--observations', required=True)
    step_ap.add_argument('--authority', required=True); step_ap.add_argument('--events', required=True)
    step_ap.add_argument('--records-root', default='records/nexus-execution')
    step_ap.add_argument('--model-id')
    accept_ap = sub.add_parser('accept')
    accept_ap.add_argument('instance'); accept_ap.add_argument('--events', required=True)
    accept_ap.add_argument('--execution-record', required=True)
    group = accept_ap.add_mutually_exclusive_group(required=True)
    group.add_argument('--accepted', action='store_true'); group.add_argument('--rejected', action='store_true')
    accept_ap.add_argument('--actual-cost', required=True, type=float)
    accept_ap.add_argument('--issuer', required=True)
    accept_ap.add_argument('--predicate-results', help='JSON object, required when --accepted')
    replay_ap = sub.add_parser('replay')
    replay_ap.add_argument('instance'); replay_ap.add_argument('--events', required=True)
    args = ap.parse_args()
    try:
        instance = load_json(args.instance, 'instance')
        if args.command == 'step':
            result = step(instance, args.observations, load_json(args.authority, 'authority'),
                          args.events, args.records_root, requested_model=args.model_id)
        elif args.command == 'accept':
            predicates = json.loads(args.predicate_results) if args.predicate_results else None
            result = accept(instance, args.events, args.execution_record, args.accepted,
                            args.actual_cost, args.issuer, predicates)
        else:
            result = replay(instance, args.events)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0
    except (PilotError, ValueError, KeyError, TypeError, OSError, json.JSONDecodeError) as exc:
        print(f'ERROR {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
