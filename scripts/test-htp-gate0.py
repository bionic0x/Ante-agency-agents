#!/usr/bin/env python3
"""Failure cases for the Gate 0 checker on disposable strategy copies."""
import importlib.util
from pathlib import Path
import shutil
import tempfile
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('htp', ROOT / 'scripts/check-htp-gate0.py')
htp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(htp)
INSTANCE = 'strategy/htp-gate0/instances/2026-09-13-kamino-aave'


class Gate0Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        # Tests only edit the copied strategy tree; catalog inputs are shared.
        for entry in ROOT.iterdir():
            if entry.name not in ('strategy', '.git'):
                (self.tmp / entry.name).symlink_to(entry)
        shutil.copytree(ROOT / 'strategy', self.tmp / 'strategy')

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def edit(self, name, mutate):
        path = self.tmp / INSTANCE / name
        doc = yaml.safe_load(path.read_text())
        mutate(doc)
        path.write_text(yaml.safe_dump(doc, sort_keys=False))

    def assertError(self, fragment):
        errors = htp.check(self.tmp)
        self.assertTrue(any(fragment in e for e in errors), errors)

    def test_repository_artifacts_pass(self):
        self.assertEqual([], htp.check(ROOT))

    def test_cross_network_handoff_rejected(self):
        self.edit('handoff-e1-sol-to-s1.yaml', lambda d: d['handoff'].update(artifact_ref=f'{INSTANCE}/arbitrum-aave-manifest.yaml'))
        self.assertError('cross-network handoff')

    def test_dual_network_scope_rejected(self):
        self.edit('handoff-e1-arb-to-s1.yaml', lambda d: d['handoff'].update(network_scope='solana | arbitrum_one'))
        self.assertError('exactly one network')

    def test_live_action_must_stay_prohibited_without_authority(self):
        self.edit('handoff-e1-sol-to-s1.yaml', lambda d: d['handoff']['prohibited_actions'].remove('transaction_signing'))
        self.assertError('transaction_signing')

    def test_evidence_ladder_enforced(self):
        self.edit('handoff-e1-sol-to-s1.yaml', lambda d: d['handoff'].update(evidence_status='production_ready'))
        self.assertError('evidence ladder')

    def test_unknown_agent_rejected(self):
        self.edit('handoff-e1-arb-to-s1.yaml', lambda d: d['handoff'].update(to_agent='marketing-growth-hacker'))
        self.assertError('HTP roster')

    def test_stale_freeze_date_rejected(self):
        self.edit('handoff-e1-sol-to-s1.yaml', lambda d: d['handoff'].update(artifact_freeze_date='2026-09-01'))
        self.assertError('frozen_at')

    def test_missing_both_freeze_dates_rejected(self):
        self.edit('handoff-e1-sol-to-s1.yaml', lambda d: d['handoff'].pop('artifact_freeze_date'))
        self.edit('solana-kamino-manifest.yaml', lambda d: d['manifest'].pop('frozen_at'))
        self.assertError('frozen_at')

    def test_blank_authority_cannot_allow_live_action(self):
        def mutate(d):
            d['handoff']['authority_ref'] = '  '
            d['handoff']['prohibited_actions'].remove('transaction_signing')
        self.edit('handoff-e1-sol-to-s1.yaml', mutate)
        self.assertError('transaction_signing')

    def test_allowed_and_prohibited_overlap_rejected(self):
        self.edit('handoff-e1-sol-to-s1.yaml', lambda d: d['handoff']['allowed_tools'].append('transaction_signing'))
        self.assertError('both allowed and prohibited')

    def test_missing_manifest_rejected(self):
        self.edit('handoff-e1-sol-to-s1.yaml', lambda d: d['handoff'].update(artifact_ref='missing.yaml'))
        self.assertError('does not resolve')

    def test_empty_handoff_inventory_rejected(self):
        for p in (self.tmp / 'strategy/htp-gate0/instances').glob('*/handoff-*.yaml'):
            p.unlink()
        self.assertError('at least one')

    def test_malformed_handoff_rejected(self):
        self.edit('handoff-e1-sol-to-s1.yaml', lambda d: d.update(handoff=[]))
        self.assertError('handoff mapping')


if __name__ == '__main__':
    unittest.main()
