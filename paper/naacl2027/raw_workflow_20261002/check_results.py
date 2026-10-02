"""Independent Python arithmetic versus actual processor output and saved data.

Stdlib only. No Explorer core imports. Finite/nonhuman software check, not
usability, new model observations, independent researcher validation or speed.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import platform

from make_cases import cases

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
TOL=1e-12


def reference(x):
    keys=x['canonical_keys'];physical={}
    for raw in x['physical_records']:
        logits=raw['logits'];peak=max(logits)
        exp=[math.exp((z-peak)/raw['temperature']) for z in logits]
        total=math.fsum(exp)
        probabilities=dict(zip(raw['candidate_keys'],[e/total for e in exp]))
        mapping=dict(zip(raw['candidate_keys'],logits))
        label=next(k for k in raw['tie_order'] if mapping[k]==peak)
        physical[raw['rid']]=(raw,probabilities,label)
    def answer(item,recipe):
        members=[physical[rid] for rid in recipe['member_ids']]
        p={k:math.fsum(m[1][k] for m in members)/len(members) for k in keys}
        label=members[0][2] if recipe['operation']=='single' else next(k for k in keys if p[k]==max(p.values()))
        value=label if x['type']=='choice' else p['true'] if x['type']=='noul' else math.fsum(p[k]*x['score_values'][int(k)] for k in keys)
        entropy=-math.fsum(q*math.log(q) for q in p.values() if q)
        return {'id':recipe['id'],'probabilities':p,'label':label,'typed_value':value,
                'concentration':min(1,max(0,1-entropy/math.log(len(keys)))),
                'calls':len(members),'member_ids':sorted(recipe['member_ids']),
                'member_sources':sorted([m[0]['source'] for m in members],key=lambda s:s['source_id']+':'+str(s['line_1based'])),
                'recipe_source':recipe['recipe_source'],
                'input_tokens':sum(m[0]['input_tokens'] for m in members),
                'recorded_latency_sum_ms':math.fsum(m[0]['latency_ms'] for m in members)}
    computed=[]
    for item in x['items']:
        a,b=[answer(item,item['conditions'][s]) for s in ['a','b']]
        aset,bset=set(a['member_ids']),set(b['member_ids'])
        ref={**item['reference']}
        if x['type']=='score':ref.update(a_error=abs(a['typed_value']-ref['value']),b_error=abs(b['typed_value']-ref['value']))
        else:ref.update(a_match=a['label']==ref['value'],b_match=b['label']==ref['value'])
        computed.append({'item_id':item['item_id'],'a':a,'b':b,'reference':ref,
                         'shared_physical_calls':len(aset&bset),'unique_physical_calls':len(aset|bset),
                         'same_physical_pool':aset==bset,'label_changed':a['label']!=b['label'],
                         'candidate_differences':[{'key':k,'a':a['probabilities'][k],'b':b['probabilities'][k],'delta':b['probabilities'][k]-a['probabilities'][k]} for k in keys]})
    panel={'items':len(computed),'conditions':{}}
    for side in ['a','b']:
        vals=[r[side] for r in computed];counts={k:sum(v['label']==k for v in vals) for k in keys}
        summary={'items':len(vals),'label_counts':counts,'maximum_label_share':max(counts.values())/len(vals),'used_labels':sum(v>0 for v in counts.values())}
        if x['type']=='score':
            nums=[v['typed_value'] for v in vals];mean=math.fsum(nums)/len(nums)
            summary.update(value_min=min(nums),value_max=max(nums),value_population_variance=math.fsum((n-mean)**2 for n in nums)/len(nums))
        panel['conditions'][side]=summary
    return {'schema_version':1,'case_id':x['case_id'],'status':'ok','new_model_calls':0,
            'physical_records':len(physical),'selected':next(r for r in computed if r['item_id']==x['selected_item']),
            'panel':panel,'reconstructed_items':computed}


class Check:
    def __init__(self):self.failures=[];self.numeric=0;self.max_delta=0.;self.fields=Counter()
    def same(self,a,b,where):
        if isinstance(b,dict):
            if not isinstance(a,dict):self.failures.append({'field':where,'reason':'not_object'});return
            for k,v in b.items():
                if k not in a:self.failures.append({'field':where+'.'+k,'reason':'missing'})
                else:self.same(a[k],v,where+'.'+k)
        elif isinstance(b,list):
            if not isinstance(a,list) or len(a)!=len(b):self.failures.append({'field':where,'reason':'list_length'});return
            for i,(v,w) in enumerate(zip(a,b)):self.same(v,w,where+f'[{i}]')
        elif isinstance(b,float):
            if type(a) not in [int,float] or not math.isfinite(a):self.failures.append({'field':where,'reason':'not_finite'});return
            d=abs(a-b);self.numeric+=1;self.max_delta=max(d,self.max_delta)
            self.fields[where.split('.')[-1].split('[')[0]]=max(self.fields[where.split('.')[-1].split('[')[0]],d)
            if not math.isclose(a,b,rel_tol=TOL,abs_tol=TOL):self.failures.append({'field':where,'reason':'numeric_difference','actual':a,'expected':b,'absolute_difference':d})
        elif a!=b or type(b) in (bool,int) and type(a)!=type(b):
            self.failures.append({'field':where,'reason':'exact_mismatch','actual':a,'expected':b})


def load_outputs(path):
    x=json.loads(path.read_text())
    if 'flow' not in x:return x
    strings=x.get('cache',{}).get('__s',[]);out={}
    # The runnable target node, never the raw source cache.
    cache=x['cache'].get('compute_raw.json')
    if cache is None:raise ValueError('Native Processor output cache absent')
    for row in cache:
        for value in row['responses']:
            text=strings[value] if isinstance(value,int) else value
            r=json.loads(text);assert r['case_id'] not in out,'duplicate result';out[r['case_id']]=r
    return out


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('outputs',type=Path);p.add_argument('--report',required=True,type=Path);p.add_argument('--execution',required=True,choices=['node','chainforge']);a=p.parse_args()
    assert not a.report.exists(),'Refusing to overwrite report'
    actual=load_outputs(a.outputs);allcases=cases();check=Check();archivecheck=Check();records=[]
    index=json.loads((ROOT/'docs/explorer/data/index.json').read_text());protocol=json.loads((HERE/'protocol.json').read_text())
    original_refs={};checked_saved=0
    check.same(sorted(actual),sorted(c['id'] for c in allcases),'case_inventory')
    for c in allcases:
        observed=actual.get(c['id'],{})
        if c['kind']=='synthetic_invalid':expected={'case_id':c['id'],'status':'rejected','error_code':c['expected_error']}
        else:expected=reference(c['input'])
        before=len(check.failures);check.same(observed,expected,c['id'])
        if c['kind']=='original':
            original_refs[c['id']]=expected
            selection=next(v['selection'] for v in protocol['cases'] if v['id']==c['id'])
            descriptor=next(d for d in index['panels'] if d['id']==selection['panel_id'])
            panel=json.loads((ROOT/'docs/explorer/data'/descriptor['path']).read_text())
            saved={i['item_id']:i for i in panel['items']}
            for item in expected['reconstructed_items']:
                for side in ['a','b']:
                    new=item[side];old=next(v for v in saved[item['item_id']]['variants'] if v['id']==selection[side])
                    archivecheck.same(new['label'],old['label'],c['id']+'.saved.label')
                    archivecheck.same(new['typed_value'],old['value'],c['id']+'.saved.typed_value')
                    archivecheck.same([new['probabilities'][k] for k in c['input']['canonical_keys']],old['probabilities'],c['id']+'.saved.probabilities')
                    archivecheck.same(new['calls'],old['calls'],c['id']+'.saved.calls')
                    archivecheck.same([new['recipe_source']['source_id'],new['recipe_source']['line_1based']],old['source'],c['id']+'.saved.source')
                    checked_saved+=1
        elif c['kind']=='synthetic_representation':
            baseline={**original_refs[c['base']],'case_id':c['id']}
            check.same(observed,baseline,c['id']+'.invariance')
        records.append({'id':c['id'],'kind':c['kind'],'status':'pass' if len(check.failures)==before else 'fail','expected_status':expected['status']})
    report={'status':'pass' if not check.failures and not archivecheck.failures else 'fail','checked_at_utc':datetime.now(timezone.utc).isoformat(),
            'execution':a.execution,'outputs_sha256':hashlib.sha256(a.outputs.read_bytes()).hexdigest(),
            'input_sha256':hashlib.sha256((HERE/'raw_inputs.json').read_bytes()).hexdigest(),
            'protocol_sha256':hashlib.sha256((HERE/'protocol.json').read_bytes()).hexdigest(),
            'processor_sha256':hashlib.sha256((HERE/'process.js').read_bytes()).hexdigest(),
            'checker_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'cases':records,'original_cases':6,'synthetic_representation_controls':6,'synthetic_invalid_controls':8,
            'original_physical_records':6000,'archived_conditions_checked':checked_saved,
            'processor_vs_python':{'numeric_comparisons':check.numeric,'max_absolute_difference':check.max_delta,'max_by_field':dict(check.fields),'failures':check.failures},
            'python_recomputation_vs_unchanged_published_saved_data':{'numeric_comparisons':archivecheck.numeric,'max_absolute_difference':archivecheck.max_delta,'max_by_field':dict(archivecheck.fields),'failures':archivecheck.failures},
            'tolerance':{'relative':TOL,'absolute':TOL},'python':platform.python_version(),'system':platform.system(),
            'human_participants':0,'new_model_calls':0,'scope':'Finite raw-logit reconstruction/custom-code feasibility; not native built-in functionality, human benefit, new model outcomes or independent human replication.'}
    a.report.parent.mkdir(parents=True,exist_ok=True);a.report.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ['cases','processor_vs_python','python_recomputation_vs_unchanged_published_saved_data']},indent=2))
    print('Processor discrepancies:',len(check.failures),'saved-data discrepancies:',len(archivecheck.failures))
    if report['status']!='pass':raise SystemExit(1)


if __name__=='__main__':main()
