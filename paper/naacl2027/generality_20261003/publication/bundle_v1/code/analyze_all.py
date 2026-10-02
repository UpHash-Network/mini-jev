"""Reanalyze every frozen stratum without pooling languages or model observations."""
import argparse
import json
from pathlib import Path
import analysis as a

HERE=Path(__file__).resolve().parent

def main():
    p=argparse.ArgumentParser();p.add_argument('--study',type=Path,required=True);p.add_argument('--out',type=Path,required=True);args=p.parse_args()
    if args.out.exists():raise ValueError('Refusing to overwrite analysis')
    protocol=a.load(HERE/'PROTOCOL.json');freeze=a.load(args.study/'FREEZE.json');schedules=a.load(args.study/'SCHEDULES.json')
    if a.digest(a.canonical(schedules))!=freeze['schedule_sha256']:raise ValueError('Schedule changed')
    for f in [HERE/'analysis.py',HERE/'analyze_all.py',HERE/'PROTOCOL.json',HERE/'frozen/exploratory/analyze.py']:
        if freeze['source_sha256'][str(f)]!=a.digest(f.read_bytes()):raise ValueError('Analysis not frozen before inference')
    outputs={};records=[];identities={};a.metric.check_metrics()
    for model in protocol['models']:
        folder=args.study/'observations'/model;receipt=a.load(folder/'COMPLETION.json');attempt=a.load(folder/'ATTEMPT.json')
        if not (receipt['status']=='completed' and receipt['model_closed'] and receipt['source_unchanged'] and receipt['failed_requests']==0 and receipt['recorded_requests']==2400 and receipt['actual_calls_including_excluded']==2428):raise ValueError('Incomplete model')
        if attempt['freeze_sha256']!=a.digest((args.study/'FREEZE.json').read_bytes()):raise ValueError('Attempt freeze mismatch')
        for dataset in protocol['datasets']:
            path=folder/(dataset+'.jsonl')
            if a.digest(path.read_bytes())!=receipt['file_sha256'][path.name]:raise ValueError('Observation changed')
            rows=[json.loads(l) for l in path.read_text().splitlines()];a.verify_schedule(rows,schedules[dataset])
            rs=a.records_from_rows(rows,model,240,dataset)
            ident=[(r['item_id'],r['group'],r['source_question_sha256'],r['gold_label']) for r in rs]
            if dataset in identities and ident!=identities[dataset]:raise ValueError('Models used different items')
            identities[dataset]=ident
            for r in rs:r['dataset']=dataset
            records.extend(rs)
            outputs[model+'/'+dataset]={'A':a.analyze_a(rs,protocol['A']),'B':a.analyze_b(rs,protocol['B'])}
            print(json.dumps({'analyzed':model+'/'+dataset}),flush=True)
    args.out.mkdir(parents=True)
    a.dump(args.out/'RESULTS.json',{'protocol':protocol,'freeze_sha256':a.digest((args.study/'FREEZE.json').read_bytes()),'strata':outputs})
    with (args.out/'records.jsonl').open('x') as f:
        for r in records:f.write(a.canonical(r).decode()+'\n')

if __name__=='__main__':main()
