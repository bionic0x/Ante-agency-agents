"""``ante develop``: the system proposes changes to itself; a human merges.

Built on NEXUS Overdrive (``nexus-improve.py`` stays the evaluator):

    ante develop propose SPEC.json --patch FILE --base REF --state S --at T
    ante develop gate    ID --patch FILE --state S --at T [evidence ...]
    ante develop pr      ID --state S [--execute]
    ante develop resume  --by NAME --reason TEXT --state S --at T
    ante develop close   ID --outcome merged|rejected|withdrawn --state S --at T
    ante develop status  --state S

``propose`` packages a bounded change (a patch produced by ``nexus-optimize.py`` or
any author) with its improvement hypothesis, pre-registered metric, kill
criterion, cost ceiling and declared autonomy delta, and refuses it if it reaches
outside the editable scopes or into a protected path.

``gate`` applies the patch to a worktree at the base and admits it only if all of
these hold:

    paths            nexus-improve.py paths: no protected or held-out path
    policy           foundation/develop-policy.json read at the base
    scope            every changed path inside the declared scope
    characterization tests/characterization: 114 recordings still match
    selftest         no institutional self-test row newly in FAIL
    held-out         nexus-improve.py compare: Pareto non-regression on held-out packs
    autonomy         the Turing lock (ante/turing): any autonomy increase, alone or
                     accumulated, needs an INDEPENDENT_OPERATOR review

Missing evidence gives HOLD, never PROPOSE. Two consecutive held-out regressions
stop the loop until a named human resumes it. ``pr`` opens at most one draft pull
request per proposal, only with ``--execute``, never force-pushes and never merges.

The loop's state is a hash-chained log (same format as the decision ledger).
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from ante.core import canon, io, schema
from ante.core import time as ante_time
from ante.develop import policy as policy_mod
from ante.constructs.frozen import ConstructError
from ante.learn import ledger
from ante.turing.lock import DIMENSIONS as AUTONOMY_DIMENSIONS
from ante.paths import ROOT

STATE_KINDS = ('proposal', 'gate', 'pr', 'resume', 'close')
METRICS = ('cost_usd', 'tokens_total', 'wall_time_seconds', 'invalid_decisions', 'rework_cycles',
           'factual_errors', 'fatal_defects', 'constraint_violations', 'evidence_coverage')
FINDING_KINDS = ('patterns', 'calibration', 'selftest')
OUTCOMES = ('merged', 'rejected', 'withdrawn')
BRANCH_PREFIX = 'ante-develop/'


class DevelopError(ValueError):
    pass


# --- state ------------------------------------------------------------------------------

class State:
    def __init__(self, path: str):
        self.path = path
        self.entries = ledger.read(path)

    def append(self, kind: str, payload: dict, at: str) -> dict:
        entry = ledger.append(self.path, kind, payload, at, kinds=STATE_KINDS)
        self.entries.append(entry)
        return entry

    def proposals(self) -> dict[str, dict]:
        return {e['payload']['id']: e for e in self.entries if e['kind'] == 'proposal'}

    def closed(self) -> set[str]:
        return {e['payload']['id'] for e in self.entries if e['kind'] == 'close'}

    def gates(self, proposal_id: str | None = None) -> list[dict]:
        return [e for e in self.entries if e['kind'] == 'gate'
                and (proposal_id is None or e['payload']['id'] == proposal_id)]

    def prs(self, proposal_id: str) -> list[dict]:
        return [e for e in self.entries if e['kind'] == 'pr' and e['payload']['id'] == proposal_id]

    def stopped(self, limit: int) -> bool:
        streak = 0
        for entry in self.entries:
            if entry['kind'] == 'resume':
                streak = 0
            elif entry['kind'] == 'gate' and entry['payload']['held_out_regression'] is not None:
                streak = streak + 1 if entry['payload']['held_out_regression'] else 0
        return streak >= limit

    def spend(self) -> float:
        return sum(e['payload']['spec']['cost']['usd_ceiling'] for e in self.entries if e['kind'] == 'proposal')


# --- propose ----------------------------------------------------------------------------

def _validate_spec(spec: dict) -> dict:
    schema.exact_keys(spec, ('id', 'title', 'findings', 'hypothesis', 'metric', 'kill_criterion', 'cost', 'scope',
                             'autonomy_delta'), 'spec')
    if not isinstance(spec['id'], str) or not spec['id'].replace('-', '').isalnum() or spec['id'] != spec['id'].lower():
        schema.fail('spec.id', 'lower-case slug required')
    for key in ('title', 'hypothesis', 'kill_criterion'):
        schema.text(spec[key], f'spec.{key}')
    for index, finding in enumerate(schema.array(spec['findings'], 'spec.findings', 1)):
        schema.exact_keys(finding, ('kind', 'path', 'sha256'), f'spec.findings[{index}]')
        schema.enum(finding['kind'], FINDING_KINDS, f'spec.findings[{index}].kind')
    metric = schema.exact_keys(spec['metric'], ('name', 'tolerances'), 'spec.metric')
    schema.enum(metric['name'], METRICS, 'spec.metric.name')
    tolerances = schema.obj(metric['tolerances'], 'spec.metric.tolerances')
    for name, value in tolerances.items():
        schema.enum(name, METRICS, 'spec.metric.tolerances')
        schema.number(value, f'spec.metric.tolerances.{name}', 0, 1)
    cost = schema.exact_keys(spec['cost'], ('usd_ceiling',), 'spec.cost')
    schema.number(cost['usd_ceiling'], 'spec.cost.usd_ceiling', 0)
    for index, glob in enumerate(schema.array(spec['scope'], 'spec.scope', 1)):
        schema.text(glob, f'spec.scope[{index}]')
    delta = schema.exact_keys(spec['autonomy_delta'], AUTONOMY_DIMENSIONS, 'spec.autonomy_delta')
    for name in AUTONOMY_DIMENSIONS:
        schema.integer(delta[name], f'spec.autonomy_delta.{name}')
    return spec


def _check_findings(spec: dict) -> list[dict]:
    checked = []
    for finding in spec['findings']:
        path = Path(finding['path'])
        try:
            raw = path.read_bytes()
        except OSError:
            raise DevelopError(f'finding {path.name} cannot be read') from None
        if canon.sha256_hex(raw) != finding['sha256']:
            raise DevelopError(f'finding {path.name} does not match its declared sha256')
        value = io.parse_json(raw.decode('utf-8'), path.name)
        kind = value.get('kind') if finding['kind'] != 'selftest' else value.get('command')
        if kind != finding['kind']:
            raise DevelopError(f'finding {path.name} is not a {finding["kind"]} output')
        if finding['kind'] == 'patterns' and not value.get('proposals'):
            raise DevelopError(f'finding {path.name} proposes no pattern that survived the apophenia guard')
        if finding['kind'] == 'calibration' and not any(g.get('result') == 'MEASURED' for g in value.get('groups', [])):
            raise DevelopError(f'finding {path.name} measured nothing (INSUFFICIENT_SAMPLE is not a finding)')
        checked.append(finding)
    return checked


def _contamination(spec: dict, patch_bytes: bytes) -> list[dict]:
    """ICE detect layer: canary strings in anything the improver produced or cites."""
    from ante.ice import canary
    hits = canary.scan_text(json.dumps(spec, ensure_ascii=False), 'proposal spec', {})
    hits += canary.scan_text(patch_bytes.decode('utf-8', 'replace'), 'patch', {})
    for finding in spec['findings']:
        try:
            hits += canary.scan_text(Path(finding['path']).read_bytes().decode('utf-8', 'replace'),
                                     f'finding {Path(finding["path"]).name}', {})
        except OSError:
            continue
    return hits


def _scope_violations(policy: policy_mod.Policy, spec: dict, paths: list[str]) -> list[dict]:
    import fnmatch
    violations = []
    for path in paths:
        reason = policy.classify(path)
        if reason is None and not any(fnmatch.fnmatchcase(path, glob) for glob in spec['scope']):
            reason = 'outside the scope this proposal declared'
        if reason:
            violations.append({'path': path, 'reason': reason})
    return violations


def propose(spec_path: str, patch: str, base: str, state_path: str, at: str, repo: Path = ROOT) -> dict:
    spec = _validate_spec(io.load_document(spec_path))
    state = State(state_path)
    policy = policy_mod.at_ref(repo, base)
    if state.stopped(policy.consecutive_regressions_to_stop):
        raise DevelopError('the develop loop is stopped after consecutive held-out regressions; a human must resume it')
    if spec['id'] in state.proposals():
        raise DevelopError(f'proposal {spec["id"]} already exists')
    open_ids = set(state.proposals()) - state.closed()
    if len(open_ids) >= policy.max_open_proposals:
        raise DevelopError(f'{len(open_ids)} open proposal(s); the limit is {policy.max_open_proposals}')
    if state.spend() + spec['cost']['usd_ceiling'] > policy.campaign_spend_usd:
        raise DevelopError(f'cost ceiling would exceed the campaign limit of {policy.campaign_spend_usd} USD')
    findings = _check_findings(spec)
    patch_path = Path(patch)
    patch_bytes = patch_path.read_bytes()
    hits = _contamination(spec, patch_bytes)
    if hits:
        raise DevelopError('held-out canary found in ' + ', '.join(sorted({h['where'] for h in hits}))
                           + ': contamination; investigate the leak before any proposal from this source')
    paths = policy_mod.patch_paths(repo, patch_path)
    if not paths:
        raise DevelopError('the patch changes nothing')
    violations = _scope_violations(policy, spec, paths)
    if violations:
        raise DevelopError('; '.join(f"{v['path']}: {v['reason']}" for v in violations))
    base_sha = policy_mod.git(repo, 'rev-parse', '--verify', f'{base}^{{commit}}').strip()
    payload = {'id': spec['id'], 'spec': spec, 'findings': findings, 'base': base_sha,
               'patch_sha256': canon.sha256_hex(patch_bytes), 'paths': paths}
    return state.append('proposal', payload, at)


# --- gate -------------------------------------------------------------------------------

def _run(cmd: list[str], cwd: Path, timeout: int = 1800) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)


def _selftest_rows(tree: Path, register: str, at: str) -> list[int]:
    proc = _run([sys.executable, 'scripts/ante', 'selftest', register, '--at', at], tree)
    if proc.returncode != 0:
        raise DevelopError(f'selftest failed to run in {tree.name}: {proc.stderr.strip()[:200]}')
    rows = json.loads(proc.stdout)['body']['rows']
    return sorted(r['row'] for r in rows if r['result'] == 'FAIL')


def gate(proposal_id: str, patch: str, state_path: str, at: str, evidence: dict | None,
         selftest_register: str | None, independent_review: str | None, repo: Path = ROOT) -> dict:
    """Admit, hold or reject one proposal. Every evaluator runs from the BASE tree."""
    from ante.turing import lock

    state = State(state_path)
    entry = state.proposals().get(proposal_id)
    if entry is None:
        raise DevelopError(f'no proposal {proposal_id}')
    if proposal_id in state.closed():
        raise DevelopError(f'proposal {proposal_id} is closed')
    proposal = entry['payload']
    policy = policy_mod.at_ref(repo, proposal['base'])
    if state.stopped(policy.consecutive_regressions_to_stop):
        raise DevelopError('the develop loop is stopped; a human must resume it')
    patch_path = Path(patch).resolve()
    patch_bytes = patch_path.read_bytes()
    if canon.sha256_hex(patch_bytes) != proposal['patch_sha256']:
        raise DevelopError('the patch differs from the one proposed')

    report = {'id': proposal_id, 'base': proposal['base'], 'checks': {}, 'reasons': [], 'holds': []}
    work = Path(tempfile.mkdtemp(prefix='ante-develop-'))
    base_tree, tree = work / 'base', work / 'head'
    worktrees = []
    try:
        for path in (base_tree, tree):
            policy_mod.git(repo, 'worktree', 'add', '-q', '--detach', str(path), proposal['base'])
            worktrees.append(path)
        apply = _run(['git', 'apply', '--index', str(patch_path)], tree)
        if apply.returncode != 0:
            raise DevelopError(f'the patch does not apply to the base: {apply.stderr.strip()[:200]}')
        commit = _run(['git', '-c', 'user.name=ante develop', '-c', 'user.email=ante-develop@invalid',
                       'commit', '-q', '--no-verify', '-m', f'ante develop: {proposal["spec"]["title"]}'], tree)
        if commit.returncode != 0:
            raise DevelopError(f'cannot commit the candidate: {commit.stderr.strip()[:200]}')
        head = policy_mod.git(tree, 'rev-parse', 'HEAD').strip()
        report['head'] = head
        evaluator = str(base_tree / 'scripts/nexus-improve.py')

        # paths: the Overdrive evaluator, as it was at the base, judging base...head
        paths_proc = _run([sys.executable, evaluator, 'paths', '--base', proposal['base'], '--head', head,
                           '--repo', str(tree)], base_tree)
        paths = json.loads(paths_proc.stdout) if paths_proc.stdout.strip().startswith('{') else None
        hits = _contamination(proposal['spec'], patch_bytes)
        report['checks']['canaries'] = {'hits': [h['where'] for h in hits]}
        if hits:
            report['reasons'].append('held-out canary in the candidate: contamination (ICE detect)')
        report['checks']['paths'] = paths['paths'] if paths else {'error': paths_proc.stderr.strip()[:300]}
        if paths is None or paths['paths']['violations']:
            report['reasons'].append('nexus-improve paths: protected or held-out path changed (or check failed)')
        changed = paths['paths']['changed'] if paths else proposal['paths']
        if sorted(changed) != sorted(proposal['paths']):
            report['reasons'].append('the committed change differs from the paths declared at proposal time')
        violations = _scope_violations(policy, proposal['spec'], changed)
        report['checks']['policy'] = {'violations': violations}
        if violations:
            report['reasons'].append('develop policy or declared scope violated')

        # characterization: the base harness and recordings, run against the head tree
        harness = tree / 'tests/characterization'
        shutil.rmtree(harness, ignore_errors=True)
        shutil.copytree(base_tree / 'tests/characterization', harness)
        char = _run([sys.executable, str(harness / 'run.py')], tree)
        report['checks']['characterization'] = {
            'exit': char.returncode, 'summary': (char.stdout.strip().splitlines() or [''])[-1]}
        if char.returncode != 0:
            report['reasons'].append('characterization recordings no longer match')

        if selftest_register:
            register = str(Path(selftest_register).resolve())
            before = _selftest_rows(base_tree, register, at)
            after = _selftest_rows(tree, register, at)
            new = sorted(set(after) - set(before))
            report['checks']['selftest'] = {'fail_rows_base': before, 'fail_rows_head': after, 'new_fail_rows': new}
            if new:
                report['reasons'].append(f'selftest rows newly in FAIL: {new}')
        else:
            report['checks']['selftest'] = {'measured': None, 'reason': 'no evidence register supplied'}

        # held-out: Pareto non-regression, judged by the base evaluator on packs outside the checkout
        regression = None
        if evidence:
            if Path(evidence['held_out']).resolve().is_relative_to(Path(repo).resolve()):
                raise DevelopError('held-out packs must live outside the checkout the improver works in')
            tolerances = work / 'tolerances.json'
            tolerances.write_text(json.dumps(proposal['spec']['metric']['tolerances']))
            cmd = [sys.executable, evaluator, 'compare', '--variant', evidence['variant'],
                   '--held-out', evidence['held_out'], '--tolerances', str(tolerances)]
            for name in ('baseline_trials', 'baseline_judgments', 'candidate_trials', 'candidate_judgments'):
                cmd += ['--' + name.replace('_', '-'), evidence[name]]
            cmd += ['--improver', evidence['improver']]
            compare = _run(cmd, base_tree)
            result = json.loads(compare.stdout) if compare.stdout.strip().startswith('{') else None
            report['checks']['held_out'] = (result['compare'] if result
                                            else {'error': compare.stderr.strip()[:300]})
            if result is None:
                report['holds'].append('held-out comparison could not run; evidence incomplete')
            elif result['compare']['decision'] != 'PROPOSE':
                regression = True
                report['reasons'].append('held-out regression or no measured improvement')
            else:
                metric = proposal['spec']['metric']['name']
                regression = False
                if metric not in result['compare']['improved']:
                    report['reasons'].append(f'the pre-registered metric {metric} did not improve')
        else:
            report['checks']['held_out'] = {'measured': None, 'reason': 'no held-out evidence supplied'}
            report['holds'].append('no held-out evidence supplied')

        autonomy = lock.assess(state.entries, proposal, independent_review, at,
                               patch_bytes.decode('utf-8', 'replace'))
        report['checks']['autonomy'] = autonomy
        if autonomy['decision'] == 'REJECT':
            report['reasons'].append(autonomy['reason'])

        if autonomy['decision'] == 'HOLD':
            report['holds'].append(autonomy['reason'])
        if report['reasons']:
            decision = 'REJECT'
        elif report['holds']:
            decision = 'HOLD'
        else:
            decision = 'PROPOSE'
        report['decision'] = decision
        report['held_out_regression'] = regression
        report['note'] = 'PROPOSE permits one draft pull request for human review; nothing here merges.'
        if decision == 'PROPOSE':
            report['branch'] = BRANCH_PREFIX + proposal_id
            policy_mod.git(repo, 'branch', '-f', report['branch'], head)
    finally:
        for path in worktrees:
            policy_mod.git(repo, 'worktree', 'remove', '--force', str(path), check=False)
        shutil.rmtree(work, ignore_errors=True)
        policy_mod.git(repo, 'worktree', 'prune', check=False)
    state.append('gate', report, at)
    return report


# --- pr ---------------------------------------------------------------------------------

def pr_plan(proposal_id: str, state_path: str, base_branch: str) -> dict:
    state = State(state_path)
    if proposal_id not in state.proposals():
        raise DevelopError(f'no proposal {proposal_id}')
    if proposal_id in state.closed():
        raise DevelopError(f'proposal {proposal_id} is closed')
    if state.prs(proposal_id):
        raise DevelopError('a pull request was already opened for this proposal (at most one)')
    gates = state.gates(proposal_id)
    if not gates or gates[-1]['payload']['decision'] != 'PROPOSE':
        raise DevelopError('the latest gate of this proposal is not PROPOSE')
    report = gates[-1]['payload']
    if any(path.startswith('.github/') for path in report['checks']['paths'].get('changed', [])):
        raise DevelopError('the loop never touches .github/**')
    spec = state.proposals()[proposal_id]['payload']['spec']
    body = ['## ante develop proposal', '', f"**{spec['title']}**", '', f"Hypothesis: {spec['hypothesis']}",
            f"Pre-registered metric: `{spec['metric']['name']}`; kill criterion: {spec['kill_criterion']}",
            f"Cost ceiling: {spec['cost']['usd_ceiling']} USD", '', '### Gate report', '', '```json',
            json.dumps(report, indent=2), '```', '',
            'Opened as a draft by the develop loop. It is never merged by the loop; a human reviews and merges.']
    return {'id': proposal_id, 'branch': report['branch'], 'base_branch': base_branch,
            'title': f"ante develop: {spec['title']}", 'body': '\n'.join(body),
            'commands': [['git', 'push', 'origin', f"{report['branch']}:{report['branch']}"],
                         ['gh', 'pr', 'create', '--draft', '--base', base_branch, '--head', report['branch'],
                          '--title', f"ante develop: {spec['title']}", '--body-file', '<body>']]}


def pr(proposal_id: str, state_path: str, base_branch: str, at: str, execute: bool, repo: Path = ROOT) -> dict:
    plan = pr_plan(proposal_id, state_path, base_branch)
    if not execute:
        return {**plan, 'executed': False, 'note': 'dry run; pass --execute to push the branch and open the draft'}
    remote = policy_mod.git(repo, 'ls-remote', '--heads', 'origin', plan['branch'], check=False)
    if remote.strip():
        raise DevelopError('the branch already exists on the remote; the loop never overwrites a remote branch')
    with tempfile.NamedTemporaryFile('w', suffix='.md', delete=False, encoding='utf-8') as handle:
        handle.write(plan['body'])
        body_file = handle.name
    try:
        push = _run(plan['commands'][0], repo)
        if push.returncode != 0:
            raise DevelopError(f'push failed: {push.stderr.strip()[:200]}')
        create = _run([part if part != '<body>' else body_file for part in plan['commands'][1]], repo)
        if create.returncode != 0:
            raise DevelopError(f'gh pr create failed: {create.stderr.strip()[:200]}')
        url = create.stdout.strip().splitlines()[-1] if create.stdout.strip() else None
    finally:
        Path(body_file).unlink(missing_ok=True)
    State(state_path).append('pr', {'id': proposal_id, 'url': url, 'branch': plan['branch'], 'draft': True}, at)
    return {**plan, 'executed': True, 'url': url}


# --- cli --------------------------------------------------------------------------------

def add_parser(sub) -> None:
    dev = sub.add_parser('develop', help='propose, gate and open draft PRs for changes to Ante itself')
    dsub = dev.add_subparsers(dest='develop_command', required=True)
    p = dsub.add_parser('propose')
    p.add_argument('spec')
    p.add_argument('--patch', required=True)
    p.add_argument('--base', required=True)
    g = dsub.add_parser('gate')
    g.add_argument('id')
    g.add_argument('--patch', required=True)
    g.add_argument('--selftest-register')
    g.add_argument('--independent-review', help='a sealed review record by an INDEPENDENT_OPERATOR (ante/turing)')
    for flag in ('--variant', '--held-out', '--baseline-trials', '--baseline-judgments', '--candidate-trials',
                 '--candidate-judgments', '--improver'):
        g.add_argument(flag)
    r = dsub.add_parser('pr')
    r.add_argument('id')
    r.add_argument('--base-branch', default='main')
    r.add_argument('--execute', action='store_true')
    s = dsub.add_parser('resume')
    s.add_argument('--by', required=True)
    s.add_argument('--reason', required=True)
    c = dsub.add_parser('close')
    c.add_argument('id')
    c.add_argument('--outcome', required=True, choices=OUTCOMES)
    st = dsub.add_parser('status')
    for q in (p, g, r, s, c, st):
        q.add_argument('--state', required=True)
        q.add_argument('--repo', default=str(ROOT), help=argparse.SUPPRESS)
    for q in (p, g, r, s, c):
        q.add_argument('--at', required=True)
    dev.set_defaults(handler=main)



def main(args) -> int:
    repo = Path(args.repo)
    try:
        at = getattr(args, 'at', None)
        if at is not None:
            at = ante_time.iso(ante_time.parse(at, 'at'))
        if args.develop_command == 'propose':
            entry = propose(args.spec, args.patch, args.base, args.state, at, repo)
            result = {'proposal': entry['payload']['id'], 'entry': entry['entry_hash'], 'paths': entry['payload']['paths']}
        elif args.develop_command == 'gate':
            names = ('variant', 'held_out', 'baseline_trials', 'baseline_judgments', 'candidate_trials',
                     'candidate_judgments', 'improver')
            supplied = {n: getattr(args, n) for n in names if getattr(args, n)}
            if supplied and len(supplied) != len(names):
                raise DevelopError('held-out evidence needs all of: ' + ', '.join('--' + n.replace('_', '-') for n in names))
            result = gate(args.id, args.patch, args.state, at, supplied or None, args.selftest_register,
                          args.independent_review, repo)
        elif args.develop_command == 'pr':
            result = pr(args.id, args.state, args.base_branch, at, args.execute, repo)
        elif args.develop_command == 'resume':
            for value, name in ((args.by, 'by'), (args.reason, 'reason')):
                schema.text(value, name)
            state = State(args.state)
            entry = state.append('resume', {'by': args.by, 'reason': args.reason}, at)
            result = {'resumed_by': args.by, 'entry': entry['entry_hash']}
        elif args.develop_command == 'close':
            state = State(args.state)
            if args.id not in state.proposals():
                raise DevelopError(f'no proposal {args.id}')
            entry = state.append('close', {'id': args.id, 'outcome': args.outcome}, at)
            result = {'closed': args.id, 'outcome': args.outcome, 'entry': entry['entry_hash']}
        else:
            state = State(args.state)
            result = {'proposals': sorted(state.proposals()), 'closed': sorted(state.closed()),
                      'gates': [{'id': g['payload']['id'], 'decision': g['payload']['decision']} for g in state.gates()],
                      'spend_ceiling_committed_usd': state.spend()}
    except ledger.LedgerError as exc:
        print(f'LINEAGE {exc}', file=sys.stderr)
        return 3
    except (DevelopError, policy_mod.PolicyError, ConstructError, io.InputError, schema.SchemaError, ante_time.TimeError) as exc:
        print(f'INVALID {exc}', file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    if args.develop_command == 'gate':
        return {'PROPOSE': 0, 'HOLD': 0, 'REJECT': 1}[result['decision']]
    return 0
