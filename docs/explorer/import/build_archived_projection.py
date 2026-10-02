"""Rebuild one hash-selected existing item; no inference and no outcome selection."""
import hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent
DATA=HERE.parent/'data'
sha=lambda b:hashlib.sha256(b).hexdigest()
index=json.loads((DATA/'index.json').read_text())
choices=[]
for desc in index['panels']:
    path=DATA/desc['path'];panel=json.loads(path.read_text())
    assert sha(path.read_bytes())==desc['sha256']
    for item in panel['items']:
        physical=[v for v in item['variants'] if v['kind']=='physical']
        if len(physical)<2:continue
        identity=json.dumps([desc['id'],item['item_id']],ensure_ascii=True,separators=(',',':'))
        choices.append((sha(identity.encode()),desc,panel,item,physical))
selected,desc,panel,item,physical=min(choices,key=lambda x:x[0])
rows=[]
for v in sorted(physical,key=lambda v:v['id']):
    source,line=v['source'];original=index['sources'][source]
    row={'schema_version':1,'kind':'physical','model':panel['model_key'],'item_id':item['item_id'],'type':panel['type'],'condition':v['id'],
         'source_id':original['sha256']+':'+str(line),'key_schema':desc['id']+':canonical_keys','candidate_keys':panel['canonical_keys'],
         'candidate_count':len(panel['canonical_keys']),'distribution_scope':'full_candidate_set','probabilities':v['probabilities'],
         'probability_semantics':'conditional_on_candidate_set','probability_origin':'reported_probabilities',
         'provenance':{'file_id':original['member'],'line_1based':line,'file_sha256':original['sha256']},
         'note':'Projection of a previously published physical observation. No new model run or human validation.'}
    if panel['type']=='score':row['score_values']=panel['score_values']
    if item.get('gold_score') is not None:row['reference']={'kind':'score','value':item['gold_score']}
    elif item.get('gold_label') is not None:row['reference']={'kind':'label','value':item['gold_label']}
    # Latency is omitted because this fixture does not project a measured cost field.
    rows.append(row)
payload=('\n'.join(json.dumps(r,ensure_ascii=False,separators=(',',':')) for r in rows)+'\n').encode()
(HERE/'archived-projection.jsonl').write_bytes(payload)
manifest={'schema_version':1,'mode':'previously_published_record_projection','selection_rule':'Minimum SHA256 of compact ASCII JSON [panel_id,item_id], across published panels/items with at least two physical conditions; all selected physical conditions retained.',
          'selection_hash':selected,'eligible_model_item_groups':len(choices),'panel_id':desc['id'],'panel_path':desc['path'],'panel_sha256':desc['sha256'],'index_sha256':sha((DATA/'index.json').read_bytes()),
          'item_id':item['item_id'],'conditions':[r['condition'] for r in rows],'projection_sha256':sha(payload),'source_archive_sha256':index['bundle']['sha256'],
          'expected':[{'condition':v['id'],'label':v['label'],'typed_value':v.get('value'),'probabilities':dict(zip(panel['canonical_keys'],v['probabilities']))} for v in sorted(physical,key=lambda v:v['id'])],
          'new_model_calls':0,'human_participants':0,'scope':'Existing-record import compatibility only; not an additional model experiment, representative effectiveness evaluation, or human validation.'}
(HERE/'archived-projection.manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps({'panel':desc['id'],'item':item['item_id'],'conditions':len(rows),'eligible_groups':len(choices),'projection_sha256':sha(payload)}))
