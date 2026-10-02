#!/usr/bin/env python3
"""Create deterministic six-case package; no inference/network/public-file writes.

Default writes tasks.json once; --check regenerates in memory and checks the
frozen file exactly. The oracle reads archived rows without using Explorer core.
Node imports the unchanged core only to construct the common presenter export.
"""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import subprocess
from urllib.parse import urlencode
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
DATA = ROOT/'docs/explorer/data'
PROTOCOL_SHA256 = '237ce0e6dc1dea51a0928d43a5167441e4b1dbf21d2438e806f80622d8d8bad0'


def digest(value):
    return hashlib.sha256(value).hexdigest()


def pretty(value):
    return json.dumps(value, ensure_ascii=False, indent=2)+'\n'


def close(actual, expected):
    assert math.isclose(actual, expected, rel_tol=1e-12, abs_tol=1e-12), (actual, expected)


def generate():
    protocol_bytes=(HERE/'protocol.json').read_bytes()
    assert digest(protocol_bytes)==PROTOCOL_SHA256
    protocol=json.loads(protocol_bytes)
    for rel, expected in protocol['input_sha256'].items():
        assert digest((ROOT/rel).read_bytes())==expected, rel
    archive_path=ROOT/protocol['archive']['path']
    assert digest(archive_path.read_bytes())==protocol['archive']['sha256']
    index=json.loads((DATA/'index.json').read_text())
    selections=[]
    panels={}
    descriptors={}
    hashes={}
    # Selection reads only IDs and the prespecified study/model/type structure.
    for n,cell in enumerate(protocol['sampling']['cells'],1):
        descriptor=next(d for d in index['panels'] if d['study_id']==cell['study'] and d['model_key']==cell['model'] and d['dataset']==cell['dataset'])
        path=DATA/descriptor['path']
        assert digest(path.read_bytes())==descriptor['sha256']
        panel=json.loads(path.read_text())
        assert panel['type']==cell['type'] and len(panel['items'])==200
        seed=protocol['sampling']['seed']
        ranked=sorted((digest((seed+'\n'+panel['id']+'\n'+item['item_id']).encode('utf-8')),item['item_id']) for item in panel['items'])
        item_id=ranked[0][1]
        a,b=protocol['sampling']['condition_rule'][cell['study']]
        selections.append({'id':f'W{n:02d}','panel_id':panel['id'],'study':cell['study'],'model':cell['model'],'dataset':cell['dataset'],'type':cell['type'],'item':item_id,'a':a,'b':b,'item_hash':ranked[0][0],'eligible_items':len(ranked),'all_eligible_id_hashes_sha256':digest(pretty(ranked).encode())})
        panels[panel['id']]=panel
        descriptors[panel['id']]=descriptor
        hashes[str(path.relative_to(ROOT))]=descriptor['sha256']
    assert sorted(Counter(s['model'] for s in selections).values())==[2,2,2]
    # Use real core unmodified, without creating an extra helper file.
    node_code=r'''
import fs from 'node:fs';
import {validatePanel,compare,comparisonExport} from './docs/explorer/core.mjs';
const input=JSON.parse(fs.readFileSync(0,'utf8'));
const index=JSON.parse(fs.readFileSync('docs/explorer/data/index.json','utf8'));
const out=[];
for(const s of input){
 const d=index.panels.find(d=>d.id===s.panel_id);
 const p=validatePanel(JSON.parse(fs.readFileSync('docs/explorer/data/'+d.path,'utf8')));
 const item=p.items.find(i=>i.item_id===s.item);
 const a=item.variants.find(v=>v.id===s.a),b=item.variants.find(v=>v.id===s.b);
 const selection={study:s.study,model:s.model,dataset:s.dataset,item:s.item,a:s.a,b:s.b};
 const result=compare(p,item,a,b);
 out.push({id:s.id,comparison_export:comparisonExport(index,p,item,a,b,result,selection),label_changed:result.labelChanged,same_physical_pool:result.samePhysicalPool});
}
process.stdout.write(JSON.stringify(out));
'''
    observed=json.loads(subprocess.run(['node','--input-type=module','-e',node_code],input=json.dumps(selections),cwd=ROOT,text=True,capture_output=True,check=True).stdout)
    core={entry['id']:entry for entry in observed}
    source_rows={}
    request_sources={}
    with zipfile.ZipFile(archive_path) as archive:
        for sid,source in index['sources'].items():
            if source['format']!='jsonl':
                continue
            raw=archive.read(source['member'])
            assert digest(raw)==source['sha256']
            source_rows[sid]=[json.loads(line) for line in raw.splitlines()]
            if '/order_ensemble/' in source['member'] and source['member'].endswith('/predictions.jsonl'):
                model=source['member'].split('/')[-2]
                for lineno,row in enumerate(source_rows[sid],1):
                    key=(model,row['request_index'])
                    assert key not in request_sources
                    request_sources[key]=(sid,lineno)
    def raw(source):
        sid,line=source
        assert isinstance(line,int) and line>=1
        return source_rows[sid][line-1]
    def members(panel,variant):
        row=raw(variant['source'])
        if variant['kind']=='physical':
            return {tuple(variant['source'])}
        return {request_sources[(panel['model_key'],i)] for i in row['physical_member_indices']}
    def source_detail(source):
        sid,line=source
        return {'source_id':sid,'member':index['sources'][sid]['member'],'line_1based':line,'member_sha256':index['sources'][sid]['sha256']}
    def distribution(panel,condition):
        rows=[raw(next(v['source'] for v in item['variants'] if v['id']==condition)) for item in panel['items']]
        counts={key:sum(row['label']==key for row in rows) for key in panel['canonical_keys']}
        out={'items':len(rows),'label_counts':counts,'maximum_label_share':max(counts.values())/len(rows),'used_labels':sum(count>0 for count in counts.values())}
        if panel['type']=='score':
            values=[row['typed_value'] for row in rows]
            mean=math.fsum(values)/len(values)
            out.update(value_min=min(values),value_max=max(values),value_population_variance=math.fsum((x-mean)**2 for x in values)/len(values))
        summary=descriptors[panel['id']]['variant_summaries'][condition]
        assert summary['items']==out['items']
        assert {key:summary['label_counts'].get(key,0) for key in counts}==counts
        close(summary['max_label_share'],out['maximum_label_share'])
        assert summary['unique_labels']==out['used_labels']
        if panel['type']=='score':
            for field,key in [('value_min','value_min'),('value_max','value_max'),('value_variance','value_population_variance')]:
                close(summary[field],out[key])
        return out
    tasks=[]
    for selection in selections:
        panel=panels[selection['panel_id']]
        desc=descriptors[panel['id']]
        item=next(i for i in panel['items'] if i['item_id']==selection['item'])
        a,b=[next(v for v in item['variants'] if v['id']==selection[k]) for k in ['a','b']]
        ra,rb=[raw(v['source']) for v in [a,b]]
        for v,row in [(a,ra),(b,rb)]:
            assert row['item_id']==item['item_id'] and row['dataset']==panel['dataset']
            assert row.get('model_key',panel['model_key'])==panel['model_key']
            member_path=index['sources'][v['source'][0]]['member']
            if 'model_key' not in row:
                assert panel['model_key']=='qwen3.6-35b-a3b'
                assert member_path=='mini-jev/paper/journal_robustness/study_v1/results/predictions.jsonl'
            else:
                assert member_path.split('/')[-2]==panel['model_key']
            assert row['label']==v['label'] and row['typed_value']==v['value']
            assert [row['probabilities'][k] for k in panel['canonical_keys']]==v['probabilities']
        ma,mb=members(panel,a),members(panel,b)
        export=core[selection['id']]['comparison_export']
        deltas=[{'key':key,'a':ra['probabilities'][key],'b':rb['probabilities'][key],'delta_b_minus_a':rb['probabilities'][key]-ra['probabilities'][key]} for key in panel['canonical_keys']]
        label_changed=ra['label']!=rb['label']
        assert core[selection['id']]['label_changed']==label_changed
        assert core[selection['id']]['same_physical_pool']==(ma==mb)
        assert export['shared_physical_calls']==len(ma&mb)
        assert export['unique_physical_calls']==len(ma|mb)
        assert {tuple(v['source']) for v in export['physical_members']}==ma|mb
        for actual,expected in zip(export['candidate_comparison'],deltas):
            assert actual['key']==expected['key']
            for field in ['a','b']:
                assert actual[field]==expected[field]
            close(actual['delta'],expected['delta_b_minus_a'])
        basic={}
        for side,row in [('a',ra),('b',rb)]:
            basic[side]={'label':row['label'],'typed_value':row['typed_value'],'probabilities':{k:row['probabilities'][k] for k in panel['canonical_keys']}}
            if panel['type']=='noul':
                basic[side]['probability_of_true']=row['probabilities']['true']
        score=None
        if panel['type']=='score':
            assert ra['gold_score']==rb['gold_score']==item['gold_score']
            score={'continuous_reference':ra['gold_score'],'reference_is_not_rounded':True}
            for side,row in [('a',ra),('b',rb)]:
                values=row.get('score_values') or {key:float(key) for key in panel['canonical_keys']}
                expected=math.fsum(row['probabilities'][k]*values[k] for k in panel['canonical_keys'])
                close(expected,row['typed_value'])
                score[side]={'expected_score':row['typed_value'],'modal_stage':values[row['label']],'absolute_expectation_mode_gap':abs(row['typed_value']-values[row['label']]),'absolute_reference_error':abs(row['typed_value']-row['gold_score'])}
        mappings=[]
        for source in sorted(ma|mb):
            row=raw(source)
            member=next(v for v in item['variants'] if tuple(v['source'])==source)
            mapping=index['mappings'][member['mapping']]
            assert row['candidate_keys']==mapping['candidate_keys']
            assert row['candidate_tokens']==mapping['candidate_tokens']
            assert row.get('display_order')==mapping['display_order']
            mappings.append({'source':list(source),'condition':member['id'],'candidate_keys':row['candidate_keys'],'candidate_tokens':row['candidate_tokens'],'display_order':row.get('display_order')})
        trace={'conditions':{'a':source_detail(a['source']),'b':source_detail(b['source'])},'physical_member_union':[source_detail(source) for source in sorted(ma|mb)],'model_metadata':panel['model_metadata'],'archive_sha256':protocol['archive']['sha256']}
        for side,v in [('a',a),('b',b)]:
            row=raw(v['source'])
            trace['conditions'][side]['original_row_checks']={'item_id':row['item_id'],'dataset':row['dataset'],'model_key_in_row':row.get('model_key'),'model_key_resolved_from_panel':panel['model_key'],'label':row['label'],'typed_value':row['typed_value'],'probabilities':row['probabilities']}
        expected={'basic_typed_decision':basic,'score_expectation_mode':score,'semantic_alignment':{'canonical_keys':panel['canonical_keys'],'label_changed':label_changed,'candidate_differences':deltas,'max_absolute_probability_difference':max(abs(d['delta_b_minus_a']) for d in deltas),'physical_member_mappings':mappings},'physical_call_accounting':{'a_calls':len(ma),'b_calls':len(mb),'shared_calls':len(ma&mb),'union_calls':len(ma|mb),'same_physical_pool':ma==mb,'a_sources':[list(s) for s in sorted(ma)],'b_sources':[list(s) for s in sorted(mb)]},'source_trace':trace,'full_panel_distribution':{'a':distribution(panel,a['id']),'b':distribution(panel,b['id'])}}
        evidence={'schema_version':1,'task_id':selection['id'],'selection':export['selection'],'comparison_export':export,'complete_item':item,'complete_panel':panel,'panel_descriptor':desc,'complete_index':index}
        evidence_json=pretty(evidence)
        featured_overlap=[f['id'] for f in index['featured'] if f['panel_id']==panel['id'] and f['item_id']==item['item_id']]
        tasks.append({'id':selection['id'],'selection':selection,'explorer_fragment':urlencode(export['selection']),'prompts':[q for q in protocol['questions'] if q['id']!='score_expectation_mode' or panel['type']=='score'],'expected_answers':expected,'evidence_json':evidence_json,'evidence_sha256':digest(evidence_json.encode('utf-8')),'evidence_bytes_utf8':len(evidence_json.encode('utf-8')),'known_featured_item_overlap':featured_overlap})
    return {'schema_version':1,'protocol_sha256':PROTOCOL_SHA256,'archive_sha256':protocol['archive']['sha256'],'input_sha256':hashes,'sample_selection':protocol['sampling'],'answer_provenance':'Independent raw ZIP reader; unchanged Explorer core export checked against original rows. No UI observation, human validation or new model measurement is claimed here.','known_featured_examples':index['featured'],'prior_audit':{'path':'paper/naacl2027/inspection_audit_20261002/results.json','sha256':protocol['input_sha256']['paper/naacl2027/inspection_audit_20261002/results.json'],'not_blinded':True},'task_count':len(tasks),'question_instance_count':sum(len(t['prompts']) for t in tasks),'tasks':tasks,'resources':{'new_model_calls':0,'human_participants':0,'paid_services':0},'oracle_check_status':'pass'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check',action='store_true')
    args=parser.parse_args()
    result=generate()
    encoded=pretty(result).encode('utf-8')
    path=HERE/'tasks.json'
    if args.check:
        assert path.read_bytes()==encoded, 'Frozen tasks differ from deterministic regeneration'
    else:
        if path.exists():
            raise SystemExit('Refusing to overwrite frozen tasks.json; use --check')
        path.write_bytes(encoded)
    print(json.dumps({'status':'pass','mode':'check' if args.check else 'create','tasks':len(result['tasks']),'question_instances':result['question_instance_count'],'protocol_sha256':PROTOCOL_SHA256,'tasks_sha256':digest(encoded),'bytes':len(encoded),'selections':[{k:v for k,v in t['selection'].items() if k not in ['all_eligible_id_hashes_sha256']} for t in result['tasks']],'featured_overlap':[{'task':t['id'],'overlap':t['known_featured_item_overlap']} for t in result['tasks']]},ensure_ascii=False,indent=2))

if __name__=='__main__':
    main()
