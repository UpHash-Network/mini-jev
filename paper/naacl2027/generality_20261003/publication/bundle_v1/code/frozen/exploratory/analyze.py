#!/usr/bin/env python3
"""Exploratory paired error-detection replay; stdlib only, no model imports."""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import random
from datetime import datetime, timezone

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def dump(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')

def entropy(p):
    return -math.fsum(x * math.log(x) for x in p if x > 0) / math.log(len(p))

def ranks(values):
    """Outcome-free cohort midranks, preserving exact ties."""
    n = len(values)
    order = sorted(range(n), key=values.__getitem__)
    result = [None] * n
    i = 0
    while i < n:
        j = i + 1
        while j < n and values[order[j]] == values[order[i]]:
            j += 1
        for k in order[i:j]:
            result[k] = (i + (j - i) / 2) / n
        i = j
    return result

def metrics(scores, errors):
    """Tie-aware threshold AP and rank AUROC; 1=error, larger score=more suspect."""
    n, positives = len(errors), sum(errors)
    negatives = n - positives
    order = sorted(range(n), key=scores.__getitem__, reverse=True)
    ap = auc = 0.0
    seen_pos = seen_neg = 0
    i = 0
    while i < n:
        j = i + 1
        while j < n and scores[order[j]] == scores[order[i]]:
            j += 1
        p = sum(errors[k] for k in order[i:j])
        q = j - i - p
        seen_pos += p
        if positives:
            ap += p / positives * seen_pos / j
        auc += p * (negatives - seen_neg - q + q / 2)
        seen_neg += q
        i = j
    return {'ap': ap if positives else None,
            'auroc': auc / (positives * negatives) if positives and negatives else None}

def interval(values):
    v = sorted(x for x in values if x is not None)
    def q(f):
        pos = (len(v)-1)*f
        low, high = math.floor(pos), math.ceil(pos)
        return v[low] + (v[high]-v[low])*(pos-low)
    return {'low': q(.025) if v else None, 'high': q(.975) if v else None,
            'valid_resamples': len(v), 'invalid_resamples': len(values)-len(v)}

def check_metrics():
    assert metrics([1, 1, 1, 1], [1, 0, 0, 0]) == {'ap': .25, 'auroc': .5}
    assert metrics([3, 2, 1, 0], [1, 1, 0, 0]) == {'ap': 1.0, 'auroc': 1.0}
    assert abs(metrics([3, 2, 1, 0], [0, 0, 1, 1])['ap'] - (1/3+2/4)/2) < 1e-15
    assert metrics([3, 2, 1, 0], [0, 0, 1, 1])['auroc'] == 0
    assert metrics([1, 0], [0, 0]) == {'ap': None, 'auroc': None}
    assert metrics([1, 0], [1, 1]) == {'ap': 1.0, 'auroc': None}
    assert ranks([2, 1, 1, 3]) == [.625, .25, .25, .875]
    # A boundary tie is one threshold, rather than arbitrary lucky ordering.
    assert abs(metrics([2, 1, 1], [0, 1, 0])['ap'] - 1/3) < 1e-15
    assert metrics([2, 1, 1], [0, 1, 0]) == metrics([2, 1, 1], [0, 0, 1])

def extract(model, spec):
    path = REPO / spec['source'].format(model=model)
    selected = {}
    for line, text in enumerate(path.open(encoding='utf-8'), 1):
        row = json.loads(text)
        if (row['method'], row['anchor'], row['replicate']) not in [('fixed_cyclic', 'canonical', 0), ('fixed_cyclic', 'canonical', 1)]:
            continue
        assert row['model_key'] == model and row['dataset'] == 'JCommonsenseQA'
        assert row['error'] is None
        if row['backend'] == 'llama.cpp':
            assert row['native_decode_count'] == 1 and row['state_cleared']
        else:
            assert row['forward_calls'] == 1
        item = selected.setdefault(row['item_id'], {})
        assert row['replicate'] not in item
        item[row['replicate']] = (row, line)
    assert len(selected) == spec['expected_items_per_model']
    records = []
    for item_id, pair in sorted(selected.items()):
        assert set(pair) == {0, 1}
        (a, la), (b, lb) = pair[0], pair[1]
        keys = a['canonical_keys']
        assert len(keys) == 5 and len(set(keys)) == 5
        for k in ('canonical_keys', 'gold_label', 'source_question_sha256', 'group'):
            assert a[k] == b[k]
        ps = []
        for r in (a,b):
            assert set(r['probabilities']) == set(keys)
            p = [r['probabilities'][k] for k in keys]
            assert all(math.isfinite(x) and 0 <= x <= 1 for x in p)
            assert abs(math.fsum(p)-1) < 1e-10
            assert r['label'] == keys[max(range(5), key=p.__getitem__)]
            ps.append(p)
        p, q = ps
        avg = [(x+y)/2 for x,y in zip(p,q)]
        first_label = keys[max(range(5), key=p.__getitem__)]
        pair_label = keys[max(range(5), key=avg.__getitem__)]
        top = sorted(p, reverse=True)
        gold = a['gold_label']
        assert gold in keys
        records.append({
            'model': model, 'item_id': item_id, 'group': a['group'],
            'source_question_sha256': a['source_question_sha256'],
            'canonical_keys': keys, 'p_first': p, 'p_second': q, 'p_pair_mean': avg,
            'gold_label': gold, 'first_label': first_label, 'pair_mean_label': pair_label,
            'first_label_error': int(first_label != gold), 'pair_mean_label_error': int(pair_label != gold),
            'scores': {
                'first_maxprob_uncertainty': 1-max(p),
                'first_margin_uncertainty': 1-(top[0]-top[1]),
                'first_entropy': entropy(p), 'order_flip': int(a['label'] != b['label']),
                'order_tv': .5*math.fsum(abs(x-y) for x,y in zip(p,q)),
                'pair_mean_entropy': entropy(avg)},
            'first_cost': {'calls': 1, 'input_tokens': a['input_tokens'], 'serial_latency_ms': a['latency_ms']},
            'pair_cost': {'calls': 2, 'input_tokens': a['input_tokens']+b['input_tokens'], 'serial_latency_ms': a['latency_ms']+b['latency_ms']},
            'sources': [dict(path=str(path.relative_to(REPO)), line=line, replicate=r['replicate'],
                request_index=r['request_index'], request_sha256=r['request_sha256'],
                backend=r['backend'], **{k:r[k] for k in ('rendered_sha256','tokenized_input_sha256') if k in r})
                for r,line in ((a,la),(b,lb))]})
    assert len({r['source_question_sha256'] for r in records}) == len(records)
    assert len({r['group'] for r in records}) == len(records)
    tv_ranks = ranks([r['scores']['order_tv'] for r in records])
    for base, name in [('first_entropy','first_entropy_tv_rank'), ('pair_mean_entropy','pair_entropy_tv_rank')]:
        base_ranks = ranks([r['scores'][base] for r in records])
        for r, x, y in zip(records, base_ranks, tv_ranks):
            r['scores'][name] = (x+y)/2
    return records, {'path': str(path.relative_to(REPO)), 'sha256': sha(path), 'bytes': path.stat().st_size}

def analyze(records, spec):
    result = {}
    n = len(records)
    rng = random.Random(2026100301)
    # Paired question resamples shared across targets and scores.
    samples = [[rng.randrange(n) for _ in range(n)] for _ in range(2000)]
    names = list(spec['scores'])
    values = {name: [r['scores'][name] for r in records] for name in names}
    for target in ('pair_mean_label_error', 'first_label_error'):
        errors = [r[target] for r in records]
        boots = {name: {'ap': [], 'auroc': []} for name in names}
        for indices in samples:
            e = [errors[i] for i in indices]
            for name in names:
                m = metrics([values[name][i] for i in indices], e)
                for metric in m:
                    boots[name][metric].append(m[metric])
        scored = {}
        for name in names:
            vals = values[name]
            threshold = sorted(vals, reverse=True)[19]
            flagged = [i for i in range(n) if vals[i] >= threshold]
            scored[name] = {**metrics(vals, errors),
                'ci95': {m: interval(v) for m,v in boots[name].items()},
                'top20_with_ties': {'nominal_review_count': 20, 'actual_review_count': len(flagged),
                    'errors_found': sum(errors[i] for i in flagged), 'threshold': threshold},
                'feature_calls': 1 if name in ('first_maxprob_uncertainty','first_margin_uncertainty','first_entropy') else 2,
                'prediction_calls': 2 if target == 'pair_mean_label_error' else 1}
        differences = []
        for a,b in spec['paired_differences']:
            diff = {'score': a, 'reference': b}
            for m in ('ap','auroc'):
                observed = None if scored[a][m] is None or scored[b][m] is None else scored[a][m]-scored[b][m]
                draws = [None if x is None or y is None else x-y for x,y in zip(boots[a][m], boots[b][m])]
                diff[m] = {'difference': observed, 'ci95': interval(draws)}
            differences.append(diff)
        result[target] = {'n': n, 'errors': sum(errors), 'error_prevalence': sum(errors)/n,
            'scores': scored, 'paired_differences': differences}
    result['cost'] = {kind: {metric: math.fsum(r[kind][metric] for r in records)
        for metric in ('calls','input_tokens','serial_latency_ms')} for kind in ('first_cost','pair_cost')}
    return result

def render(result):
    lines = ['# Exploratory value of order diagnostics', '',
        '**Saved-record replay; no new inference or untouched holdout.** Earlier study outcomes were known. This specification was fixed before this extraction, not independently preregistered.', '',
        'All 200 existing JCQA questions are retained for both checkpoints. Replicates 0 and 1 of the canonical fixed cyclic pool provide the first answer and paid probe. Primary target: error of the two-call probability-mean answer; secondary target: first-call error. No later pool member enters any score.', '',
        'Larger scores indicate suspected error. AP includes complete score ties at each threshold; chance/constant AP equals error prevalence. AUROC is chance-centered at 0.5. Intervals are 2,000 paired whole-question percentile bootstraps, conditional on the outcome-free cohort ranks. They are descriptive, unadjusted, and do not establish a winner.', '']
    for model, analysis in result['models'].items():
        lines += ['## '+model, '']
        for target in ('pair_mean_label_error','first_label_error'):
            t = analysis[target]
            lines += [f"### {target}: {t['errors']}/{t['n']} errors ({t['error_prevalence']:.1%})", '',
                '| Score | Feature / prediction calls | AP [95% interval] | AUROC [95% interval] | Found errors / reviewed (nominal 20) |',
                '|---|---:|---:|---:|---:|']
            for name,m in t['scores'].items():
                def fmt(metric):
                    ci=m['ci95'][metric]
                    return f"{m[metric]:.4f} [{ci['low']:.4f}, {ci['high']:.4f}]" if m[metric] is not None else 'undefined'
                top=m['top20_with_ties']
                lines += [f"| {name} | {m['feature_calls']} / {m['prediction_calls']} | {fmt('ap')} | {fmt('auroc')} | {top['errors_found']} / {top['actual_review_count']} |"]
            lines += ['', '| Paired score − reference | AP difference [95% interval] | AUROC difference [95% interval] |', '|---|---:|---:|']
            for d in t['paired_differences']:
                vals=[]
                for metric in ('ap','auroc'):
                    m=d[metric];ci=m['ci95']
                    vals.append(f"{m['difference']:+.4f} [{ci['low']:+.4f}, {ci['high']:+.4f}]")
                lines += [f"| {d['score']} − {d['reference']} | {vals[0]} | {vals[1]} |"]
            lines += ['']
        lines += ['Saved serial costs (not online measurements): `'+json.dumps(analysis['cost'],sort_keys=True)+'`.', '']
    lines += ['## Interpretation boundaries', '',
        '- Primary comparison fixed in advance of this extraction: 1.5B, pair-mean error, pair-entropy+TV versus pair entropy. Both require two paid calls. All secondary results remain visible.',
        '- Feature calls and prediction calls overlap: total required calls are their maximum, not their sum. A one-call feature evaluated against a two-call mean prediction is still a two-call system.',
        '- Equal midrank weights use no gold, but cohort ranks require the available unlabeled cohort. They are not per-item risk probabilities or a deployment cutoff. Bootstrap intervals condition on these ranks.',
        '- The two checkpoints share 200 questions; model-item rows are not 400 independent questions. The native checkpoint has few errors, so AP and subgroup comparisons are fragile. No score or threshold was selected from these results.',
        '- Exact question hashes are unique within the panel; semantic dependence and public-data pretraining contamination remain possible. Existing results were already inspected. A new confirmation panel must be source-audited and frozen after policy selection.',
        '- These analyses extend earlier confidence/entropy risk–coverage descriptions by testing incremental order information; they do not repeat the completed static equal-call quality comparison or establish user benefit.',
        '', '## Reproduce', '',
        'From the repository root: `python3 paper/naacl2027/diagnostic_value_20261003/exploratory/analyze.py --out /tmp/logittrail-diagnostic-replay`.',
        'The output directory must be absent. No dependencies or model weights are loaded. Source hashes, specification hash, script hash, selected raw line/request identities, all scores, and bootstrap counts are saved. Compare numerical results after excluding timestamp/output-path metadata.', '']
    return '\n'.join(lines)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise SystemExit('Refusing to overwrite an existing output directory')
    check_metrics()
    spec_path=HERE/'SPECIFICATION.json'
    spec=json.loads(spec_path.read_text(encoding='utf-8'))
    args.out.mkdir(parents=True)
    result={'schema_version':1,'scope':spec['scope'],'started_utc':datetime.now(timezone.utc).isoformat(),
        'specification_sha256':sha(spec_path),'script_sha256':sha(Path(__file__)),
        'bootstrap_replicates':2000,'bootstrap_seed':2026100301,
        'metric_contract_checks':'passed; exact ties, chance, perfect, reversed, undefined and tied-order invariance',
        'models':{},'sources':[]}
    all_records=[]
    for model in spec['models']:
        records,source=extract(model,spec)
        result['sources'].append(source)
        result['models'][model]=analyze(records,spec)
        all_records += records
    a,b=spec['models']
    assert {r['item_id'] for r in all_records if r['model']==a} == {r['item_id'] for r in all_records if r['model']==b}
    (args.out/'records.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False,sort_keys=True,allow_nan=False)+'\n' for r in all_records),encoding='utf-8')
    result['completed_utc']=datetime.now(timezone.utc).isoformat()
    dump(args.out/'RESULTS.json',result)
    (args.out/'REPORT.md').write_text(render(result),encoding='utf-8')
    with (args.out/'metrics.csv').open('w',encoding='utf-8',newline='') as f:
        w=csv.writer(f);w.writerow(['model','target','n','errors','score','feature_calls','prediction_calls','ap','ap_lo','ap_hi','auroc','auroc_lo','auroc_hi','top20_actual_reviewed','top20_errors_found'])
        for model,analysis in result['models'].items():
            for target in ('pair_mean_label_error','first_label_error'):
                t=analysis[target]
                for name,m in t['scores'].items():
                    w.writerow([model,target,t['n'],t['errors'],name,m['feature_calls'],m['prediction_calls'],m['ap'],m['ci95']['ap']['low'],m['ci95']['ap']['high'],m['auroc'],m['ci95']['auroc']['low'],m['ci95']['auroc']['high'],m['top20_with_ties']['actual_review_count'],m['top20_with_ties']['errors_found']])
    manifest={'files':[{'path':str(p.relative_to(args.out)),'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(args.out.iterdir()) if p.is_file()]}
    dump(args.out/'MANIFEST.json',manifest)
    for model,analysis in result['models'].items():
        t=analysis['pair_mean_label_error'];d=t['paired_differences'][-1]
        print(json.dumps({'model':model,'pair_errors':t['errors'],'first_errors':analysis['first_label_error']['errors'],'primary_contrast':d},ensure_ascii=False))

if __name__=='__main__':
    main()
