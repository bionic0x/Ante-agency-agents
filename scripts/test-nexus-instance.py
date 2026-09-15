#!/usr/bin/env python3
import copy
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('nexus', ROOT / 'scripts/nexus-instance.py')
n = importlib.util.module_from_spec(spec); spec.loader.exec_module(n)
AT = '2026-09-15T12:00:00Z'

class InstanceTests(unittest.TestCase):
    def setUp(self):
        self.i = json.loads((ROOT / 'examples/nexus/strategic-decision.instance.json').read_text())
        self.s = n.initial(self.i)
        self.count = 0

    def event(self, kind, **fields):
        self.count += 1
        return {'id': f'e{self.count}', 'at': AT, 'issuer': 'fixture-owner', 'type': kind, **fields}

    def run_event(self, kind, **fields):
        self.s = n.apply(self.i, self.s, self.event(kind, **fields)); return self.s

    def start(self, task='A', cost=1):
        return self.run_event('start', task_id=task, reserved_cost=cost)

    def finish(self, task='A', accepted=True, cost=1):
        return self.run_event('finish', task_id=task, accepted=accepted, actual_cost=cost,
                              evidence_refs=['fixture-result'], predicate_results={'contract_met': True})

    def test_pilot_full_trace_and_closure(self):
        events = [json.loads(l) for l in (ROOT / 'examples/nexus/strategic-decision.events.jsonl').read_text().splitlines()]
        state = n.replay(self.i, events)
        self.assertTrue(state['closed']); self.assertEqual(3, state['spent'])
        self.assertFalse(n.plan(self.i, state, AT)['execution_authority'])

    def test_hold_blocks_descendants_not_independent_work(self):
        self.run_event('hold', condition={'id':'h1','classification':'PENDING_EVIDENCE','task_ids':['A'],'reason':'needs evidence'})
        with self.assertRaisesRegex(ValueError,'blocked'): self.start('A')
        self.start('B')
        rows = {r['task_id']:r for r in n.plan(self.i,self.s,AT)['tasks']}
        self.assertFalse(rows['C']['ready'])
        with self.assertRaisesRegex(ValueError,'only named owner'):
            self.run_event('resolve_hold', issuer='fixture-reviewer', condition_id='h1', evidence_refs=['x'], reason='reviewed')

    def test_fatal_defect_cannot_be_accepted(self):
        self.run_event('hold', condition={'id':'fatal','classification':'FATAL_DEFECT','task_ids':['A'],'reason':'inadmissible'})
        with self.assertRaisesRegex(ValueError,'fatal defect'):
            self.run_event('resolve_hold', condition_id='fatal', evidence_refs=['x'], reason='accept')
        with self.assertRaisesRegex(ValueError,'fatal defect'):
            self.run_event('decision', state='PROCEED', reason='ignore')

    def test_claim_promotion_requires_new_evidence(self):
        c = copy.deepcopy(self.s['claims']['CLM-1']); c.update(revision=2,status='EVIDENCE')
        with self.assertRaisesRegex(ValueError,'new evidence'):
            self.run_event('claim_revision', claim=c, reason='same source')
        c['source_refs'].append('fixture-new-source')
        self.run_event('claim_revision', claim=c, reason='new discriminating observation')
        self.assertIn('CLM-2',self.s['review_required'])
        self.assertIn('CLAIM_REVIEW:CLM-1', n.blockers(self.i,self.s,'A',AT))

    def test_expiry_propagates_through_claim_dependencies(self):
        self.s['claims']['CLM-1']['expires'] = '2020-01-01T00:00:00Z'
        self.assertIn('CLAIM_EXPIRED:CLM-2',n.blockers(self.i,self.s,'C',AT))

    def test_cross_network_evidence_rejected(self):
        self.i['claims'][0]['scope']='solana'
        self.i['tasks'][0]['evidence_scope']='arbitrum'
        with self.assertRaisesRegex(ValueError,'cross-scope'): n.initial(self.i)

    def test_shared_sources_are_not_counted_as_independent(self):
        report=n.plan(self.i,self.s,AT)
        self.assertEqual(['CLM-1','CLM-2'],report['shared_source_roots']['fixture-source'])

    def test_budget_reservation_and_actual_overrun(self):
        self.i['budget'].update(cost_limit=3,reserve=1)
        self.start('A',2)
        with self.assertRaisesRegex(ValueError,'reserve boundary'): self.start('B',1)
        self.finish('A',cost=4)
        self.assertEqual(4,self.s['spent'])
        with self.assertRaisesRegex(ValueError,'BUDGET_OVERRUN'): self.start('B')

    def test_no_fixed_global_retry_count(self):
        self.i['tasks'][0]['attempt_limit']=1
        self.start(); self.finish(accepted=False)
        with self.assertRaisesRegex(ValueError,'attempt budget'): self.start()

    def test_replay_idempotence_and_conflicting_duplicate(self):
        e=self.event('start',task_id='A',reserved_cost=1)
        s=n.replay(self.i,[e,e]); self.assertEqual(1,s['tasks']['A']['attempts'])
        with self.assertRaisesRegex(ValueError,'conflicting duplicate'):
            n.replay(self.i,[e,{**e,'reserved_cost':2}])

    def test_checkpoint_requires_matching_full_history(self):
        e=self.event('start',task_id='A',reserved_cost=1)
        checkpoint=n.replay(self.i,[e])
        end=self.event('finish',task_id='A',actual_cost=1,accepted=False,evidence_refs=[])
        self.assertEqual(1,n.replay(self.i,[e,end],checkpoint)['spent'])
        bad=copy.deepcopy(checkpoint); bad['spent']=0.01
        with self.assertRaisesRegex(ValueError,'checkpoint'):
            n.replay(self.i,[e,end],bad)

    def test_shared_mutable_resource_is_exclusive(self):
        self.i['tasks'][1]['resource_scope']=self.i['tasks'][0]['resource_scope']
        self.start('A')
        with self.assertRaisesRegex(ValueError,'resource'):self.start('B')

    def test_no_closure_with_unfinished_work(self):
        with self.assertRaisesRegex(ValueError,'incomplete'):
            self.run_event('close',closure={},evidence_refs=['fixture'])

    def test_qa_acceptance_requires_predicates(self):
        self.start()
        with self.assertRaisesRegex(ValueError,'predicates'):
            self.run_event('finish',task_id='A',actual_cost=1,accepted=True,evidence_refs=['fixture'],predicate_results={'contract_met':False})

    def test_cycles_and_orphan_tasks_fail(self):
        self.i['tasks'][0]['depends_on']=['C']
        with self.assertRaisesRegex(ValueError,'cycle'): n.initial(self.i)
        self.i['tasks'][0]['depends_on']=[]
        self.i['tasks'][0]['purpose_ref']='different'
        with self.assertRaisesRegex(ValueError,'orphan'):n.initial(self.i)

    def test_dissent_survives_replay(self):
        e=self.event('dissent',issuer='fixture-reviewer',objection='strong alternative',risk_owner='fixture-owner',evidence_refs=['fixture'])
        self.assertEqual('strong alternative',n.replay(self.i,[e])['dissent'][0]['objection'])

    def test_host_authority_not_inferred(self):
        self.i['mandate']['scope']='production'
        with self.assertRaisesRegex(ValueError,'offline-analysis only'):n.initial(self.i)

    def test_sufficient_result_can_cancel_unneeded_work(self):
        closure={k:'fixture record' for k in ('achieved','outstanding','accountable','on_breach','conservation_resources')}
        self.run_event('terminate',outcome='SUFFICIENT_RESULT',reason='Cooperation resolved the need',closure=closure,evidence_refs=['fixture-cooperation'])
        self.assertEqual('CANCELLED',self.s['tasks']['A']['status'])
        self.assertTrue(self.s['closed'])
        with self.assertRaisesRegex(ValueError,'closed instance'):self.start()

    def test_deadline_and_event_order(self):
        with self.assertRaisesRegex(ValueError,'EXPIRED'):
            self.run_event('start',task_id='A',reserved_cost=1,at='2031-01-01T00:00:00Z')
        self.start()
        with self.assertRaisesRegex(ValueError,'out-of-order'):
            self.run_event('dissent',at='2026-09-14T00:00:00Z',objection='x',risk_owner='owner',evidence_refs=['x'])

if __name__ == '__main__':unittest.main()
