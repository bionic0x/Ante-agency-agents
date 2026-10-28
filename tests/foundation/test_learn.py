"""Learning layer: ledger chain, reconciliation rules, calibration, guarded patterns."""
import contextlib
import io as stdio
import json
import random
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from ante import cli  # noqa: E402
from ante.constructs import frozen, snapshot  # noqa: E402
from ante.core import canon  # noqa: E402
from ante.learn import apophenia, commands, ledger  # noqa: E402
from ante.strategy.artifact import seal  # noqa: E402

T0 = '2026-10-28T12:00:00Z'


def decide_artifact(case, verdict='PROCEED_WITH_CONDITIONS', pathologies=(), review='SEPARATED_CONTEXT',
                    expectations=None, at=T0):
    expectations = expectations or [{'id': 'e1', 'what_should_change': 'x', 'in_whom': 'y',
                                     'horizon': '2026-12-01T00:00:00Z', 'refuted_by': 'z',
                                     'probability': {'verbal': 'likely', 'interval': [0.6, 0.8]}}]
    return seal({'schema_version': 1, 'command': 'decide', 'case_id': case, 'at': at,
                 'input_sha256': canon.digest(case), 'parents': [], 'independence_level': None, 'claims': [],
                 'body': {'verdict': verdict, 'review_independence': review,
                          'detected_pathologies': list(pathologies), 'expectations': expectations,
                          'snapshot': snapshot.build(at, [], [], expectations, verdict)},
                 'findings': [], 'verdict': verdict, 'next_decision': 'n'})


class Workspace(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix='ante-learn-'))
        self.ledger = str(self.dir / 'ledger.jsonl')

    def write(self, name, value):
        path = self.dir / name
        path.write_text(json.dumps(value))
        return str(path)

    def record(self, art, synthetic=False, runbook='strategic-decision', agent='agent-a', at='2026-10-28T13:00:00Z'):
        return commands.record(self.write(f'{art["artifact_sha256"][:12]}.json', art), self.ledger, at, runbook,
                               agent, synthetic)

    def observe(self, art, outcome, expectation='e1', origin='external', at='2026-12-02T00:00:00Z',
                observed_at='2026-12-01T00:00:00Z'):
        doc = {'observations': [{'decision': art['artifact_sha256'], 'expectation': expectation, 'outcome': outcome,
                                 'observed': 'measured', 'source': {'ref': 'audit', 'origin': origin},
                                 'observed_at': observed_at}]}
        return commands.reconcile(self.write('obs.json', doc), self.ledger, at)


class LedgerChain(Workspace):
    def test_appends_chain_and_verify(self):
        self.record(decide_artifact('a'))
        self.record(decide_artifact('b'))
        entries = ledger.read(self.ledger)
        self.assertEqual([1, 2], [e['seq'] for e in entries])
        self.assertEqual(entries[0]['entry_hash'], entries[1]['prev_hash'])

    def test_edited_or_removed_line_breaks_the_chain(self):
        self.record(decide_artifact('a'))
        self.record(decide_artifact('b'))
        lines = Path(self.ledger).read_text().splitlines()
        Path(self.ledger).write_text(lines[0].replace('"synthetic":false', '"synthetic":true') + '\n' + lines[1] + '\n')
        with self.assertRaisesRegex(ledger.LedgerError, 'does not match'):
            ledger.read(self.ledger)
        Path(self.ledger).write_text(lines[1] + '\n')
        with self.assertRaisesRegex(ledger.LedgerError, 'chain broken'):
            ledger.read(self.ledger)

    def test_cli_reports_a_broken_chain_with_exit_3(self):
        self.record(decide_artifact('a'))
        Path(self.ledger).write_text(Path(self.ledger).read_text().replace('agent-a', 'agent-b'))
        with contextlib.redirect_stdout(stdio.StringIO()), contextlib.redirect_stderr(stdio.StringIO()):
            self.assertEqual(3, cli.main(['learn', 'verify', '--ledger', self.ledger]))

    def test_entries_are_appended_in_time_order(self):
        self.record(decide_artifact('a'), at='2026-10-29T00:00:00Z')
        with self.assertRaisesRegex(ledger.LedgerError, 'time order'):
            self.record(decide_artifact('b'), at='2026-10-28T23:00:00Z')


class Record(Workspace):
    def test_only_sealed_decisions_once_and_not_before_they_were_taken(self):
        art = decide_artifact('a')
        not_decide = dict(art, command='cohere')
        with self.assertRaises(Exception):
            commands.record(self.write('x.json', not_decide), self.ledger, T0, None, None, False)
        self.record(art)
        with self.assertRaisesRegex(commands.LearnError, 'already'):
            self.record(art, at='2026-10-29T00:00:00Z')
        with self.assertRaisesRegex(commands.LearnError, 'before it was taken'):
            self.record(decide_artifact('c', at='2026-11-01T00:00:00Z'), at='2026-10-30T00:00:00Z')


class Reconcile(Workspace):
    def setUp(self):
        super().setUp()
        self.art = decide_artifact('a')
        self.record(self.art)

    def test_outcome_is_a_new_entry_and_the_prediction_is_untouched(self):
        before = ledger.read(self.ledger)[0]
        self.observe(self.art, 'CONFIRMED')
        entries = ledger.read(self.ledger)
        self.assertEqual(before, entries[0])
        self.assertEqual('reconciliation', entries[1]['kind'])
        self.assertEqual(before['entry_hash'], entries[1]['payload']['decision_entry'])

    def test_system_sources_cannot_confirm_or_refute(self):
        with self.assertRaisesRegex(Exception, 'system-produced'):
            self.observe(self.art, 'CONFIRMED', origin='system')
        self.observe(self.art, 'INCONCLUSIVE', origin='system')

    def test_unknown_expectation_and_pre_decision_observation_fail(self):
        with self.assertRaisesRegex(Exception, 'not an expectation'):
            self.observe(self.art, 'CONFIRMED', expectation='e9')
        with self.assertRaisesRegex(Exception, 'before the decision'):
            self.observe(self.art, 'CONFIRMED', observed_at='2026-10-01T00:00:00Z')

    def test_not_yet_observable_only_before_the_horizon(self):
        self.observe(self.art, 'NOT_YET_OBSERVABLE', at='2026-11-15T00:00:00Z', observed_at='2026-11-14T00:00:00Z')
        with self.assertRaisesRegex(Exception, 'horizon has passed'):
            self.observe(self.art, 'NOT_YET_OBSERVABLE')


class Calibrate(Workspace):
    def test_below_the_minimum_the_answer_is_insufficient_sample(self):
        arts = [decide_artifact(f'c{index}') for index in range(3)]
        for art in arts:
            self.record(art)
        for index, art in enumerate(arts):
            self.observe(art, 'CONFIRMED', at=f'2026-12-0{index + 2}T00:00:00Z')
        result = commands.calibrate(self.ledger, '2026-12-31T00:00:00Z', min_sample=5)
        overall = result['groups'][0]
        self.assertEqual(('INSUFFICIENT_SAMPLE', None, 3), (overall['result'], overall['brier'], overall['n']))

    def test_synthetic_decisions_never_enter_calibration(self):
        art = decide_artifact('syn')
        self.record(art, synthetic=True)
        self.observe(art, 'REFUTED')
        result = commands.calibrate(self.ledger, '2026-12-31T00:00:00Z', min_sample=1)
        self.assertEqual(0, result['decisive_predictions'])
        self.assertEqual(1, result['excluded']['synthetic'])

    def test_brier_is_measured_on_the_declared_midpoint(self):
        outcomes = ['CONFIRMED', 'CONFIRMED', 'REFUTED', 'CONFIRMED']
        arts = [decide_artifact(f'm{index}') for index in range(len(outcomes))]
        for index, art in enumerate(arts):
            self.record(art, agent='agent-b' if index % 2 else 'agent-a')
        for index, (art, outcome) in enumerate(zip(arts, outcomes)):
            self.observe(art, outcome, at=f'2026-12-0{index + 2}T00:00:00Z')
        result = commands.calibrate(self.ledger, '2026-12-31T00:00:00Z', min_sample=4)
        overall = result['groups'][0]
        expected = (3 * (0.7 - 1) ** 2 + (0.7 - 0) ** 2) / 4
        self.assertEqual('MEASURED', overall['result'])
        self.assertAlmostEqual(expected, overall['brier'], places=6)
        by_agent = [g for g in result['groups'] if g['dimension'] == 'agent']
        self.assertTrue(all(g['result'] == 'INSUFFICIENT_SAMPLE' for g in by_agent))

    def test_latest_reconciliation_wins_without_rewriting(self):
        art = decide_artifact('x')
        self.record(art)
        self.observe(art, 'CONFIRMED')
        self.observe(art, 'REFUTED', at='2026-12-03T00:00:00Z')
        result = commands.calibrate(self.ledger, '2026-12-31T00:00:00Z', min_sample=1)
        self.assertAlmostEqual(0.49, result['groups'][0]['brier'], places=6)


class Patterns(Workspace):
    def build(self, n, refuted_if, seed=7):
        rng = random.Random(seed)
        made = []
        for index in range(n):
            pathologies = ['metric_substitution'] if rng.random() < 0.5 else []
            art = decide_artifact(f'p{index}', pathologies=pathologies)
            self.record(art, at=f'2026-10-28T13:{index:02d}:00Z')
            made.append((art, 'REFUTED' if refuted_if(pathologies, rng) else 'CONFIRMED'))
        for index, (art, outcome) in enumerate(made):
            self.observe(art, outcome, at=f'2026-12-02T00:{index:02d}:00Z')

    def test_a_pattern_injected_in_noise_does_not_pass_the_guard(self):
        self.build(40, lambda pathologies, rng: rng.random() < 0.5)
        result = commands.patterns(self.ledger, '2026-12-31T00:00:00Z', min_group=3)
        self.assertFalse(result['learned_anything'])
        self.assertGreater(result['features_tested'], 0)
        self.assertEqual(result['features_tested'], len(result['tested']))

    def test_a_real_difference_is_proposed_with_its_genealogy(self):
        self.build(40, lambda pathologies, rng: bool(pathologies))
        result = commands.patterns(self.ledger, '2026-12-31T00:00:00Z', min_group=3)
        features = [p['feature'] for p in result['proposals']]
        self.assertEqual(['pathology:metric_substitution'], features)
        proposal = result['proposals'][0]
        self.assertEqual('PROPOSAL', proposal['status'])
        self.assertTrue(proposal['sources'][0]['outcome_entries'])

    def test_patterns_are_reproducible_with_the_fixed_seed(self):
        self.build(30, lambda pathologies, rng: bool(pathologies) or rng.random() < 0.2)
        first = commands.patterns(self.ledger, '2026-12-31T00:00:00Z', min_group=3)
        second = commands.patterns(self.ledger, '2026-12-31T00:00:00Z', min_group=3)
        self.assertEqual(first, second)

    def test_without_reconciled_decisions_nothing_is_learned(self):
        self.record(decide_artifact('lonely'))
        result = commands.patterns(self.ledger, '2026-12-31T00:00:00Z', min_group=3)
        self.assertEqual((0, False), (result['decisions_used'], result['learned_anything']))


class Constructs(Workspace):
    def test_learn_cannot_write_into_a_construct(self):
        art = decide_artifact('a')
        for target in (ROOT / 'specialized/strategic-red-team.md', ROOT / 'ante/constructs/ledger.jsonl'):
            before = target.read_bytes() if target.exists() else None
            with self.assertRaises(frozen.ConstructError):
                commands.record(self.write('a.json', art), str(target), '2026-10-28T13:00:00Z', None, None, False)
            self.assertEqual(before, target.read_bytes() if target.exists() else None)
        self.assertEqual([], frozen.verify())

    def test_reconcile_compares_only_against_the_frozen_snapshot(self):
        art = decide_artifact('a')
        # A record whose visible expectations were edited after the snapshot was taken
        # (and then resealed) cannot be recorded: the snapshot no longer matches.
        body = dict(art['body'], snapshot=dict(art['body']['snapshot'], expectations=[]))
        resealed = seal({**{k: v for k, v in art.items() if k != 'artifact_sha256'}, 'body': body})
        with self.assertRaisesRegex(commands.LearnError, 'snapshot'):
            commands.record(self.write('r.json', resealed), self.ledger, '2026-10-28T13:00:00Z', None, None, False)
        # Expectations added to the body but absent from the snapshot are not reconcilable.
        extra = dict(art['body'], expectations=art['body']['expectations'] + [
            dict(art['body']['expectations'][0], id='e2')])
        late = seal({**{k: v for k, v in art.items() if k != 'artifact_sha256'}, 'body': extra})
        self.record(late)
        with self.assertRaisesRegex(Exception, 'not an expectation'):
            self.observe(late, 'CONFIRMED', expectation='e2')
        self.observe(late, 'CONFIRMED', expectation='e1')

    def test_frozen_reviewers_are_marked_in_calibration(self):
        art = decide_artifact('a')
        self.record(art, agent='strategic-red-team')
        self.observe(art, 'CONFIRMED')
        groups = commands.calibrate(self.ledger, '2026-12-31T00:00:00Z', min_sample=1)['groups']
        agent = next(g for g in groups if g['dimension'] == 'agent')
        self.assertTrue(agent['frozen_reviewer'])


class Guard(unittest.TestCase):
    def test_correction_scales_with_the_number_of_features_tested(self):
        rng = random.Random(3)
        samples = [({f'f{j}' for j in range(20) if rng.random() < 0.5}, rng.randint(0, 1)) for _ in range(60)]
        verdicts, tested = apophenia.guard(samples, [f'f{j}' for j in range(20)], rounds=500)
        self.assertEqual(20, tested)
        self.assertTrue(all(v.p_adjusted == min(1.0, v.p_value * 20) for v in verdicts))
        self.assertFalse(any(v.passes for v in verdicts))


if __name__ == '__main__':
    unittest.main()
