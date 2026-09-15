#!/usr/bin/env python3
"""Compare declared factors without weighted scores or compensating fatal defects."""
import argparse
import copy
import json
import math
from pathlib import Path
import sys


def analyze(doc):
    if not isinstance(doc,dict): raise ValueError('option analysis must be an object')
    factors = doc['factors']
    if not isinstance(factors,dict) or not factors or any(v not in ('higher','lower') for v in factors.values()):
        raise ValueError('factors require higher/lower preference')
    options = doc['options']; ids = [o['id'] for o in options]
    if not options or len(ids)!=len(set(ids)) or any(not isinstance(i,str) or not i.strip() for i in ids):
        raise ValueError('nonempty unique option IDs required')
    for o in options:
        if o['admissibility'] not in ('ADMISSIBLE','INADMISSIBLE','PENDING_REVIEW') or type(o['fatal_defect']) is not bool:
            raise ValueError('explicit admissibility and fatal_defect required')
        if set(o['factors'])!=set(factors): raise ValueError('every option must identify every factor')
    def evaluate(current):
        eligible, excluded = [], []
        for o in current:
            if o['admissibility']!='ADMISSIBLE' or o['fatal_defect']:
                excluded.append({'id':o['id'],'admissibility':o['admissibility'],'fatal_defect':o['fatal_defect']})
            else: eligible.append(o)
            for observation in o['factors'].values():
                value,status=observation['value'],observation['status']
                if status not in ('MEASURED','TARGET','ESTIMATE','HYPOTHESIS','UNKNOWN'): raise ValueError('unknown factor status')
                if value is not None and (type(value) not in (float,int) or not math.isfinite(value)):
                    raise ValueError('factor value must be finite or null')
                if (value is None)!=(status=='UNKNOWN'): raise ValueError('unknown factors require null; numeric factors need a declared status')
                if status=='MEASURED' and any(not isinstance(observation.get(f),str) or not observation[f].strip() for f in ('source_ref','window','method','baseline')):
                    raise ValueError('measured factor requires source/window/method/baseline')
        def dominates(a,b):
            better=[]
            for f,prefer in factors.items():
                av,bv=a['factors'][f]['value'],b['factors'][f]['value']
                if av is None or bv is None: return False
                better.append((av-bv)*(1 if prefer=='higher' else -1))
            return all(v>=0 for v in better) and any(v>0 for v in better)
        edges=[{'preferred':a['id'],'dominated':b['id']} for a in eligible for b in eligible if a!=b and dominates(a,b)]
        dominated={e['dominated'] for e in edges}
        return {'undominated':[o['id'] for o in eligible if o['id'] not in dominated], 'dominance':edges,'excluded':excluded,
                'unknown_factors':[{'option':o['id'],'factor':f} for o in eligible for f,v in o['factors'].items() if v['value'] is None]}
    base=evaluate(options); scenarios=[]
    scenario_ids=set()
    for scenario in doc.get('scenarios',[]):
        if scenario['id'] in scenario_ids: raise ValueError('duplicate scenario')
        scenario_ids.add(scenario['id']); modified=copy.deepcopy(options)
        for oid,overrides in scenario['overrides'].items():
            if oid not in ids or set(overrides)-set(factors): raise ValueError('unknown scenario option/factor')
            next(o for o in modified if o['id']==oid)['factors'].update(overrides)
        result=evaluate(modified)
        scenarios.append({'id':scenario['id'],'comparison':result,'frontier_changed':set(base['undominated'])!=set(result['undominated'])})
    return {'base':base,'scenarios':scenarios,'decision':'HUMAN_COMPARISON_REQUIRED',
            'interpretation':'Dominance is conditional on supplied values and the selected factors. No causal proof or weighted score.'}


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('input');args=ap.parse_args()
    try:
        print(json.dumps(analyze(json.loads(Path(args.input).read_text())),indent=2));return 0
    except (OSError,ValueError,KeyError,TypeError) as exc:
        print(f'ERROR {exc}',file=sys.stderr);return 1

if __name__=='__main__':sys.exit(main())
