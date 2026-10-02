"""Integrity-check and recompute all four strata using saved logits. No models/network."""
import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys
sys.dont_write_bytecode=True

def sha(raw):return hashlib.sha256(raw).hexdigest()
def canonical(x):return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def load(p):return json.loads(p.read_text())
def require(x,msg):
    if not x:raise ValueError(msg)
def compare(a,b,path='strata'):
    if isinstance(b,dict):
        require(isinstance(a,dict) and set(a)==set(b),'keys '+path)
        return max((compare(a[k],v,path+'/'+k) for k,v in b.items()),default=0.)
    if isinstance(b,list):
        require(isinstance(a,list) and len(a)==len(b),'length '+path)
        return max((compare(x,y,path+'/'+str(i)) for i,(x,y) in enumerate(zip(a,b))),default=0.)
    if type(b) is float:
        require(type(a) in (float,int) and math.isfinite(a) and math.isfinite(b),'finite '+path)
        delta=abs(a-b);require(delta<=1e-12,'value '+path);return delta
    require(type(a) is type(b) and a==b,'identity '+path);return 0.

def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path);p.add_argument('--verify-only',action='store_true');args=p.parse_args()
    root=Path(__file__).resolve().parent;m=load(root/'MANIFEST.json')
    for name,digest in m['files_sha256'].items():
        path=root/name
        require(not Path(name).is_absolute() and path.resolve().is_relative_to(root) and not path.is_symlink(),'unsafe path')
        require(sha(path.read_bytes())==digest,'altered bundle '+name)
    freeze=load(root/'provenance/FREEZE.public.json');protocol=load(root/'code/PROTOCOL.json');schedules=load(root/'data/SCHEDULES.json')
    require(freeze['stage']=='before_any_generality_model_forward','freeze stage')
    require(sha(canonical(schedules))==freeze['schedule_sha256'],'schedule integrity')
    for path,h in m['frozen_code_bindings'].items():
        require(freeze['source_sha256'][path]==h,'source not frozen')
        require(sha((root/path).read_bytes())==h,'copied source differs from original frozen bytes')
    selection={r['id']:r for r in load(root/'code/SELECTION.json')['items']}
    pools={}
    for model in protocol['models']:
        folder=root/'observations'/model;receipt=load(folder/'COMPLETION.json');attempt=load(folder/'ATTEMPT.json')
        require(receipt['status']=='completed' and receipt['recorded_requests']==2400 and receipt['failed_requests']==0 and receipt['model_closed'] and receipt['source_unchanged'],'incomplete model')
        require(receipt['actual_calls_including_excluded']==2428 and receipt['excluded_calls']==28,'actual accounting')
        require(attempt['freeze_sha256']==m['original_v2_freeze_sha256'],'attempt freeze')
        for name,h in receipt['file_sha256'].items():require(sha((folder/name).read_bytes())==h,'receipt hash')
        gate=load(folder/'REPEATABILITY_GATE.json');require(gate['passed'] and gate['english']['passed'],'synthetic gate')
        for dataset in protocol['datasets']:
            rows=[json.loads(l) for l in (folder/(dataset+'.jsonl')).read_text().splitlines()]
            require(len(rows)==1200,'physical count')
            for row in rows:
                ref=selection[row['item_id']]
                require(ref['dataset']==dataset and ref['question_sha256']==row['source_question_sha256'] and ref['group']==row['group'],'selection mismatch')
                require(row['logits_to_keep']==0 and row['candidate_boundary_verified'],'readout mode')
            pools[model+'/'+dataset]=rows
    spec=importlib.util.spec_from_file_location('generality_frozen_analysis',root/'code/analysis.py');a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)
    outputs={};records_by_stratum={};a.metric.check_metrics()
    for model in protocol['models']:
        for dataset in protocol['datasets']:
            rows=pools[model+'/'+dataset];a.verify_schedule(rows,schedules[dataset]);records=a.records_from_rows(rows,model,240,dataset)
            records_by_stratum[model+'/'+dataset]=records
    if args.verify_only:print(json.dumps({'status':'verified','calls':4800,'questions':480,'strata':4}));return
    require(args.out is not None and not args.out.exists(),'new --out required')
    for key,records in records_by_stratum.items():
        outputs[key]={'A':a.analyze_a(records,protocol['A']),'B':a.analyze_b(records,protocol['B'])}
    expected=load(root/'RESULTS.json');require(expected['freeze_sha256']==m['original_v2_freeze_sha256'],'result freeze')
    maximum=compare(outputs,expected['strata'])
    with args.out.open('x') as f:json.dump({'status':'exact_replay' if maximum==0 else 'tolerance_replay','max_absolute_difference':maximum,'strata':outputs},f,ensure_ascii=False,allow_nan=False)
    print(json.dumps({'status':'passed','strata':4,'measured_calls':4800,'max_absolute_difference':maximum}))

if __name__=='__main__':main()
