"""Restore exact frozen input bytes from locally acquired, hash-verified public datasets.

This convenience script was written after measurement began. It does not select
new items or change the pre-inference selection; exact original hashes are required.
Raw data must be kept outside this bundle and the publication repository.
"""
import argparse
import hashlib
import json
from pathlib import Path

def sha(raw):return hashlib.sha256(raw).hexdigest()
def canonical(x):return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()

def main():
    p=argparse.ArgumentParser();p.add_argument('--japanese-source',type=Path,required=True);p.add_argument('--english-source',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    here=Path(__file__).resolve().parent
    if a.out.exists():raise ValueError('Output must be a new directory')
    roots=[here]+[r for r in here.parents if (r/'.git').exists()]
    if any(a.out.resolve().is_relative_to(r) for r in roots):raise ValueError('Raw inputs must remain outside publication repository')
    selection=json.loads((here/'code/SELECTION.json').read_text())
    raw={}
    for dataset,path in [('JCommonsenseQA',a.japanese_source),('CommonsenseQA',a.english_source)]:
        spec=selection['dataset_sources'][dataset]
        if sha(path.read_bytes())!=spec['source_sha256']:raise ValueError('Wrong source bytes')
        if dataset=='JCommonsenseQA':
            rows=[json.loads(l) for l in path.read_text().splitlines()];raw[dataset]={str(r['q_id']):r for r in rows}
        else:
            import pyarrow.parquet as pq
            rows=pq.read_table(path).to_pylist();raw[dataset]={r['id']:r for r in rows}
    outputs={d:[] for d in raw}
    for ref in selection['items']:
        dataset=ref['dataset'];r=raw[dataset][ref['original_id']];ja=dataset=='JCommonsenseQA'
        if sha(canonical(r))!=ref['source_row_sha256']:raise ValueError('Source row changed')
        question=r['question'];row={'id':ref['id'],'dataset':dataset,'split':'valid' if ja else 'validation',
            'group':('jcqa-question:' if ja else 'csqa-question:')+sha(question.encode()),'type':'choice','source':'external',
            'state':('質問: ' if ja else 'Question: ')+question,
            'instructions':'質問に対して、一般的な知識や常識に基づく最も適切な答えを選択肢から一つ選んでください。' if ja else 'Choose the single most appropriate answer to the question using general knowledge and common sense.',
            'criteria':{f'option_{i}':r[f'choice{i}'] if ja else r['choices']['text'][i] for i in range(5)},
            'label':f'option_{r["label"]}' if ja else f'option_{r["choices"]["label"].index(r["answerKey"])}'}
        if sha(canonical(row))!=ref['question_sha256']:raise ValueError('Restored prompt record differs')
        outputs[dataset].append(canonical(row)+b'\n')
    blobs={d:b''.join(rows) for d,rows in outputs.items()}
    if sha(blobs['JCommonsenseQA']+blobs['CommonsenseQA'])!=selection['questions_sha256']:raise ValueError('Combined frozen input differs')
    a.out.mkdir(parents=True)
    for d,name in [('JCommonsenseQA','questions-ja.jsonl'),('CommonsenseQA','questions-en.jsonl')]:
        (a.out/name).write_bytes(blobs[d])
    print(json.dumps({'status':'exact_frozen_inputs_restored','questions':480,'sha256':{d:sha(b) for d,b in blobs.items()}}))

if __name__=='__main__':main()
