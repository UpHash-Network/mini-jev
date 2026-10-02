#!/usr/bin/env python3
"""Frozen-pool diagnostic and same-budget batch-routing replay, standard library only."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import random

HERE = Path(__file__).resolve().parent
HELPER = HERE.parent / 'exploratory/analyze.py'
_spec = importlib.util.spec_from_file_location('diagnostic_metrics', HELPER)
metric = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(metric)
POLICIES = ('pair_entropy_tv_rank', 'pair_mean_entropy', 'pair_random', 'first_entropy')

def digest(value):
    return hashlib.sha256(value).hexdigest()

def load(path):
    return json.loads(Path(path).read_text())

def dump(path, value):
    with Path(path).open('x') as f:
        f.write(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+'\n')

def canonical(value):
    return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()

def verify_schedule(rows, schedule):
    if len(rows)!=len(schedule):
        raise ValueError('Physical pool length differs from frozen schedule')
    for index,(row,expected) in enumerate(zip(rows,schedule)):
        if expected['request_index']!=index or any(row.get(k)!=v for k,v in expected.items()):
            raise ValueError('Physical row differs from frozen schedule at index '+str(index))

def label(p, keys):
    return keys[max(range(len(keys)), key=p.__getitem__)]

def mean(ps):
    return [math.fsum(p[k] for p in ps)/len(ps) for k in range(len(ps[0]))]

def records_from_rows(rows, model, n):
    items, request_indices = {}, set()
    for row in rows:
        if row.get('error') is not None:
            raise ValueError('Failed measurement; no item replacement')
        if (row['model_key'], row['dataset'], row['type'], row['method'], row['anchor']) != (
                model, 'JCommonsenseQA', 'choice', 'fixed_cyclic', 'canonical'):
            raise ValueError('Unexpected identity or physical method')
        if row['request_index'] in request_indices:
            raise ValueError('Duplicate physical request index')
        request_indices.add(row['request_index'])
        if row['backend'] == 'llama.cpp':
            if row['native_decode_count'] != 1 or not row['state_cleared']:
                raise ValueError('Native physical invocation accounting differs')
        elif row['backend'] == 'transformers':
            if row['forward_calls'] != 1:
                raise ValueError('Transformer forward accounting differs')
        else:
            raise ValueError('Unknown inference backend')
        if row['output_tokens'] != 0:
            raise ValueError('Unexpected autoregressive generation')
        item = items.setdefault(row['item_id'], {})
        if row['replicate'] in item:
            raise ValueError('Duplicate logical member')
        item[row['replicate']] = row
    if len(items) != n or len(rows) != 5*n or request_indices != set(range(5*n)):
        raise ValueError('Incomplete or unexpected physical pool')
    records = []
    for item_id, member_map in sorted(items.items()):
        if set(member_map) != set(range(5)):
            raise ValueError('Missing fixed member')
        members = [member_map[i] for i in range(5)]
        a = members[0]
        keys = a['canonical_keys']
        if keys != ['option_'+str(i) for i in range(5)]:
            raise ValueError('Unexpected semantic key order')
        ps = []
        for r in members:
            if any(r[k] != a[k] for k in ('canonical_keys', 'gold_label', 'group', 'source_question_sha256')):
                raise ValueError('Inconsistent item identity')
            if set(r['probabilities']) != set(keys) or r['gold_label'] not in keys:
                raise ValueError('Invalid probabilities or reference')
            p = [r['probabilities'][k] for k in keys]
            logits=r['logits'];candidate_keys=r['candidate_keys']
            if (type(r['temperature']) not in (float,int) or r['temperature']!=1 or candidate_keys!=keys
                    or len(logits)!=5 or any(type(x) not in (float,int) or not math.isfinite(x) for x in logits)):
                raise ValueError('Expected five fixed-binding finite logits at temperature1')
            e=[math.exp(x-max(logits)) for x in logits];z=math.fsum(e)
            reconstructed=[x/z for x in e]
            if any(abs(x-y)>1e-12 for x,y in zip(p,reconstructed)):
                raise ValueError('Saved probabilities disagree with T1 raw logits')
            if (any(type(x) not in (int,float) or not math.isfinite(x) or x < 0 or x > 1 for x in p)
                    or abs(math.fsum(p)-1) > 1e-10 or label(p,keys) != r['label']):
                raise ValueError('Probability normalization or semantic label differs')
            if (type(r['input_tokens']) is not int or r['input_tokens'] < 1 or
                    not math.isfinite(r['latency_ms']) or r['latency_ms'] < 0):
                raise ValueError('Invalid measured cost')
            ps.append(p)
        p, q = ps[:2]
        pair = mean(ps[:2]); full = mean(ps)
        top = sorted(p, reverse=True)
        records.append({'model': model, 'item_id': item_id, 'group':a['group'],
            'source_question_sha256':a['source_question_sha256'], 'canonical_keys':keys,
            'gold_label':a['gold_label'], 'probability_vectors':ps,
            'first_label':label(p,keys), 'pair_mean_label':label(pair,keys), 'full_mean_label':label(full,keys),
            'first_label_error':int(label(p,keys)!=a['gold_label']),
            'pair_mean_label_error':int(label(pair,keys)!=a['gold_label']),
            'scores':{'first_maxprob_uncertainty':1-max(p),
                'first_margin_uncertainty':1-(top[0]-top[1]), 'first_entropy':metric.entropy(p),
                'order_flip':int(label(p,keys)!=label(q,keys)),
                'order_tv':.5*math.fsum(abs(x-y) for x,y in zip(p,q)),
                'pair_mean_entropy':metric.entropy(pair)},
            'members':[{'replicate':r['replicate'], 'request_index':r['request_index'],
                'request_sha256':r['request_sha256'],'input_tokens':r['input_tokens'],
                'latency_ms':r['latency_ms']} for r in members]})
    if len({r['group'] for r in records}) != n or len({r['source_question_sha256'] for r in records}) != n:
        raise ValueError('Repeated question group/hash')
    tv = metric.ranks([r['scores']['order_tv'] for r in records])
    for base, name in [('first_entropy','first_entropy_tv_rank'),('pair_mean_entropy','pair_entropy_tv_rank')]:
        rank = metric.ranks([r['scores'][base] for r in records])
        for r,x,y in zip(records,rank,tv):
            r['scores'][name]=(x+y)/2
    return records

def allocation(records, policy, budget, protocol):
    """Gate reads only prespecified scores and IDs, never labels or later outputs."""
    n=len(records); base=1 if policy=='first_entropy' else 2
    count=(budget*n-base*n)/(5-base)
    if count != int(count) or not 0 <= count <= n:
        raise ValueError('Budget cannot be realized exactly')
    def tie(r):
        return digest((protocol['tie_salt']+r['item_id']).encode()),r['item_id']
    if policy=='pair_random':
        ordered=sorted(records,key=lambda r:(digest((protocol['random_salt']+r['item_id']).encode()),r['item_id']))
    elif policy in POLICIES:
        ordered=sorted(records,key=lambda r:(-r['scores'][policy],*tie(r)))
    else:
        raise ValueError('Unknown frozen policy')
    return {r['item_id'] for r in ordered[:int(count)]},base

def replay(records, policy, budget, protocol):
    selected,base=allocation(records,policy,budget,protocol)
    outcomes=[];physical=set();tokens=0;latency=[]
    for r in records:
        paid=5 if r['item_id'] in selected else base
        prediction=r['full_mean_label'] if paid==5 else r['pair_mean_label'] if paid==2 else r['first_label']
        for m in r['members'][:paid]:
            identity=(r['item_id'],m['request_index'])
            if identity in physical:
                raise ValueError('Repeated physical payment')
            physical.add(identity);tokens+=m['input_tokens'];latency.append(m['latency_ms'])
        outcomes.append({'item_id':r['item_id'],'selected':paid==5,'calls':paid,
            'prediction':prediction,'correct':int(prediction==r['gold_label']),
            'paid_request_indices':[m['request_index'] for m in r['members'][:paid]]})
    if len(physical)!=budget*len(records):
        raise ValueError('Same-budget accounting failed')
    return {'policy':policy,'budget_calls_per_item':budget,'selected_count':len(selected),
        'accuracy':sum(r['correct'] for r in outcomes)/len(records),'correct':sum(r['correct'] for r in outcomes),
        'calls':len(physical),'input_tokens':tokens,'recorded_serial_latency_ms':math.fsum(latency),'outcomes':outcomes}

def analyze_a(records, protocol):
    n=len(records);rng=random.Random(protocol['seed'])
    samples=[[rng.randrange(n) for _ in range(n)] for _ in range(2000)]
    result={}
    for target in ('pair_mean_label_error','first_label_error'):
        errors=[r[target] for r in records];scored={};boots={}
        for name in protocol['scores']:
            scores=[r['scores'][name] for r in records]
            draws=[metric.metrics([scores[i] for i in indices],[errors[i] for i in indices]) for indices in samples]
            boots[name]=draws
            threshold=sorted(scores,reverse=True)[19]
            flagged=[i for i,s in enumerate(scores) if s>=threshold]
            scored[name]={**metric.metrics(scores,errors),'ci95':{m:metric.interval([d[m] for d in draws]) for m in ('ap','auroc')},
                'feature_calls':1 if name in ('first_entropy','first_margin_uncertainty','first_maxprob_uncertainty') else 2,
                'prediction_calls':2 if target=='pair_mean_label_error' else 1,
                'top20_with_ties':{'reviewed':len(flagged),'errors_found':sum(errors[i] for i in flagged)}}
        a,b=protocol['primary_contrast'];diff={}
        for m in ('ap','auroc'):
            diff[m]={'difference':None if scored[a][m] is None or scored[b][m] is None else scored[a][m]-scored[b][m],
                'ci95':metric.interval([None if x[m] is None or y[m] is None else x[m]-y[m] for x,y in zip(boots[a],boots[b])])}
        result[target]={'n':n,'errors':sum(errors),'scores':scored,'primary_contrast':{'score':a,'reference':b,**diff}}
    return result

def analyze_b(records,protocol):
    n=len(records);rng=random.Random(protocol['seed'])
    samples=[[rng.randrange(n) for _ in range(n)] for _ in range(2000)]
    results=[];contrasts=[]
    for budget in protocol['budgets_calls_per_item']:
        policies={name:replay(records,name,budget,protocol) for name in POLICIES}
        for p in policies.values():
            correct=[r['correct'] for r in p['outcomes']]
            p['accuracy_ci95']=metric.interval([sum(correct[i] for i in s)/n for s in samples])
            results.append(p)
        a,b=protocol['primary_contrast'];x=policies[a]['outcomes'];y=policies[b]['outcomes']
        differences=[u['correct']-v['correct'] for u,v in zip(x,y)]
        contrasts.append({'budget_calls_per_item':budget,'score':a,'reference':b,
            'accuracy_difference':sum(differences)/n,
            'ci95':metric.interval([sum(differences[i] for i in s)/n for s in samples]),
            'reference_wrong_score_correct':sum(d==1 for d in differences),
            'reference_correct_score_wrong':sum(d==-1 for d in differences)})
    return {'curves':results,'paired_contrasts':contrasts,
        'reference_accuracy':{k:sum(r[k]==r['gold_label'] for r in records)/n for k in ('first_label','pair_mean_label','full_mean_label')}}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--study',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    if args.out.exists():
        raise ValueError('Refusing to overwrite prior analysis')
    protocol=load(HERE/'PROTOCOL.json');freeze=load(args.study/'FREEZE.json')
    schedule=load(args.study/'SCHEDULE.json')
    if digest(canonical(schedule))!=freeze['schedule_sha256']:
        raise ValueError('Frozen schedule hash differs')
    source_paths=[HERE/'PROTOCOL.json',Path(__file__),HELPER,args.study/'FREEZE.json',args.study/'SCHEDULE.json']
    outputs={};records_all=[];panel_identity=None
    metric.check_metrics()
    for model in protocol['models']:
        folder=args.study/'results'/model;receipt=load(folder/'COMPLETION.json')
        path=folder/'predictions.jsonl'
        if (receipt['status']!='completed' or not receipt['model_closed_before_receipt'] or
                not receipt['source_unchanged'] or receipt['recorded_requests']!=protocol['measured_requests_per_model']
                or receipt['file_sha256']['predictions.jsonl']!=digest(path.read_bytes())):
            raise ValueError('Incomplete or altered physical measurements')
        attempt=load(folder/'ATTEMPT.json')
        if attempt['freeze_sha256']!=digest((args.study/'FREEZE.json').read_bytes()):
            raise ValueError('Attempt belongs to another study freeze')
        source_paths.append(folder/'ATTEMPT.json')
        source_paths += [path,folder/'COMPLETION.json']
        rows=[json.loads(line) for line in path.read_text().splitlines()]
        verify_schedule(rows,schedule)
        records=records_from_rows(rows,model,protocol['n_items']);records_all+=records
        identity=[(r['item_id'],r['group'],r['source_question_sha256'],r['gold_label']) for r in records]
        if panel_identity is not None and identity!=panel_identity:
            raise ValueError('Model panels differ')
        panel_identity=identity
        outputs[model]={'A':analyze_a(records,protocol['A']),'B':analyze_b(records,protocol['B'])}
    # Freeze verification uses the actual preparation manifest, not a new retrospective hash.
    for path in (HERE/'PROTOCOL.json',Path(__file__),HELPER):
        expected=freeze['source_sha256'].get(str(path.resolve()))
        if expected!=digest(path.read_bytes()):
            raise ValueError('Analysis code/protocol was not frozen before inference: '+str(path))
    args.out.mkdir(parents=True)
    dump(args.out/'RESULTS.json',{'created_at':datetime.now(timezone.utc).isoformat(),
        'scope':'Fixed-pool batch-policy replay on project-unused questions; not online serving timing or independent replication.',
        'protocol':protocol,'source_sha256':{str(p.resolve()):digest(p.read_bytes()) for p in source_paths},'models':outputs})
    with (args.out/'records.jsonl').open('x') as f:
        for r in records_all:f.write(json.dumps(r,ensure_ascii=False,sort_keys=True,allow_nan=False)+'\n')
    print(json.dumps({'status':'complete','models':list(outputs),'model_item_records':len(records_all),'out':str(args.out)}))

if __name__=='__main__':
    main()
