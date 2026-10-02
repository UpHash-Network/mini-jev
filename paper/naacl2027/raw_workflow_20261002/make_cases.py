"""Deterministic original, representation-invariance and malformed-input cases.

Controls are synthetic software checks. Never substitute them for observations.
"""
import copy
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent


def cases():
    originals=json.loads((HERE/'raw_inputs.json').read_text())['cases']
    result=[{'id':x['case_id'],'kind':'original','base':x['case_id'],'expected_status':'ok','input':x} for x in originals]
    for original in originals:
        x=copy.deepcopy(original);x['case_id']+='-tuple-reversed'
        for record in x['physical_records']:
            for field in ['candidate_keys','candidate_tokens','logits']:
                record[field].reverse()
        result.append({'id':x['case_id'],'kind':'synthetic_representation','base':original['case_id'],'expected_status':'ok','input':x})
    for spec in json.loads((HERE/'protocol.json').read_text())['controls']['invalid']:
        x=copy.deepcopy(next(o for o in originals if o['case_id']==spec['base']))
        x['case_id']+='-'+spec['id']
        item=next(i for i in x['items'] if i['item_id']==x['selected_item'])
        if spec['id']=='missing_member':
            rid=item['conditions']['a']['member_ids'][0]
            x['physical_records']=[r for r in x['physical_records'] if r['rid']!=rid]
        elif spec['id']=='duplicate_source':x['physical_records'].append(copy.deepcopy(x['physical_records'][0]))
        elif spec['id']=='cross_item_member':
            item['conditions']['a']['member_ids'][0]=next(r['rid'] for r in x['physical_records'] if r['item_id']!=item['item_id'])
        elif spec['id']=='duplicate_candidate':x['physical_records'][0]['candidate_keys'][1]=x['physical_records'][0]['candidate_keys'][0]
        elif spec['id']=='nonfinite_logit':x['physical_records'][0]['logits'][0]='NaN'
        elif spec['id']=='nonpositive_temperature':x['physical_records'][0]['temperature']=0
        elif spec['id']=='invalid_source_line':x['physical_records'][0]['source']['line_1based']=0
        elif spec['id']=='empty_recipe':item['conditions']['a']['member_ids']=[]
        else:raise ValueError(spec['id'])
        result.append({'id':x['case_id'],'kind':'synthetic_invalid','base':spec['base'],'expected_status':'rejected','expected_error':spec['expected_error'],'input':x})
    return result


if __name__=='__main__':
    import argparse,hashlib
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    assert not a.output.exists(),'Refusing to overwrite outputs'
    data=(json.dumps(cases(),ensure_ascii=False,separators=(',',':'),allow_nan=False)+'\n').encode()
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_bytes(data)
    print(json.dumps({'cases':20,'original':6,'synthetic_representation':6,'synthetic_invalid':8,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()},indent=2))
