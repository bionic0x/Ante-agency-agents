#!/usr/bin/env python3
"""Regression tests for nexus-plan.py, the planner agent and owner adoption. No model is called."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('plan', ROOT / 'scripts/nexus-plan.py')
pl = importlib.util.module_from_spec(spec); spec.loader.exec_module(pl)
OBJECTIVE = ROOT / 'examples/nexus/planner-objective.example.json'
AT = '2026-10-11T10:00:00Z'


def scripted(*outputs):
    """An executor that returns the given graphs (or raw text) in turn, recording each packet."""
    seen = []

    def plan(packet, model):
        seen.append(packet)
        item = outputs[min(len(seen), len(outputs)) - 1]
        text = item if isinstance(item, str) else '```json\n' + json.dumps(item) + '\n```'
        return {'output': text, 'cost_usd': 0.0, 'tokens_total': 0, 'evidence_ref': f'scripted-{len(seen)}',
                'model_version': model}
    plan.seen = seen
    return plan


def good_graph():
    packet = pl.planner_packet(pl.load_objective(OBJECTIVE), pl.roster('strategic-decision'))
    return json.loads(pl.fake_planner(packet, 'm')['output'].split('```json\n')[1].split('\n```')[0])


class PlanTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def draft(self, executor=pl.fake_planner, name='d'):
        return pl.draft(OBJECTIVE, self.base / name, executor), self.base / name

    def test_owner_fields_are_verbatim_and_the_planner_writes_only_tasks(self):
        summary, out = self.draft()
        self.assertEqual('DRAFTED', summary['status'])
        instance = json.loads((out / 'instance.json').read_text())
        owner = json.loads(OBJECTIVE.read_text())
        for field in ('mandate', 'objective', 'budget', 'claims', 'decision_state'):
            self.assertEqual(owner[field], instance[field])
        roster = {m['agent'] for m in pl.roster('strategic-decision')}
        self.assertTrue(all(t['agent'] in roster for t in instance['tasks']))
        self.assertTrue(all(t['purpose_ref'] == owner['objective']['id'] for t in instance['tasks']))
        self.assertEqual('CLEAN', summary['lint_status'])

    def test_a_planner_that_sets_the_budget_or_mandate_is_refused(self):
        greedy = {**good_graph(), 'budget': {'cost_limit': 1000}}
        summary, out = self.draft(scripted(greedy, greedy, greedy))
        self.assertEqual('REFUSED', summary['status'])
        self.assertIn('may only return tasks', summary['attempts'][0]['engine_refusal'])
        self.assertFalse((out / 'instance.json').exists())
        rogue = copy.deepcopy(good_graph()); rogue['tasks'][0]['purpose_ref'] = 'OTHER'
        summary, _ = self.draft(scripted(rogue, rogue, rogue), name='d2')
        self.assertIn('does not own', summary['attempts'][0]['engine_refusal'])

    def test_an_engine_refusal_is_fed_back_and_repaired(self):
        bad = copy.deepcopy(good_graph()); bad['tasks'][0]['agent'] = 'marketing-growth-hacker'
        executor = scripted(bad, good_graph())
        summary, _ = self.draft(executor)
        self.assertEqual('DRAFTED', summary['status'])
        self.assertEqual(2, len(summary['attempts']))
        self.assertIn('runbook roster', executor.seen[1]['engine_refusal'])
        self.assertIn('previous_draft', executor.seen[1])

    def test_three_failed_attempts_stop_the_planner(self):
        summary, _ = self.draft(scripted('no json here'))
        self.assertEqual(('REFUSED', 3), (summary['status'], len(summary['attempts'])))

    def test_only_the_owner_adopts_and_every_warning_must_be_accepted(self):
        heavy = copy.deepcopy(good_graph())
        for task in heavy['tasks']:
            task['cost_limit'] = 5
        _, out = self.draft(scripted(heavy))
        with self.assertRaisesRegex(pl.PlanError, 'only the mandate owner'):
            pl.adopt(out, 'fixture-reviewer', AT)
        with self.assertRaisesRegex(pl.PlanError, "BUDGET_HEADROOM"):
            pl.adopt(out, 'fixture-owner', AT)
        adoption = pl.adopt(out, 'fixture-owner', AT, ['BUDGET_HEADROOM'])
        self.assertEqual(['BUDGET_HEADROOM'], adoption['accepted_warnings'])
        with self.assertRaisesRegex(pl.PlanError, 'already adopted'):
            pl.adopt(out, 'fixture-owner', AT, ['BUDGET_HEADROOM'])

    def test_adoption_pins_the_exact_instance(self):
        _, out = self.draft()
        pl.adopt(out, 'fixture-owner', AT)
        self.assertEqual('ADOPTED', pl.verify(out / 'instance.json', out / 'adoption.json')['status'])
        instance = json.loads((out / 'instance.json').read_text()); instance['budget']['cost_limit'] = 99
        (out / 'instance.json').write_text(json.dumps(instance))
        with self.assertRaisesRegex(pl.PlanError, 'differs from the adopted plan'):
            pl.verify(out / 'instance.json', out / 'adoption.json')

    def test_a_draft_edited_before_adoption_is_refused(self):
        _, out = self.draft()
        instance = json.loads((out / 'instance.json').read_text()); instance['tasks'][0]['cost_limit'] = 1
        (out / 'instance.json').write_text(json.dumps(instance))
        with self.assertRaisesRegex(pl.PlanError, 'changed after drafting'):
            pl.adopt(out, 'fixture-owner', AT)

    def test_the_packet_shows_field_types_and_hides_nothing_the_owner_fixed(self):
        packet = pl.planner_packet(pl.load_objective(OBJECTIVE), pl.roster('strategic-decision'))
        self.assertIsInstance(packet['example_task']['resource_scope'], list)
        self.assertEqual(pl.TASK_FIELDS, set(packet['example_task']))
        self.assertEqual(json.loads(OBJECTIVE.read_text())['budget'], packet['budget'])

    def test_cli(self):
        self.assertEqual(0, pl.main(['draft', '--objective', str(OBJECTIVE), '--out', str(self.base / 'c'),
                                     '--executor', 'fake']))
        self.assertEqual(0, pl.main(['adopt', '--draft', str(self.base / 'c'), '--owner', 'fixture-owner', '--at', AT]))


if __name__ == '__main__':
    unittest.main()
