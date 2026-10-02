#!/usr/bin/env python3
"""Independent bounded check of extracted source identity and point metrics."""
import hashlib
import json
import math
from pathlib import Path

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[3]
RUN=HERE/'run02'

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def reference(scores, errors):
    # Deliberately use direct per-positive thresholds and all positive/negative
    # pairs, independently of the grouped cumulative implementation in analyze.
    pos=[i for i,e in enumerate(errors) if e]
    neg=[i for i,e in enumerate(errors) if not e]
    ap=None if not pos else sum(sum(e for s,e in zip(scores,errors) if s >= scores[i]) / sum(s >= scores[i] for s in scores) for i in pos)/len(pos)
    auc=None if not pos or not neg else sum((scores[i]>scores[j])+.5*(scores[i]==scores[j]) for i in pos for j in neg)/(len(pos)*len(neg))
    return ap,auc

def main():
    result=json.loads((RUN/'RESULTS.json').read_text())
    records=[json.loads(line) for line in (RUN/'records.jsonl').read_text().splitlines()]
    assert len(records)==400
    assert sha(HERE/'SPECIFICATION.json')==result['specification_sha256']
    assert sha(HERE/'analyze.py')==result['script_sha256']
    sources={}
    for s in result['sources']:
        p=REPO/s['path'];assert sha(p)==s['sha256']
        sources[s['path']]=[json.loads(line) for line in p.read_text().splitlines()]
    for r in records:
        raw=[]
        for index,s in enumerate(r['sources']):
            x=sources[s['path']][s['line']-1]
            assert (x['method'],x['anchor'],x['replicate'])==('fixed_cyclic','canonical',index)
            assert x['request_index']==s['request_index'] and x['request_sha256']==s['request_sha256']
            assert x['item_id']==r['item_id'] and x['gold_label']==r['gold_label']
            raw.append(x)
        p=[raw[0]['probabilities'][k] for k in r['canonical_keys']]
        q=[raw[1]['probabilities'][k] for k in r['canonical_keys']]
        assert p==r['p_first'] and q==r['p_second']
        avg=[(x+y)/2 for x,y in zip(p,q)]
        assert avg==r['p_pair_mean']
        for name,v in [('first',p),('pair_mean',avg)]:
            label=r['canonical_keys'][v.index(max(v))]
            assert label==r[name+'_label']
            assert r[name+'_label_error']==int(label!=r['gold_label'])
        assert r['first_cost']['input_tokens']==raw[0]['input_tokens']
        assert r['pair_cost']['input_tokens']==sum(x['input_tokens'] for x in raw)
        assert r['pair_cost']['serial_latency_ms']==sum(x['latency_ms'] for x in raw)
        # Independent recomputation of all component scores.
        h=lambda v:sum(-x*math.log(x)/math.log(5) for x in v if x)
        s=r['scores'];top=sorted(p)
        expected={'first_maxprob_uncertainty':1-max(p),'first_margin_uncertainty':1-top[-1]+top[-2],
            'first_entropy':h(p),'order_flip':int(raw[0]['label']!=raw[1]['label']),
            'order_tv':sum(abs(x-y) for x,y in zip(p,q))/2,'pair_mean_entropy':h(avg)}
        assert all(abs(s[k]-v)<1e-14 for k,v in expected.items())
    point_checks=0
    for model,a in result['models'].items():
        rs=[r for r in records if r['model']==model]
        for base,combo in [('first_entropy','first_entropy_tv_rank'),('pair_mean_entropy','pair_entropy_tv_rank')]:
            for r in rs:
                rank=lambda field:sum((x['scores'][field]<r['scores'][field])+.5*(x['scores'][field]==r['scores'][field]) for x in rs)/len(rs)
                assert r['scores'][combo]==(rank(base)+rank('order_tv'))/2
        for target in ('first_label_error','pair_mean_label_error'):
            errors=[r[target] for r in rs]
            assert sum(errors)==a[target]['errors']
            for name,m in a[target]['scores'].items():
                vals=[r['scores'][name] for r in rs]
                ap,auc=reference(vals,errors)
                assert abs(ap-m['ap'])<1e-14 and abs(auc-m['auroc'])<1e-14
                threshold=sorted(vals,reverse=True)[19]
                chosen=[i for i,v in enumerate(vals) if v>=threshold]
                assert len(chosen)==m['top20_with_ties']['actual_review_count']
                assert sum(errors[i] for i in chosen)==m['top20_with_ties']['errors_found']
                point_checks+=2
    receipt={'status':'PASS','scope':'independent deterministic source/feature/point-metric checks, no new inference or full bootstrap rerun',
        'model_item_rows':len(records),'raw_source_members_checked':2*len(records),'point_metrics_checked':point_checks,
        'source_line_request_identity':'exact','probabilities_labels_costs':'exact','component_score_tolerance':1e-14,
        'all_cohort_rank_combinations':'exact','top20_with_ties':'exact','metric_reference':'direct per-positive thresholds for AP; all positive-negative pairs for AUROC',
        'results_sha256':sha(RUN/'RESULTS.json'),'records_sha256':sha(RUN/'records.jsonl'),'validator_sha256':sha(Path(__file__))}
    out=HERE/'VALIDATION.json'
    if out.exists():raise SystemExit('Refusing to overwrite VALIDATION.json')
    out.write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))

if __name__=='__main__':main()
