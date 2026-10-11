#!/usr/bin/env python3
"""Regression tests for nexus-review.py, the blind reviewer's kit. No model is called."""
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


rv = load('review', 'scripts/nexus-review.py')
tr = load('trial', 'scripts/nexus-trial.py')
blind = load('blind', 'scripts/nexus-blind.py')
ev = load('evaluation', 'scripts/evaluate-nexus.py')
PACK = ROOT / 'examples/nexus/casepacks/level-inversion-northwind'
CASES = json.loads((ROOT / 'examples/nexus/evaluation-cases.json').read_text())


class ReviewKitTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.packs = self.base / 'packs'
        shutil.copytree(PACK, self.packs / PACK.name)
        policies = self.base / 'policies.json'
        policies.write_text(json.dumps({'schema_version': 1, 'policies': {'p': {
            'max_cost_usd': 2.0, 'max_tokens': 400000, 'max_calls': 8, 'max_wall_seconds': 1800}}}))
        self.trials = self.base / 'trials.json'
        pack = self.packs / PACK.name
        for variant in ('single_agent', 'fixed_team', 'nexus_instance'):
            tr.start(pack, variant, 't1', 'claude-test', 'p', policies, 'op-1', self.base / 'runs',
                     self.base / 'art', self.trials, tr.fake_executor)
        run = self.base / 'runs' / PACK.name / 't1' / 'nexus_instance'
        for task in ('A', 'B', 'C'):
            tr.accept(run, task, True, 'trial-owner', {'contract_met': True}, use_proposed=task != 'C',
                      executor=tr.fake_executor)
        blind.seal(self.trials, self.base / 'art', self.base / 'sealed', seed=3)
        self.kit = self.base / 'kit'
        rv.kit(self.base / 'sealed', self.trials, self.packs, self.kit)

    def tearDown(self):
        self.temp.cleanup()

    def fill(self, present=False, covered=True, errors=0, extra=()):
        for path in (self.kit / 'sheets').glob('*.json'):
            sheet = json.loads(path.read_text())
            for item in sheet['fatal_defects']:
                item['present'] = present
            for item in sheet['evidence_required']:
                item['covered'] = covered
            sheet['factual_errors']['count'] = errors
            sheet['constraint_violations']['count'] = 0
            sheet['additional_fatal_defects'] = list(extra)
            path.write_text(json.dumps(sheet))

    def collect(self, reviewer='blind-reviewer', name='judgments.json', trials=True):
        return rv.collect(self.kit, reviewer, '2099-01-01T00:00:00Z', self.base / name,
                          self.trials if trials else None)

    def test_kit_carries_the_rubric_and_case_but_nothing_that_names_the_variant(self):
        sheets = list((self.kit / 'sheets').glob('*.json'))
        self.assertEqual(3, len(sheets))
        sheet = json.loads(sheets[0].read_text())
        rubric = json.loads((PACK / 'pack.json').read_text())['rubric']
        self.assertEqual(rubric['fatal_defects'], [i['criterion'] for i in sheet['fatal_defects']])
        self.assertTrue((self.kit / sheet['case'] / 'materials' / 'metrics.md').is_file())
        text = ' '.join(p.read_text(errors='ignore') for p in self.kit.rglob('*') if p.is_file()).lower()
        for leak in ('single_agent', 'fixed_team', 'nexus_instance', 'level-inversion-northwind', 'op-1'):
            self.assertNotIn(leak, text)

    def test_filled_sheets_become_judgments_the_evaluator_accepts(self):
        self.fill(extra=['Invents a renewal figure not in the materials'])
        self.assertEqual(3, self.collect()['judgments'])
        rows = json.loads((self.base / 'judgments.json').read_text())
        self.assertEqual({1}, {r['fatal_defects'] for r in rows})
        self.assertEqual({2}, {r['evidence_coverage']['required'] for r in rows})
        report = ev.evaluate(CASES, json.loads(self.trials.read_text()), rows)
        self.assertEqual(1, report['judged_paired_trials'])

    def test_an_unfilled_item_refuses_the_whole_review(self):
        self.fill()
        path = next((self.kit / 'sheets').glob('*.json'))
        sheet = json.loads(path.read_text()); sheet['evidence_required'][0]['covered'] = None
        path.write_text(json.dumps(sheet))
        with self.assertRaisesRegex(rv.ReviewError, 'set true or false'):
            self.collect()
        self.assertFalse((self.base / 'judgments.json').exists())

    def test_an_artifact_edited_during_review_is_refused(self):
        self.fill()
        artifact = next(self.kit.glob('*.md'))
        artifact.write_text('## Decision\nRewritten by the reviewer.\n')
        with self.assertRaisesRegex(rv.ReviewError, 'edited during review'):
            self.collect()

    def test_the_operator_cannot_judge_their_own_runs(self):
        self.fill()
        with self.assertRaisesRegex(ValueError, 'also ran this trial'):
            self.collect(reviewer='op-1')

    def test_a_kit_needs_the_frozen_pack_each_trial_answered(self):
        with self.assertRaisesRegex(rv.ReviewError, 'no frozen pack'):
            rv.kit(self.base / 'sealed', self.trials, self._other_packs(), self.base / 'kit2')

    def _other_packs(self):
        other = self.base / 'other'
        shutil.copytree(ROOT / 'examples/nexus/casepacks/shared-source-market', other / 'shared-source-market')
        return other

    def test_cli_round_trip(self):
        self.fill()
        code = rv.main(['collect', '--kit', str(self.kit), '--reviewer', 'blind-reviewer',
                        '--judged-at', '2099-01-01T00:00:00Z', '--out', str(self.base / 'cli.json'),
                        '--trials', str(self.trials)])
        self.assertEqual(0, code)


if __name__ == '__main__':
    unittest.main()
