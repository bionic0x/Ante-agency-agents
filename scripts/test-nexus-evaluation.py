#!/usr/bin/env python3
import importlib.util
import json
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
def module(file):
 s=importlib.util.spec_from_file_location(file,ROOT/'scripts'/file);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
e=module('evaluate-nexus.py');o=module('nexus-options.py')

class EvaluationTests(unittest.TestCase):
 def setUp(self):
  self.cases=json.loads((ROOT/'examples/nexus/evaluation-cases.json').read_text())
  self.rows=[{'case_id':'level-inversion','trial_id':'fixture-1','variant':v,'model_version':'fixture','host_version':'fixture','evidence_ref':'fixture-only','reviewer':'fixture-reviewer','inputs_hash':'same-inputs','budget_policy_ref':'same-budget','started_at':'2026-09-15T00:00:00Z','cost':1,'latency_seconds':1,'correct_reaction':True,'uncertainty_preserved':True,'traceable':True,'fatal_violation':False} for v in sorted(e.VARIANTS)]
 def test_empty_runs_cannot_claim_gain(self):self.assertEqual('NOT_MEASURED',e.evaluate(self.cases,[])['status'])
 def test_complete_pairs_and_missing_coverage_visible(self):
  r=e.evaluate(self.cases,self.rows);self.assertEqual(1,r['paired_trials']);self.assertEqual(11,len(r['missing_cases']))
 def test_rejects_unpaired_or_incomparable_trials(self):
  with self.assertRaises(ValueError):e.evaluate(self.cases,self.rows[:2])
  self.rows[0]['inputs_hash']='different'
  with self.assertRaises(ValueError):e.evaluate(self.cases,self.rows)
 def test_fatal_violation_stays_separate(self):
  self.rows[0]['fatal_violation']=True
  r=e.evaluate(self.cases,self.rows)
  self.assertEqual(1,sum(v['fatal_violation'] for v in r['comparisons']))
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
