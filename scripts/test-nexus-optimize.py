#!/usr/bin/env python3
"""Regression tests for nexus-optimize.py, the gated profile optimizer. No model is called."""
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('optimize', ROOT / 'scripts/nexus-optimize.py')
op = importlib.util.module_from_spec(spec); spec.loader.exec_module(op)
AGENT = 'general-strategy-director'
DEV = ROOT / 'examples/nexus/casepacks/level-inversion-northwind'
HELD = ROOT / 'examples/nexus/casepacks/harbor-pricing-intent'
PROFILE = (ROOT / 'specialized/general-strategy-director.md').read_text()
FRONTMATTER, BODY = op.split_profile(PROFILE)
RULE = '- Before recommending, check that the measure being improved still tracks its outcome.\n'


def scripted(*bodies):
    seen = []

    def run(packet, model):
        seen.append(packet)
        body = bodies[min(len(seen), len(bodies)) - 1]
        return {'output': f'```markdown\n{body.strip()}\n```', 'cost_usd': 0.0, 'evidence_ref': f's-{len(seen)}'}
    run.seen = seen
    return run


def with_rule(text=RULE, body=BODY):
    return body.replace('## 🚨 Critical Rules You Must Follow\n', '## 🚨 Critical Rules You Must Follow\n' + text, 1)


class OptimizeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def evidence(self, pack=DEV):
        path = self.base / f'evidence-{pack.name}.json'
        path.write_text(json.dumps({'schema_version': 1, 'observations': [{'pack': str(pack), 'failures': [
            {'rubric': 'fatal_defects', 'item': 'Treats the indicator as the outcome', 'note': 'cited speed only'}]}]}))
        return path

    def propose(self, executor, name='p', pack=DEV, **kw):
        return op.propose(AGENT, self.evidence(pack), self.base / name, executor, **kw), self.base / name

    def test_a_bounded_general_edit_is_proposed_as_a_clean_patch(self):
        summary, out = self.propose(op.fake_optimizer)
        self.assertEqual('PROPOSED', summary['status'])
        proposed = (out / f'{AGENT}.md').read_text()
        self.assertTrue(proposed.startswith(FRONTMATTER))
        check = subprocess.run(['git', 'apply', '--check', str(out / 'proposal.patch')], cwd=ROOT,
                               capture_output=True, text=True)
        self.assertEqual(0, check.returncode, check.stderr)
        self.assertEqual('profile-optimizer', summary['improver'])

    def test_held_out_evidence_is_never_read(self):
        with self.assertRaisesRegex(op.OptimizeError, 'development packs only'):
            self.propose(op.fake_optimizer, pack=HELD)

    def refusal(self, body):
        summary, out = self.propose(scripted(body, body))
        self.assertEqual('REFUSED', summary['status'])
        self.assertFalse((out / 'proposal.patch').exists())
        return summary['attempts'][0]['refusal']

    def test_frontmatter_cannot_change(self):
        self.assertIn('frontmatter is fixed', self.refusal('---\nname: X\ntools: Bash\n---\n' + BODY))

    def test_size_is_bounded(self):
        self.assertIn('above the 30% bound', self.refusal(with_rule(RULE * 200)))

    def test_required_sections_stay(self):
        self.assertIn('drops the Critical Rules section', self.refusal(BODY.replace('Critical Rules', 'Rules')))

    def test_copying_case_material_is_overfitting(self):
        material = (DEV / 'metrics.md').read_text().split('\n')
        line = next(l for l in material if len(l.split()) >= 10)
        self.assertIn('copies case material', self.refusal(with_rule(f'- Remember: {line}\n')))

    def test_naming_the_evidence_pack_is_overfitting(self):
        self.assertIn('names evidence pack', self.refusal(with_rule('- Recall level-inversion-northwind.\n')))

    def test_no_change_is_not_a_proposal(self):
        self.assertIn('changes nothing', self.refusal(BODY))

    def test_a_refusal_is_fed_back_once(self):
        executor = scripted(BODY, with_rule())
        summary, _ = self.propose(executor)
        self.assertEqual(('PROPOSED', 2), (summary['status'], len(summary['attempts'])))
        self.assertIn('changes nothing', executor.seen[1]['refusal'])

    def test_a_longer_outer_fence_wraps_a_body_with_code_blocks(self):
        body = with_rule() + '\n```text\nexample\n```\n'
        self.assertEqual(body.strip('\n'), op.parse(f'Here it is.\n````markdown\n{body}````\n').strip('\n'))
        with self.assertRaisesRegex(op.OptimizeError, 'no fenced markdown'):
            op.parse('````markdown\nunclosed\n```\n')

    def test_every_attempt_is_kept_for_audit(self):
        _, out = self.propose(scripted(BODY, with_rule()))
        records = sorted((out / 'attempts').glob('*.json'))
        self.assertEqual(2, len(records))
        self.assertIn('changes nothing', json.loads(records[0].read_text())['refusal'])

    def test_cli(self):
        code = op.main(['propose', '--agent', AGENT, '--evidence', str(self.evidence()), '--out',
                        str(self.base / 'cli'), '--executor', 'fake'])
        self.assertEqual(0, code)


if __name__ == '__main__':
    unittest.main()
