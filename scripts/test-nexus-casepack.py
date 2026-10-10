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


if __name__ == '__main__':
    unittest.main()
