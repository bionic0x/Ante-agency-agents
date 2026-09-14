#!/usr/bin/env python3
"""Exercise runbook closure validation in a disposable Git fixture."""
import copy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class TerminationContractTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / 'scripts').mkdir()
        shutil.copy2(ROOT / 'scripts/check-runbooks.sh', self.root / 'scripts')
        registry_bytes = (ROOT / 'strategy/runbooks.json').read_bytes().replace(b'\r\n', b'\n')
        self.registry_sha256 = hashlib.sha256(registry_bytes).hexdigest()
        self.data = json.loads(registry_bytes)
        # Keep the real registry's references; only their existence matters here.
        for rb in self.data['runbooks']:
            for path in [rb['doc'], *rb['required_artifacts']]:
                dest = self.root / path
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.touch()
            for group in rb['roster']:
                for slug in group['agents']:
                    dest = self.root / 'specialized' / (slug + '.md')
                    dest.parent.mkdir(exist_ok=True)
                    dest.touch()
        subprocess.run(['git', 'init', '-q'], cwd=self.root, check=True)
        subprocess.run(['git', 'add', '.'], cwd=self.root, check=True)
        self.index = next(i for i, rb in enumerate(self.data['runbooks'])
                          if rb['slug'] == 'marketing-mispricing-diagnostic')

    def check(self, value, expected, message, *, field='termination_contract', omit=False):
        data = copy.deepcopy(self.data)
        rb = data['runbooks'][self.index]
        if omit:
            rb.pop(field, None)
        else:
            rb[field] = value
        (self.root / 'strategy/runbooks.json').write_text(json.dumps(data))
        result = subprocess.run(['bash', 'scripts/check-runbooks.sh'], cwd=self.root,
                                text=True, capture_output=True)
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        self.assertIn(message, result.stdout)

    def test_registry_has_eight_substantive_contracts(self):
        print(f'runbooks.json sha256={self.registry_sha256}')
        self.assertEqual(8, len(self.data['runbooks']))
        required = {'achieved', 'outstanding', 'accountable', 'on_breach'}
        for rb in self.data['runbooks']:
            with self.subTest(runbook=rb['slug']):
                contract = rb.get('termination_contract')
                self.assertIsInstance(contract, dict)
                self.assertTrue(required.issubset(contract))
                for key in required:
                    value = contract[key]
                    self.assertIsInstance(value, str)
                    self.assertGreater(len(value.strip()), 20)
                # A structured contract must add closure semantics rather than
                # copy the one-line termination criterion into four fields.
                self.assertEqual(4, len({contract[key].strip() for key in required}))
                self.assertNotIn(rb['termination_criteria'].strip(),
                                 {contract[key].strip() for key in required})

    def test_valid_contract_and_absent_contract_is_failure(self):
        self.check(self.data['runbooks'][self.index]['termination_contract'], 0,
                   '8/8 termination contracts')
        self.check(None, 1, "missing required field 'termination_contract'", omit=True)

    def test_explicit_invalid_contract_is_not_advisory(self):
        for value in (None, [], '', 'TBD', 4):
            with self.subTest(value=value):
                self.check(value, 1, 'termination_contract must be an object')

    def test_required_fields_and_unknown_keys(self):
        valid = self.data['runbooks'][self.index]['termination_contract']
        for key in ('achieved', 'outstanding', 'accountable', 'on_breach'):
            with self.subTest(key=key):
                contract = dict(valid)
                del contract[key]
                self.check(contract, 1, f"missing {key!r}")
                contract[key] = '  TbD  '
                self.check(contract, 1, f'termination_contract.{key}')
        self.check({**valid, 'achived': 'Typo'}, 1, 'unknown key(s): achived')

    def test_optional_fields_are_validated_when_present(self):
        valid = self.data['runbooks'][self.index]['termination_contract']
        required = {k: v for k, v in valid.items() if k not in ('conservation_resources', 'revision_conditions')}
        self.check(required, 0, '8/8 termination contracts')
        for key in ('conservation_resources', 'revision_conditions'):
            for value in (None, [], '  ', 'pending'):
                with self.subTest(key=key, value=value):
                    self.check({**valid, key: value}, 1, f'termination_contract.{key}')

    def test_criteria_reject_placeholders_without_a_word_count_rule(self):
        for value in ('TBD', '  unknown  ', 'N/A', '--', 'None'):
            with self.subTest(value=value):
                self.check(value, 1, 'termination_criteria is a placeholder', field='termination_criteria')
        self.check('Stop when funds expire.', 0, 'PASSED:', field='termination_criteria')


if __name__ == '__main__':
    unittest.main()
