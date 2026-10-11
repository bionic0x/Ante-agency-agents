#!/usr/bin/env python3
"""Regression tests for nexus-improve.py, the self-improvement gate. No model is called."""
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


imp = load('improve', 'scripts/nexus-improve.py')
tr = load('trial', 'scripts/nexus-trial.py')
cp = load('casepack', 'scripts/nexus-casepack.py')
PACKS = ROOT / 'examples/nexus/casepacks'
AT = '2026-10-10T12:00:00Z'


def git(repo, *args):
    subprocess.run(['git', '-C', str(repo), *args], check=True, capture_output=True,
                   env={'GIT_AUTHOR_NAME': 't', 'GIT_AUTHOR_EMAIL': 't@t', 'GIT_COMMITTER_NAME': 't',
                        'GIT_COMMITTER_EMAIL': 't@t', 'PATH': '/usr/bin:/bin:/usr/local/bin', 'HOME': str(repo)})


class PathGateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.repo = Path(self.temp.name)
        git(self.repo, 'init', '-q', '-b', 'main')
        (self.repo / 'strategy').mkdir()
        shutil.copy(ROOT / imp.POLICY, self.repo / imp.POLICY)
        for name, split in (('dev-pack', 'development'), ('held-pack', 'held_out')):
            d = self.repo / 'examples/nexus/casepacks' / name; d.mkdir(parents=True)
            (d / 'pack.json').write_text(json.dumps({'split': split}))
            (d / 'brief.md').write_text('original')
        (self.repo / 'agents').mkdir(); (self.repo / 'agents/profile.md').write_text('v1')
        (self.repo / 'scripts').mkdir(); (self.repo / 'scripts/evaluate-nexus.py').write_text('judge')
        git(self.repo, 'add', '-A'); git(self.repo, 'commit', '-qm', 'base')
        git(self.repo, 'checkout', '-qb', 'proposal')

    def tearDown(self):
        self.temp.cleanup()

    def commit(self, path, content):
        target = self.repo / path; target.parent.mkdir(parents=True, exist_ok=True); target.write_text(content)
        git(self.repo, 'add', '-A'); git(self.repo, 'commit', '-qm', 'change')
        return imp.check_paths('main', 'proposal', self.repo)

    def test_profile_and_development_changes_are_allowed(self):
        self.commit('agents/profile.md', 'v2')
        result = self.commit('examples/nexus/casepacks/dev-pack/brief.md', 'tuned')
        self.assertEqual([], result['violations'])
        self.assertEqual(2, len(result['changed']))

    def test_evaluator_is_protected(self):
        result = self.commit('scripts/evaluate-nexus.py', 'lenient judge')
        self.assertEqual('protected by scripts/evaluate-nexus.py', result['violations'][0]['reason'])

    def test_tests_and_ci_are_protected(self):
        self.assertTrue(self.commit('scripts/test-nexus-instance.py', 'weakened')['violations'])
        self.assertTrue(self.commit('.github/workflows/ci.yml', 'skip')['violations'])

    def test_held_out_pack_is_protected(self):
        result = self.commit('examples/nexus/casepacks/held-pack/brief.md', 'easier')
        self.assertEqual('held-out case pack', result['violations'][0]['reason'])

    def test_reclassifying_a_pack_as_development_does_not_unprotect_it(self):
        result = self.commit('examples/nexus/casepacks/held-pack/pack.json', json.dumps({'split': 'development'}))
        self.assertEqual('held-out case pack', result['violations'][0]['reason'])

    def test_a_proposal_cannot_loosen_the_policy_it_is_judged_by(self):
        policy = json.loads((self.repo / imp.POLICY).read_text()); policy['protected'] = []
        self.commit(imp.POLICY, json.dumps(policy))
        result = self.commit('scripts/evaluate-nexus.py', 'lenient judge')
        reasons = {v['path']: v['reason'] for v in result['violations']}
        self.assertIn(imp.POLICY, reasons)
        self.assertIn('scripts/evaluate-nexus.py', reasons)


class CompareGateTests(unittest.TestCase):
    """Baseline and candidate run on held-out copies of the example packs with the fake executor."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.held = self.base / 'held'
        for source in PACKS.iterdir():
            target = self.held / source.name
            shutil.copytree(source, target)
            data = json.loads((target / 'pack.json').read_text()); data.pop('frozen'); data['split'] = 'held_out'
            data['author'] = 'independent-author'
            (target / 'pack.json').write_text(json.dumps(data))
            for name in data['materials']:  # verbatim published material is refused as exposed
                with open(target / name, 'a', encoding='utf-8') as out:
                    out.write('\n<!-- test fixture -->\n')
            cp.freeze(target, 'independent-author', AT)
        self.policies = self.base / 'policies.json'
        self.policies.write_text(json.dumps({'schema_version': 1, 'policies': {'p': {
            'max_cost_usd': 2.0, 'max_tokens': 400000, 'max_calls': 8, 'max_wall_seconds': 1800}}}))
        self.tolerances = self.base / 'tolerances.json'
        self.tolerances.write_text(json.dumps({'cost_usd': 0.1, 'tokens_total': 0.1, 'wall_time_seconds': 0.2}))

    def tearDown(self):
        self.temp.cleanup()

    def record(self, label, model='claude-test'):
        trials = self.base / f'{label}-trials.json'
        for pack in sorted(self.held.iterdir()):
            for variant in ('single_agent', 'fixed_team', 'nexus_instance'):
                tr.start(pack, variant, 't1', model, 'p', self.policies, 'op-1', self.base / label / 'runs',
                         self.base / label / 'art', trials, tr.fake_executor)
            run = self.base / label / 'runs' / pack.name / 't1' / 'nexus_instance'
            for task in ('A', 'B', 'C'):
                tr.accept(run, task, True, 'trial-owner', {'contract_met': True}, use_proposed=task != 'C',
                          executor=tr.fake_executor)
        return trials

    def judge(self, label, trials, fatal=None, errors=0):
        rows = json.loads(trials.read_text())
        judgments = [{'submission_id': r['submission_id'], 'reviewer': 'blind-reviewer', 'judged_at': '2099-01-01T00:00:00Z',
                      'evidence_ref': 'review', 'factual_errors': errors,
                      'fatal_defects': (fatal or {}).get(r['variant'], 0), 'constraint_violations': 0,
                      'evidence_coverage': {'covered': 2, 'required': 2}} for r in rows]
        path = self.base / f'{label}-judgments.json'
        path.write_text(json.dumps(judgments))
        return path

    def compare(self, baseline, candidate, variant='nexus_instance'):
        return imp.compare(variant, self.held, json.loads(self.tolerances.read_text()), baseline, candidate)

    def test_fewer_fatal_defects_with_nothing_worse_is_proposed(self):
        b = self.record('b'); c = self.record('c')
        decision, reasons, table = self.compare((b, self.judge('b', b, {'nexus_instance': 1})), (c, self.judge('c', c)))
        self.assertEqual('PROPOSE', decision, reasons)
        self.assertEqual(['fatal_defects'], table['improved'])

    def test_any_fatal_defect_increase_is_rejected_whatever_else_improves(self):
        b = self.record('b'); c = self.record('c')
        decision, reasons, _ = self.compare((b, self.judge('b', b, errors=3)),
                                            (c, self.judge('c', c, {'nexus_instance': 1}, errors=0)))
        self.assertEqual('REJECT', decision)
        self.assertTrue(any(r.startswith('fatal_defects') for r in reasons))

    def test_no_measured_benefit_is_not_an_improvement(self):
        b = self.record('b'); c = self.record('c')
        decision, reasons, _ = self.compare((b, self.judge('b', b)), (c, self.judge('c', c)))
        self.assertEqual('REJECT', decision)
        self.assertIn('no metric improved', reasons[0])

    def test_development_evidence_is_refused(self):
        b = self.record('b'); c = self.record('c')
        for pack in self.held.iterdir():
            data = json.loads((pack / 'pack.json').read_text()); data.pop('frozen'); data['split'] = 'development'
            (pack / 'pack.json').write_text(json.dumps(data)); cp.freeze(pack, 'x', AT)
        with self.assertRaisesRegex(imp.GateError, 'no frozen held-out packs'):
            self.compare((b, self.judge('b', b)), (c, self.judge('c', c)))

    def test_different_model_compares_models_not_the_proposal(self):
        b = self.record('b'); c = self.record('c', model='claude-other')
        with self.assertRaisesRegex(imp.GateError, 'differ in model_version'):
            self.compare((b, self.judge('b', b, {'nexus_instance': 1})), (c, self.judge('c', c)))

    def test_unjudged_submissions_are_refused(self):
        b = self.record('b'); c = self.record('c')
        judgments = self.judge('c', c); rows = json.loads(judgments.read_text())[:-1]
        judgments.write_text(json.dumps(rows))
        with self.assertRaisesRegex(imp.GateError, 'fully judged'):
            self.compare((b, self.judge('b', b)), (c, judgments))

    def test_packs_written_by_the_improver_are_refused(self):
        b = self.record('b'); c = self.record('c')
        with self.assertRaisesRegex(imp.GateError, 'written or frozen by the improver'):
            imp.compare('nexus_instance', self.held, {}, (b, self.judge('b', b, {'nexus_instance': 1})),
                        (c, self.judge('c', c)), improvers=['independent-author'])
        decision, _, _ = imp.compare('nexus_instance', self.held, {}, (b, self.judge('b', b, {'nexus_instance': 1})),
                                     (c, self.judge('c', c)), improvers=['profile-optimizer'])
        self.assertEqual('PROPOSE', decision)

    def test_public_or_copied_packs_cannot_judge_a_proposal(self):
        b = self.record('b'); c = self.record('c')
        args = ({}, (b, self.judge('b', b, {'nexus_instance': 1})), (c, self.judge('c', c)))
        with self.assertRaisesRegex(imp.GateError, 'public repository checkout'):
            imp.compare('nexus_instance', PACKS, *args)
        copied = self.base / 'copied'
        target = copied / 'verbatim'
        shutil.copytree(PACKS / 'harbor-pricing-intent', target)
        data = json.loads((target / 'pack.json').read_text()); data.pop('frozen'); data['id'] = 'verbatim'
        (target / 'pack.json').write_text(json.dumps(data)); cp.freeze(target, 'independent-author', AT)
        with self.assertRaisesRegex(imp.GateError, 'published in this repository'):
            imp.compare('nexus_instance', copied, *args)

    def test_tolerances_cannot_name_unknown_metrics(self):
        b = self.record('b'); c = self.record('c')
        with self.assertRaisesRegex(imp.GateError, 'unknown tolerance'):
            imp.compare('nexus_instance', self.held, {'score': 1}, (b, self.judge('b', b)), (c, self.judge('c', c)))


if __name__ == '__main__':
    unittest.main()
