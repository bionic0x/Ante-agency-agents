#!/usr/bin/env python3
"""Regression tests for nexus-lint.py, the plan linter (NEXUS Overdrive, Phase 2)."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('lint', ROOT / 'scripts/nexus-lint.py')
lint = importlib.util.module_from_spec(spec); spec.loader.exec_module(lint)
ENGINE = lint._engine()
BASE = json.loads((ROOT / 'examples/nexus/casepacks/level-inversion-northwind/instance.json').read_text())


def variant(**changes):
    instance = copy.deepcopy(BASE)
    instance['budget']['cost_limit'] = 20  # headroom, unless a test removes it
    tasks = {t['id']: t for t in instance['tasks']}
    for tid, fields in changes.items():
        tasks[tid].update(fields)
    return instance


def codes(result):
    return [f['code'] for f in result['findings']]


class LintTests(unittest.TestCase):
    def test_a_plan_with_parallel_independent_assessors_is_clean(self):
        result = lint.lint(variant(), ENGINE)
        self.assertEqual('CLEAN', result['status'], result['findings'])
        self.assertEqual({'tasks': 3, 'depth': 2, 'critical_path': ['B', 'C'], 'widest_level': 2, 'sinks': ['C'],
                          'levels': {'1': ['A', 'B'], '2': ['C']}}, result['shape'])

    def test_shared_resource_between_independent_tasks_is_flagged(self):
        result = lint.lint(variant(B={'resource_scope': ['fixture-artifact-A']}), ENGINE)
        self.assertEqual(['SERIALIZED_RESOURCE'], codes(result))
        self.assertEqual(['A', 'B'], result['findings'][0]['tasks'])

    def test_task_limits_above_the_ordinary_budget_are_flagged(self):
        instance = variant(); instance['budget']['cost_limit'] = 10  # 9 of limits, 8 ordinary
        self.assertEqual(['BUDGET_HEADROOM'], codes(lint.lint(instance, ENGINE)))

    def test_a_key_only_one_task_asserts_cannot_conflict(self):
        result = lint.lint(variant(B={'asserts': ['evidence.lineage_independent']}), ENGINE)
        self.assertEqual(['SINGLE_SOURCE_KEY', 'SINGLE_SOURCE_KEY'], codes(result))

    def test_asserters_that_depend_on_each_other_are_not_independent(self):
        result = lint.lint(variant(B={'depends_on': ['A']}), ENGINE)
        self.assertIn('DEPENDENT_ASSERTERS', codes(result))
        self.assertEqual(1, result['shape']['widest_level'])

    def test_one_agent_asserting_a_key_twice_is_flagged(self):
        result = lint.lint(variant(B={'agent': BASE['tasks'][0]['agent']}), ENGINE)
        self.assertIn('SAME_AGENT_ASSERTERS', codes(result))

    def test_more_than_one_final_task_is_flagged(self):
        result = lint.lint(variant(C={'depends_on': ['A']}), ENGINE)
        self.assertEqual(['MULTIPLE_SINKS'], codes(result))
        self.assertEqual(['B', 'C'], result['shape']['sinks'])

    def test_an_invalid_instance_is_an_error(self):
        result = lint.lint(variant(A={'agent': 'no-such-agent'}), ENGINE)
        self.assertEqual('ERRORS', result['status'])
        self.assertEqual(['INVALID_INSTANCE'], codes(result))

    def test_cli_exit_codes(self):
        with tempfile.TemporaryDirectory() as td:
            clean, warned = Path(td) / 'clean.json', Path(td) / 'warned.json'
            clean.write_text(json.dumps(variant()))
            warned.write_text(json.dumps(variant(C={'depends_on': ['A']})))
            self.assertEqual(0, lint.main([str(clean), '--strict']))
            self.assertEqual(0, lint.main([str(warned)]))
            self.assertEqual(1, lint.main([str(warned), '--strict']))


if __name__ == '__main__':
    unittest.main()
