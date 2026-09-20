"""Exercise the actual model, normal logits, padding and typed decision contract."""
import argparse
import copy
import json
from pathlib import Path

import torch

from release_engine import ReleaseEngine

ROOT = Path(__file__).resolve().parent


def validate(engine):
    cases = [json.loads(line) for file in ['eval_ja.jsonl','head_test_ja.jsonl']
             for line in (ROOT/'data'/file).read_text().splitlines() if line]
    chosen = [cases[i] for i in [0,5,17,25,33,47,55,78,104,121,137,143]]
    checks = []
    def check(name, passed, **detail):
        checks.append(dict(name=name,passed=bool(passed),**detail))

    singles = [engine.decide(q) for q in chosen]
    with torch.inference_mode():
        for q,a in zip(chosen[:4],singles[:4]):
            opts,ids = engine._prepare(q)
            normal = engine.model(**engine._batch([ids]),use_cache=False,return_dict=True).logits[0,-1].float()
            normal = normal[engine.symbol_ids[:len(opts)]].cpu()
            selected = torch.tensor(a['candidate_logits'])
            delta = float((normal-selected).abs().max())
            check('normal_forward_'+q['id'],delta<=1e-3,max_logit_difference=delta,tolerance=1e-3)
    batches = engine.decide_many(chosen)
    difference = max(abs(a['probabilities'][k]-b['probabilities'][k])
        for a,b in zip(singles,batches) for k in a['probabilities'])
    check('single_batch_probabilities',difference<=1e-3,max_difference=difference,tolerance=1e-3)
    check('single_batch_labels',all(a['label']==b['label'] for a,b in zip(singles,batches)))
    for q,a in zip(chosen,singles):
        if q['type']=='choice':
            reverse=copy.deepcopy(q)
            reverse['criteria']=dict(reversed(list(q['criteria'].items())))
            check('permutation_'+q['id'],engine.decide(reverse)['probabilities']==a['probabilities'])
    for count in [2,8,26]:
        q={'type':'score','state':'進捗は未着手。','instructions':'完了した段階は？',
           'criteria':[f'第{i}段階まで完了' for i in range(count)]}
        a=engine.decide(q)
        check('score_'+str(count),len(a['probabilities'])==count and 0<=a['score']<=count-1
              and abs(sum(a['probabilities'].values())-1)<1e-5)
    q=copy.deepcopy(chosen[0]); q['state']='判定用の文。'*3000
    try:
        engine.decide(q)
    except ValueError as e:
        check('long_input_rejected','no truncation applied' in str(e))
    else:
        check('long_input_rejected',False)
    check('frozen_backbone',all(not p.requires_grad for p in engine.model.parameters()))
    check('no_generated_tokens',all(a['output_tokens']==0 for a in singles+batches))
    check('repeat_deterministic',engine.decide(chosen[0])['probabilities']==singles[0]['probabilities'])
    return dict(model=engine.model_id,revision=engine.model_revision,dtype=str(engine.dtype),
        device=str(engine.device),attention=engine.attention,prompt_style=engine.prompt_style,
        runtime_fingerprint=engine.runtime_fingerprint,passed=all(c['passed'] for c in checks),checks=checks)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--config',type=Path,default=ROOT/'release_config.json')
    p.add_argument('--output',type=Path,default=ROOT/'results/release-development/production-validation.json')
    p.add_argument('--temperature-config',type=Path)
    args=p.parse_args()
    kwargs=json.loads(args.config.read_text())
    if args.temperature_config: kwargs['temperature_config']=args.temperature_config
    engine=ReleaseEngine(**kwargs)
    result=validate(engine)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False,indent=2))
    raise SystemExit(0 if result['passed'] else 1)
