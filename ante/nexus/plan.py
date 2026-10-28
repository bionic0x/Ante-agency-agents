"""nexus-plan.py — a planner agent drafts a NEXUS task graph; the owner adopts it (Overdrive, Phase 3).

Writing an instance by hand is the slowest step before any NEXUS run. A planner
agent can draft it, but an agent that writes its own mandate grants itself
authority, money and deadlines. So the split is fixed:

  the owner writes   objective.json: runbook, mandate (owner, reviewers,
                     authority, scope, expiry), objective (purpose, non-object,
                     success condition, constraints), budget, claims, and a
                     plain-language brief of the problem
  the planner writes only the task graph: tasks, agents from the runbook
                     roster, levels, vectors, mechanisms, dependencies,
                     assertion keys, resource scopes, per-task limits
  this tool          assembles the instance, has the engine validate it, feeds
                     any refusal back to the planner (at most two repairs), and
                     runs the plan linter
  the owner adopts   `adopt` pins the instance hash with the owner's name and
                     time, and refuses unless every linter warning is accepted
                     by code. `verify` checks a pinned adoption later.

    nexus-plan.py draft  --objective FILE --out DIR [--model M] [--operator NAME] [--executor claude|fake]
    nexus-plan.py adopt  --draft DIR --owner NAME --at ISO [--accept-warning CODE ...]
    nexus-plan.py verify --instance FILE --adoption FILE

The planner call is the only model call; `draft --executor fake` makes none.
Nothing here runs a task, accepts a result or spends from the instance budget.
"""
from __future__ import annotations

import argparse
import copy
import datetime as dt
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import runpy
import sys

from ante.paths import ROOT
ENGINE = runpy.run_path(str(ROOT / 'scripts/nexus-instance.py'), run_name='nexus_engine_for_plan')
_spec = importlib.util.spec_from_file_location('lint_for_plan', ROOT / 'scripts/nexus-lint.py')
LINT = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(LINT)
PLANNER_AGENT = 'agents-orchestrator'
MAX_ATTEMPTS = 3
OWNER_FIELDS = ('id', 'runbook_ref', 'mandate', 'objective', 'budget', 'claims', 'decision_state', 'brief')
TASK_FIELDS = {'id', 'agent', 'level', 'vector', 'mechanism', 'evidence_scope', 'depends_on', 'asserts',
               'resource_scope', 'acceptance_predicates', 'retry_rationale', 'cost_limit', 'attempt_limit'}
REQUIRED_TASK_FIELDS = TASK_FIELDS - {'depends_on', 'asserts'}


class PlanError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise PlanError(message)


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')


def load_objective(path):
    owner = read_json(path)
    require(isinstance(owner, dict), 'objective file must be an object')
    missing = [f for f in OWNER_FIELDS if f not in owner]
    require(not missing, f'objective file lacks {missing}; the owner, not the planner, sets these')
    extra = set(owner) - set(OWNER_FIELDS) - {'option_analysis', 'open_conditions'}
    require(not extra, f'objective file has unknown field(s) {sorted(extra)}')
    require(isinstance(owner['brief'], str) and owner['brief'].strip(), 'brief: describe the problem in prose')
    return owner


def roster(runbook_ref):
    _, agents, runbooks = runpy.run_path(str(ROOT / 'scripts/build-catalog.py'))['collect']()
    books = {r['slug']: r for r in runbooks}
    require(runbook_ref in books, f'unknown runbook {runbook_ref!r}')
    catalog = {a['slug']: a for a in agents}
    slugs = sorted({a for g in books[runbook_ref]['roster'] for a in g['agents']} & set(catalog))
    return [{'agent': s, 'name': catalog[s]['name'], 'description': catalog[s]['description']} for s in slugs]


def planner_packet(owner, members, previous=None, error=None):
    pairs = [{'proposer': p['proposer'], 'challenger': p['challenger']}
             for p in ENGINE['PAIRS']['pairs'] if owner['runbook_ref'] not in p['excluded_runbooks']]
    packet = {
        'role': 'NEXUS planner. Draft only the task graph; the owner has fixed everything else.',
        'brief': owner['brief'], 'objective': owner['objective'], 'budget': owner['budget'],
        'claims': [{k: c[k] for k in ('id', 'statement', 'status', 'scope')} for c in owner['claims']],
        'roster': members,
        'vocabulary': {'levels': ENGINE['VOCAB']['levels'], 'vectors': sorted(ENGINE['VECTORS'])},
        'challenger_pairs': pairs,
        'rules': [
            'Use only agents from the roster. Task ids are short and unique.',
            'Give two independent tasks (neither depends on the other) the same assertion key for each '
            'judgement the decision turns on, with different agents, so a disagreement can surface.',
            'End with one synthesis task that depends on the analyses; it needs no asserts.',
            'Independent tasks get disjoint resource_scope values so they can run in parallel.',
            'Keep the sum of task cost_limit at or below budget.cost_limit minus budget.reserve.',
            'If a challenger pair proposer is used, add a task for its challenger that depends on it and '
            'asserts "verdict:<proposer task id>".',
            'evidence_scope must equal a claim scope or "decision"; acceptance_predicates is a non-empty '
            'list such as ["contract_met"].',
        ],
        'output': 'Return only a fenced ```json block holding {"tasks": [...]}; each task has fields '
                  + ', '.join(sorted(TASK_FIELDS)) + ', with the types shown in example_task.',
        # Field types are where drafts fail most (a scope given as a string, not a list).
        'example_task': {'id': 'A', 'agent': '<roster agent>', 'level': 'strategic', 'vector': 'causal',
                         'mechanism': 'What this task tests and how', 'evidence_scope': 'decision',
                         'depends_on': [], 'asserts': ['decision.key'], 'resource_scope': ['analysis/A'],
                         'acceptance_predicates': ['contract_met'], 'retry_rationale': 'Why a retry is affordable',
                         'cost_limit': 2, 'attempt_limit': 2},
    }
    if previous is not None:
        packet['previous_draft'] = previous
        packet['engine_refusal'] = error
        packet['repair'] = 'The engine refused the previous draft. Fix exactly that and return the full graph.'
    return packet


def parse_graph(output):
    match = re.search(r'```json\s*\n(.*?)\n```', output, re.DOTALL)
    require(match is not None, 'the planner returned no fenced json block')
    try:
        graph = json.loads(match.group(1))
    except json.JSONDecodeError as exc:
        raise PlanError(f'the planner returned invalid json: {exc}') from None
    require(isinstance(graph, dict) and isinstance(graph.get('tasks'), list) and graph['tasks'],
            'the planner must return {"tasks": [...]} with at least one task')
    require(set(graph) == {'tasks'}, f'the planner may only return tasks; it set {sorted(set(graph) - {"tasks"})}, '
            'which the owner fixes in the objective file')
    for i, task in enumerate(graph['tasks']):
        require(isinstance(task, dict), f'tasks[{i}] must be an object')
        unknown = set(task) - TASK_FIELDS
        require(not unknown, f'tasks[{i}] sets field(s) the planner does not own: {sorted(unknown)}')
        missing = REQUIRED_TASK_FIELDS - set(task)
        require(not missing, f'tasks[{i}] lacks {sorted(missing)}')
    return graph


def assemble(owner, graph):
    """The instance: owner fields verbatim, the planner's tasks, and derived bindings."""
    claims = {c['id']: c for c in owner['claims']}
    tasks = []
    for task in graph['tasks']:
        bound = {cid: c['revision'] for cid, c in claims.items()
                 if c['scope'] in ('shared', task['evidence_scope'])}
        tasks.append({**copy.deepcopy(task), 'depends_on': task.get('depends_on', []),
                      'asserts': task.get('asserts', []), 'purpose_ref': owner['objective']['id'],
                      'claim_revisions': bound})
    instance = {'schema_version': 1, 'id': owner['id'], 'runbook_ref': owner['runbook_ref'],
                'doctrine_sha256': hashlib.sha256((ROOT / 'strategy/GENERAL-STRATEGY-DOCTRINE.md')
                                                  .read_bytes()).hexdigest(),
                'mandate': owner['mandate'], 'objective': owner['objective'],
                'decision_state': owner['decision_state'], 'budget': owner['budget'],
                'claims': owner['claims'], 'tasks': tasks,
                'open_conditions': owner.get('open_conditions', [])}
    if 'option_analysis' in owner:
        instance['option_analysis'] = owner['option_analysis']
    return instance


# --- executors -------------------------------------------------------------------------

def claude_planner(operator):
    anthropic = runpy.run_path(str(ROOT / 'scripts/nexus-anthropic.py'), run_name='anthropic_for_plan')

    def plan(packet, model):
        expires = (dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=1)).replace(microsecond=0)
        record = anthropic['execute'](packet, PLANNER_AGENT, model, authority_ref='planner draft for owner review',
                                      operator=operator, policy_expires=expires.isoformat().replace('+00:00', 'Z'))
        return {'output': record['output'], 'cost_usd': record['cost_usd'], 'tokens_total': record['tokens_total'],
                'evidence_ref': record['evidence_ref'], 'model_version': record['observed_model_id'] or model}
    return plan


def fake_planner(packet, model):
    """Deterministic draft for tests: two independent assessors sharing a key, then a synthesis."""
    agents = [m['agent'] for m in packet['roster'] if m['agent'] != PLANNER_AGENT]
    first, second, last = agents[0], agents[1 % len(agents)], agents[-1]
    budget = packet['budget']
    limit = max(1, int((budget['cost_limit'] - budget['reserve']) // 3))
    common = {'level': 'strategic', 'evidence_scope': 'decision', 'acceptance_predicates': ['contract_met'],
              'retry_rationale': 'one correction fits the budget', 'cost_limit': limit, 'attempt_limit': 2}
    tasks = [{**common, 'id': 'A', 'agent': first, 'vector': 'causal', 'mechanism': 'Test the causal claim',
              'resource_scope': ['draft-A'], 'asserts': ['decision.holds']},
             {**common, 'id': 'B', 'agent': second, 'vector': 'evidence', 'mechanism': 'Trace the evidence',
              'resource_scope': ['draft-B'], 'asserts': ['decision.holds']},
             {**common, 'id': 'C', 'agent': last, 'level': 'operational', 'vector': 'assurance',
              'mechanism': 'Integrate into one decision', 'resource_scope': ['draft-C'], 'depends_on': ['A', 'B']}]
    if packet.get('engine_refusal'):
        tasks[2]['mechanism'] += ' (repaired)'
    body = json.dumps({'tasks': tasks}, indent=1)
    return {'output': f'```json\n{body}\n```', 'cost_usd': 0.0, 'tokens_total': 0,
            'evidence_ref': 'fake-planner', 'model_version': model}


# --- commands ----------------------------------------------------------------------------

def draft(objective_path, out, executor, model='claude-opus-5-5'):
    out = Path(out)
    require(not out.exists(), f'{out} already exists; a draft is written once')
    owner = load_objective(objective_path)
    members = roster(owner['runbook_ref'])
    require(len(members) >= 2, 'the runbook roster needs at least two agents to plan independent work')
    out.mkdir(parents=True)
    (out / 'attempts').mkdir()
    attempts, previous, error, instance = [], None, None, None
    for n in range(1, MAX_ATTEMPTS + 1):
        packet = planner_packet(owner, members, previous, error)
        result = executor(packet, model)
        record = {'attempt': n, 'packet': packet, 'output': result['output'],
                  **{k: result.get(k) for k in ('cost_usd', 'tokens_total', 'evidence_ref', 'model_version')}}
        try:
            graph = parse_graph(result['output'])
            candidate = assemble(owner, graph)
            ENGINE['validate'](candidate)
            instance, error = candidate, None
        except (PlanError, ValueError, KeyError, TypeError) as exc:
            error = str(exc)
            previous = result['output']
        record['engine_refusal'] = error
        write_json(out / 'attempts' / f'{n:03d}.json', record)
        attempts.append({k: record[k] for k in ('attempt', 'engine_refusal', 'cost_usd', 'tokens_total',
                                                'evidence_ref', 'model_version')})
        if instance is not None:
            break
    summary = {'status': 'DRAFTED' if instance else 'REFUSED', 'objective': str(Path(objective_path).resolve()),
               'planner_agent': PLANNER_AGENT, 'attempts': attempts}
    if instance is None:
        write_json(out / 'draft.json', summary)
        return summary
    lint = LINT.lint(instance, ENGINE)
    write_json(out / 'instance.json', instance)
    write_json(out / 'lint.json', lint)
    summary.update(instance_sha256=ENGINE['digest'](instance), lint_status=lint['status'],
                   warnings=sorted({f['code'] for f in lint['findings']}))
    write_json(out / 'draft.json', summary)
    return summary


def adopt(draft_dir, owner, at, accepted=()):
    draft_dir = Path(draft_dir)
    summary = read_json(draft_dir / 'draft.json')
    require(summary['status'] == 'DRAFTED', 'the planner produced no valid instance to adopt')
    require(not (draft_dir / 'adoption.json').exists(), 'already adopted; a changed plan is a new draft')
    instance = read_json(draft_dir / 'instance.json')
    ENGINE['validate'](instance)
    require(owner == instance['mandate']['owner'], 'only the mandate owner can adopt the plan')
    ENGINE['when'](at)
    digest = ENGINE['digest'](instance)
    require(digest == summary['instance_sha256'], 'instance.json changed after drafting; draft again')
    lint = LINT.lint(instance, ENGINE)
    require(lint['status'] != 'ERRORS', 'the plan has linter errors')
    codes = sorted({f['code'] for f in lint['findings']})
    unaccepted = sorted(set(codes) - set(accepted))
    require(not unaccepted, f'accept each warning explicitly with --accept-warning: {unaccepted}')
    adoption = {'schema_version': 1, 'instance_id': instance['id'], 'instance_sha256': digest,
                'adopted_by': owner, 'adopted_at': at, 'accepted_warnings': codes,
                'planner_agent': summary['planner_agent'],
                'planner_evidence': [a['evidence_ref'] for a in summary['attempts']]}
    write_json(draft_dir / 'adoption.json', adoption)
    return adoption


def verify(instance_path, adoption_path):
    instance, adoption = read_json(instance_path), read_json(adoption_path)
    require(ENGINE['digest'](instance) == adoption['instance_sha256'], 'instance differs from the adopted plan')
    require(adoption['adopted_by'] == instance['mandate']['owner'], 'adopted by someone other than the owner')
    return {'status': 'ADOPTED', 'instance_id': instance['id'], 'adopted_by': adoption['adopted_by'],
            'adopted_at': adoption['adopted_at']}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='command', required=True)
    d = sub.add_parser('draft')
    d.add_argument('--objective', required=True); d.add_argument('--out', required=True)
    d.add_argument('--model', default='claude-opus-5-5'); d.add_argument('--operator', default='planner-operator')
    d.add_argument('--executor', choices=('claude', 'fake'), default='claude')
    a = sub.add_parser('adopt')
    a.add_argument('--draft', required=True); a.add_argument('--owner', required=True); a.add_argument('--at', required=True)
    a.add_argument('--accept-warning', action='append', default=[])
    v = sub.add_parser('verify')
    v.add_argument('--instance', required=True); v.add_argument('--adoption', required=True)
    args = ap.parse_args(argv)
    try:
        if args.command == 'draft':
            executor = fake_planner if args.executor == 'fake' else claude_planner(args.operator)
            result = draft(args.objective, args.out, executor, args.model)
        elif args.command == 'adopt':
            result = adopt(args.draft, args.owner, args.at, args.accept_warning)
        else:
            result = verify(args.instance, args.adoption)
        print(json.dumps(result, indent=2))
        return 0 if result.get('status') != 'REFUSED' else 1
    except (PlanError, ValueError, OSError, KeyError) as exc:
        print(f'ERROR {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
