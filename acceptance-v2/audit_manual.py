"""Read-only data checks; writes only the v2 aggregate audit report, no examples."""
import collections
import hashlib
import json
import re
from pathlib import Path

ROOT=Path(__file__).resolve().parent
V1=ROOT.parent/'acceptance'/'private'
PRIVATE=ROOT/'private'

def load(path):
    return [json.loads(x) for x in path.read_text().splitlines()]

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def signature(row):
    return json.dumps({k:row[k] for k in ('type','state','instructions','criteria')},ensure_ascii=False,sort_keys=True)

def trigrams(row):
    text=json.dumps(row['state'],ensure_ascii=False,sort_keys=True).split('\\n\\n')[0]
    text=re.sub(r'[0-9０-９]+','N',text)
    return set(text[i:i+3] for i in range(max(0,len(text)-2)))

def main():
    new={name:load(PRIVATE/f'{name}.jsonl') for name in ('acceptance_test','calibration')}
    prior={name:load(V1/f'{name}.jsonl') for name in ('acceptance_test','calibration','generated_2220')}
    all_new=sum(new.values(),[]); all_old=sum(prior.values(),[])
    ngrams=[trigrams(x) for x in all_new]; ograms=[trigrams(x) for x in all_old]
    max_sim=max(len(a&b)/len(a|b) if a|b else 0 for a in ngrams for b in ograms)
    assert len({x['id'] for x in all_new})==300
    assert len({signature(x) for x in all_new})==300
    assert not {signature(x) for x in all_new}&{signature(x) for x in all_old}
    report={
        'version':2,'status':'self-audit complete','no_model_calls':True,
        'authoring_context':'The author diagnosed the first 400 frozen v1 predictions before v2 authoring. No later predictions, v2 predictions, or selected new model were consulted. Per-type skill-family counts and candidate cardinalities were held exactly constant.',
        'split_scope':'Independent new situations and rubrics. Logical skill families intentionally recur; no claim of new abstract skills.',
        'exact_input_overlap_with_all_v1':0,'exact_duplicates_within_v2_manual_and_calibration':0,
        'normalized_state_trigram_max_jaccard_to_v1':round(max_sim,6),
        'similarity_note':'Numbers normalized, long supplemental paragraphs removed. Highest-similarity pairs manually reviewed; lexical similarity is not a proof of semantic independence.',
        'v1_files_unchanged':{n:sha(V1/f'{n}.jsonl') for n in prior},'datasets':{}}
    for name,rows in new.items():
        count=60 if name=='acceptance_test' else 40
        assert collections.Counter(x['type'] for x in rows)=={k:count for k in ('choice','noul','score')}
        report['datasets'][name]=entry={
            'count':len(rows),'sha256':sha(PRIVATE/f'{name}.jsonl'),
            'family_count':len({x['tag'] for x in rows}),
            'families':dict(collections.Counter(x['tag'] for x in rows)),
            'structured_states':sum(isinstance(x['state'],dict) for x in rows),
            'long_states':sum('補足' in x['state'] if isinstance(x['state'],dict) else '\n\n' in x['state'] for x in rows),
            'max_state_characters':max(len(json.dumps(x['state'],ensure_ascii=False)) for x in rows),
            'per_type':{}}
        assert entry['structured_states']==sum(isinstance(x['state'],dict) for x in prior[name])
        for kind in ('choice','noul','score'):
            rr=[x for x in rows if x['type']==kind];oo=[x for x in prior[name] if x['type']==kind]
            assert collections.Counter(x['tag'] for x in rr)==collections.Counter(x['tag'] for x in oo)
            counts=collections.Counter(len(x['criteria']) for x in rr)
            assert counts==collections.Counter(len(x['criteria']) for x in oo)
            entry['per_type'][kind]=info={
                'family_distribution_exactly_matches_v1':True,
                'candidate_count_distribution_exactly_matches_v1':True,'candidate_counts':dict(counts)}
            for row in rr:
                criteria=row['criteria']; assert 2<=len(criteria)<=8
                keys=[str(i) for i in range(len(criteria))] if isinstance(criteria,list) else list(criteria)
                assert row['label'] in keys
                assert all(isinstance(d,str) and d.strip() for d in (criteria if isinstance(criteria,list) else criteria.values()))
                assert isinstance(row['instructions'],str) and row['instructions'].strip()
            if kind=='noul':
                labels=collections.Counter(x['label'] for x in rr)
                assert labels=={'true':count//2,'false':count//2}
                info['labels']=dict(labels)
            elif kind=='score':
                info['stages']=dict(collections.Counter(x['label'] for x in rr))
            else:
                balance={}
                for k in range(2,9):
                    positions=collections.Counter(sorted(x['criteria']).index(x['label']) for x in rr if len(x['criteria'])==k)
                    numbers=[positions.get(i,0) for i in range(k)]
                    assert max(numbers)-min(numbers)<=1
                    balance[k]=numbers
                info['correct_positions_after_key_sort']=balance
    peer=ROOT/'MANUAL_PEER_REVIEW.json'
    if peer.is_file():
        report['peer_review']=json.loads(peer.read_text())
        report['status']='self-audit complete; peer review recorded'
    (ROOT/'MANUAL_AUDIT.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'status':report['status'],'counts':{k:v['count'] for k,v in report['datasets'].items()},
        'sha256':{k:v['sha256'] for k,v in report['datasets'].items()},'v1_exact_overlap':0,
        'internal_exact_duplicates':0,'normalized_state_max_jaccard':round(max_sim,6)},indent=2))

if __name__=='__main__':main()
