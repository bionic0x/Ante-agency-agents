"""Strategy commands: the full example chain, every minimum validation, and lineage.

Each test starts from the synthetic laboratory-consortium inputs
(examples/foundation/lab-consortium/input), changes one thing, and checks the
exit status and the finding code. Doctrine tables come from the D-004 proposal
until strategy/contracts.json carries them.
"""
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

INPUTS = ROOT / 'examples/foundation/lab-consortium/input'
CONTRACTS = str(ROOT / 'foundation/proposals/contracts-v2.json')
DOCTRINE_COMMANDS = {'cohere', 'pathology', 'decide'}
PLAN = [  # command, parents
    ('frame', []), ('map', ['frame']), ('cause', ['frame', 'map']), ('focus', ['map']),
    ('options', ['cause', 'frame', 'map']), ('react', ['options', 'map']), ('ach', ['frame']),
    ('watch', ['options']), ('close', ['frame']), ('cohere', ['frame', 'cause', 'map']),
    ('pathology', ['frame', 'map']),
    ('decide', ['frame', 'cohere', 'pathology', 'close', 'cause']),
]


def load(name):
    return json.loads((INPUTS / f'{name}.json').read_text())


class Chain:
    """A temporary case directory with helpers to run commands in-process."""

    def __init__(self):
        self.dir = Path(tempfile.mkdtemp(prefix='ante-chain-'))
        self.out = self.dir / 'out'

    def close(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def run(self, command, doc, parents=(), contracts=True, out=None, at=None):
        path = self.dir / f'{command}.input.json'
        path.write_text(json.dumps(doc), encoding='utf-8')
        argv = [command, str(path), '--out', str(out or self.out)]
        for parent in parents:
            argv += ['--from', str(parent if isinstance(parent, Path) else self.out / f'{parent}.json')]
        if contracts and command in DOCTRINE_COMMANDS:
            argv += ['--contracts', CONTRACTS]
        if at:
            argv += ['--at', at]
        stdout, stderr = stdio.StringIO(), stdio.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = cli.main(argv)
        return code, stdout.getvalue(), stderr.getvalue()

    def build(self, until=None):
        for command, parents in PLAN:
            code, _, err = self.run(command, load(command), parents)
            if code != 0:
                raise AssertionError(f'{command} failed: {err}')
            if command == until:
                return

    def artefact(self, command):
        return json.loads((self.out / f'{command}.json').read_text())


class Base(unittest.TestCase):
    def setUp(self):
        self.chain = Chain()
        self.addCleanup(self.chain.close)

    def rejects(self, command, doc, code, parents=None, exit_code=2):
        parents = parents if parents is not None else dict(PLAN)[command]
        status, _, err = self.chain.run(command, doc, parents, out=self.chain.dir / 'rejected')
        self.assertEqual(exit_code, status, err)
        self.assertIn(code, err)
        return err


class FullChain(Base):
    def test_example_chain_runs_end_to_end(self):
        self.chain.build()
        decision = self.chain.artefact('decide')
        self.assertEqual('PROCEED_WITH_CONDITIONS', decision['verdict'])
        self.assertIn('does not itself grant', decision['body']['authority'])
        self.assertTrue((self.chain.out / 'decide.md').read_text().startswith('# ante decide'))

    def test_same_input_same_at_same_bytes(self):
        first = self.chain.run('frame', load('frame'), out=self.chain.dir / 'a')
        second = self.chain.run('frame', load('frame'), out=self.chain.dir / 'b')
        self.assertEqual((0, 0), (first[0], second[0]))
        self.assertEqual((self.chain.dir / 'a/frame.json').read_bytes(), (self.chain.dir / 'b/frame.json').read_bytes())

    def test_at_flag_overrides_and_is_normalised(self):
        doc = load('frame')
        del doc['at']
        self.assertEqual(2, self.chain.run('frame', doc)[0])
        code, _, _ = self.chain.run('frame', doc, at='2026-10-28T10:00:00+01:00')
        self.assertEqual(0, code)
        self.assertEqual('2026-10-28T09:00:00Z', self.chain.artefact('frame')['at'])

    def test_stdout_without_out(self):
        path = self.chain.dir / 'f.json'
        path.write_text(json.dumps(load('frame')))
        buffer = stdio.StringIO()
        with contextlib.redirect_stdout(buffer):
            self.assertEqual(0, cli.main(['frame', str(path)]))
        self.assertEqual('frame', json.loads(buffer.getvalue())['command'])


class CommandValidations(Base):
    def test_frame_rejects_objective_without_observable_condition(self):
        doc = load('frame')
        doc['end_state']['observable_condition'] = 'the lab works better'
        self.rejects('frame', doc, 'NOMINAL_OBJECTIVE')
        doc = load('frame')
        doc['minimum_acceptable']['observable_condition']['threshold'] = 'TBD'
        self.rejects('frame', doc, 'NOMINAL_OBJECTIVE')

    def test_map_requires_preference_representation_capacity_apart(self):
        self.chain.build('frame')
        doc = load('map')
        actor = doc['actors'][1]
        actor['representation'] = actor['preference']
        self.rejects('map', doc, 'ACTOR_UNDIFFERENTIATED')

    def test_cause_needs_a_rival_and_an_observable_refutation(self):
        self.chain.build('map')
        doc = load('cause')
        doc['rivals'] = []
        self.rejects('cause', doc, 'at least 1 item')
        doc = load('cause')
        doc['refutations'][0]['observation'] = 'n/a'
        self.rejects('cause', doc, 'UNOBSERVABLE_REFUTATION')

    def test_focus_refuses_centre_without_substitution_or_horizon(self):
        self.chain.build('cause')
        doc = load('focus')
        doc['matrix']['substitution']['time'] = 'TBD'
        self.rejects('focus', doc, 'CENTRE_WITHOUT_SUBSTITUTION')
        doc = load('focus')
        doc['system']['horizon'] = ''
        self.rejects('focus', doc, 'CENTRE_WITHOUT_HORIZON')

    def test_focus_refuses_concept_confusion(self):
        self.chain.build('cause')
        doc = load('focus')
        doc['schwerpunkt']['focus'] = doc['decisive_point']['statement']
        self.rejects('focus', doc, 'CONCEPT_CONFUSION')

    def test_focus_accepts_no_dominant_dependency_with_reason(self):
        self.chain.build('cause')
        doc = load('focus')
        doc['candidate'] = None
        doc['no_dominant_reason'] = 'No single dependency explains the conflicts; capacity and rules both matter.'
        self.assertEqual(0, self.chain.run('focus', doc, ['map'])[0])

    def test_options_refuses_one_viable_option_plus_decoys(self):
        self.chain.build('focus')
        doc = load('options')
        doc['options'][1]['viable'] = False
        doc['options'][1]['why_not_viable'] = 'too slow'
        self.rejects('options', doc, 'DECOY_SET')

    def test_options_needs_continuity_and_distinct_mechanisms(self):
        self.chain.build('focus')
        doc = load('options')
        doc['options'][0]['kind'] = 'alternative'
        self.rejects('options', doc, 'NO_CONTINUITY_BASELINE')
        doc = load('options')
        doc['options'][2]['mechanism'] = doc['options'][1]['mechanism'].upper()
        self.rejects('options', doc, 'SAME_MECHANISM')

    def test_options_refuses_scores(self):
        self.chain.build('focus')
        doc = load('options')
        doc['comparison']['central']['legitimacy'] = 7
        self.rejects('options', doc, 'WEIGHTED_SCORE')

    def test_react_requires_unexpected_cooperation_as_well_as_opposition(self):
        self.chain.build('options')
        doc = load('react')
        doc['reactions'] = [r for r in doc['reactions'] if r['kind'] != 'cooperation']
        doc['reactions'].append({**copy.deepcopy(doc['reactions'][0]), 'id': 'extra'})
        self.rejects('react', doc, 'NO_UNEXPECTED_COOPERATION')

    def test_watch_refuses_indicators_without_decision(self):
        self.chain.build('options')
        doc = load('watch')
        del doc['thresholds'][0]['response']
        self.rejects('watch', doc, 'INDICATOR_WITHOUT_DECISION')
        doc = load('watch')
        for item in doc['thresholds']:
            item['response'] = 'adjust'
        self.rejects('watch', doc, 'NO_STOPPING_THRESHOLD')

    def test_close_refuses_placeholders_and_a_single_clause(self):
        self.chain.build('frame')
        doc = load('close')
        doc['termination_contract']['on_breach'] = 'TBD'
        self.rejects('close', doc, 'PLACEHOLDER_CLAUSE')
        doc = load('close')
        clause = doc['termination_contract']['achieved']
        for key in ('outstanding', 'accountable'):
            doc['termination_contract'][key] = clause
        self.rejects('close', doc, 'SINGLE_CLAUSE')


class Coherence(Base):
    def setUp(self):
        super().setUp()
        self.chain.build('close')

    def test_not_applicable_is_forbidden_on_epistemic_and_exit(self):
        for test in ('epistemic', 'exit'):
            doc = load('cohere')
            doc['tests'][test] = {'status': 'NOT_APPLICABLE', 'reason': 'out of scope', 'evidence': [], 'finding': None}
            self.rejects('cohere', doc, 'NOT_APPLICABLE_FORBIDDEN')

    def test_not_applicable_is_allowed_with_a_reason_elsewhere(self):
        doc = load('cohere')
        doc['tests']['interactive'] = {'status': 'NOT_APPLICABLE', 'reason': 'no adaptive actor after checking',
                                       'evidence': [], 'finding': None}
        self.assertEqual(0, self.chain.run('cohere', doc, ['frame', 'cause', 'map'])[0])

    def test_a_failed_test_is_fatal_and_removes_proceed(self):
        doc = load('cohere')
        doc['tests']['conversion'] = {'status': 'FAIL', 'reason': 'hours are counted twice', 'evidence': ['cap-100'],
                                      'finding': {'class': 'ACCEPTED_RISK', 'owner': 'x', 'reason': 'y'}}
        self.rejects('cohere', doc, 'FAIL_NOT_FATAL')
        doc['tests']['conversion']['finding'] = {'class': 'FATAL_DEFECT', 'reason': 'reserve double-counted'}
        self.assertEqual(0, self.chain.run('cohere', doc, ['frame', 'cause', 'map'])[0])
        self.assertEqual(['REDESIGN', 'REJECT'], self.chain.artefact('cohere')['body']['admissible_verdicts'])

    def test_pending_evidence_caps_at_hold(self):
        doc = load('cohere')
        doc['tests']['causal']['finding'] = {'class': 'PENDING_EVIDENCE', 'trigger': 'booking forecast confirmed'}
        self.assertEqual(0, self.chain.run('cohere', doc, ['frame', 'cause', 'map'])[0])
        self.assertEqual('HOLD', self.chain.artefact('cohere')['body']['admissible_verdicts'][0])

    def test_every_test_must_be_answered(self):
        doc = load('cohere')
        del doc['tests']['legitimacy']
        self.rejects('cohere', doc, 'TEST_NOT_ANSWERED')

    def test_without_doctrine_tables_the_command_refuses(self):
        status, _, err = self.chain.run('cohere', load('cohere'), ['frame', 'cause', 'map'], contracts=False,
                                        out=self.chain.dir / 'x')
        self.assertEqual(2, status)
        self.assertIn('D-004', err)


class Pathologies(Base):
    def setUp(self):
        super().setUp()
        self.chain.build('cohere')

    def test_all_fourteen_must_be_swept(self):
        doc = load('pathology')
        del doc['pathologies']['dispersion']
        self.rejects('pathology', doc, 'PATHOLOGY_NOT_SWEPT')

    def test_detected_needs_evidence_and_a_false_positive_check(self):
        doc = load('pathology')
        doc['pathologies']['dispersion'] = {'status': 'DETECTED', 'evidence': ['cap-100'],
                                            'false_positive_check': 'TBD', 'note': 'x'}
        self.rejects('pathology', doc, 'NO_FALSE_POSITIVE_CHECK')

    def test_culmination_is_not_conflated_with_escalation_or_inversion(self):
        for other in ('escalation_of_commitment', 'level_inversion'):
            doc = load('pathology')
            for pid in ('denied_culmination', other):
                doc['pathologies'][pid] = {'status': 'DETECTED', 'evidence': ['priority-50'],
                                           'false_positive_check': 'checked against the watch thresholds',
                                           'note': 'continuing after the sign changed'}
            self.rejects('pathology', doc, 'CONFLATED_PATHOLOGIES')


class Decision(Base):
    def setUp(self):
        super().setUp()
        self.chain.build('pathology')
        self.parents = ['frame', 'cohere', 'pathology', 'close', 'cause']

    def decide(self, **changes):
        doc = load('decide')
        doc.update(changes)
        return doc

    def test_proceed_needs_an_independent_review(self):
        self.rejects('decide', self.decide(verdict='PROCEED', conditions=[]), 'REVIEW_NOT_INDEPENDENT',
                     self.parents)

    def test_proceed_needs_a_termination_contract(self):
        err = self.rejects('decide', self.decide(), 'NO_TERMINATION_CONTRACT',
                           ['frame', 'cohere', 'pathology', 'cause'])
        self.assertIn('close', err)

    def test_verdict_must_be_admissible_after_a_fatal_defect(self):
        doc = load('cohere')
        doc['tests']['conversion'] = {'status': 'FAIL', 'reason': 'reserve double-counted', 'evidence': ['cap-100'],
                                      'finding': {'class': 'FATAL_DEFECT', 'reason': 'reserve double-counted'}}
        self.chain.run('cohere', doc, ['frame', 'cause', 'map'])
        self.rejects('decide', self.decide(), 'VERDICT_NOT_ADMISSIBLE', self.parents)

    def test_independent_review_and_clean_sweep_allow_proceed(self):
        cohere = load('cohere')
        cohere['independence_level'] = 'INDEPENDENT_OPERATOR'
        cohere['tests']['causal'] = {'status': 'PASS', 'reason': 'slack confirmed', 'evidence': ['slack-20'],
                                     'finding': None}
        self.assertEqual(0, self.chain.run('cohere', cohere, ['frame', 'cause', 'map'])[0])
        sweep = load('pathology')
        sweep['pathologies']['metric_substitution'] = {'status': 'NOT_DETECTED', 'evidence': [],
                                                       'false_positive_check': 'n/a', 'note': 'deadline documents required'}
        self.assertEqual(0, self.chain.run('pathology', sweep, ['frame', 'map'])[0])
        code, _, err = self.chain.run('decide', self.decide(verdict='PROCEED', conditions=[]), self.parents)
        self.assertEqual(0, code, err)
        self.assertEqual('PROCEED', self.chain.artefact('decide')['verdict'])

    def test_dissent_or_its_solicitation_is_recorded(self):
        self.rejects('decide', self.decide(dissent=[], dissent_solicited_from=[]), 'DISSENT_NOT_SOLICITED',
                     self.parents)

    def test_activating_decision_needs_dated_expectations(self):
        self.rejects('decide', self.decide(expectations=[]), 'NO_DATED_EXPECTATIONS', self.parents)

    def test_cohere_from_another_doctrine_breaks_the_lineage(self):
        other = json.loads(Path(CONTRACTS).read_text())
        other['coherence_tests'][0]['question'] = 'changed'
        path = self.chain.dir / 'other-contracts.json'
        path.write_text(json.dumps(other))
        doc_path = self.chain.dir / 'd.json'
        doc_path.write_text(json.dumps(self.decide()))
        argv = ['decide', str(doc_path), '--contracts', str(path), '--out', str(self.chain.dir / 'o')]
        for parent in self.parents:
            argv += ['--from', str(self.chain.out / f'{parent}.json')]
        with contextlib.redirect_stderr(stdio.StringIO()) as err:
            self.assertEqual(3, cli.main(argv))
        self.assertIn('another doctrine', err.getvalue())


class Lineage(Base):
    def setUp(self):
        super().setUp()
        self.chain.build('cause')

    def test_altered_parent_breaks_the_chain(self):
        frame = self.chain.artefact('frame')
        frame['body']['end_state']['horizon'] = 'ten cycles'
        tampered = self.chain.dir / 'tampered.json'
        tampered.write_text(json.dumps(frame))
        self.rejects('map', load('map'), 'altered after sealing', [tampered], exit_code=3)

    def test_missing_required_parent_breaks_the_chain(self):
        self.rejects('options', load('options'), 'needs a cause artefact', ['frame'], exit_code=3)

    def test_parents_from_two_cases_break_the_chain(self):
        other = load('frame')
        other['case']['id'] = 'another-case'
        self.chain.run('frame', other, out=self.chain.dir / 'other')
        self.rejects('cause', load('cause'), 'different cases', ['map', self.chain.dir / 'other/frame.json'],
                     exit_code=3)

    def test_root_commands_take_no_parents_and_others_need_them(self):
        self.rejects('frame', load('frame'), 'starts a lineage', ['frame'], exit_code=3)
        self.rejects('map', load('map'), 'pass them with --from', [], exit_code=3)

    def test_parent_dated_after_the_decision_breaks_the_chain(self):
        doc = load('map')
        doc['at'] = '2026-10-27T00:00:00Z'
        self.rejects('map', doc, 'dated after', ['frame'], exit_code=3)


class Claims(Base):
    def setUp(self):
        super().setUp()
        self.chain.build('map')

    def cause_with(self, claim):
        doc = load('cause')
        doc['claims'].append(claim)
        doc['basis'].append(claim['id'])
        return doc

    def test_system_output_cannot_be_evidence(self):
        claim = {'id': 'echo', 'text': 'Our own draft says demand is fine.', 'status': 'EVIDENCE',
                 'source': {'ref': 'ante-draft-1', 'origin': 'system'}, 'date': '2026-10-27', 'limit': 'x'}
        self.rejects('cause', self.cause_with(claim), 'SELF_CORROBORATION')

    def test_evidence_needs_source_and_date(self):
        claim = {'id': 'e', 'text': 't', 'status': 'EVIDENCE', 'source': {'ref': 'TBD', 'origin': 'external'},
                 'date': None, 'limit': 'x'}
        err = self.rejects('cause', self.cause_with(claim), 'EVIDENCE_WITHOUT_SOURCE')
        self.assertIn('EVIDENCE_WITHOUT_DATE', err)

    def test_attributed_intent_separates_capability_from_will(self):
        claim = {'id': 'i', 'text': 't', 'status': 'ATTRIBUTED_INTENT', 'source': {'ref': 'r', 'origin': 'external'},
                 'date': '2026-10-01', 'limit': 'x', 'intent': {'capability': 'wants it', 'will': 'wants it'}}
        self.rejects('cause', self.cause_with(claim), 'INTENT_NOT_SEPARATED')

    def upgraded(self, **upgrade):
        return {'id': 'a-inflates', 'text': 'A inflated its requests in cycle 1.', 'status': 'EVIDENCE',
                'source': {'ref': 'booking-audit-cycle-1', 'origin': 'external'}, 'date': '2026-11-10',
                'limit': 'cycle 1 only', 'upgrade': {'observation': 'audit of A requests against deadline letters',
                                                     'could_have_refuted': True, 'source': 'booking-audit-cycle-1',
                                                     'date': '2026-11-10', **upgrade}}

    def test_attributed_intent_rises_only_through_a_refuting_observation(self):
        claim = self.upgraded()
        del claim['upgrade']
        self.rejects('cause', self.cause_with(claim), 'INTENT_UPGRADE_WITHOUT_OBSERVATION')
        self.rejects('cause', self.cause_with(self.upgraded(could_have_refuted=False)), 'INTENT_UPGRADE_UNFALSIFIABLE')

    def test_repetition_of_the_same_source_is_not_observation(self):
        claim = self.upgraded(source='council-minutes-2026-09')
        self.rejects('cause', self.cause_with(claim), 'INTENT_UPGRADE_BY_REPETITION')

    def test_a_proper_upgrade_is_accepted(self):
        claim = self.upgraded()
        claim['source'] = {'ref': 'booking-audit-cycle-1', 'origin': 'external'}
        claim['upgrade']['source'] = 'deadline-letter-register'
        code, _, err = self.chain.run('cause', self.cause_with(claim), ['frame', 'map'], at='2026-11-11T00:00:00Z')
        self.assertEqual(0, code, err)


class Inputs(Base):
    def test_duplicate_keys_fail_without_echoing_content(self):
        path = self.chain.dir / 'dup.json'
        path.write_text('{"case": {"id": "secret-value-xyz"}, "case": 1}')
        with contextlib.redirect_stderr(stdio.StringIO()) as err:
            self.assertEqual(2, cli.main(['frame', str(path)]))
        self.assertIn('duplicate object key', err.getvalue())
        self.assertNotIn('secret-value-xyz', err.getvalue())

    def test_unknown_field_is_rejected(self):
        doc = load('frame')
        doc['budget'] = 1
        self.rejects('frame', doc, 'unknown field(s) budget')

    def test_yaml_input_is_accepted(self):
        import yaml
        path = self.chain.dir / 'frame.yaml'
        path.write_text(yaml.safe_dump(load('frame')))
        with contextlib.redirect_stdout(stdio.StringIO()):
            self.assertEqual(0, cli.main(['frame', str(path), '--out', str(self.chain.out)]))


class ACH(Base):
    def setUp(self):
        super().setUp()
        self.chain.build('frame')

    def test_shared_sources_count_once_and_system_output_is_excluded(self):
        self.assertEqual(0, self.chain.run('ach', load('ach'), ['frame'])[0])
        art = self.chain.artefact('ach')
        analysis = art['body']['analysis']
        self.assertEqual([['e-minutes', 'e-tech']], analysis['source_groups'])
        self.assertEqual(['e-summary'], analysis['excluded_self_produced'])
        self.assertEqual(2, analysis['inconsistency_raw']['bad-records'])
        self.assertEqual(1, analysis['inconsistency_by_source_group']['bad-records'])
        self.assertEqual(['e-demand'], analysis['non_diagnostic'])
        self.assertEqual('SELF', art['independence_level'])

    def test_sensitive_evidence_is_named(self):
        doc = load('ach')
        doc['matrix']['e-dups']['structural-scarcity'] = 'I'
        doc['evidence'][3]['depends_on'] = []
        doc['evidence'][3]['source_id'] = 'council-own-count'
        self.assertEqual(0, self.chain.run('ach', doc, ['frame'])[0])
        # With independent sources, dropping either near-capacity report ties the leading hypotheses.
        self.assertEqual(['e-minutes', 'e-tech'], self.chain.artefact('ach')['body']['analysis']['sensitive_evidence'])

    def test_review_commands_declare_independence(self):
        doc = load('ach')
        del doc['independence_level']
        self.rejects('ach', doc, 'independence_level')


class SelfTest(Base):
    ENTRY = {'row': 4, 'scope': 'lab-consortium example', 'evidence_ref': 'examples/foundation/lab-consortium',
             'date': '2026-10-28T00:00:00Z', 'result': 'PASS', 'reviewer': 'release owner',
             'owner': 'UNDESIGNATED', 'gap': 'none', 'next_trigger': 'next release'}

    def test_rows_come_from_the_doctrine_and_gaps_are_published(self):
        code, _, err = self.chain.run('selftest', {'at': '2026-10-28T12:00:00Z', 'claims': [],
                                                   'entries': [self.ENTRY]})
        self.assertEqual(0, code, err)
        body = self.chain.artefact('selftest')['body']
        self.assertEqual(8, len(body['rows']))
        self.assertEqual('The warning does not arrive', body['rows'][0]['failure'])
        self.assertEqual('PASS', body['rows'][3]['result'])
        self.assertEqual([1, 2, 3, 5, 6, 7, 8], body['published_gaps'])

    def test_pass_needs_evidence_and_cannot_be_future_dated(self):
        entry = {**self.ENTRY, 'evidence_ref': ''}
        self.rejects('selftest', {'at': '2026-10-28T12:00:00Z', 'claims': [], 'entries': [entry]},
                     'RESULT_WITHOUT_EVIDENCE', [])
        entry = {**self.ENTRY, 'date': '2027-01-01T00:00:00Z'}
        self.rejects('selftest', {'at': '2026-10-28T12:00:00Z', 'claims': [], 'entries': [entry]},
                     'FUTURE_EVIDENCE', [])


if __name__ == '__main__':
    unittest.main()
