"""Runbook command chains, `ante run`, and unsigned model drafts."""
import contextlib
import copy
import io as stdio
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from ante import cli, registry  # noqa: E402
from ante.strategy import draft  # noqa: E402
from ante.strategy.commands import COMMANDS  # noqa: E402
from test_strategy import CONTRACTS, Chain, load  # noqa: E402


class RunbookChains(unittest.TestCase):
    def test_every_chain_names_real_commands_in_lineage_order(self):
        for slug, runbook in registry.runbooks().items():
            chain = runbook['strategy_commands']
            with self.subTest(runbook=slug):
                self.assertTrue(set(chain) <= set(COMMANDS), chain)
                for position, name in enumerate(chain):
                    for parent in COMMANDS[name].parents:
                        self.assertIn(parent, chain[:position], f'{name} needs {parent} earlier')
                for control in ('cohere', 'pathology', 'close', 'decide'):
                    self.assertIn(control, chain)

    def check_runbooks(self, mutate):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'scripts').mkdir()
            (root / 'strategy').mkdir()
            for name in ('scripts/check-runbooks.sh', 'scripts/build-catalog.py', 'divisions.json',
                         'strategy/contracts.json'):
                shutil.copy2(ROOT / name, root / name)
            data = json.loads((ROOT / 'strategy/runbooks.json').read_text())
            for rb in data['runbooks']:
                for path in [rb['doc'], *rb['required_artifacts']]:
                    (root / path).parent.mkdir(parents=True, exist_ok=True)
                    (root / path).touch()
            for division in json.loads((ROOT / 'divisions.json').read_text())['divisions']:
                if (ROOT / division).is_dir():
                    shutil.copytree(ROOT / division, root / division)
            mutate(data['runbooks'][0])
            (root / 'strategy/runbooks.json').write_text(json.dumps(data))
            subprocess.run(['git', 'init', '-q'], cwd=root, check=True)
            subprocess.run(['git', 'add', '.'], cwd=root, check=True)
            return subprocess.run(['bash', 'scripts/check-runbooks.sh'], cwd=root, capture_output=True, text=True)

    def test_check_runbooks_requires_the_four_controls(self):
        result = self.check_runbooks(lambda rb: rb['strategy_commands'].remove('pathology'))
        self.assertEqual(1, result.returncode)
        self.assertIn('lacks control command(s): pathology', result.stdout)

    def test_check_runbooks_accepts_a_reasoned_non_material_runbook(self):
        def mutate(rb):
            rb['material'] = 'informational briefing with no commitment'
            rb['strategy_commands'] = ['frame']
        self.assertEqual(0, self.check_runbooks(mutate).returncode)


class RunCheck(unittest.TestCase):
    def setUp(self):
        self.chain = Chain()
        self.addCleanup(self.chain.close)
        self.chain.build()
        self.chain.run('ach', load('ach'), ['frame'])

    def run_cli(self, *argv):
        out, err = stdio.StringIO(), stdio.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = cli.main(list(argv))
        return code, out.getvalue(), err.getvalue()

    def test_complete_chain(self):
        code, out, _ = self.run_cli('run', 'strategic-decision', '--artifacts', str(self.chain.out),
                                    '--contracts', CONTRACTS)
        self.assertEqual(0, code)
        self.assertEqual('PROCEED_WITH_CONDITIONS', json.loads(out)['verdict'])

    def test_a_chain_built_on_another_doctrine_is_not_complete(self):
        code, out, _ = self.run_cli('run', 'strategic-decision', '--artifacts', str(self.chain.out))
        self.assertEqual(1, code)
        self.assertEqual(['cohere', 'pathology'], json.loads(out)['non_canonical_doctrine'])

    def test_incomplete_chain(self):
        for name in ('react', 'nodal', 'decide'):   # nodal names react as a parent, decide names nodal
            (self.chain.out / f'{name}.json').unlink()
        code, out, _ = self.run_cli('run', 'strategic-decision', '--artifacts', str(self.chain.out))
        self.assertEqual(1, code)
        self.assertEqual(['react', 'decide'], json.loads(out)['missing'])

    def test_a_missing_parent_breaks_the_run(self):
        (self.chain.out / 'react.json').unlink()
        self.assertEqual(3, self.run_cli('run', 'strategic-decision', '--artifacts', str(self.chain.out))[0])

    def test_tampered_artefact_breaks_the_run(self):
        art = json.loads((self.chain.out / 'watch.json').read_text())
        art['body']['reserve']['what'] = '0 hours'
        (self.chain.out / 'watch.json').write_text(json.dumps(art))
        self.assertEqual(3, self.run_cli('run', 'strategic-decision', '--artifacts', str(self.chain.out))[0])


class Drafts(unittest.TestCase):
    def setUp(self):
        self.chain = Chain()
        self.addCleanup(self.chain.close)
        self.chain.build('frame')
        self.brief = self.chain.dir / 'brief.md'
        self.brief.write_text('Three universities share a laboratory; bookings conflict weekly.')
        self.calls = []
        original = dict(draft.ADAPTERS)
        self.addCleanup(lambda: (draft.ADAPTERS.clear(), draft.ADAPTERS.update(original)))

    def fake(self, reply):
        def adapter(model, prompt):
            self.calls.append((model, prompt))
            return reply
        draft.ADAPTERS['anthropic'] = adapter

    def run_draft(self, *extra):
        out, err = stdio.StringIO(), stdio.StringIO()
        argv = ['map', str(self.brief), '--from', str(self.chain.out / 'frame.json'), '--draft-with', 'anthropic',
                '--at', '2026-10-28T09:10:00Z', '--out', str(self.chain.dir / 'drafts'), *extra]
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = cli.main(argv)
        return code, err.getvalue()

    def test_draft_forces_hypothesis_and_cannot_be_chained(self):
        proposal = copy.deepcopy(load('map'))
        proposal['claims'][0]['status'] = 'EVIDENCE'
        self.fake('Here you go:\n```json\n' + json.dumps(proposal) + '\n```')
        code, err = self.run_draft('--model', 'claude-fixture')
        self.assertEqual(0, code, err)
        result = json.loads((self.chain.dir / 'drafts/map.draft.json').read_text())
        self.assertFalse(result['draft']['signed'])
        self.assertTrue(all(c['status'] == 'HYPOTHESIS' and c['source']['origin'] == 'system'
                            for c in result['input']['claims']))
        self.assertIn('ante map', self.calls[0][1])
        # The draft itself is not an input: running the command on it fails on the header.
        status, _, err = self.chain.run('map', result, ['frame'])
        self.assertEqual(2, status)
        self.assertIn('missing field(s) actors, claims', err)

    def test_model_is_explicit_and_provider_declared(self):
        self.fake('{}')
        self.assertIn('--model is required', self.run_draft()[1])
        code, err = self.run_draft('--model', 'x')
        self.assertEqual(0, code, err)
        out = stdio.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(stdio.StringIO()) as e:
            code = cli.main(['map', str(self.brief), '--from', str(self.chain.out / 'frame.json'),
                             '--draft-with', 'nobody', '--model', 'x', '--at', '2026-10-28T09:10:00Z'])
        self.assertEqual(2, code)
        self.assertIn('not declared', e.getvalue())

    def test_non_json_reply_is_refused(self):
        self.fake('I cannot help with that.')
        code, err = self.run_draft('--model', 'claude-fixture')
        self.assertEqual(2, code)
        self.assertIn('strict JSON object', err)


if __name__ == '__main__':
    unittest.main()
