#!/usr/bin/env python3
"""Regression tests for nexus-trial.py (NEXUS Overdrive, Phase 1). No model is called."""
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


tr = load('trial', 'scripts/nexus-trial.py')
ev = load('evaluation', 'scripts/evaluate-nexus.py')
blind = load('blind', 'scripts/nexus-blind.py')
cp = load('casepack', 'scripts/nexus-casepack.py')
PACKS = ROOT / 'examples/nexus/casepacks'
PREDICATES = {'contract_met': True}


class TrialTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.pack = self.base / 'level-inversion-northwind'
        shutil.copytree(PACKS / 'level-inversion-northwind', self.pack)
        self.policies = self.base / 'policies.json'
        self.policy(max_calls=8)
        self.trials = self.base / 'trials.json'

    def tearDown(self):
        self.temp.cleanup()

    def policy(self, **overrides):
        policy = {'max_cost_usd': 2.0, 'max_tokens': 400000, 'max_calls': 8, 'max_wall_seconds': 1800, **overrides}
        self.policies.write_text(json.dumps({'schema_version': 1, 'policies': {'p': policy}}))

    def run_variant(self, variant, trial='t1', executor=tr.fake_executor, pack=None):
        return tr.start(pack or self.pack, variant, trial, 'claude-test', 'p', self.policies, 'op-1',
                        self.base / 'runs', self.base / 'art', self.trials, executor)

    def run_dir(self, variant, trial='t1'):
        return self.base / 'runs' / 'level-inversion-northwind' / trial / variant

    def accept(self, task, issuer='trial-owner', **kw):
        return tr.accept(self.run_dir('nexus_instance'), task, True, issuer, dict(PREDICATES),
                         executor=tr.fake_executor, **kw)

    def complete_nexus(self):
        self.run_variant('nexus_instance')
        self.accept('A', use_proposed=True)
        self.accept('B', use_proposed=True)
        return self.accept('C')

    def test_three_variants_produce_one_evaluable_pair(self):
        self.assertEqual('COMPLETE', self.run_variant('single_agent')['status'])
        self.assertEqual('COMPLETE', self.run_variant('fixed_team')['status'])
        self.assertEqual('COMPLETE', self.complete_nexus()['status'])
        rows = json.loads(self.trials.read_text())
        self.assertEqual(3, len(rows))
        report = ev.evaluate(json.loads((ROOT / 'examples/nexus/evaluation-cases.json').read_text()), rows)
        self.assertEqual('RECORDED_TRIALS', report['status'])
        self.assertTrue(all(e['paired_trials'] == 1 for e in report['execution_comparisons']))
        self.assertEqual({1, 3, 3}, {r['tokens_total'] // 1000 for r in rows})
        self.assertEqual({0}, {r['invalid_decisions'] for r in rows})

    def test_artifacts_seal_for_blind_review(self):
        self.run_variant('single_agent'); self.run_variant('fixed_team'); self.complete_nexus()
        result = blind.seal(self.trials, self.base / 'art', self.base / 'review', seed=1)
        self.assertEqual(3, result['sealed'])
        self.assertFalse(result['tells_recorded'])

    def test_a_trial_runs_once(self):
        self.run_variant('single_agent')
        with self.assertRaisesRegex(tr.TrialError, 'runs once'):
            self.run_variant('single_agent')

    def test_budget_exhaustion_stops_and_still_records(self):
        self.policy(max_calls=2)
        state = self.run_variant('fixed_team')
        self.assertEqual('BUDGET_EXHAUSTED', state['status'])
        self.assertEqual('max_calls', state['stop_reason'])
        self.assertEqual(2, state['spent']['calls'])
        self.assertEqual(1, len(json.loads(self.trials.read_text())))

    def test_missing_instrumentation_writes_no_row(self):
        def silent(packet, agent, model):
            return {**tr.fake_executor(packet, agent, model), 'cost_usd': None}
        state = self.run_variant('single_agent', executor=silent)
        self.assertEqual('INCOMPLETE_INSTRUMENTATION', state['status'])
        self.assertFalse(self.trials.exists())

    def test_host_change_within_a_run_is_refused(self):
        calls = []
        def drifting(packet, agent, model):
            calls.append(agent)
            return {**tr.fake_executor(packet, agent, model), 'host_version': f'h{len(calls)}'}
        state = self.run_variant('fixed_team', executor=drifting)
        self.assertEqual('INCOMPLETE_INSTRUMENTATION', state['status'])
        self.assertFalse(self.trials.exists())

    def test_contract_failures_count_as_invalid_decisions(self):
        def sloppy(packet, agent, model):
            return {**tr.fake_executor(packet, agent, model), 'output': '## Decision\nExtend.\n## Decision\nAgain.'}
        self.run_variant('single_agent', executor=sloppy)
        self.assertEqual(3, json.loads(self.trials.read_text())[0]['invalid_decisions'])

    def test_nexus_waits_for_an_independent_acceptance(self):
        state = self.run_variant('nexus_instance')
        self.assertEqual('AWAITING_ACCEPTANCE', state['status'])
        self.assertEqual({'diagnosis.kpi_tracks_outcome': True}, state['pending']['proposed_asserts'])
        with self.assertRaisesRegex(tr.TrialError, 'independent owner/reviewer'):
            self.accept('A', issuer='general-strategy-director', use_proposed=True)
        with self.assertRaisesRegex(tr.TrialError, 'not awaiting acceptance'):
            self.accept('B', use_proposed=True)
        with self.assertRaisesRegex(tr.TrialError, 'needs asserts'):
            self.accept('A')

    def test_rejection_counts_rework_and_reruns(self):
        self.run_variant('nexus_instance')
        state = tr.accept(self.run_dir('nexus_instance'), 'A', False, 'trial-owner', executor=tr.fake_executor)
        self.assertEqual(1, state['rework_cycles'])
        self.assertEqual('A', state['pending']['task_id'])
        self.accept('A', use_proposed=True); self.accept('B', use_proposed=True)
        self.assertEqual(1, self.accept('C')['row']['rework_cycles'])

    def test_conflicting_results_block_synthesis_until_owner_resolves(self):
        self.run_variant('nexus_instance')
        self.accept('A', use_proposed=True)
        state = self.accept('B', asserts={'diagnosis.kpi_tracks_outcome': False})
        self.assertEqual('BLOCKED', state['status'])
        self.assertIn('ASSERTION_CONFLICT:diagnosis.kpi_tracks_outcome', state['blockers']['C'])
        with self.assertRaisesRegex(tr.TrialError, 'only named owner'):
            tr.owner_event(self.run_dir('nexus_instance'), {'issuer': 'trial-reviewer', 'type': 'resolve_conflict',
                           'key': 'diagnosis.kpi_tracks_outcome', 'value': False, 'reason': 'r', 'evidence_refs': ['x']},
                           tr.fake_executor)
        state = tr.owner_event(self.run_dir('nexus_instance'), {'issuer': 'trial-owner', 'type': 'resolve_conflict',
                               'key': 'diagnosis.kpi_tracks_outcome', 'value': False,
                               'reason': 'renewals and reopens deteriorated', 'evidence_refs': ['metrics.md']},
                               tr.fake_executor)
        self.assertEqual('C', state['pending']['task_id'])
        synthesis_packet = json.loads((self.run_dir('nexus_instance') / 'steps' / '003.json').read_text())['packet']
        self.assertEqual(['A', 'B'], [d['task'] for d in synthesis_packet['dependency_results']])
        self.assertEqual('COMPLETE', self.accept('C')['status'])

    def test_owner_wait_is_recorded_but_not_charged_as_wall_time(self):
        state = self.complete_nexus()
        self.assertEqual(3.0, state['row']['wall_time_seconds'])
        self.assertIn('owner_wait_seconds', state)

    def test_pack_change_during_a_run_is_refused(self):
        self.run_variant('nexus_instance')
        (self.pack / 'metrics.md').write_text('Renewals improved.')
        with self.assertRaisesRegex(Exception, 'material changed'):
            self.accept('A', use_proposed=True)

    def test_unfrozen_pack_cannot_run(self):
        data = json.loads((self.pack / 'pack.json').read_text()); data.pop('frozen')
        (self.pack / 'pack.json').write_text(json.dumps(data))
        with self.assertRaisesRegex(Exception, 'not frozen'):
            self.run_variant('single_agent')

    def test_fake_rows_never_mix_with_live_rows(self):
        self.trials.write_text(json.dumps([{**json.loads('{}'), 'host_version': '2.1.300'}]))
        with self.assertRaisesRegex(tr.TrialError, 'cannot share a trials file'):
            self.run_variant('single_agent')

    # --- Phase 2: parallel schedule ---------------------------------------------------------

    def run_parallel(self, trial='p1', pack=None, trials=None, **kw):
        return tr.start(pack or self.pack, 'nexus_instance', trial, 'claude-test', 'p', self.policies, 'op-1',
                        self.base / 'runs', self.base / 'art', trials or self.base / 'parallel-trials.json',
                        tr.fake_executor, schedule='parallel', **kw)

    def accept_in(self, trial, task, pack_name='level-inversion-northwind', **kw):
        return tr.accept(self.base / 'runs' / pack_name / trial / 'nexus_instance', task, True, 'trial-owner',
                         dict(PREDICATES), executor=tr.fake_executor, **kw)

    def test_parallel_starts_independent_tasks_together_and_charges_wall_once(self):
        state = self.run_parallel()
        self.assertEqual({'A', 'B'}, set(state['pending_all']))
        self.assertEqual(2, state['spent']['calls'])
        self.assertEqual(1.0, state['spent']['wall_time_seconds'])
        self.accept_in('p1', 'B', use_proposed=True)  # any order
        state = self.accept_in('p1', 'A', use_proposed=True)
        self.assertEqual({'C'}, set(state['pending_all']))
        state = self.accept_in('p1', 'C')
        self.assertEqual('COMPLETE', state['status'])
        self.assertEqual(2.0, state['row']['wall_time_seconds'])  # sequential takes 3.0
        self.assertEqual('parallel', (self.base / 'parallel-trials.json.schedule').read_text().strip())

    def test_parallel_still_blocks_synthesis_on_conflicting_results(self):
        self.run_parallel()
        self.accept_in('p1', 'A', use_proposed=True)
        state = self.accept_in('p1', 'B', asserts={'diagnosis.kpi_tracks_outcome': False})
        self.assertEqual('BLOCKED', state['status'])
        self.assertIn('ASSERTION_CONFLICT:diagnosis.kpi_tracks_outcome', state['blockers']['C'])

    def test_parallel_never_gives_one_resource_to_two_tasks(self):
        instance = json.loads((self.pack / 'instance.json').read_text())
        for task in instance['tasks']:
            if task['id'] == 'B':
                task['resource_scope'] = ['fixture-artifact-A']
        (self.pack / 'instance.json').write_text(json.dumps(instance))
        data = json.loads((self.pack / 'pack.json').read_text()); data.pop('frozen')
        (self.pack / 'pack.json').write_text(json.dumps(data))
        cp.freeze(self.pack, 'tester', '2026-10-10T12:00:00Z')
        state = self.run_parallel()
        self.assertEqual({'A'}, set(state['pending_all']))
        state = self.accept_in('p1', 'A', use_proposed=True)
        self.assertEqual({'B'}, set(state['pending_all']))

    def test_parallel_respects_max_parallel_and_remaining_calls(self):
        self.assertEqual({'A'}, set(self.run_parallel(max_parallel=1)['pending_all']))
        self.policy(max_calls=1)
        state = self.run_parallel(trial='p2', trials=self.base / 'other-parallel.json')
        self.assertEqual(1, state['spent']['calls'])

    def test_a_trials_file_holds_one_schedule(self):
        self.run_variant('single_agent')  # sequential file
        with self.assertRaisesRegex(tr.TrialError, 'needs its own trials file'):
            self.run_parallel(trials=self.trials)
        self.run_parallel()
        with self.assertRaisesRegex(tr.TrialError, 'needs its own trials file'):
            tr.start(self.pack, 'single_agent', 'x', 'claude-test', 'p', self.policies, 'op-1', self.base / 'runs',
                     self.base / 'art', self.base / 'parallel-trials.json', tr.fake_executor)

    def test_cli_fake_run(self):
        code = tr.main(['run', '--pack', str(self.pack), '--variant', 'single_agent', '--trial-id', 'cli',
                        '--model', 'claude-test', '--policy', 'p', '--policies', str(self.policies),
                        '--operator', 'op-1', '--runs', str(self.base / 'runs'), '--artifacts', str(self.base / 'art'),
                        '--trials', str(self.trials), '--executor', 'fake'])
        self.assertEqual(0, code)


if __name__ == '__main__':
    unittest.main()
