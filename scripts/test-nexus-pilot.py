#!/usr/bin/env python3
"""Offline end-to-end lifecycle tests for the NEXUS execution pilot."""
from __future__ import annotations

import copy
import datetime as dt
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def module(path):
    spec = importlib.util.spec_from_file_location('nexus_pilot_tested', path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


p = module(ROOT / 'scripts' / 'nexus-pilot.py')
NOW = dt.datetime(2026, 9, 19, 20, 0, tzinfo=dt.timezone.utc)


class PilotTests(unittest.TestCase):
    def setUp(self):
        self.instance = json.loads((ROOT / 'examples/nexus/strategic-decision.instance.json').read_text())
        self.temp = tempfile.TemporaryDirectory(prefix='nexus-pilot-test-')
        base = Path(self.temp.name)
        self.events = base / 'events.jsonl'
        self.records = base / 'records'
        self.observations = base / 'observations.json'
        self.observations.write_text(json.dumps([self.observation('claude-fixture')]))
        self.authority = self.good_authority()

    def tearDown(self):
        self.temp.cleanup()

    def observation(self, model, out_cost=1, window=200000):
        return {
            'model_id': model, 'provider': 'anthropic',
            'observed_at': (NOW - dt.timedelta(hours=1)).isoformat(),
            'valid_until': (NOW + dt.timedelta(days=1)).isoformat(),
            'evidence_ref': 'fixture-session', 'host': 'claude-code', 'host_version': '2.1.278',
            'capabilities': {'reasoning_depth': 'extended', 'context_class': 'large',
                             'modality': ['text'], 'tool_use': 'enforced',
                             'determinism_need': 'repeatable'},
            'context_window': window, 'declared_cost_per_1k_input': 1,
            'declared_cost_per_1k_output': out_cost,
        }

    def good_authority(self):
        return {
            'schema_version': 1, 'instance_id': self.instance['id'],
            'authority_ref': self.instance['mandate']['authority_ref'],
            'operator': 'fixture-operator', 'provider': 'anthropic',
            'issued_at': (NOW - dt.timedelta(hours=1)).isoformat(),
            'not_before': (NOW - dt.timedelta(minutes=1)).isoformat(),
            'expires': (NOW + dt.timedelta(hours=6)).isoformat(),
            'task_ids': ['A', 'B', 'C'], 'allow_external_actions': False,
            'instance_cost_unit': self.instance['budget']['unit'],
            'reserved_costs': {'A': 1, 'B': 1, 'C': 1},
        }

    def fake_execute(self, **kwargs):
        task = kwargs['packet']['task']
        return {
            'record_id': f"record-{task['id']}", 'instance_id': self.instance['id'],
            'task_id': task['id'], 'agent_id': kwargs['agent_id'], 'provider': 'anthropic',
            'model_id': kwargs['model_id'], 'authority_ref': kwargs['authority_ref'],
            'operator': kwargs['operator'], 'host_version': '2.1.278',
            'outcome': 'COMPLETED', 'output': f"output-{task['id']}",
            'cost_usd': 0.1, 'tokens_total': 10, 'wall_time_seconds': 0.2,
            'evidence_ref': f"session-{task['id']}", 'level': task['level'], 'vector': task['vector'],
            'permission_denials': [], 'packet_sha256': p._packet_sha(kwargs['packet']),
            'limitations': [],
        }

    def step(self, at, model=None):
        return p.step(self.instance, self.observations, self.authority, self.events,
                      self.records, at=at, requested_model=model, execute_fn=self.fake_execute)

    def accept(self, record, at):
        return p.accept(self.instance, self.events, record, True, 0.5,
                        self.instance['mandate']['owner'], {'contract_met': True}, at=at)

    def test_full_three_task_pilot_stops_for_acceptance_and_replays(self):
        first = self.step(NOW)
        self.assertEqual('A', first['task_id'])
        self.assertEqual('AWAITING_ACCEPTANCE', first['status'])
        # A live completion cannot silently let B run.
        stopped = self.step(NOW + dt.timedelta(seconds=1))
        self.assertEqual('AWAITING_ACCEPTANCE', stopped['status'])

        accepted_a = self.accept(first['execution_record'], NOW + dt.timedelta(minutes=1))
        self.assertEqual('READY', accepted_a['status'])
        second = self.step(NOW + dt.timedelta(minutes=2))
        self.assertEqual('B', second['task_id'])
        self.accept(second['execution_record'], NOW + dt.timedelta(minutes=3))
        third = self.step(NOW + dt.timedelta(minutes=4))
        self.assertEqual('C', third['task_id'])
        self.accept(third['execution_record'], NOW + dt.timedelta(minutes=5))

        final = self.step(NOW + dt.timedelta(minutes=6))
        self.assertEqual('AWAITING_TERMINATION', final['status'])
        replay = p.replay(self.instance, self.events)['state']
        self.assertTrue(all(row['status'] == 'SUCCEEDED' for row in replay['tasks'].values()))
        self.assertFalse(replay['closed'])
        self.assertEqual(1.5, replay['spent'])
        # Evidence is content-bound as well as path-bound.
        self.assertTrue(any(ref.startswith('sha256:') for ref in replay['tasks']['A']['evidence_refs']))

    def test_authority_gates_fail_closed(self):
        cases = []
        row = self.good_authority(); row['expires'] = (NOW - dt.timedelta(seconds=1)).isoformat(); cases.append(('expired', row))
        row = self.good_authority(); row['not_before'] = (NOW + dt.timedelta(seconds=1)).isoformat(); cases.append(('not active', row))
        row = self.good_authority(); row['instance_id'] = 'OTHER'; cases.append(('another instance', row))
        row = self.good_authority(); row['authority_ref'] = 'OTHER'; cases.append(('authority_ref', row))
        row = self.good_authority(); row['operator'] = ''; cases.append(('operator', row))
        row = self.good_authority(); row['allow_external_actions'] = True; cases.append(('allow_external_actions', row))
        row = self.good_authority(); row['instance_cost_unit'] = 'USD'; cases.append(('budget unit', row))
        for fragment, authority in cases:
            with self.subTest(fragment=fragment):
                with self.assertRaises(p.PilotError):
                    p.step(self.instance, self.observations, authority, self.events,
                           self.records, at=NOW, execute_fn=self.fake_execute)

    def test_router_ambiguity_and_missing_observation_stop_execution(self):
        self.observations.write_text(json.dumps([
            self.observation('one', out_cost=1, window=100000),
            self.observation('two', out_cost=2, window=200000),
        ]))
        with self.assertRaisesRegex(p.PilotError, 'SELECTION_AMBIGUOUS'):
            self.step(NOW)
        self.events.unlink(missing_ok=True)
        self.observations.write_text('[]')
        with self.assertRaisesRegex(p.PilotError, 'NO_OBSERVED_TARGET'):
            self.step(NOW)

    def test_failure_is_durable_and_must_be_rejected_before_retry(self):
        def fail(**kwargs):
            raise RuntimeError('host unavailable')
        result = p.step(self.instance, self.observations, self.authority, self.events,
                        self.records, at=NOW, execute_fn=fail)
        self.assertEqual('AWAITING_ACCEPTANCE', result['status'])
        record = json.loads(Path(result['execution_record']).read_text())
        self.assertEqual('FAILED', record['outcome'])
        with self.assertRaisesRegex(p.PilotError, 'failed provider execution'):
            p.accept(self.instance, self.events, result['execution_record'], True, 0,
                     self.instance['mandate']['owner'], {'contract_met': True},
                     at=NOW + dt.timedelta(minutes=1))
        rejected = p.accept(self.instance, self.events, result['execution_record'], False, 0,
                            self.instance['mandate']['owner'], at=NOW + dt.timedelta(minutes=1))
        self.assertEqual('READY', rejected['status'])

    def test_accept_rejects_forged_packet_binding(self):
        result = self.step(NOW)
        path = Path(result['execution_record'])
        record = json.loads(path.read_text())
        record['packet_sha256'] = '0' * 64
        path.write_text(json.dumps(record))
        with self.assertRaisesRegex(p.PilotError, 'packet_sha256'):
            p.accept(self.instance, self.events, path, True, 0.5,
                     self.instance['mandate']['owner'], {'contract_met': True},
                     at=NOW + dt.timedelta(minutes=1))

    def test_replay_detects_execution_evidence_tampering(self):
        result = self.step(NOW)
        self.accept(result['execution_record'], NOW + dt.timedelta(minutes=1))
        path = Path(result['execution_record'])
        record = json.loads(path.read_text())
        record['output'] = 'tampered after acceptance'
        path.write_text(json.dumps(record))
        with self.assertRaisesRegex(p.PilotError, 'evidence hash mismatch'):
            p.replay(self.instance, self.events)
        with self.assertRaisesRegex(p.PilotError, 'evidence hash mismatch'):
            p.step(self.instance, self.observations, self.authority, self.events,
                   self.records, at=NOW + dt.timedelta(minutes=2), execute_fn=self.fake_execute)

    def test_host_version_drift_invalidates_the_execution_record(self):
        def drift(**kwargs):
            row = self.fake_execute(**kwargs)
            row['host_version'] = '2.1.279'
            return row
        result = p.step(self.instance, self.observations, self.authority, self.events,
                        self.records, at=NOW, execute_fn=drift)
        record = json.loads(Path(result['execution_record']).read_text())
        self.assertEqual('FAILED', record['outcome'])
        self.assertIn('HOST_VERSION_DRIFT', record['error'])
        with self.assertRaisesRegex(p.PilotError, 'failed provider execution'):
            p.accept(self.instance, self.events, result['execution_record'], True, 0,
                     self.instance['mandate']['owner'], {'contract_met': True},
                     at=NOW + dt.timedelta(minutes=1))

    def test_requested_model_must_still_be_admissible(self):
        with self.assertRaisesRegex(p.PilotError, 'not admissible'):
            self.step(NOW, model='not-there')


if __name__ == '__main__':
    unittest.main(verbosity=2)
