#!/usr/bin/env python3
"""nexus-trial.py — run one evaluation trial on a frozen case pack (NEXUS Overdrive, Phase 1).

Three variants answer the same frozen pack with the same model, host adapter and
budget policy, so that a difference in the judged metrics can be attributed to
how the work was organised rather than to more material, more money or another
model (strategy/NEXUS-MEASUREMENT-PROTOCOL.md):

  single_agent    one call to the pack's single agent
  fixed_team      the pack's fixed roster, called once each, in order
  nexus_instance  the pack's NEXUS instance, admitted event by event by the
                  engine; every result waits for owner acceptance (P1)

The nexus_instance schedule is `sequential` (one task at a time, the Phase 1
baseline) or `parallel` (Phase 2: every ready task the engine admits starts at
once, up to --max-parallel). A trials file records one schedule in a
`<trials>.schedule` manifest and refuses rows from the other.

    nexus-trial.py run    --pack DIR --variant V --trial-id T --model M --policy ID \\
                          --operator NAME --runs DIR --artifacts DIR --trials FILE [--executor claude|fake]
                          [--schedule sequential|parallel] [--max-parallel N]
    nexus-trial.py accept --run DIR --task-id X (--accepted|--rejected) --issuer NAME \\
                          [--predicates JSON] [--asserts JSON | --accept-proposed-asserts]
    nexus-trial.py owner-event --run DIR --event JSON   # resolve_conflict, dissent_response, decision...
    nexus-trial.py resume --run DIR
    nexus-trial.py status --run DIR

A finished run writes exactly one row to --trials, in the format evaluate-nexus.py
accepts, and one artifact named after an opaque submission id for nexus-blind.py.

Instrumentation rules, applied identically to all variants:
  cost_usd, tokens_total  sums of host-reported counters; if the host omits one,
                          the run ends INCOMPLETE_INSTRUMENTATION and writes no row
                          (unavailable data is never entered as zero)
  wall_time_seconds       sum of measured model-call time; owner waiting time is
                          recorded in the run record but excluded, because the
                          other variants have no owner gate to wait on. Calls
                          made concurrently count once, at the longest of them
  invalid_decisions       output-contract failures of the final artifact (each
                          required section missing or repeated)
  rework_cycles           results the owner rejected and that were redone

The runner never spends money without an explicit `run` command, and the fake
executor exists only to test the runner itself; its rows are labelled
host_version "fake-executor" and must never be mixed with live trials.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import secrets
from concurrent.futures import ThreadPoolExecutor
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
VARIANTS = ('single_agent', 'fixed_team', 'nexus_instance')
POLICY_KEYS = ('max_cost_usd', 'max_tokens', 'max_calls', 'max_wall_seconds')
FAKE_HOST = 'fake-executor'
SCHEDULES = ('sequential', 'parallel')
DEFAULT_MAX_PARALLEL = 4


def _module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


CASEPACK = _module('casepack_for_trial', ROOT / 'scripts/nexus-casepack.py')
ENGINE = _module('nexus_engine_for_trial', ROOT / 'scripts/nexus-instance.py')
EVALUATION = _module('evaluation_for_trial', ROOT / 'scripts/evaluate-nexus.py')


class TrialError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise TrialError(message)


def now():
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0)


def iso(value):
    return value.isoformat().replace('+00:00', 'Z')


def atomic_json(path, value):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(dir=path.parent, prefix='.' + path.name)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as out:
            json.dump(value, out, indent=2, ensure_ascii=False); out.write('\n'); out.flush(); os.fsync(out.fileno())
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


# --- executors ---------------------------------------------------------------------------

def claude_executor(operator):
    """Live adapter: the same Read-only, temporary-profile host call for every variant."""
    anthropic = _module('nexus_anthropic_for_trial', ROOT / 'scripts/nexus-anthropic.py')

    def execute(packet, agent_id, model_id):
        record = anthropic.execute(packet, agent_id, model_id,
                                   authority_ref='evaluation trial on a frozen case pack',
                                   operator=operator, policy_expires=iso(now() + dt.timedelta(hours=2)))
        return {'output': record['output'], 'cost_usd': record['cost_usd'], 'tokens_total': record['tokens_total'],
                'wall_time_seconds': record['wall_time_seconds'], 'host_version': record['host_version'],
                'model_version': record['observed_model_id'] or model_id, 'evidence_ref': record['evidence_ref']}
    return execute


def fake_executor(packet, agent_id, model_id):
    """Deterministic stand-in used to test the runner. Never a measurement."""
    sections = packet['case']['output_contract']['required_sections']
    body = '\n\n'.join(f'{s}\n{agent_id} contribution for {packet["task"]["id"]}.' for s in sections)
    asserts = packet['task'].get('asserts') or []
    if asserts:
        body += '\n\n```asserts\n' + json.dumps({k: True for k in asserts}) + '\n```'
    digest = hashlib.sha256(json.dumps(packet, sort_keys=True).encode()).hexdigest()
    return {'output': body, 'cost_usd': 0.01, 'tokens_total': 1000, 'wall_time_seconds': 1.0,
            'host_version': FAKE_HOST, 'model_version': model_id, 'evidence_ref': 'fake:' + digest[:16]}


# --- shared helpers ----------------------------------------------------------------------

def load_policy(policies_path, policy_id):
    data = read_json(policies_path)
    policy = data.get('policies', {}).get(policy_id)
    require(isinstance(policy, dict) and set(policy) == set(POLICY_KEYS), f'unknown or malformed budget policy {policy_id!r}')
    for key in POLICY_KEYS:
        require(type(policy[key]) in (int, float) and policy[key] > 0, f'policy {key} must be positive')
    return policy


def case_material(pack_dir, pack):
    return {'brief': pack['brief'], 'constraints': pack['constraints'],
            'permitted_evidence': pack['permitted_evidence'],
            'materials': {name: (Path(pack_dir) / name).read_text(encoding='utf-8') for name in pack['materials']},
            'output_contract': pack['output_contract'],
            'presentation_rule': 'Write the deliverable for its reader. Do not describe how it was produced, '
                                 'who contributed to it, or the process used.'}


def contract_failures(artifact, contract):
    lines = [line.strip() for line in artifact.splitlines()]
    return sum(1 for section in contract['required_sections'] if lines.count(section) != 1)


def proposed_asserts(output):
    match = re.search(r'```asserts\s*\n(.*?)\n```', output, re.DOTALL)
    if not match:
        return None
    try:
        value = json.loads(match.group(1))
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) else None


class Run:
    """A trial run directory: run.json (state), steps/*.json, events.jsonl for nexus."""

    def __init__(self, path):
        self.path = Path(path)
        self.state = read_json(self.path / 'run.json')

    def save(self):
        atomic_json(self.path / 'run.json', self.state)

    @property
    def pack_dir(self):
        return Path(self.state['pack_dir'])

    def pack(self):
        pack = CASEPACK.verify(self.pack_dir)
        require(pack['frozen']['inputs_hash'] == self.state['inputs_hash'], 'pack changed since the run started')
        return pack

    def budget_reason(self):
        spent, policy = self.state['spent'], self.state['policy']
        if spent['cost_usd'] >= policy['max_cost_usd']: return 'max_cost_usd'
        if spent['tokens_total'] >= policy['max_tokens']: return 'max_tokens'
        if spent['calls'] >= policy['max_calls']: return 'max_calls'
        if spent['wall_time_seconds'] >= policy['max_wall_seconds']: return 'max_wall_seconds'
        return None

    def admit(self):
        """The budget is checked before calls are made; False stops the run."""
        reason = self.budget_reason()
        if reason:
            self.state.update(status='BUDGET_EXHAUSTED', stop_reason=reason)
            return False
        return True

    def call(self, executor, packet, agent_id, label):
        """One model call under the policy. Returns the step record, or None if budget stops the run."""
        if not self.admit():
            return None
        return self.record(executor(packet, agent_id, self.state['model']), packet, agent_id, label)

    def record(self, result, packet, agent_id, label, charge_wall=True):
        """Store one call. Concurrent calls pass charge_wall=False and charge their batch once."""
        index = len(self.state['steps']) + 1
        step = {'index': index, 'label': label, 'agent': agent_id, **{k: result.get(k) for k in
                ('cost_usd', 'tokens_total', 'wall_time_seconds', 'host_version', 'model_version', 'evidence_ref')}}
        atomic_json(self.path / 'steps' / f'{index:03d}.json', {**step, 'packet': packet, 'output': result['output']})
        self.state['steps'].append(step)
        if result.get('cost_usd') is None or result.get('tokens_total') is None or result.get('wall_time_seconds') is None:
            self.state.update(status='INCOMPLETE_INSTRUMENTATION',
                              stop_reason=f'step {index} lacks host cost, token or time counters')
            return None
        for key in ('cost_usd', 'tokens_total') + (('wall_time_seconds',) if charge_wall else ()):
            self.state['spent'][key] += result[key]
        self.state['spent']['calls'] += 1
        hosts = {s['host_version'] for s in self.state['steps']}
        models = {s['model_version'] for s in self.state['steps']}
        if len(hosts) != 1 or len(models) != 1:
            self.state.update(status='INCOMPLETE_INSTRUMENTATION', stop_reason='host or model changed within the run')
            return None
        return {**step, 'output': result['output']}

    def output(self, index):
        return read_json(self.path / 'steps' / f'{index:03d}.json')['output']


# --- variants ----------------------------------------------------------------------------

def run_single(run, executor, pack, case):
    agent = pack['roster']['single_agent']
    packet = {'instance_id': run.state['run_id'], 'case': case,
              'task': {'id': 'answer', 'instruction': 'Produce the complete deliverable.'}}
    step = run.call(executor, packet, agent, 'answer')
    if step:
        run.state['final_steps'] = [step['index']]; run.state['status'] = 'COMPLETE'


def run_fixed(run, executor, pack, case):
    team = pack['roster']['fixed_team']
    contributions = []
    for position, agent in enumerate(team):
        last = position == len(team) - 1
        packet = {'instance_id': run.state['run_id'], 'case': case, 'prior_contributions': contributions,
                  'task': {'id': f'member-{position + 1}',
                           'instruction': 'Produce the complete deliverable, integrating the prior contributions.' if last
                           else 'Contribute the analysis your specialty adds; the last contributor writes the deliverable.'}}
        step = run.call(executor, packet, agent, f'member-{position + 1}')
        if not step:
            break
        contributions.append({'position': position + 1, 'text': step['output']})
        if last:
            run.state['final_steps'] = [step['index']]; run.state['status'] = 'COMPLETE'
    if run.state['status'] == 'BUDGET_EXHAUSTED' and run.state['steps']:
        run.state['final_steps'] = [run.state['steps'][-1]['index']]


def nexus_events(run):
    path = run.path / 'events.jsonl'
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()] if path.exists() else []


def nexus_append(run, instance, event):
    events = nexus_events(run)
    ENGINE.apply(instance, ENGINE.replay(instance, events), event)  # raises if the engine refuses
    with open(run.path / 'events.jsonl', 'a', encoding='utf-8') as out:
        out.write(json.dumps(event, sort_keys=True) + '\n')


def nexus_state(run, instance):
    return ENGINE.replay(instance, nexus_events(run))


def nexus_sinks(instance):
    consumed = {parent for t in instance['tasks'] for parent in t.get('depends_on', [])}
    return [t['id'] for t in instance['tasks'] if t['id'] not in consumed]


def nexus_packet(run, instance, case, task):
    inputs = [{'task': parent, 'accepted_result': run.output(run.state['accepted_step'][parent])}
              for parent in task.get('depends_on', [])]
    return {'instance_id': instance['id'], 'case': case, 'dependency_results': inputs,
            'task': {'id': task['id'], 'purpose': instance['objective']['purpose'],
                     'mechanism': task['mechanism'], 'level': task['level'], 'vector': task['vector'],
                     'asserts': task.get('asserts', []),
                     'instruction': ('Produce the complete deliverable from the accepted dependency results.'
                                     if task['id'] in nexus_sinks(instance) else
                                     'Produce your analysis for this task.')
                                    + (' End with a fenced ```asserts block: a JSON object giving a value for '
                                       'each listed key.' if task.get('asserts') else '')}}


def set_pending(run):
    """`pending` is the earliest result awaiting acceptance; `pending_all` holds every one."""
    waiting = sorted(run.state.get('pending_all', {}).values(), key=lambda p: p['step'])
    run.state['pending'] = waiting[0] if waiting else None


def advance_nexus(run, executor):
    """Start ready tasks the engine admits, then wait for acceptance.

    sequential: one task at a time, as in Phase 1.
    parallel:   every ready task the engine admits (disjoint resource scopes, budget
                reservations within the ordinary budget) up to max_parallel running
                at once, including results still awaiting acceptance.
    """
    pack = run.pack()
    case = case_material(run.pack_dir, pack)
    instance = read_json(run.pack_dir / pack['nexus_instance'])
    tasks = {t['id']: t for t in instance['tasks']}
    parallel = run.state.get('schedule') == 'parallel'
    run.state.setdefault('pending_all', {})
    while True:
        state = nexus_state(run, instance)
        if all(p['status'] == 'SUCCEEDED' for p in state['tasks'].values()):
            run.state['final_steps'] = [run.state['accepted_step'][tid] for tid in nexus_sinks(instance)]
            run.state['status'] = 'COMPLETE'; return
        running = [tid for tid, p in state['tasks'].items() if p['status'] == 'RUNNING']
        slots = (run.state.get('max_parallel', DEFAULT_MAX_PARALLEL) if parallel else 1) - len(running)
        if slots <= 0:
            run.state['status'] = 'AWAITING_ACCEPTANCE'; return
        at = iso(now())
        rows = ENGINE.plan(instance, state, at)['tasks']
        ready = [row['task_id'] for row in rows if row['ready']]
        if not ready:
            if running:
                run.state['status'] = 'AWAITING_ACCEPTANCE'; return
            run.state.update(status='BLOCKED', blockers={row['task_id']: row['blockers'] for row in rows
                                                         if row['status'] != 'SUCCEEDED'})
            return
        if not run.admit():
            return
        slots = min(slots, run.state['policy']['max_calls'] - run.state['spent']['calls'])
        started = []
        for tid in ready:
            if len(started) >= slots:
                break
            task = tasks[tid]
            try:
                nexus_append(run, instance, {'id': f"start-{tid}-{len(run.state['steps']) + len(started) + 1}",
                                             'at': at, 'issuer': task['agent'], 'type': 'start', 'task_id': tid,
                                             'reserved_cost': 1, 'model_id': run.state['model']})
            except ValueError:
                continue  # not admitted now (shared resource, reservation boundary); it waits
            started.append(task)
        if not started:
            if running:
                run.state['status'] = 'AWAITING_ACCEPTANCE'; return
            run.state.update(status='BLOCKED', blockers={tid: ['NOT_ADMITTED'] for tid in ready})
            return
        packets = [(task, nexus_packet(run, instance, case, task)) for task in started]
        if len(packets) == 1:
            task, packet = packets[0]
            steps = [run.record(executor(packet, task['agent'], run.state['model']), packet, task['agent'], task['id'])]
        else:
            with ThreadPoolExecutor(max_workers=len(packets)) as pool:
                futures = [pool.submit(executor, packet, task['agent'], run.state['model']) for task, packet in packets]
                results = [future.result() for future in futures]
            steps = []
            for (task, packet), result in zip(packets, results):
                step = run.record(result, packet, task['agent'], task['id'], charge_wall=False)
                steps.append(step)
                if step is None:
                    break
            walls = [r['wall_time_seconds'] for r in results if r.get('wall_time_seconds') is not None]
            run.state['spent']['wall_time_seconds'] += max(walls) if walls else 0
        for step in steps:
            if step is None:
                return
            run.state['pending_all'][step['label']] = {
                'task_id': step['label'], 'step': step['index'],
                'proposed_asserts': proposed_asserts(step['output']), 'since': iso(now())}
        set_pending(run)
        if not parallel:
            run.state['status'] = 'AWAITING_ACCEPTANCE'; return


# --- lifecycle ---------------------------------------------------------------------------

def schedule_manifest(trials):
    return Path(trials).with_name(Path(trials).name + '.schedule')


def trials_schedule(trials):
    """The schedule a trials file already holds; files from before Phase 2 are sequential."""
    manifest = schedule_manifest(trials)
    if manifest.exists():
        return manifest.read_text(encoding='utf-8').strip()
    return 'sequential' if Path(trials).exists() else None


def start(pack_dir, variant, trial_id, model, policy_id, policies, operator, runs, artifacts, trials, executor,
          schedule='sequential', max_parallel=DEFAULT_MAX_PARALLEL):
    require(variant in VARIANTS, f'variant must be one of {VARIANTS}')
    require(schedule in SCHEDULES, f'schedule must be one of {SCHEDULES}')
    require(type(max_parallel) is int and max_parallel >= 1, 'max_parallel must be a positive integer')
    held = trials_schedule(trials)
    require(held in (None, schedule), f'{trials} holds {held} trials; a {schedule} run needs its own trials file')
    if held is None:  # the first run claims the file for its schedule
        schedule_manifest(trials).parent.mkdir(parents=True, exist_ok=True)
        schedule_manifest(trials).write_text(schedule + '\n', encoding='utf-8')
    for label, value in (('trial_id', trial_id), ('model', model), ('operator', operator)):
        require(isinstance(value, str) and value.strip(), f'{label} required')
    pack = CASEPACK.verify(pack_dir)
    policy = load_policy(policies, policy_id)
    run_dir = Path(runs) / pack['id'] / trial_id / variant
    require(not run_dir.exists(), f'{run_dir} exists; a trial runs once')
    (run_dir / 'steps').mkdir(parents=True)
    state = {'schema_version': 1, 'run_id': f"{pack['id']}/{trial_id}/{variant}", 'pack_id': pack['id'],
             'case_id': pack['case_ref'], 'pack_dir': str(Path(pack_dir).resolve()),
             'inputs_hash': pack['frozen']['inputs_hash'], 'variant': variant, 'trial_id': trial_id,
             'model': model, 'policy_id': policy_id, 'policy': policy, 'operator': operator,
             'submission_id': secrets.token_hex(8), 'started_at': iso(now()),
             'artifacts': str(Path(artifacts).resolve()), 'trials': str(Path(trials).resolve()),
             'status': 'RUNNING', 'steps': [], 'spent': {'cost_usd': 0, 'tokens_total': 0, 'calls': 0, 'wall_time_seconds': 0},
             'rework_cycles': 0, 'owner_wait_seconds': 0, 'accepted_step': {}, 'acceptances': [],
             'schedule': schedule, 'max_parallel': max_parallel, 'pending_all': {}}
    atomic_json(run_dir / 'run.json', state)
    run = Run(run_dir)
    case = case_material(pack_dir, pack)
    if variant == 'single_agent':
        run_single(run, executor, pack, case)
    elif variant == 'fixed_team':
        run_fixed(run, executor, pack, case)
    else:
        advance_nexus(run, executor)
    return finish_if_done(run)


def finish_if_done(run):
    if run.state['status'] in ('COMPLETE', 'BUDGET_EXHAUSTED') and 'row' not in run.state:
        pack = run.pack()
        artifact = '\n\n'.join(run.output(i) for i in run.state.get('final_steps', []))
        artifact_path = Path(run.state['artifacts']) / f"{run.state['submission_id']}.md"
        require(not artifact_path.exists(), f'{artifact_path} already exists')
        artifact_path.parent.mkdir(parents=True, exist_ok=True)
        artifact_path.write_text(artifact + '\n', encoding='utf-8')
        host = {s['host_version'] for s in run.state['steps']}
        model = {s['model_version'] for s in run.state['steps']}
        row = {'submission_id': run.state['submission_id'], 'case_id': run.state['case_id'],
               'trial_id': run.state['trial_id'], 'variant': run.state['variant'],
               'model_version': model.pop() if model else run.state['model'],
               'host_version': host.pop() if host else 'no-call-made',
               'evidence_ref': f"{run.state['run_id']}#sha256:{hashlib.sha256(artifact_path.read_bytes()).hexdigest()}",
               'operator': run.state['operator'], 'inputs_hash': run.state['inputs_hash'],
               'budget_policy_ref': run.state['policy_id'], 'started_at': run.state['started_at'],
               'cost_usd': round(run.state['spent']['cost_usd'], 6), 'tokens_total': int(run.state['spent']['tokens_total']),
               'wall_time_seconds': round(run.state['spent']['wall_time_seconds'], 3),
               'invalid_decisions': contract_failures(artifact, pack['output_contract']),
               'rework_cycles': run.state['rework_cycles']}
        trials_path = Path(run.state['trials'])
        rows = read_json(trials_path) if trials_path.exists() else []
        # Runner self-tests must never be mixed with measurements.
        require(all((r['host_version'] == FAKE_HOST) == (row['host_version'] == FAKE_HOST) for r in rows),
                'fake-executor rows and live rows cannot share a trials file')
        EVALUATION.load_trials(rows + [row])  # same validation the evaluator applies
        schedule = run.state.get('schedule', 'sequential')
        held = trials_schedule(trials_path)
        require(held in (None, schedule), f'{trials_path} holds {held} trials; this run is {schedule}')
        atomic_json(trials_path, rows + [row])
        if not schedule_manifest(trials_path).exists():
            schedule_manifest(trials_path).write_text(schedule + '\n', encoding='utf-8')
        run.state['row'] = row
    run.save()
    return run.state


def accept(run_dir, task_id, accepted, issuer, predicates=None, asserts=None, use_proposed=False, executor=None):
    run = Run(run_dir)
    require(run.state['variant'] == 'nexus_instance', 'only nexus_instance runs have acceptance')
    waiting = run.state.get('pending_all') or ({run.state['pending']['task_id']: run.state['pending']}
                                               if run.state.get('pending') else {})
    pending = waiting.get(task_id)
    require(run.state['status'] == 'AWAITING_ACCEPTANCE' and pending is not None,
            f'task {task_id} is not awaiting acceptance')
    pack = run.pack()
    instance = read_json(run.pack_dir / pack['nexus_instance'])
    task = {t['id']: t for t in instance['tasks']}[task_id]
    event = {'id': f"finish-{task_id}-{pending['step']}", 'at': iso(now()), 'issuer': issuer, 'type': 'finish',
             'task_id': task_id, 'actual_cost': 1, 'accepted': bool(accepted),
             'evidence_refs': [f"{run.state['run_id']}/steps/{pending['step']:03d}.json"]}
    if accepted:
        event['predicate_results'] = predicates if predicates is not None else {}
        if task.get('asserts'):
            if use_proposed:
                require(pending.get('proposed_asserts') is not None, 'the result proposed no asserts block')
                asserts = pending['proposed_asserts']
            require(isinstance(asserts, dict), f"task {task_id} needs asserts for {task['asserts']}")
            event['asserts'] = asserts
    else:
        require(asserts is None and not use_proposed, 'a rejected result carries no asserts')
    try:
        nexus_append(run, instance, event)  # the engine enforces P1 (independent issuer) and P7 (exact keys)
    except ValueError as exc:
        raise TrialError(f'engine refused acceptance: {exc}') from None
    waited = (now() - dt.datetime.fromisoformat(pending['since'].replace('Z', '+00:00'))).total_seconds()
    run.state['owner_wait_seconds'] += max(0, waited)
    run.state['acceptances'].append({'task_id': task_id, 'step': pending['step'], 'accepted': bool(accepted), 'issuer': issuer})
    if accepted:
        run.state['accepted_step'][task_id] = pending['step']
    else:
        run.state['rework_cycles'] += 1
    run.state.setdefault('pending_all', {}).pop(task_id, None)
    set_pending(run)
    run.state['status'] = 'RUNNING'
    run.save()
    return resume(run_dir, executor)


def owner_event(run_dir, event, executor=None):
    """Append an owner/reviewer event (resolve_conflict, dissent_response, decision, hold...) and resume."""
    run = Run(run_dir)
    require(run.state['variant'] == 'nexus_instance', 'only nexus_instance runs take owner events')
    require(isinstance(event, dict) and event.get('type') not in ('start', 'finish'), 'use accept for task results')
    pack = run.pack()
    instance = read_json(run.pack_dir / pack['nexus_instance'])
    event = {'at': iso(now()), **event}
    event.setdefault('id', f"owner-{len(nexus_events(run)) + 1}")
    try:
        nexus_append(run, instance, event)
    except ValueError as exc:
        raise TrialError(f'engine refused event: {exc}') from None
    if run.state['status'] == 'BLOCKED':
        run.state['status'] = 'RUNNING'; run.state.pop('blockers', None)
    run.save()
    return resume(run_dir, executor)


def resume(run_dir, executor=None):
    run = Run(run_dir)
    if run.state['status'] in ('RUNNING', 'BLOCKED') and run.state['variant'] == 'nexus_instance':
        require(executor is not None, 'resume needs an executor')
        run.state['status'] = 'RUNNING'; run.state.pop('blockers', None)
        advance_nexus(run, executor)
    return finish_if_done(run)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='command', required=True)
    r = sub.add_parser('run')
    for flag in ('--pack', '--variant', '--trial-id', '--model', '--policy', '--operator', '--runs', '--artifacts', '--trials'):
        r.add_argument(flag, required=True)
    r.add_argument('--policies', default=str(ROOT / 'examples/nexus/budget-policies.json'))
    r.add_argument('--executor', choices=('claude', 'fake'), default='claude')
    r.add_argument('--schedule', choices=SCHEDULES, default='sequential')
    r.add_argument('--max-parallel', type=int, default=DEFAULT_MAX_PARALLEL)
    a = sub.add_parser('accept')
    a.add_argument('--run', required=True); a.add_argument('--task-id', required=True); a.add_argument('--issuer', required=True)
    g = a.add_mutually_exclusive_group(required=True); g.add_argument('--accepted', action='store_true'); g.add_argument('--rejected', action='store_true')
    a.add_argument('--predicates'); a.add_argument('--asserts'); a.add_argument('--accept-proposed-asserts', action='store_true')
    a.add_argument('--executor', choices=('claude', 'fake'), default='claude')
    o = sub.add_parser('owner-event'); o.add_argument('--run', required=True); o.add_argument('--event', required=True)
    o.add_argument('--executor', choices=('claude', 'fake'), default='claude')
    s = sub.add_parser('resume'); s.add_argument('--run', required=True); s.add_argument('--executor', choices=('claude', 'fake'), default='claude')
    t = sub.add_parser('status'); t.add_argument('--run', required=True)
    args = ap.parse_args(argv)

    def executor_for(operator):
        return fake_executor if args.executor == 'fake' else claude_executor(operator)
    try:
        if args.command == 'run':
            state = start(args.pack, args.variant, args.trial_id, args.model, args.policy, args.policies, args.operator,
                          args.runs, args.artifacts, args.trials, executor_for(args.operator),
                          schedule=args.schedule, max_parallel=args.max_parallel)
        elif args.command == 'status':
            state = Run(args.run).state
        else:
            operator = Run(args.run).state['operator']
            executor = executor_for(operator)
            if args.command == 'accept':
                state = accept(args.run, args.task_id, args.accepted, args.issuer,
                               json.loads(args.predicates) if args.predicates else None,
                               json.loads(args.asserts) if args.asserts else None,
                               args.accept_proposed_asserts, executor)
            elif args.command == 'owner-event':
                state = owner_event(args.run, json.loads(args.event), executor)
            else:
                state = resume(args.run, executor)
        summary = {k: state.get(k) for k in ('run_id', 'status', 'stop_reason', 'pending', 'blockers', 'spent', 'row')}
        if len(state.get('pending_all') or {}) > 1:
            summary['pending_all'] = state['pending_all']
        print(json.dumps({k: v for k, v in summary.items() if v is not None}, indent=2))
        return 0
    except (TrialError, CASEPACK.PackError, ValueError, OSError, json.JSONDecodeError) as exc:
        print(f'ERROR {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
