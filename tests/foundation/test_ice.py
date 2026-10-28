"""ICE layers and held-out canaries."""
import contextlib
import copy
import io as stdio
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from ante import cli  # noqa: E402
from ante.ice import canary, layers  # noqa: E402

PACK = ROOT / 'examples/nexus/casepacks/harbor-pricing-intent'
FAKE = 'ANTE-CANARY-' + '5a' * 16   # built at run time so this file carries no canary itself


class Layers(unittest.TestCase):
    def test_shipped_layers_are_functionally_independent(self):
        self.assertEqual([], layers.check(layers.load()))
        with contextlib.redirect_stdout(stdio.StringIO()):
            self.assertEqual(0, cli.main(['ice', 'layers']))

    def test_two_layers_on_the_same_data_or_assumption_fail(self):
        shipped = layers.load()
        shared_data = copy.deepcopy(shipped)
        shared_data[1]['data'].append(shared_data[0]['data'][0])
        self.assertTrue(any('same data' in p for p in layers.check(shared_data)))
        shared_assumption = copy.deepcopy(shipped)
        shared_assumption[4]['assumptions'] = list(shared_assumption[2]['assumptions'])
        self.assertTrue(any('same assumption' in p for p in layers.check(shared_assumption)))
        missing = [layer for layer in shipped if layer['function'] != 'recover']
        self.assertIn('no layer performs recover', layers.check(missing))

    def test_cli_fails_on_a_dependent_configuration(self):
        shipped = layers.load()
        shipped[1]['data'] = list(shipped[0]['data'])
        path = Path(tempfile.mkdtemp()) / 'layers.json'
        path.write_text(json.dumps({'layers': shipped}))
        with contextlib.redirect_stdout(stdio.StringIO()), contextlib.redirect_stderr(stdio.StringIO()):
            self.assertEqual(1, cli.main(['ice', 'layers', '--layers', str(path)]))


class Canaries(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix='ante-ice-'))
        self.pack = self.dir / 'packs' / PACK.name
        shutil.copytree(PACK, self.pack)
        doc = json.loads((self.pack / 'pack.json').read_text())
        doc.pop('frozen')
        (self.pack / 'pack.json').write_text(json.dumps(doc))
        self.registry = self.dir / 'packs' / 'canaries.json'

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_seed_writes_one_canary_per_pack_and_scan_attributes_it(self):
        result = canary.seed(str(self.pack), str(self.registry))
        self.assertEqual(['intel-digest.md', 'board-memo.md'], result['materials'])
        token = json.loads(self.registry.read_text())['canaries'][0]['canary']
        self.assertRegex(token, canary.PATTERN)
        self.assertIn(token, (self.pack / 'board-memo.md').read_text())
        leaked = self.dir / 'proposal.patch'
        leaked.write_text(f'+ the memo said {token}\n')
        hits = canary.scan([str(leaked)], str(self.registry))
        self.assertEqual([PACK.name], [h['pack'] for h in hits])
        with self.assertRaisesRegex(canary.CanaryError, 'already seeded'):
            canary.seed(str(self.pack), str(self.registry))

    def test_seeding_refuses_frozen_packs_development_packs_and_registries_in_the_checkout(self):
        with self.assertRaisesRegex(canary.CanaryError, 'frozen'):
            canary.seed(str(PACK), str(self.registry))
        with self.assertRaisesRegex(canary.CanaryError, 'outside the checkout'):
            canary.seed(str(self.pack), str(ROOT / 'canaries.json'))
        doc = json.loads((self.pack / 'pack.json').read_text())
        doc['split'] = 'development'
        (self.pack / 'pack.json').write_text(json.dumps(doc))
        with self.assertRaisesRegex(canary.CanaryError, 'held-out'):
            canary.seed(str(self.pack), str(self.registry))

    def test_scan_finds_the_format_without_a_registry_and_the_cli_exits_1(self):
        target = self.dir / 'calibration.json'
        target.write_text(json.dumps({'note': FAKE}))
        self.assertEqual([None], [h['pack'] for h in canary.scan([str(self.dir)])])
        with contextlib.redirect_stdout(stdio.StringIO()):
            self.assertEqual(1, cli.main(['ice', 'scan', str(target)]))
            target.write_text('{}')
            self.assertEqual(0, cli.main(['ice', 'scan', str(target)]))

    def test_the_checkout_itself_carries_no_canary(self):
        tracked = [p for p in ROOT.rglob('*') if p.is_file() and '.git' not in p.parts
                   and p.suffix in canary.TEXT_SUFFIXES and p.stat().st_size < 2_000_000]
        hits = [h for p in tracked for h in canary.scan_text(p.read_text(errors='replace'), str(p), {})]
        self.assertEqual([], hits)


if __name__ == '__main__':
    unittest.main()
