#!/usr/bin/env python3
"""Independent, offline task oracle. Standard library only; Node runs real core.

No model execution, data regeneration, source-file mutation or benchmark text
export. Only the explicitly named output file is written.
"""
from __future__ import annotations
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import itertools
import json
import math
from pathlib import Path
import platform
import subprocess
import sys
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
DATA = ROOT / 'docs/explorer/data'
PROTOCOL = HERE / 'protocol.json'
FROZEN_PROTOCOL = 'da0b8af3a46597e780eba8f3b85b9d61e03ed28a3986e9851d210273a941e8b2'

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def equal(actual, expected, context, numeric=False):
    good = math.isclose(actual, expected, rel_tol=1e-12, abs_tol=1e-12) if numeric else actual == expected
    if not good:
        raise AssertionError(f'{context}: {actual!r} != {expected!r}')

def run():
    equal(digest(PROTOCOL), FROZEN_PROTOCOL, 'prewritten protocol')
    protocol = json.loads(PROTOCOL.read_text())
    archive_path = ROOT / protocol['archive']['path']
    equal(digest(archive_path), protocol['archive']['sha256'], 'frozen archive hash')
    index = json.loads((DATA/'index.json').read_text())
    source_rows = {}
    # Request indices resolve physical membership independently of UI member_ids.
    request_sources = {}
    with zipfile.ZipFile(archive_path) as archive:
        for sid, source in index['sources'].items():
            raw = archive.read(source['member'])
            equal(hashlib.sha256(raw).hexdigest(), source['sha256'], f'member {sid}')
            if source['format'] == 'jsonl':
                source_rows[sid] = [json.loads(line) for line in raw.splitlines()]
                if '/order_ensemble/' in source['member'] and source['member'].endswith('/predictions.jsonl'):
                    model = source['member'].split('/')[-2]
                    for lineno, row in enumerate(source_rows[sid], 1):
                        key = (model, row['request_index'])
                        if key in request_sources:
                            raise AssertionError('Duplicate archived physical request identity')
                        request_sources[key] = (sid, lineno)
    def raw(source):
        sid, line = source
        if not isinstance(line, int) or line < 1:
            raise AssertionError('Source line must be a positive integer')
        return source_rows[sid][line - 1]
    def members(panel, variant):
        row = raw(variant['source'])
        if variant['kind'] == 'physical':
            return {tuple(variant['source'])}
        return {request_sources[(panel['model_key'], idx)] for idx in row['physical_member_indices']}

    panels = {}
    descriptors = {}
    items = {}
    variants = {}
    counts = Counter()
    source_identities = set()
    panel_distributions = []
    expected_pair_ids = set()
    expected_frequency_ids = set()
    score_gap_max = 0.0
    for desc in index['panels']:
        path = DATA / desc['path']
        equal(digest(path), desc['sha256'], f'panel {desc["id"]}')
        panel = json.loads(path.read_text())
        pid = panel['id']
        panels[pid], descriptors[pid] = panel, desc
        counts['panels'] += 1
        for item in panel['items']:
            counts['study_item_model_combinations'] += 1
            items[pid,item['item_id']] = item
            for variant in item['variants']:
                counts['saved_conditions'] += 1
                variants[pid,item['item_id'],variant['id']] = variant
                source_identities.add(tuple(variant['source']))
                row = raw(variant['source'])
                for field, expected in [('item_id',item['item_id']),('dataset',panel['dataset'])]:
                    equal(row[field], expected, f'source identity {field}')
                equal(row.get('model_key',panel['model_key']),panel['model_key'],'source model')
                equal(variant['probabilities'],[row['probabilities'][key] for key in panel['canonical_keys']],'exact probabilities')
                equal(variant['label'],row['label'],'exact modal label')
                equal(variant['value'],row['typed_value'],'exact typed value')
                equal(variant['calls'],len(members(panel,variant)),'individual physical calls')
                if panel['type'] == 'score':
                    counts['score_conditions'] += 1
                    expected = math.fsum(row['probabilities'][key]*row['score_values'][key] for key in panel['canonical_keys'])
                    equal(variant['value'],expected,'score expectation',numeric=True)
                    equal(item['gold_score'],row['gold_score'],'continuous reference remains exact')
                    gap = abs(variant['value']-row['score_values'][variant['label']])
                    score_gap_max = max(score_gap_max,gap)
                    counts['score_gap_at_least_0_4'] += gap >= 0.4
            for a,b in itertools.combinations(item['variants'],2):
                expected_pair_ids.add((pid,item['item_id'],a['id'],b['id']))
        for condition in desc['variant_ids']:
            expected_frequency_ids.add((pid,condition))
            rows = [raw(next(v['source'] for v in item['variants'] if v['id']==condition)) for item in panel['items']]
            labels = dict(Counter(row['label'] for row in rows))
            summary = desc['variant_summaries'][condition]
            equal(summary['items'],len(rows),'complete panel count')
            equal(summary['label_counts'],labels,'complete panel label counts')
            result = {'panel':pid,'condition':condition,'items':len(rows),'label_counts':labels,'max_label_share':max(labels.values())/len(rows),'unique_labels':len(labels)}
            equal(summary['max_label_share'],result['max_label_share'],'maximum label share',numeric=True)
            equal(summary['unique_labels'],result['unique_labels'],'distinct selected labels')
            if panel['type']=='score':
                vals=[row['typed_value'] for row in rows]
                mean=math.fsum(vals)/len(vals)
                var=math.fsum((val-mean)**2 for val in vals)/len(vals)
                for field, expected in [('value_min',min(vals)),('value_max',max(vals)),('value_variance',var)]:
                    equal(summary[field],expected,field,numeric=True)
                    result[field]=summary[field]
            panel_distributions.append(result)

    def check_pair(answer):
        key=(answer['panel'],answer['item'],answer['a'],answer['b'])
        panel=panels[key[0]]
        a,b=(variants[key[0],key[1],v] for v in key[2:])
        ra,rb=raw(a['source']),raw(b['source'])
        sa,sb=members(panel,a),members(panel,b)
        equal(answer['labelChanged'],ra['label']!=rb['label'],'semantic change flag')
        expected_deltas=[rb['probabilities'][k]-ra['probabilities'][k] for k in panel['canonical_keys']]
        for actual,expected in zip(answer['deltas'],expected_deltas):
            equal(actual,expected,'semantic probability delta',numeric=True)
        equal(len(answer['deltas']),len(expected_deltas),'delta vector length')
        equal(answer['maxProbabilityDifference'],max(abs(x) for x in expected_deltas),'maximum semantic difference',numeric=True)
        equal(answer['unique'],len(sa|sb),'distinct call union')
        equal(answer['shared'],len(sa&sb),'shared call intersection')
        equal(answer['samePool'],sa==sb,'physical pool identity')
        equal({tuple(v) for v in answer['physicalSources']},sa|sb,'export physical source identities')
        for sid,_ in [tuple(a['source']),tuple(b['source']),*(sa|sb)]:
            if sid not in answer['sourceDefinitions']:
                raise AssertionError('Export omitted a required original source definition')
        ref=answer['reference']
        if panel['type']=='score':
            equal(ref['kind'],'continuous','reference kind')
            equal(ref['value'],ra['gold_score'],'continuous reference')
            equal(ref['aError'],abs(ra['typed_value']-ra['gold_score']),'A reference error',numeric=True)
            equal(ref['bError'],abs(rb['typed_value']-rb['gold_score']),'B reference error',numeric=True)
        else:
            equal(ref,{'kind':'label','value':ra['gold_label'],'aMatch':ra['label']==ra['gold_label'],'bMatch':rb['label']==rb['gold_label']},'label reference')
        equal(answer['completeJsonRoundTrip'],True,'complete formatted JSON round trip')
        return key

    seen_pairs=set()
    seen_frequencies=set()
    negative_examples={}
    process=subprocess.Popen(['node',str(HERE/'explorer_answers.mjs')],stdout=subprocess.PIPE,text=True)
    assert process.stdout is not None
    try:
        for line in process.stdout:
            answer=json.loads(line)
            if answer['kind']=='pair':
                key=check_pair(answer)
                if key in seen_pairs:
                    raise AssertionError('Duplicate pair answer')
                seen_pairs.add(key)
                counts['condition_pairs'] += 1
                counts['pairs_with_changed_label'] += answer['labelChanged']
                counts['pairs_with_shared_calls'] += answer['shared']>0
                counts['pairs_with_same_physical_pool'] += answer['samePool']
                if not negative_examples:
                    for name,field,value in [('false_change_flag','labelChanged',not answer['labelChanged']),('overcounted_union','unique',answer['unique']+1),('false_source_line','physicalSources',[[answer['physicalSources'][0][0],0],*answer['physicalSources'][1:]])]:
                        mutant={**answer,field:value}
                        try:
                            check_pair(mutant)
                        except AssertionError:
                            negative_examples[name]='rejected'
                        else:
                            raise AssertionError(f'Oracle accepted negative control {name}')
            else:
                key=(answer['panel'],answer['condition'])
                if key in seen_frequencies:
                    raise AssertionError('Duplicate frequency answer')
                seen_frequencies.add(key)
                panel=panels[key[0]]
                expected={k:0 for k in panel['canonical_keys']}
                for item in panel['items']:
                    expected[raw(variants[key[0],item['item_id'],key[1]]['source'])['label']]+=1
                equal(answer['items'],len(panel['items']),'full-panel item count')
                equal(answer['label_counts'],expected,'full-panel frequencies from actual core')
                counts['panel_condition_distributions'] += 1
    finally:
        process.stdout.close()
        if process.poll() is None:
            process.wait(timeout=30)
    equal(process.returncode,0,'Explorer task process exit')
    equal(seen_pairs,expected_pair_ids,'exhaustive pair inventory')
    equal(seen_frequencies,expected_frequency_ids,'exhaustive panel inventory')
    equal(len(source_identities),counts['saved_conditions'],'all source conditions distinct')
    files=[PROTOCOL,HERE/'run_audit.py',HERE/'explorer_answers.mjs',ROOT/'docs/explorer/core.mjs',ROOT/'docs/explorer/app.js',DATA/'index.json']
    return {
        'status':'pass','completed_utc':datetime.now(timezone.utc).isoformat(),
        'scope':'nonhuman functional task-answer and evidence-preservation audit; not a human or browser-usability experiment',
        'protocol_sha256':digest(PROTOCOL),'archive_sha256':digest(archive_path),
        'input_sha256':{str(path.relative_to(ROOT)):digest(path) for path in files},
        'environment':{'python':sys.version,'node':subprocess.check_output(['node','--version'],text=True).strip(),'platform':platform.platform()},
        'counts':dict(counts),'failed_checks':0,'negative_controls':negative_examples,
        'maximum_score_expectation_mode_gap':score_gap_max,
        'population_notes':['Condition-pair counts are derived inspection cases, not independent questions or new model calls.','Same frozen observations are represented in both conditions; successful preservation is expected and does not establish interface superiority.','Reference implementation is independently written code, not an independent researcher replication.'],
        'new_model_calls':0,'human_participants':0,
        'panel_distributions':panel_distributions,
    }

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True,help='New JSON result path; existing files are refused.')
    args=parser.parse_args()
    if args.output.exists():
        parser.error('output already exists; choose a new path')
    result=run()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2,ensure_ascii=False,allow_nan=False)+'\n')
    print(json.dumps({k:result[k] for k in ['status','counts','failed_checks','negative_controls','new_model_calls','human_participants']},indent=2))
