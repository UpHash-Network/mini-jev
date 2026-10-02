"""Extract text-free candidate logits and membership recipes, never task answers.

Python standard library only. --check is read-only deterministic regeneration.
The physical-row projection intentionally excludes saved probability/label/value
fields. Whole archive and member bytes are authenticated here, not in the GUI.
"""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PROTOCOL_SHA = '367691c071d2e353f8968bac5a031ed0a239a435667752480508fd1501f56f53'
sha = lambda b: hashlib.sha256(b).hexdigest()
encode = lambda x: (json.dumps(x, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)+'\n').encode()


def build():
    assert sha((HERE/'protocol.json').read_bytes()) == PROTOCOL_SHA
    protocol = json.loads((HERE/'protocol.json').read_text())
    index = json.loads((ROOT/'docs/explorer/data/index.json').read_text())
    archive_path = ROOT/'paper/naacl2027/reproducibility/naacl-repro-v1-20260925.zip'
    assert sha(archive_path.read_bytes()) == protocol['archive_sha256']
    rows, sources = {}, {}
    with zipfile.ZipFile(archive_path) as archive:
        for sid, meta in index['sources'].items():
            if meta['format'] != 'jsonl':
                continue
            data = archive.read(meta['member'])
            assert sha(data) == meta['sha256']
            rows[sid] = [json.loads(line) for line in data.splitlines()]
            sources[sid] = meta
    def source(sid, line):
        meta = sources[sid]
        return {'source_id': sid, 'member': meta['member'], 'line_1based': line,
                'member_sha256': meta['sha256']}
    def identity(sid, line):
        return sid+':'+str(line)
    cases = []
    for case in protocol['cases']:
        s = case['selection']
        descriptor = next(d for d in index['panels'] if d['id'] == s['panel_id'])
        path = ROOT/'docs/explorer/data'/descriptor['path']
        assert sha(path.read_bytes()) == descriptor['sha256']
        # Only source routing, canonical rubric and IDs are read from this panel.
        panel = json.loads(path.read_text())
        recipes, physical = [], {}
        physical_by_request = {}
        if s['study'] == 'order_ensemble':
            for sid, meta in sources.items():
                if '/order_ensemble/' in meta['member'] and meta['member'].endswith('/'+s['model']+'/predictions.jsonl'):
                    physical_by_request = {row['request_index']:(sid,n,row) for n,row in enumerate(rows[sid],1)}
            assert physical_by_request
        for item in panel['items']:
            conditions = {}
            refs = []
            for side in ['a','b']:
                variant = next(v for v in item['variants'] if v['id'] == s[side])
                sid, line = variant['source']
                row = rows[sid][line-1]
                assert row['item_id'] == item['item_id'] and row['dataset'] == s['dataset']
                refs.append({'kind':'continuous','value':row['gold_score']} if s['type']=='score'
                            else {'kind':'label','value':row['gold_label']})
                if variant['kind'] == 'physical':
                    members = [(sid,line,row)]
                else:
                    members = [physical_by_request[i] for i in row['physical_member_indices']]
                ids = []
                for msid,mline,raw in members:
                    assert raw['item_id'] == item['item_id'] and raw['dataset'] == s['dataset']
                    assert raw.get('model_key',s['model']) == s['model']
                    rid = identity(msid,mline)
                    # Explicit allowlist: no original benchmark text or saved answers.
                    projected = {k:raw[k] for k in ['candidate_keys','candidate_tokens','logits','temperature','input_tokens','latency_ms','item_id','dataset','type']}
                    projected.update(rid=rid,source=source(msid,mline),model_key=s['model'],
                                     model_identity_origin='row' if 'model_key' in raw else 'validated_archive_member',
                                     tie_order=raw['candidate_keys'])
                    if rid in physical:
                        assert physical[rid] == projected
                    physical[rid] = projected
                    ids.append(rid)
                conditions[side] = {'id':s[side], 'operation':'single' if variant['kind']=='physical' else 'mean',
                                    'member_ids':ids,'recipe_source':source(sid,line)}
            assert refs[0] == refs[1]
            recipes.append({'item_id':item['item_id'],'reference':refs[0],'conditions':conditions})
        assert len(recipes) == 200
        case_input = {'schema_version':1,'case_id':case['id'],'study':s['study'],'model_key':s['model'],
                      'dataset':s['dataset'],'type':s['type'],'selected_item':s['item'],
                      'canonical_keys':panel['canonical_keys'],'score_values':panel.get('score_values'),
                      'archive_sha256':protocol['archive_sha256'],
                      'physical_records':sorted(physical.values(),key=lambda v:v['rid']),
                      'items':recipes}
        cases.append(case_input)
    return {'schema_version':1,'protocol_sha256':PROTOCOL_SHA,'cases':cases}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check',action='store_true')
    args = parser.parse_args()
    result = build()
    data = encode(result)
    p = HERE/'raw_inputs.json'
    if args.check:
        assert p.read_bytes() == data, 'Frozen input mismatch'
    else:
        assert not p.exists(), 'Refusing to overwrite frozen inputs'
        p.write_bytes(data)
    print(json.dumps({'status':'pass','input_sha256':sha(data),'bytes':len(data),'cases':len(result['cases']),
                      'physical_records':sum(len(x['physical_records']) for x in result['cases']),
                      'reconstructed_condition_instances':sum(2*len(x['items']) for x in result['cases']),
                      'case_counts':[{ 'id':x['case_id'],'physical':len(x['physical_records']),'items':len(x['items'])} for x in result['cases']]},indent=2))
