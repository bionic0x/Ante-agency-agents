#!/usr/bin/env python3
"""Regression tests for nexus-casepack.py (NEXUS Overdrive, Phase 1)."""
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('casepack', ROOT / 'scripts/nexus-casepack.py')
cp = importlib.util.module_from_spec(spec); spec.loader.exec_module(cp)
EXAMPLES = ROOT / 'examples/nexus/casepacks'
AT = '2026-10-10T11:30:00Z'


class CasePackTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.pack = Path(self.temp.name) / 'level-inversion-northwind'
        shutil.copytree(EXAMPLES / 'level-inversion-northwind', self.pack)
        data = json.loads((self.pack / 'pack.json').read_text())
        data.pop('frozen')
        self.write(data)

    def tearDown(self):
        self.temp.cleanup()

    def read(self):
        return json.loads((self.pack / 'pack.json').read_text())

    def write(self, data):
        (self.pack / 'pack.json').write_text(json.dumps(data, indent=2))

    def test_examples_are_frozen_and_intact(self):
        for pack_dir in sorted(EXAMPLES.iterdir()):
            with self.subTest(pack=pack_dir.name):
                self.assertTrue(cp.verify(pack_dir)['frozen']['inputs_hash'].startswith('sha256:'))

    def test_freeze_then_verify_and_refuse_refreeze(self):
        frozen = cp.freeze(self.pack, 'tester', AT)
        self.assertEqual(frozen['frozen']['inputs_hash'], cp.verify(self.pack)['frozen']['inputs_hash'])
        with self.assertRaisesRegex(cp.PackError, 'already frozen'):
            cp.freeze(self.pack, 'tester', AT)

    def test_unfrozen_pack_cannot_be_used(self):
        with self.assertRaisesRegex(cp.PackError, 'not frozen'):
            cp.verify(self.pack)

    def test_material_change_after_freezing_is_detected(self):
        cp.freeze(self.pack, 'tester', AT)
        (self.pack / 'metrics.md').write_text('Renewals improved.')
        with self.assertRaisesRegex(cp.PackError, 'material changed'):
            cp.verify(self.pack)

    def test_rubric_or_brief_change_after_freezing_is_detected(self):
        cp.freeze(self.pack, 'tester', AT)
        data = self.read(); data['rubric']['fatal_defects'] = ['Nothing is fatal']
        self.write(data)
        with self.assertRaisesRegex(cp.PackError, 'material changed'):
            cp.verify(self.pack)

    def test_instance_change_after_freezing_is_detected(self):
        cp.freeze(self.pack, 'tester', AT)
        instance = json.loads((self.pack / 'instance.json').read_text())
        instance['budget']['cost_limit'] += 1
        (self.pack / 'instance.json').write_text(json.dumps(instance))
        with self.assertRaisesRegex(cp.PackError, 'material changed'):
            cp.verify(self.pack)

    def test_materials_cannot_escape_the_pack(self):
        data = self.read(); data['materials'] = ['../outside.md']
        self.write(data)
        with self.assertRaisesRegex(cp.PackError, 'inside the pack'):
            cp.freeze(self.pack, 'tester', AT)

    def test_unknown_agent_and_case_are_rejected(self):
        data = self.read(); data['roster']['fixed_team'] = ['no-such-agent']
        self.write(data)
        with self.assertRaisesRegex(cp.PackError, 'unknown agent'):
            cp.freeze(self.pack, 'tester', AT)
        data['roster']['fixed_team'] = ['research-synthesist']; data['case_ref'] = 'no-such-case'
        self.write(data)
        with self.assertRaisesRegex(cp.PackError, 'case_ref'):
            cp.freeze(self.pack, 'tester', AT)

    def test_output_contract_needs_level_two_headings(self):
        data = self.read(); data['output_contract']['required_sections'] = ['Decision']
        self.write(data)
        with self.assertRaisesRegex(cp.PackError, 'level-2'):
            cp.freeze(self.pack, 'tester', AT)

    def test_invalid_nexus_instance_is_rejected(self):
        instance = json.loads((self.pack / 'instance.json').read_text())
        instance['tasks'][0]['agent'] = 'marketing-growth-hacker'
        (self.pack / 'instance.json').write_text(json.dumps(instance))
        with self.assertRaisesRegex(cp.PackError, 'nexus_instance'):
            cp.freeze(self.pack, 'tester', AT)

    def test_id_must_match_directory_and_split_is_closed(self):
        data = self.read(); data['split'] = 'test'
        self.write(data)
        with self.assertRaisesRegex(cp.PackError, 'split'):
            cp.freeze(self.pack, 'tester', AT)
        data['split'] = 'held_out'; data['id'] = 'other'
        self.write(data)
        with self.assertRaisesRegex(cp.PackError, 'directory name'):
            cp.freeze(self.pack, 'tester', AT)

    def test_scaffold_refuses_to_validate_until_every_todo_is_written(self):
        target = Path(self.temp.name) / 'new-case'
        cp.scaffold(target, 'outside-author', 'level-inversion')
        with self.assertRaisesRegex(cp.PackError, 'unfilled TODO'):
            cp.freeze(target, 'outside-author', AT)
        data = json.loads((target / 'pack.json').read_text())
        data['brief'] = 'Decide whether to extend the pilot.'
        data['constraints'] = ['Two-page limit']; data['permitted_evidence'] = ['The attached memo']
        data['rubric'] = {k: [f'{k} example'] for k in cp.RUBRIC_KEYS}
        (target / 'pack.json').write_text(json.dumps(data))
        self.assertEqual('held_out', cp.freeze(target, 'outside-author', AT)['split'])
        with self.assertRaisesRegex(cp.PackError, 'already exists'):
            cp.scaffold(target, 'outside-author', 'level-inversion')

    def test_a_held_out_pack_cannot_be_started_inside_the_public_checkout(self):
        target = ROOT / 'examples/nexus/casepacks/never-created-held-out'
        with self.assertRaisesRegex(cp.PackError, 'outside this public checkout'):
            cp.scaffold(target, 'outside-author', 'level-inversion')
        self.assertFalse(target.exists())
        alias = Path(self.temp.name) / 'alias'
        alias.symlink_to(ROOT / 'examples', target_is_directory=True)
        with self.assertRaisesRegex(cp.PackError, 'outside this public checkout'):
            cp.scaffold(alias / 'never-created-held-out', 'outside-author', 'level-inversion')
        self.assertFalse((ROOT / 'examples/never-created-held-out').exists())

    def test_a_held_out_pack_inside_the_checkout_cannot_be_frozen(self):
        original, sandbox = cp.in_checkout, Path(self.temp.name).resolve()
        cp.in_checkout = lambda path: sandbox in Path(path).resolve().parents  # sandbox stands in for the checkout
        data = self.read(); data['split'] = 'held_out'; self.write(data)
        try:
            with self.assertRaisesRegex(cp.PackError, 'outside this public checkout'):
                cp.freeze(self.pack, 'tester', AT)
            data = self.read(); data['split'] = 'development'; self.write(data)
            self.assertEqual('development', cp.freeze(self.pack, 'tester', AT)['split'])
        finally:
            cp.in_checkout = original

    def test_the_authoring_guide_keeps_held_out_packs_out_of_the_repository(self):
        guide = (ROOT / 'strategy/NEXUS-CASEPACK-AUTHORING.md').read_text()
        blocks = guide.split('```bash')[1:]
        commands = ' '.join(' '.join(block.split('```')[0] for block in blocks).replace('\\', ' ').split())
        self.assertIn('nexus-casepack.py new', commands)
        for public in ('casepack.py new examples/', 'casepack.py freeze examples/', '--held-out examples/'):
            self.assertNotIn(public, commands)
        self.assertNotIn('Submit held-out packs in a', guide)
        self.assertIn('Never commit a held-out pack', guide)


if __name__ == '__main__':
    unittest.main()
