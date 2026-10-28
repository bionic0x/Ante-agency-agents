"""Second-line mechanisms: stale claims, the discard archive, weak signals, the read-only deck."""
import contextlib
import hashlib
import io as stdio
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from ante import cli, deck  # noqa: E402
from ante.learn import boxmaker, signals  # noqa: E402
from ante.strategy import ghosts  # noqa: E402
from test_strategy import Chain, load  # noqa: E402


def tree_digest(directory: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(directory.rglob('*')):
        if path.is_file():
            digest.update(path.name.encode() + path.read_bytes())
    return digest.hexdigest()


class Case(unittest.TestCase):
    def setUp(self):
        self.chain = Chain()
        self.addCleanup(self.chain.close)

    def run_cli(self, *argv):
        out, err = stdio.StringIO(), stdio.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = cli.main([str(a) for a in argv])
        return code, out.getvalue(), err.getvalue()


class Ghosts(Case):
    def test_an_expired_claim_still_cited_is_a_ghost(self):
        frame = load('frame')
        frame['claims'][0]['expires'] = '2026-11-15'      # cap-100, cited by map, options, cohere
        self.chain.run('frame', frame)
        for command, parents in (('map', ['frame']), ('cause', ['frame', 'map'])):
            self.assertEqual(0, self.chain.run(command, load(command), parents)[0])
        self.assertEqual([], ghosts.audit(self.chain.out, '2026-11-01T00:00:00Z')['ghosts'])
        found = ghosts.audit(self.chain.out, '2026-11-20T00:00:00Z')['ghosts']
        self.assertEqual(['cap-100'], [g['claim'] for g in found])
        self.assertTrue(found[0]['cited_by'])
        code, _, _ = self.run_cli('ghosts', '--artifacts', self.chain.out, '--at', '2026-11-20T00:00:00Z')
        self.assertEqual(1, code)

    def test_claims_before_a_declared_regime_change_are_ghosts_until_renewed(self):
        self.chain.build('cause')
        regimes = self.chain.dir / 'regimes.json'
        regimes.write_text(json.dumps({'changes': [{'id': 'new-funding-rules', 'at': '2026-10-23T00:00:00Z',
                                                    'scope': 'funder deadlines',
                                                    'description': 'funders moved to rolling deadlines'}]}))
        found = ghosts.audit(self.chain.out, '2026-10-28T23:00:00Z', ghosts._regimes(str(regimes)))['ghosts']
        self.assertIn('demand-110', [g['claim'] for g in found])   # dated 2026-10-21, cited downstream

    def test_a_case_whose_decision_expired_is_not_live(self):
        self.chain.build()
        self.assertLess(self.chain.artefact('decide')['body']['expires'], '2030-01-01')
        result = ghosts.audit(self.chain.out, '2030-01-01T00:00:00Z')
        self.assertFalse(result['live'])
        self.assertEqual([], result['ghosts'])


class Boxmaker(Case):
    def test_discarded_material_is_archived_with_its_reason_and_returns_only_as_hypothesis(self):
        self.chain.build('ach')
        box = boxmaker.build('2026-10-29T00:00:00Z', [str(self.chain.out)])
        kinds = {item['kind'] for item in box['items']}
        self.assertTrue({'discarded_option', 'rejected_hypothesis'} <= kinds)
        self.assertTrue(all(item['reason'] for item in box['items']))
        claims = boxmaker.recombine(box, [box['items'][0]['id']], '2026-10-29T00:00:00Z')['claims']
        self.assertEqual(['HYPOTHESIS'], [c['status'] for c in claims])
        self.assertEqual('system', claims[0]['source']['origin'])
        options = load('options')
        promoted = dict(claims[0], status='EVIDENCE')
        options['claims'] = [promoted]
        code, _, err = self.chain.run('options', options, ['cause', 'frame', 'map'], out=self.chain.dir / 'x')
        self.assertEqual(2, code)
        self.assertIn('SELF_CORROBORATION', err)
        options['claims'] = claims
        self.assertEqual(0, self.chain.run('options', options, ['cause', 'frame', 'map'], out=self.chain.dir / 'y')[0])


class Signals(Case):
    def spec(self, ident='s1', first='2026-09-01T00:00:00Z'):
        path = self.chain.dir / f'{ident}.json'
        path.write_text(json.dumps({'id': ident, 'observed': 'a funder accepts rolling deadlines',
                                    'topic': 'funding', 'first_observed_at': first, 'where': 'funder B newsletter',
                                    'source': {'ref': 'newsletter-2026-09', 'origin': 'external'},
                                    'note': 'one funder only'}))
        return str(path)

    def test_signals_export_as_hypotheses_without_probability(self):
        register = str(self.chain.dir / 'signals.jsonl')
        signals.add(self.spec(), register, '2026-09-02T00:00:00Z')
        with self.assertRaisesRegex(signals.SignalError, 'before it was observed'):
            signals.add(self.spec('s2', '2026-12-01T00:00:00Z'), register, '2026-10-01T00:00:00Z')
        with self.assertRaisesRegex(signals.SignalError, 'already registered'):
            signals.add(self.spec(), register, '2026-10-01T00:00:00Z')
        exported = signals.export(register, '2026-10-28T00:00:00Z', 'fund')['claims']
        self.assertEqual(['HYPOTHESIS'], [c['status'] for c in exported])
        self.assertNotIn('probability', json.dumps(exported))
        self.assertEqual([], signals.export(register, '2026-09-01T12:00:00Z')['claims'])
        frame = load('frame')
        frame['claims'] += exported
        self.assertEqual(0, self.chain.run('frame', frame)[0])


class Deck(Case):
    def test_the_deck_shows_the_chain_and_writes_nothing(self):
        self.chain.build()
        before = tree_digest(self.chain.out)
        code, out, _ = self.run_cli('deck', '--artifacts', self.chain.out, '--plain')
        self.assertEqual(0, code)
        self.assertIn('ANTE DECK  case lab-consortium', out)
        self.assertIn('BLOCKING', out)
        self.assertIn('independent', out)
        self.assertEqual(before, tree_digest(self.chain.out))
        view = deck.model(str(self.chain.out))
        self.assertEqual('decide', view['nodes'][-1]['command'])
        self.assertIn('slack-20', view['blocking'])

    def test_a_broken_chain_is_reported_not_rendered(self):
        self.chain.build('cause')
        (self.chain.out / 'map.json').unlink()
        self.assertEqual(3, self.run_cli('deck', '--artifacts', self.chain.out, '--plain')[0])


if __name__ == '__main__':
    unittest.main()
