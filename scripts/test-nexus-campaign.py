#!/usr/bin/env python3
"""Regression tests for nexus-campaign.py, the pre-registered Phase 1 exit. No model is called."""
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


camp = load('campaign', 'scripts/nexus-campaign.py')
tr = load('trial', 'scripts/nexus-trial.py')
cp = load('casepack', 'scripts/nexus-casepack.py')
PACKS = ROOT / 'examples/nexus/casepacks'
AT = '2026-10-10T12:00:00Z'
IMPROVER = ['profile-optimizer']


def live_looking(packet, agent, model):
    """Deterministic like the fake executor, but reported as a live host."""
    return {**tr.fake_executor(packet, agent, model), 'host_version': 'claude-code-test'}


def make_packs(root, count, author='outside-author', distinct=True):
    sources = sorted(PACKS.iterdir())
    for i in range(count):
        target = root / f'pack-{i + 1}'
        shutil.copytree(sources[i % len(sources)], target)
        data = json.loads((target / 'pack.json').read_text())
        data.pop('frozen'); data.update(id=target.name, split='held_out', author=author)
        (target / 'pack.json').write_text(json.dumps(data))
        if distinct:  # a verbatim copy of published material is refused as exposed
            for name in data['materials']:
                with open(target / name, 'a', encoding='utf-8') as out:
                    out.write(f'\n<!-- test fixture {target.name} -->\n')
        cp.freeze(target, author, AT)


class CampaignTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.base = Path(cls.temp.name)
        cls.held = cls.base / 'held'
        make_packs(cls.held, camp.MIN_PACKS)
        cls.policies = cls.base / 'policies.json'
        cls.policies.write_text(json.dumps({'schema_version': 1, 'policies': {'p': {
            'max_cost_usd': 2.0, 'max_tokens': 400000, 'max_calls': 8, 'max_wall_seconds': 1800}}}))
        cls.trials = cls.base / 'out' / 'trials.json'
        planned = camp.plan(cls.held, IMPROVER, 'claude-test', 'p', cls.policies, None, 'op-1', cls.base / 'out')
        cls.planned = planned
        for run in planned['runs']:
            pack = cls.held / run['pack']
            tr.start(pack, run['variant'], run['trial_id'], 'claude-test', 'p', cls.policies, 'op-1',
                     cls.base / 'out' / 'runs', cls.base / 'out' / 'artifacts', cls.trials, live_looking)
            if run['variant'] == 'nexus_instance':
                run_dir = cls.base / 'out' / 'runs' / run['pack'] / run['trial_id'] / 'nexus_instance'
                for task in ('A', 'B', 'C'):
                    tr.accept(run_dir, task, True, 'trial-owner', {'contract_met': True},
                              use_proposed=task != 'C', executor=live_looking)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def judge(self, fatal):
        rows = json.loads(self.trials.read_text())
        path = self.base / 'judgments.json'
        path.write_text(json.dumps([{'submission_id': r['submission_id'], 'reviewer': 'blind-reviewer',
                                     'judged_at': '2099-01-01T00:00:00Z', 'evidence_ref': 'review',
                                     'factual_errors': 0, 'fatal_defects': fatal.get(r['variant'], 0),
                                     'constraint_violations': 0, 'evidence_coverage': {'covered': 1, 'required': 1}}
                                    for r in rows]))
        return path

    def test_plan_lists_every_run_and_its_spend_ceiling(self):
        self.assertEqual(camp.MIN_PACKS * 3 * camp.TRIALS_PER_VARIANT, self.planned['runs_missing'])
        self.assertEqual(self.planned['runs_missing'] * 2.0, self.planned['spend_ceiling_usd'])
        self.assertIn('--executor claude', self.planned['runs'][0]['command'])
        self.assertEqual(0, self.planned['packs_needed'])

    def test_plan_skips_runs_already_recorded(self):
        again = camp.plan(self.held, IMPROVER, 'claude-test', 'p', self.policies, self.trials, 'op-1', self.base / 'out')
        self.assertEqual(0, again['runs_missing'])
        self.assertEqual(0, again['spend_ceiling_usd'])

    def test_unjudged_campaign_is_incomplete(self):
        result = camp.status(self.held, IMPROVER, self.trials)
        self.assertEqual('INCOMPLETE', result['decision'])
        self.assertTrue(any('not blind-judged' in m for m in result['missing']))

    def test_fewer_fatal_defects_than_the_fixed_team_proceeds(self):
        result = camp.status(self.held, IMPROVER, self.trials, self.judge({'fixed_team': 1, 'single_agent': 2}))
        self.assertEqual('PROCEED_TO_PHASE_2', result['decision'], result)

    def test_a_tie_on_fatal_defects_redirects(self):
        result = camp.status(self.held, IMPROVER, self.trials, self.judge({}))
        self.assertEqual('REDIRECT', result['decision'])

    def test_more_fatal_defects_redirects_whatever_else_improves(self):
        result = camp.status(self.held, IMPROVER, self.trials, self.judge({'nexus_instance': 1}))
        self.assertEqual('REDIRECT', result['decision'])

    def test_packs_written_by_the_improver_do_not_count(self):
        result = camp.status(self.held, ['outside-author'], self.trials, self.judge({'fixed_team': 1}))
        self.assertEqual('INCOMPLETE', result['decision'])
        self.assertTrue(any('written or frozen by improver' in m for m in result['missing']))

    def test_an_improver_must_be_named(self):
        with self.assertRaisesRegex(camp.CampaignError, 'at least one improver'):
            camp.status(self.held, [], self.trials)


class SmallCampaignTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.policies = self.base / 'policies.json'
        self.policies.write_text(json.dumps({'schema_version': 1, 'policies': {'p': {
            'max_cost_usd': 1.0, 'max_tokens': 400000, 'max_calls': 8, 'max_wall_seconds': 1800}}}))

    def tearDown(self):
        self.temp.cleanup()

    def test_public_casepacks_are_not_independent_held_out_evidence(self):
        result = camp.status(PACKS, IMPROVER, self.base / 'none.json')
        self.assertEqual('INCOMPLETE', result['decision'])
        self.assertEqual(0, result['held_out_packs'])
        self.assertTrue(any('public repository checkout' in x for x in result['missing']))
        plan = camp.plan(PACKS, IMPROVER, 'm', 'p', self.policies, None, 'operator', self.base / 'out')
        self.assertEqual(0, plan['runs_missing'])
        self.assertEqual(0, plan['spend_ceiling_usd'])

    def test_a_copy_of_published_material_outside_the_checkout_does_not_count(self):
        make_packs(self.base / 'copied', 1, distinct=False)
        packs, problems = camp.held_out_packs(self.base / 'copied', IMPROVER)
        self.assertEqual({}, packs)
        self.assertTrue(any('published in this repository' in p for p in problems), problems)

    def test_symlink_into_public_checkout_does_not_bypass_exposure_guard(self):
        alias = self.base / 'public-alias'
        alias.symlink_to(PACKS, target_is_directory=True)
        result = camp.status(alias, IMPROVER, self.base / 'none.json')
        self.assertEqual(0, result['held_out_packs'])
        self.assertTrue(any('public repository checkout' in x for x in result['missing']))

    def test_too_few_packs_is_incomplete_and_says_how_many(self):
        make_packs(self.base / 'held', 2)
        result = camp.status(self.base / 'held', IMPROVER, self.base / 'none.json')
        self.assertIn(f'2 independent held-out packs; the exit needs {camp.MIN_PACKS}', result['missing'])
        self.assertEqual(4, camp.plan(self.base / 'held', IMPROVER, 'm', 'p', self.policies, None, 'op',
                                      self.base / 'out')['packs_needed'])

    def test_fake_executor_rows_are_not_evidence(self):
        make_packs(self.base / 'held', 1)
        trials = self.base / 'trials.json'
        tr.start(self.base / 'held' / 'pack-1', 'single_agent', 'pack-1-t1', 'm', 'p', self.policies, 'op',
                 self.base / 'runs', self.base / 'art', trials, tr.fake_executor)
        result = camp.status(self.base / 'held', IMPROVER, trials)
        self.assertTrue(any('fake-executor rows are not evidence' in m for m in result['missing']))

    def test_two_packs_on_the_same_case_do_not_collide(self):
        make_packs(self.base / 'held', 3)
        ids = {r['trial_id'] for r in camp.plan(self.base / 'held', IMPROVER, 'm', 'p', self.policies, None, 'op',
                                                 self.base / 'out')['runs']}
        self.assertIn('pack-1-t1', ids); self.assertIn('pack-3-t1', ids)


if __name__ == '__main__':
    unittest.main()
