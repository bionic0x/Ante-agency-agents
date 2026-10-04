#!/usr/bin/env python3
"""Offline regressions for the Claude Code execution adapter. No live host calls."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def module(path):
    spec = importlib.util.spec_from_file_location('nexus_anthropic_tested', path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


a = module(ROOT / 'scripts' / 'nexus-anthropic.py')


def stream(model='claude-fixture', version='2.1.278', session='s1'):
    rows = [
        {'type': 'system', 'subtype': 'init', 'session_id': session,
         'claude_code_version': version, 'tools': ['Read'], 'model': model,
         'context_window': 200000},
        {'type': 'assistant', 'session_id': session,
         'message': {'model': model, 'content': [{'type': 'text', 'text': 'fixture output'}]}},
        {'type': 'result', 'subtype': 'success', 'is_error': False, 'session_id': session,
         'total_cost_usd': 0.5, 'duration_ms': 1250,
         'usage': {'input_tokens': 100, 'output_tokens': 20, 'cache_read_input_tokens': 5},
         'permission_denials': []},
    ]
    return '\n'.join(json.dumps(row) for row in rows) + '\n'


class AnthropicAdapterTests(unittest.TestCase):
    def test_stream_parser_binds_host_model_session_and_counters(self):
        row = a.parse_stream(stream(), 0, measured_wall_time=1.5)
        self.assertEqual('s1', row['session_id'])
        self.assertEqual('2.1.278', row['host_version'])
        self.assertEqual('claude-fixture', row['observed_model_id'])
        self.assertEqual(200000, row['context_window'])
        self.assertEqual(125, row['tokens_total'])
        self.assertEqual(0.5, row['cost_usd'])
        self.assertEqual('fixture output', row['output'])
        self.assertEqual(['Read'], row['tools'])

    def test_stream_parser_rejects_failure_mixed_session_and_model_conflict(self):
        with self.assertRaisesRegex(a.AdapterError, 'did not complete'):
            a.parse_stream(stream().replace('"is_error": false', '"is_error": true'), 0)
        mixed = stream().replace('"session_id": "s1", "message"', '"session_id": "s2", "message"')
        with self.assertRaisesRegex(a.AdapterError, 'multiple session'):
            a.parse_stream(mixed, 0)
        conflicting = stream().replace('"message": {"model": "claude-fixture"',
                                       '"message": {"model": "another-model"')
        with self.assertRaisesRegex(a.AdapterError, 'multiple model ids'):
            a.parse_stream(conflicting, 0)

    def test_observe_keeps_pricing_unknown_unless_operator_supplies_it(self):
        original = a._invoke
        try:
            a._invoke = lambda *args, **kwargs: {
                'session_id': 'obs1', 'host_version': '2.1.278', 'tools': [],
                'observed_model_id': 'claude-fixture', 'context_window': 200000,
                'cost_usd': 0.01, 'tokens_total': 12, 'host_duration_seconds': 0.4,
                'wall_time_seconds': 0.5, 'permission_denials': [], 'output': 'ANTE_NEXUS_OBSERVATION',
                'stderr': '',
            }
            row = a.observe('alias', {
                'reasoning_depth': 'standard', 'context_class': 'large',
                'modality': ['text'], 'tool_use': 'declared',
                'determinism_need': 'repeatable',
            })
        finally:
            a._invoke = original
        self.assertEqual('claude-fixture', row['model_id'])
        self.assertIsNone(row['declared_cost_per_1k_input'])
        self.assertIsNone(row['declared_cost_per_1k_output'])
        self.assertEqual('UNKNOWN', row['provenance']['declared_cost_per_1k_output'])

    def test_execute_is_only_an_adapter_and_verifies_scoped_read_boundary(self):
        original_render, original_invoke = a.CAPABILITIES.render, a._invoke
        try:
            def fake_render(agent_id, policy, output, at=None):
                self.assertEqual(['Read'], policy['allowed_tools'])
                Path(output).write_text('---\nname: Fixture Agent\n---\nbody\n')
                return {'status': 'PROFILE_PREPARED'}
            a.CAPABILITIES.render = fake_render
            a._invoke = lambda *args, **kwargs: {
                'session_id': 'exec1', 'host_version': '2.1.278', 'tools': ['Read'],
                'observed_model_id': 'claude-fixture', 'context_window': 200000,
                'cost_usd': 0.2, 'tokens_total': 50, 'host_duration_seconds': 1.0,
                'wall_time_seconds': 1.2, 'permission_denials': [], 'output': 'done', 'stderr': '',
            }
            packet = {'instance_id': 'I', 'task': {'id': 'A', 'level': 'strategic', 'vector': 'causal'}}
            row = a.execute(packet, 'fixture-agent', 'claude-fixture', 'AUTH', 'operator',
                            '2030-01-01T00:00:00+00:00')
        finally:
            a.CAPABILITIES.render, a._invoke = original_render, original_invoke
        self.assertEqual('COMPLETED', row['outcome'])
        self.assertEqual('A', row['task_id'])
        self.assertEqual('anthropic', row['provider'])
        self.assertEqual('done', row['output'])
        self.assertTrue(row['packet_sha256'])

        try:
            a.CAPABILITIES.render = fake_render
            a._invoke = lambda *args, **kwargs: {
                'session_id': 'exec2', 'host_version': '2.1.278', 'tools': ['Read', 'Write'],
                'observed_model_id': 'claude-fixture', 'context_window': 200000,
                'cost_usd': 0.2, 'tokens_total': 50, 'host_duration_seconds': 1.0,
                'wall_time_seconds': 1.2, 'permission_denials': [], 'output': 'done', 'stderr': '',
            }
            with self.assertRaisesRegex(a.AdapterError, 'expected the scoped'):
                a.execute(packet, 'fixture-agent', 'claude-fixture', 'AUTH', 'operator',
                          '2030-01-01T00:00:00+00:00')
        finally:
            a.CAPABILITIES.render, a._invoke = original_render, original_invoke


if __name__ == '__main__':
    unittest.main(verbosity=2)
