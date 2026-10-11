#!/usr/bin/env python3
"""Regression tests for nexus-brief.py, the owner's decision brief (NEXUS Overdrive, Phase 3)."""
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from contextlib import redirect_stdout

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('brief', ROOT / 'scripts/nexus-brief.py')
br = importlib.util.module_from_spec(spec); spec.loader.exec_module(br)
INSTANCE = json.loads((ROOT / 'examples/nexus/casepacks/level-inversion-northwind/instance.json').read_text())
AGENT = {t['id']: t['agent'] for t in INSTANCE['tasks']}
OWNER = INSTANCE['mandate']['owner']
REVIEWER = INSTANCE['mandate']['reviewers'][0]
AT = '2026-10-11T10:00:00Z'


def at(minute):
    return f'2026-10-11T09:{minute:02d}:00Z'


def start(tid, minute, model='m-1'):
    return {'id': f'start-{tid}', 'at': at(minute), 'issuer': AGENT[tid], 'type': 'start', 'task_id': tid,
            'reserved_cost': 1, 'model_id': model}


def accept(tid, minute, asserts=None):
    event = {'id': f'finish-{tid}', 'at': at(minute), 'issuer': OWNER, 'type': 'finish', 'task_id': tid,
             'actual_cost': 1, 'accepted': True, 'evidence_refs': [f'out-{tid}'],
             'predicate_results': {'contract_met': True}}
    if asserts is not None:
        event['asserts'] = asserts
    return event


KEY = 'diagnosis.kpi_tracks_outcome'
CONFLICTED = [start('A', 1), start('B', 2, model='m-2'), accept('A', 3, {KEY: True}), accept('B', 4, {KEY: False})]


class BriefTests(unittest.TestCase):
    def kinds(self, b):
        return [w['kind'] for w in b['waiting_on_owner']]

    def test_a_conflict_is_put_to_the_owner_with_both_answers_and_blocks_closure(self):
        b = br.brief(INSTANCE, CONFLICTED, AT)
        self.assertEqual(['ASSERTION_CONFLICT'], self.kinds(b))
        detail = b['waiting_on_owner'][0]['detail']
        self.assertEqual({'A': True, 'B': False}, {t: d['value'] for t, d in detail.items()})
        self.assertFalse(b['closure']['close']['admitted'])
        self.assertIn('unresolved assertion conflict', b['closure']['terminate_sufficient_result']['reason'])

    def test_the_owner_resolution_leaves_a_reason_in_the_record(self):
        events = CONFLICTED + [{'id': 'r1', 'at': at(5), 'issuer': OWNER, 'type': 'resolve_conflict', 'key': KEY,
                                'value': False, 'reason': 'renewals fell while the KPI rose',
                                'evidence_refs': ['metrics.md']}]
        b = br.brief(INSTANCE, events, AT)
        self.assertEqual([], self.kinds(b))
        self.assertEqual({'at': at(5), 'type': 'resolve_conflict', 'issuer': OWNER, 'reason':
                          'renewals fell while the KPI rose', 'key': KEY, 'value': False,
                          'evidence_refs': ['metrics.md']}, b['record'][0])

    def test_open_dissent_and_running_work_are_waiting_items(self):
        events = [start('A', 1), {'id': 'd1', 'at': at(2), 'issuer': REVIEWER, 'type': 'dissent',
                                  'objection': 'renewal data is one quarter', 'risk_owner': OWNER,
                                  'evidence_refs': ['metrics.md']}]
        b = br.brief(INSTANCE, events, AT)
        self.assertEqual(['OPEN_DISSENT', 'RESULT_PENDING'], self.kinds(b))
        self.assertEqual('dissent_response', b['waiting_on_owner'][0]['next_event'])

    def test_results_from_one_model_are_flagged_as_not_independent(self):
        events = [start('A', 1), start('B', 2), accept('A', 3, {KEY: True}), accept('B', 4, {KEY: True})]
        b = br.brief(INSTANCE, events, AT)
        self.assertEqual({'m-1': ['A', 'B']}, b['independence']['shared_model_tasks'])
        self.assertIn('same model', br.markdown(b))

    def test_the_probe_never_changes_the_recorded_state(self):
        b1 = br.brief(INSTANCE, CONFLICTED, AT)
        b2 = br.brief(INSTANCE, CONFLICTED, AT)
        self.assertEqual(b1, b2)
        self.assertEqual([], b1['record'])

    def test_a_closed_instance_reports_its_outcome(self):
        root = ROOT / 'examples/nexus'
        events = [json.loads(line) for line in (root / 'strategic-decision.events.jsonl').read_text().splitlines()
                  if line.strip()]
        b = br.brief(json.loads((root / 'strategic-decision.instance.json').read_text()), events, AT)
        self.assertEqual('SUCCESS', b['closure']['closed']['outcome'])
        self.assertEqual('close', b['record'][-1]['type'])

    def test_cli_prints_markdown_and_json(self):
        with tempfile.TemporaryDirectory() as td:
            inst, log = Path(td) / 'i.json', Path(td) / 'e.jsonl'
            inst.write_text(json.dumps(INSTANCE))
            log.write_text('\n'.join(json.dumps(e) for e in CONFLICTED) + '\n')
            out = io.StringIO()
            with redirect_stdout(out):
                self.assertEqual(0, br.main([str(inst), '--events', str(log), '--at', AT]))
            self.assertIn('## Waiting on you (1)', out.getvalue())
            out = io.StringIO()
            with redirect_stdout(out):
                self.assertEqual(0, br.main([str(inst), '--events', str(log), '--at', AT, '--json']))
            self.assertEqual('ASSERTION_CONFLICT', json.loads(out.getvalue())['waiting_on_owner'][0]['kind'])


if __name__ == '__main__':
    unittest.main()
