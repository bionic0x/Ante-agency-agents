#!/usr/bin/env python3
import importlib.util
import json
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
def module(file):
 s=importlib.util.spec_from_file_location(file,ROOT/'scripts'/file);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
import shutil,tempfile
e=module('evaluate-nexus.py');o=module('nexus-options.py');b=module('nexus-blind.py')

SUBMISSIONS={'single_agent':'a1b2c3d4e5f60001','fixed_team':'a1b2c3d4e5f60002','nexus_instance':'a1b2c3d4e5f60003'}

def trial(variant,**over):
 row={'submission_id':SUBMISSIONS[variant],'case_id':'level-inversion','trial_id':'fixture-1','variant':variant,
  'model_version':'fixture-model','host_version':'fixture-host','evidence_ref':'fixture-only','operator':'fixture-operator',
  'inputs_hash':'same-inputs','budget_policy_ref':'same-budget','started_at':'2026-09-15T00:00:00Z',
  'cost_usd':1.0,'tokens_total':100,'wall_time_seconds':10,'invalid_decisions':0,'rework_cycles':0}
 row.update(over);return row

def judgment(variant,**over):
 row={'submission_id':SUBMISSIONS[variant],'reviewer':'fixture-reviewer','judged_at':'2026-09-16T00:00:00Z',
  'evidence_ref':'fixture-rubric','factual_errors':0,'fatal_defects':0,'constraint_violations':0,
  'evidence_coverage':{'covered':4,'required':4}}
 row.update(over);return row

class EvaluationTests(unittest.TestCase):
 def setUp(self):
  self.cases=json.loads((ROOT/'examples/nexus/evaluation-cases.json').read_text())
  self.rows=[trial(v) for v in sorted(e.VARIANTS)]
  self.judgments=[judgment(v) for v in sorted(e.VARIANTS)]

 def test_empty_runs_cannot_claim_gain(self):
  r=e.evaluate(self.cases,[])
  self.assertEqual('NOT_MEASURED',r['status']);self.assertEqual(12,len(r['missing_cases']))

 def test_complete_pairs_and_missing_coverage_visible(self):
  r=e.evaluate(self.cases,self.rows,self.judgments)
  self.assertEqual('RECORDED_TRIALS',r['status']);self.assertEqual(1,r['paired_trials'])
  self.assertEqual(11,len(r['missing_cases']));self.assertEqual([],r['unjudged_submissions'])

 def test_never_ranks_or_scores(self):
  r=e.evaluate(self.cases,self.rows,self.judgments)
  self.assertNotIn('winner',r);self.assertNotIn('score',r);self.assertNotIn('rank',r)
  for entry in r['comparisons']:
   self.assertFalse({'score','rank','overall','winner','composite'}&set(entry))

 def test_rejects_supplied_score_or_rank(self):
  for field in ('score','rank','overall','winner','composite'):
   with self.assertRaisesRegex(ValueError,'ranking field'):
    e.evaluate(self.cases,[trial(v,**({field:1} if v=='nexus_instance' else {})) for v in sorted(e.VARIANTS)],self.judgments)

 def test_judgment_naming_its_variant_is_not_blind(self):
  for leak in ('variant','case_id','trial_id','model_version'):
   bad=[judgment(v) for v in sorted(e.VARIANTS)];bad[0][leak]='nexus_instance'
   with self.assertRaisesRegex(ValueError,'not made blind'):e.evaluate(self.cases,self.rows,bad)

 def test_submission_id_must_not_encode_the_variant(self):
  rows=[trial(v) for v in sorted(e.VARIANTS)];rows[0]['submission_id']='nexus-run-0001'
  with self.assertRaisesRegex(ValueError,'16 hex'):e.evaluate(self.cases,rows,[])

 def test_operator_cannot_judge_own_run(self):
  bad=[judgment(v) for v in sorted(e.VARIANTS)];bad[0]['reviewer']='fixture-operator'
  with self.assertRaisesRegex(ValueError,'cannot be judged by'):e.evaluate(self.cases,self.rows,bad)

 def test_rejects_unpaired_or_incomparable_trials(self):
  r=e.evaluate(self.cases,self.rows[:2],[])
  self.assertEqual('NOT_MEASURED',r['status']);self.assertEqual(1,len(r['incomplete_pairs']))
  self.assertEqual(['single_agent'],r['incomplete_pairs'][0]['missing_variants'])
  for field in ('inputs_hash','budget_policy_ref','model_version','host_version'):
   rows=[trial(v) for v in sorted(e.VARIANTS)];rows[0][field]='different'
   with self.assertRaisesRegex(ValueError,field):e.evaluate(self.cases,rows,[])

 def test_fatal_defects_stay_separate_and_uncompensated(self):
  judgments=[judgment(v) for v in sorted(e.VARIANTS)]
  judgments=[judgment(v,**({'fatal_defects':1} if v=='nexus_instance' else {})) for v in sorted(e.VARIANTS)]
  rows=[trial(v,**({'cost_usd':0.01,'tokens_total':1} if v=='nexus_instance' else {})) for v in sorted(e.VARIANTS)]
  r=e.evaluate(self.cases,rows,judgments)
  nexus=[c for c in r['comparisons'] if c['variant']=='nexus_instance'][0]
  self.assertEqual(1,nexus['fatal_defects']['total'])
  self.assertEqual(1,nexus['fatal_defects']['trials_with_any'])
  self.assertTrue(any('never offset' in l for l in r['limitations']))

 def test_evidence_coverage_keeps_its_denominator(self):
  judgments=[judgment(v) for v in sorted(e.VARIANTS)]
  judgments[0]['evidence_coverage']={'covered':0,'required':0}
  r=e.evaluate(self.cases,self.rows,judgments)
  entry=[c for c in r['comparisons'] if c['variant']==sorted(e.VARIANTS)[0]][0]
  self.assertIsNone(entry['evidence_coverage']['ratio'])
  bad=[judgment(v) for v in sorted(e.VARIANTS)];bad[0]['evidence_coverage']={'covered':5,'required':4}
  with self.assertRaisesRegex(ValueError,'exceeds'):e.evaluate(self.cases,self.rows,bad)

 def test_unjudged_runs_are_named_not_assumed_clean(self):
  r=e.evaluate(self.cases,self.rows,self.judgments[:2])
  self.assertEqual(1,len(r['unjudged_submissions']))
  for entry in r['comparisons']:
   if entry['judged_trials']==0:
    self.assertNotIn('fatal_defects',entry)

 def test_run_counters_are_reported_with_spread(self):
  r=e.evaluate(self.cases,self.rows,self.judgments)
  entry=r['comparisons'][0]
  for field in e.RUN_COUNTERS:
   self.assertEqual({'median','min','max','total'},set(entry[field]))

 def test_quality_uses_identical_fully_judged_pairs(self):
  r=e.evaluate(self.cases,self.rows,self.judgments[:2])
  self.assertEqual(0,r['judged_paired_trials'])
  for entry in r['comparisons']:
   self.assertEqual(0,entry['paired_trials'])
   self.assertNotIn('factual_errors',entry)
   self.assertNotIn('cost_usd',entry)
  self.assertTrue(all(c['paired_trials']==1 for c in r['execution_comparisons']))

 def test_incomplete_pair_keeps_fatal_findings_and_unjudged_ids(self):
  rows=[trial('nexus_instance'),trial('fixed_team')]
  r=e.evaluate(self.cases,rows,[judgment('nexus_instance',fatal_defects=2)])
  self.assertEqual(2,r['fatal_observations'][0]['fatal_defects'])
  self.assertEqual([SUBMISSIONS['fixed_team']],r['unjudged_submissions'])

 def test_orphan_judgments_rejected_even_without_trials(self):
  with self.assertRaisesRegex(ValueError,'unknown submission'):
   e.evaluate(self.cases,[],self.judgments)

 def test_trial_metadata_types_and_chronology(self):
  for rows in ({},None,[None],[[]]):
   with self.assertRaises(ValueError):e.evaluate(self.cases,rows,[])
  for sid in (1234567890123456,'1234567890123456\n','../escape'):
   with self.assertRaisesRegex(ValueError,'16 hex'):
    e.load_trials([trial('single_agent',submission_id=sid)])
  with self.assertRaisesRegex(ValueError,'timezone'):
   e.load_trials([trial('single_agent',started_at='2026-09-15T00:00:00')])
  with self.assertRaisesRegex(ValueError,'predates'):
   e.evaluate(self.cases,self.rows,[judgment('single_agent',judged_at='2025-01-01T00:00:00Z')])

 def test_reviewer_cannot_be_any_trial_operator(self):
  rows=[trial(v,operator=v+'-operator') for v in sorted(e.VARIANTS)]
  with self.assertRaisesRegex(ValueError,'cannot be judged by'):
   e.evaluate(self.cases,rows,[judgment('single_agent',reviewer=' FIXED_TEAM-OPERATOR ')])


class BlindingTests(unittest.TestCase):
 def setUp(self):
  self.dir=Path(tempfile.mkdtemp(prefix='nexus-blind-'));self.addCleanup(shutil.rmtree,self.dir,True)
  self.artifacts=self.dir/'runs';self.artifacts.mkdir()
  self.trials=[trial(v) for v in sorted(e.VARIANTS)]
  for row in self.trials:
   (self.artifacts/f"{row['submission_id']}.md").write_text('The local KPI improves while the superior outcome deteriorates.\n')
  self.trials_file=self.dir/'trials.json';self.trials_file.write_text(json.dumps(self.trials))

 def test_submission_id_is_opaque_and_salt_dependent(self):
  a=b.submission_id('c','t','nexus_instance','salt-one')
  c=b.submission_id('c','t','nexus_instance','salt-two')
  self.assertNotEqual(a,c);self.assertEqual(16,len(a))
  self.assertNotIn('nexus',a);self.assertEqual(a,b.submission_id('c','t','nexus_instance','salt-one'))

 def test_seal_produces_shuffled_packet_without_variant(self):
  r=b.seal(self.trials_file,self.artifacts,self.dir/'review',seed=1)
  self.assertEqual(3,r['sealed'])
  index=json.loads((self.dir/'review'/'index.json').read_text())
  self.assertEqual(3,len(index['submissions']))
  for entry in index['submissions']:
   self.assertEqual({'submission_id','case_scenario','expected_behavior','artifact','artifact_sha256'},set(entry))
   self.assertTrue(entry['case_scenario'])
   self.assertTrue(entry['expected_behavior'])
   self.assertEqual(64,len(entry['artifact_sha256']))
  self.assertIsNone(index['known_tells'])
  self.assertNotIn('variant',json.dumps(index))

 def test_self_narrating_artifact_refuses_to_seal(self):
  target=self.artifacts/f"{SUBMISSIONS['nexus_instance']}.md"
  target.write_text('As the NEXUS orchestrator I will delegate this to a subagent.\n')
  with self.assertRaisesRegex(ValueError,'defeats the blind'):
   b.seal(self.trials_file,self.artifacts,self.dir/'review2',seed=1)
  self.assertFalse((self.dir/'review2').exists())
  r=b.seal(self.trials_file,self.artifacts,self.dir/'review3',allow_tells=True,seed=1)
  self.assertTrue(r['tells_recorded'])
  index=json.loads((self.dir/'review3'/'index.json').read_text())
  self.assertIn(SUBMISSIONS['nexus_instance'],index['known_tells'])

 def test_will_not_overwrite_a_sealed_packet(self):
  b.seal(self.trials_file,self.artifacts,self.dir/'review4',seed=1)
  with self.assertRaisesRegex(ValueError,'already exists'):
   b.seal(self.trials_file,self.artifacts,self.dir/'review4',seed=1)

 def test_missing_artifact_is_an_error_not_an_omission(self):
  (self.artifacts/f"{SUBMISSIONS['fixed_team']}.md").unlink()
  with self.assertRaisesRegex(ValueError,'missing artifact'):
   b.seal(self.trials_file,self.artifacts,self.dir/'review5',seed=1)
  self.assertFalse((self.dir/'review5').exists())

 def test_unsafe_or_duplicate_ids_fail_before_writing(self):
  for sid in ('../escape','/tmp/escape',SUBMISSIONS['fixed_team']):
   rows=[trial(v) for v in sorted(e.VARIANTS)]
   rows[-1]['submission_id']=sid
   self.trials_file.write_text(json.dumps(rows))
   with self.assertRaises(ValueError):
    b.seal(self.trials_file,self.artifacts,self.dir/'unsafe')
   self.assertFalse((self.dir/'unsafe').exists())

 def test_external_artifact_symlink_rejected(self):
  target=self.artifacts/f"{SUBMISSIONS['single_agent']}.md"
  target.unlink();outside=self.dir/'external.md';outside.write_text('external')
  target.symlink_to(outside)
  with self.assertRaisesRegex(ValueError,'regular file'):
   b.seal(self.trials_file,self.artifacts,self.dir/'linked')
  self.assertFalse((self.dir/'linked').exists())

 def test_missing_case_and_existing_empty_destination_rejected(self):
  out=self.dir/'empty';out.mkdir()
  with self.assertRaisesRegex(ValueError,'already exists'):
   b.seal(self.trials_file,self.artifacts,out)
  self.trials[0]['case_id']='unknown'
  self.trials_file.write_text(json.dumps(self.trials))
  with self.assertRaisesRegex(ValueError,'unknown case'):
   b.seal(self.trials_file,self.artifacts,self.dir/'unknown')
  self.assertFalse((self.dir/'unknown').exists())

 def test_factor_comparison_respects_veto_and_sensitivity(self):
  d=json.loads((ROOT/'examples/nexus/options.json').read_text());r=o.analyze(d)
  self.assertNotIn('inadmissible-fast',r['base']['undominated'])
  self.assertEqual(['bounded-pilot'],r['base']['undominated'])
  self.assertTrue(r['scenarios'][0]['frontier_changed'])
 def test_unknown_and_unfounded_measurements(self):
  d=json.loads((ROOT/'examples/nexus/options.json').read_text());d['options'][0]['factors']['cost']={'value':None,'status':'UNKNOWN'}
  self.assertTrue(o.analyze(d)['base']['unknown_factors'])
  d['options'][0]['factors']['cost']={'value':2,'status':'MEASURED'}
  with self.assertRaisesRegex(ValueError,'source/window'):o.analyze(d)

 def test_dominance_discloses_evidence_basis(self):
  d=json.loads((ROOT/'examples/nexus/options.json').read_text())
  edge=o.analyze(d)['base']['dominance'][0]
  self.assertEqual(['HYPOTHESIS'],edge['evidence_basis']);self.assertFalse(edge['measured_only'])
  for option in d['options']:
   for factor in option['factors'].values():
    factor.update(status='MEASURED',source_ref='fixture',window='fixture',method='fixture',baseline='fixture')
  edge=o.analyze(d)['base']['dominance'][0]
  self.assertEqual(['MEASURED'],edge['evidence_basis']);self.assertTrue(edge['measured_only'])
  d['options'][0]['factors']['cost']['status']='ESTIMATE'
  edge=o.analyze(d)['base']['dominance'][0]
  self.assertEqual(['ESTIMATE','MEASURED'],edge['evidence_basis']);self.assertFalse(edge['measured_only'])
  self.assertFalse(o.analyze(d)['scenarios'][0]['comparison']['dominance'])

if __name__=='__main__':unittest.main()
