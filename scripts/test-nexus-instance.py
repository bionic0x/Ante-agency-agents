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
        with self.assertRaisesRegex(ValueError,'new independent source root'):
            self.run_event('claim_revision', claim=c, reason='new reference, same lineage')
        c['source_roots'].append('fixture-independent-root')
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
        with self.assertRaisesRegex(ValueError,'offline-analysis or local-relay'):n.initial(self.i)

    def test_local_relay_scope_uses_the_same_contract(self):
        self.i['mandate']['scope']='local-relay'
        self.assertEqual('PENDING',n.initial(self.i)['tasks']['A']['status'])

    def test_sufficient_result_can_cancel_unneeded_work(self):
        closure={k:'fixture record' for k in ('achieved','outstanding','accountable','on_breach','conservation_resources')}
        self.run_event('terminate',outcome='SUFFICIENT_RESULT',reason='Cooperation resolved the need',closure=closure,evidence_refs=['fixture-cooperation'])
        self.assertEqual('CANCELLED',self.s['tasks']['A']['status'])
        self.assertTrue(self.s['closed'])
        with self.assertRaisesRegex(ValueError,'closed instance'):self.start()

    def test_plan_rejects_non_text_clock_cleanly(self):
        import datetime as dt
        with self.assertRaisesRegex(ValueError, 'timestamp text'):
            n.plan(self.i, self.s, dt.datetime(2026, 9, 19, tzinfo=dt.timezone.utc))

    def test_deadline_and_event_order(self):
        with self.assertRaisesRegex(ValueError,'EXPIRED'):
            self.run_event('start',task_id='A',reserved_cost=1,at='2031-01-01T00:00:00Z')
        self.start()
        with self.assertRaisesRegex(ValueError,'out-of-order'):
            self.run_event('dissent',at='2026-09-14T00:00:00Z',objection='x',risk_owner='owner',evidence_refs=['x'])

    def completed_pilot(self):
        events = [json.loads(l) for l in (ROOT / 'examples/nexus/strategic-decision.events.jsonl').read_text().splitlines()]
        self.s = n.replay(self.i, events[:-1])
        return {k: events[-1][k] for k in ('closure', 'evidence_refs')}

    def rebind(self, task):
        return self.run_event('rebind_claims', task_id=task,
                              claim_revisions=self.s['tasks'][task]['claim_revisions'], reason='Review changed inputs')

    def test_upstream_rerun_requires_new_downstream_result(self):
        closure = self.completed_pilot()
        self.rebind('B'); self.start('B'); self.finish('B')
        self.assertFalse(n.blockers(self.i, self.s, 'A', AT))
        with self.assertRaisesRegex(ValueError, 'incomplete/stale'):
            self.run_event('close', **closure)
        self.assertIn('TASK_INPUT_REVIEW', n.blockers(self.i, self.s, 'C', AT))
        self.rebind('C')
        self.assertEqual((1, 1), (self.s['tasks']['C']['spent'], self.s['tasks']['C']['attempts']))
        self.start('C'); self.finish('C')
        self.assertEqual({'A': 1, 'B': 2}, self.s['tasks']['C']['dependency_revisions'])
        self.assertEqual(2, self.s['tasks']['C']['result_revision'])
        self.run_event('close', **closure)
        self.assertEqual(5, self.s['spent'])

    def test_running_consumer_reconciles_cost_but_requires_review(self):
        self.start('A'); self.finish('A'); self.start('B'); self.finish('B'); self.start('C')
        self.rebind('B'); self.start('B'); self.finish('B'); self.finish('C')
        self.assertEqual(4, self.s['spent'])
        self.assertEqual(0, self.s['tasks']['C']['reserved'])
        self.assertIn('TASK_INPUT_REVIEW', n.blockers(self.i, self.s, 'C', AT))
        self.assertIn('DEPENDENCY_REVISION:B', n.blockers(self.i, self.s, 'C', AT))

    def test_task_invalidation_reaches_transitive_consumers(self):
        d = copy.deepcopy(self.i['tasks'][2])
        d.update(id='D', depends_on=['C'], resource_scope=['fixture-D'])
        self.i['tasks'].append(d); self.s = n.initial(self.i)
        for task in ('A', 'B', 'C', 'D'):
            self.start(task); self.finish(task)
        self.rebind('B'); self.start('B'); self.finish('B')
        self.rebind('C'); self.start('C'); self.finish('C')
        self.assertIn('TASK_INPUT_REVIEW', n.blockers(self.i, self.s, 'D', AT))
        self.assertFalse(n.blockers(self.i, self.s, 'A', AT))

    def test_shared_claim_cannot_hide_cross_scope_ancestor(self):
        self.i['claims'][0]['scope'] = 'solana'
        self.i['tasks'][0]['evidence_scope'] = 'solana'
        self.i['tasks'][2]['evidence_scope'] = 'arbitrum'
        with self.assertRaisesRegex(ValueError, 'cross-scope'):
            n.initial(self.i)

    def test_revised_claim_scope_blocks_transitive_consumers(self):
        claim = copy.deepcopy(self.s['claims']['CLM-1'])
        claim.update(revision=2, scope='solana')
        self.run_event('claim_revision', claim=claim, reason='Premise applies only to Solana')
        self.assertIn('CLAIM_SCOPE:CLM-1', n.blockers(self.i, self.s, 'C', AT))

    def test_same_scope_and_shared_ancestry_are_accepted(self):
        self.i['claims'][0]['scope'] = 'solana'
        for task in self.i['tasks']:
            task['evidence_scope'] = 'solana'
        self.s = n.initial(self.i)
        self.assertFalse([b for b in n.blockers(self.i, self.s, 'C', AT) if 'SCOPE' in b])

    def test_empty_task_plan_is_rejected(self):
        self.i['tasks'] = []
        with self.assertRaisesRegex(ValueError, 'at least one task'):
            n.initial(self.i)

    def test_success_closure_checks_mandate_and_deadline(self):
        closure = self.completed_pilot()
        for field in ('mandate', 'budget'):
            with self.subTest(field=field):
                instance = copy.deepcopy(self.i)
                instance[field]['expires' if field == 'mandate' else 'deadline'] = AT
                with self.assertRaisesRegex(ValueError, 'EXPIRED'):
                    n.apply(instance, self.s, self.event('close', **closure))
        self.run_event('terminate', at='2031-01-01T00:00:00Z', outcome='EXPIRED',
                       reason='Record closure after expiry', **closure)
        self.assertTrue(self.s['closed'])

    def closure(self):
        return {k:'fixture record' for k in ('achieved','outstanding','accountable','on_breach','conservation_resources')}

    def test_sufficient_result_cannot_bypass_fatal_defect(self):
        self.run_event('hold', condition={'id':'fatal','classification':'FATAL_DEFECT','task_ids':['A'],'reason':'inadmissible'})
        with self.assertRaisesRegex(ValueError,'fatal defect prevents sufficient-result'):
            self.run_event('terminate',outcome='SUFFICIENT_RESULT',reason='declare success',closure=self.closure(),evidence_refs=['x'])
        self.run_event('terminate',outcome='REDESIGN',reason='fatal defect',closure=self.closure(),evidence_refs=['x'])
        self.assertEqual('REDESIGN',self.s['termination_outcome'])

    def test_sufficient_result_cannot_overwrite_negative_decision(self):
        for decision in ('REJECT', 'REDESIGN'):
            with self.subTest(decision=decision):
                self.s = n.initial(self.i)
                self.run_event('decision', state=decision, reason='inadmissible mechanism')
                with self.assertRaisesRegex(ValueError,'REJECT/REDESIGN termination'):
                    self.run_event('terminate',outcome='SUFFICIENT_RESULT',reason='relabel',closure=self.closure(),evidence_refs=['x'])

    def test_rebind_rejects_cross_scope_claim(self):
        c = copy.deepcopy(self.s['claims']['CLM-1']); c.update(revision=2, scope='arbitrum')
        self.run_event('claim_revision', claim=c, reason='scope narrowed to one network')
        revisions = dict(self.s['tasks']['A']['claim_revisions']); revisions['CLM-1'] = 2
        with self.assertRaisesRegex(ValueError,'cross-scope'):
            self.run_event('rebind_claims', task_id='A', claim_revisions=revisions, reason='rebind')

    def test_rebind_rejects_cross_scope_ancestor(self):
        c = copy.deepcopy(self.s['claims']['CLM-1']); c.update(revision=2, scope='arbitrum')
        self.run_event('claim_revision', claim=c, reason='scope narrowed')
        c = copy.deepcopy(self.s['claims']['CLM-2']); c.update(revision=2)
        self.run_event('claim_revision', claim=c, reason='review shared conclusion')
        with self.assertRaisesRegex(ValueError,'cross-scope'):
            self.run_event('rebind_claims', task_id='C', claim_revisions={'CLM-2':2}, reason='rebind shared conclusion')

    def test_unknown_references_fail_with_diagnostics(self):
        with self.assertRaisesRegex(ValueError,'unknown or already resolved condition'):
            self.run_event('resolve_hold', condition_id='missing', evidence_refs=['x'], reason='r')
        with self.assertRaisesRegex(ValueError,'existing claim'):
            self.run_event('claim_revision', claim={'id':'CLM-404'}, reason='r')
        for field in ('at', 'type'):
            event = self.event('dissent'); event.pop(field)
            with self.assertRaisesRegex(ValueError, f'event.{field} required'):
                n.apply(self.i, self.s, event)


class IndependentJudgmentTests(unittest.TestCase):
    """P1-P6 of the 2026-10-10 stress test: who may judge, and on what evidence."""
    setUp, event, run_event = InstanceTests.setUp, InstanceTests.event, InstanceTests.run_event
    start, finish, closure = InstanceTests.start, InstanceTests.finish, InstanceTests.closure

    def complete_fixture(self):
        for task in ('A', 'B', 'C'):
            self.start(task); self.finish(task)

    # P1: work never grades itself.
    def test_p1_task_agent_cannot_accept_its_own_work(self):
        self.start('A')
        with self.assertRaisesRegex(ValueError, 'independent owner/reviewer'):
            self.run_event('finish', issuer='general-strategy-director', task_id='A', accepted=True, actual_cost=1,
                           evidence_refs=['own-output'], predicate_results={'contract_met': True})
        # The agent may still report a non-accepted finish; a named reviewer may accept.
        self.run_event('finish', issuer='general-strategy-director', task_id='A', accepted=False, actual_cost=1,
                       evidence_refs=['own-output'])
        self.assertEqual('FAILED', self.s['tasks']['A']['status'])
        self.start('A')
        self.run_event('finish', issuer='fixture-reviewer', task_id='A', accepted=True, actual_cost=1,
                       evidence_refs=['reviewed-output'], predicate_results={'contract_met': True})
        self.assertEqual('SUCCEEDED', self.s['tasks']['A']['status'])

    def test_p1_reviewer_named_as_task_agent_still_cannot_self_accept(self):
        self.i['mandate']['reviewers'].append('general-strategy-director')
        self.s = n.initial(self.i)
        self.start('A')
        with self.assertRaisesRegex(ValueError, 'independent owner/reviewer'):
            self.run_event('finish', issuer='general-strategy-director', task_id='A', accepted=True, actual_cost=1,
                           evidence_refs=['own-output'], predicate_results={'contract_met': True})

    # P2: task output and old lineage are not corroboration.
    def test_p2_task_output_cannot_promote_claim(self):
        self.start('A'); self.finish('A')
        c = copy.deepcopy(self.s['claims']['CLM-1'])
        c.update(revision=2, status='EVIDENCE', source_refs=c['source_refs'] + ['fixture-result'],
                 source_roots=c['source_roots'] + ['task-A-run'])
        with self.assertRaisesRegex(ValueError, 'task outputs cannot promote'):
            self.run_event('claim_revision', issuer='fixture-reviewer', claim=c, reason='agent output agrees')

    def test_p2_rejected_output_is_also_not_evidence(self):
        self.start('A'); self.finish('A', accepted=False)
        c = copy.deepcopy(self.s['claims']['CLM-1'])
        c.update(revision=2, status='EVIDENCE', source_refs=c['source_refs'] + ['fixture-result'],
                 source_roots=c['source_roots'] + ['task-A-run'])
        with self.assertRaisesRegex(ValueError, 'task outputs cannot promote'):
            self.run_event('claim_revision', claim=c, reason='rejected output reused')

    # P3: widening or transferring a scoped claim costs as much as a promotion.
    def scoped_fixture(self):
        self.i['claims'][0]['scope'] = 'solana'
        self.i['claims'][1]['depends_on'] = []
        self.i['tasks'][0]['evidence_scope'] = 'solana'
        self.i['tasks'][2]['evidence_scope'] = 'arbitrum'
        self.s = n.initial(self.i)

    def test_p3_reviewer_cannot_launder_scope_to_shared(self):
        self.scoped_fixture()
        c = copy.deepcopy(self.s['claims']['CLM-1']); c.update(revision=2, scope='shared')
        with self.assertRaisesRegex(ValueError, 'scope reclassification requires the named owner'):
            self.run_event('claim_revision', issuer='fixture-reviewer', claim=c, reason='reclassified',
                           evidence_refs=['x'])
        with self.assertRaisesRegex(ValueError, 'evidence_refs'):
            self.run_event('claim_revision', claim=c, reason='reclassified without evidence')
        self.run_event('claim_revision', claim=c, reason='network-independent premise',
                       evidence_refs=['owner-review:network-independence'])
        self.assertEqual('shared', self.s['claims']['CLM-1']['scope'])

    def test_p3_transfer_between_scopes_needs_owner_evidence(self):
        self.scoped_fixture()
        c = copy.deepcopy(self.s['claims']['CLM-1']); c.update(revision=2, scope='arbitrum')
        with self.assertRaisesRegex(ValueError, 'scope reclassification'):
            self.run_event('claim_revision', issuer='fixture-reviewer', claim=c, reason='move premise')

    def test_p3_narrowing_a_shared_claim_stays_open_to_reviewers(self):
        c = copy.deepcopy(self.s['claims']['CLM-1']); c.update(revision=2, scope='solana')
        self.run_event('claim_revision', issuer='fixture-reviewer', claim=c, reason='applies only to Solana')
        self.assertEqual('solana', self.s['claims']['CLM-1']['scope'])

    # P4: sufficiency cannot relabel a pending decision or missing evidence.
    def test_p4_sufficient_result_refused_under_hold_decision(self):
        self.run_event('decision', state='HOLD', reason='await evidence')
        with self.assertRaisesRegex(ValueError, 'HOLD decision prevents'):
            self.run_event('terminate', outcome='SUFFICIENT_RESULT', reason='good enough',
                           closure=self.closure(), evidence_refs=['x'])
        self.run_event('terminate', outcome='FAILURE', reason='abandoned while held',
                       closure=self.closure(), evidence_refs=['x'])
        self.assertEqual('FAILURE', self.s['termination_outcome'])

    def test_p4_sufficient_result_refused_with_pending_evidence(self):
        self.run_event('hold', condition={'id': 'h1', 'classification': 'PENDING_EVIDENCE', 'task_ids': ['A'],
                                          'reason': 'unverified market data'})
        with self.assertRaisesRegex(ValueError, 'pending evidence prevents'):
            self.run_event('terminate', outcome='SUFFICIENT_RESULT', reason='good enough',
                           closure=self.closure(), evidence_refs=['x'])

    def test_p4_accepted_risk_does_not_block_sufficiency(self):
        self.run_event('hold', condition={'id': 'r1', 'classification': 'ACCEPTED_RISK', 'task_ids': ['A'],
                                          'reason': 'known exposure'})
        self.run_event('terminate', outcome='SUFFICIENT_RESULT', reason='need met by cooperation',
                       closure=self.closure(), evidence_refs=['x'])
        self.assertTrue(self.s['closed'])

    # P5: dissent needs an answer before success.
    def dissent(self):
        self.run_event('dissent', issuer='fixture-reviewer', objection='Subplans A and B are incompatible',
                       risk_owner='fixture-owner', evidence_refs=['review-1'])
        return self.s['open_dissent'][-1]

    def test_p5_unanswered_dissent_blocks_success(self):
        self.complete_fixture()
        did = self.dissent()
        with self.assertRaisesRegex(ValueError, 'unanswered dissent prevents success closure'):
            self.run_event('close', closure=self.closure(), evidence_refs=['x'])
        with self.assertRaisesRegex(ValueError, 'unanswered dissent prevents sufficient-result'):
            self.run_event('terminate', outcome='SUFFICIENT_RESULT', reason='done', closure=self.closure(),
                           evidence_refs=['x'])
        self.assertIn(did, n.plan(self.i, self.s, AT)['open_dissent'])

    def test_p5_owner_answer_unblocks_closure_and_is_preserved(self):
        self.complete_fixture()
        did = self.dissent()
        with self.assertRaisesRegex(ValueError, 'only named owner can answer'):
            self.run_event('dissent_response', issuer='fixture-reviewer', dissent_id=did, disposition='REFUTED',
                           response='no', risk_owner='fixture-owner', evidence_refs=['x'])
        with self.assertRaisesRegex(ValueError, 'unknown dissent disposition'):
            self.run_event('dissent_response', dissent_id=did, disposition='IGNORED',
                           response='no', risk_owner='fixture-owner', evidence_refs=['x'])
        self.run_event('dissent_response', dissent_id=did, disposition='RISK_ACCEPTED',
                       response='Integration conflict accepted until pricing pilot', risk_owner='fixture-owner',
                       evidence_refs=['owner-memo-1'])
        with self.assertRaisesRegex(ValueError, 'already answered'):
            self.run_event('dissent_response', dissent_id=did, disposition='REFUTED',
                           response='again', risk_owner='fixture-owner', evidence_refs=['x'])
        self.run_event('close', closure=self.closure(), evidence_refs=['x'])
        self.assertTrue(self.s['closed'])
        self.assertEqual('RISK_ACCEPTED', self.s['dissent_responses'][0]['disposition'])

    def test_p5_negative_termination_allowed_with_open_dissent(self):
        self.dissent()
        self.run_event('terminate', outcome='REDESIGN', reason='objection upheld in substance',
                       closure=self.closure(), evidence_refs=['x'])
        self.assertEqual('REDESIGN', self.s['termination_outcome'])

    # P6: the reserve has conditions of use.
    def test_p6_owner_can_release_reserve_for_named_contingency(self):
        for task in self.i['tasks']: task['cost_limit'] = 10
        with self.assertRaisesRegex(ValueError, 'reserve boundary'):
            self.start('A', 9)
        with self.assertRaisesRegex(ValueError, 'only named owner can release'):
            self.run_event('release_reserve', issuer='fixture-reviewer', amount=1, contingency='c',
                           reason='r', evidence_refs=['x'])
        with self.assertRaisesRegex(ValueError, 'exceeds remaining reserve'):
            self.run_event('release_reserve', amount=3, contingency='c', reason='r', evidence_refs=['x'])
        with self.assertRaisesRegex(ValueError, 'positive'):
            self.run_event('release_reserve', amount=0, contingency='c', reason='r', evidence_refs=['x'])
        self.run_event('release_reserve', amount=1, contingency='provider outage rerun',
                       reason='named contingency occurred', evidence_refs=['incident-7'])
        self.start('A', 9)
        report = n.plan(self.i, self.s, AT)
        self.assertEqual(1, report['reserve']); self.assertEqual(1, report['reserve_released'])
        self.assertEqual(0, report['uncommitted_cost'])

    def test_p6_release_survives_replay(self):
        events = [self.event('release_reserve', amount=2, contingency='c', reason='r', evidence_refs=['x'])]
        self.assertEqual(0, n.effective_reserve(self.i, n.replay(self.i, events)))

if __name__ == '__main__':unittest.main()
