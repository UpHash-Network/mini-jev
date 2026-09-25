"""Independent arithmetic and trace audit. Does not import the execution runner."""
import argparse, hashlib, json, math, struct
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[4]
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for x in iter(lambda:f.read(8*1024*1024),b''):h.update(x)
 return h.hexdigest()
def softmax(values):
 exp=[math.exp(v-max(values)) for v in values];s=math.fsum(exp)
 return [v/s for v in exp]
def f32(x):return struct.unpack('f',struct.pack('f',x))[0]
def main():
 p=argparse.ArgumentParser();p.add_argument('--run',type=Path,default=HERE/'run_v1');a=p.parse_args()
 target=a.run/'AUDIT.json'
 if target.exists():raise RuntimeError('Do not overwrite audit')
 checks=[]
 def check(name,value,category='integrity'):
  checks.append({'name':name,'passed':bool(value),'category':category})
 cases=json.loads((HERE/'CASES.json').read_text());frozen=json.loads((HERE/'FREEZE.json').read_text())
 rows=[json.loads(s) for s in (a.run/'results.jsonl').read_text().splitlines()]
 receipt=json.loads((a.run/'SUMMARY.json').read_text())
 check('summary complete real model closed',receipt['status']=='complete' and not receipt['fixture_only_not_model_evidence'] and receipt['model_closed'])
 check('results digest',receipt['results_sha256']==sha(a.run/'results.jsonl'))
 check('freeze digest',receipt['freeze_sha256']==sha(HERE/'FREEZE.json'))
 check('12 cases complete in fixed order',[r['case_id'] for r in rows]==[c['case_id'] for c in cases] and len(rows)==12)
 counters=[];errors=[];typed=[];logit_deltas=[];lse_ranges=[]
 for case,row in zip(cases,rows):
  name=case['case_id'];direct=row['native_direct'];ids=row['input_token_ids'];labels=case['request']['candidates'];traces=row['lmql_backend_trace'];pids=row['candidate_token_ids']
  check(name+' native prompt exact',direct['prompt']==case['prompt'] and hashlib.sha256(case['prompt'].encode()).hexdigest()==direct['prompt_sha256']==row['prompt_sha256'])
  check(name+' native prefix and candidate IDs',ids==direct['input_token_ids'] and pids==direct['candidate_ids'])
  check(name+' native prefix digest',direct['input_token_ids_sha256']==hashlib.sha256(json.dumps(ids,separators=(',',':')).encode()).hexdigest())
  check(name+' native candidate digest',direct['candidate_ids_sha256']==hashlib.sha256(json.dumps(pids,separators=(',',':')).encode()).hexdigest())
  check(name+' each continuation one token',row['lmql_num_value_tokens']==[1]*len(labels))
  check(name+' LMTP candidate coverage',len(traces)==len(labels) and sorted(t['request']['input_token_ids'][-1] for t in traces)==sorted(pids))
  score_by_id={}
  lses=[]
  counters.append(direct['total_decode_count']);check(name+' direct single clear decode',direct['decode_count']==1 and direct['state_cleared'])
  for j,trace in enumerate(traces):
   req=trace['request'];resp=trace['response'];tid=req['input_token_ids'][-1];counters.append(resp['total_decode_count'])
   check(f'{name} LMTP {j} exact prefix',req['input_token_ids'][:-1]==ids and resp['input_token_ids']==req['input_token_ids'])
   check(f'{name} LMTP {j} full finite scores',len(resp['scores'])==len(ids)+1 and all(math.isfinite(v) for v in resp['scores']) and resp['scores'][0]==0)
   check(f'{name} LMTP {j} true vocabulary normalized score',abs(resp['scores'][-1]-(resp['final_logit']-resp['final_vocabulary_logsumexp']))<1e-12)
   check(f'{name} LMTP {j} single clear decode',resp['decode_count']==1 and resp['state_cleared'])
   score_by_id[tid]=f32(resp['scores'][-1]);lses.append(resp['final_vocabulary_logsumexp'])
   logit_deltas.append(abs(resp['final_logit']-direct['logits'][pids.index(tid)]))
  check(name+' LMQL actual scores equal LMTP float32 returned scores',row['lmql_scores']==[score_by_id[t] for t in pids])
  direct_p=softmax(direct['logits']);lmql_p=softmax(row['lmql_scores'])
  check(name+' direct probability recomputation',max(abs(x-y) for x,y in zip(direct_p,direct['probabilities']))<1e-12)
  check(name+' LMQL probability recomputation',max(abs(x-y) for x,y in zip(lmql_p,row['lmql_probabilities']))<1e-6)
  delta=max(abs(x-y) for x,y in zip(direct_p,row['lmql_probabilities']));errors.append(delta)
  check(name+' frozen probability tolerance',delta<=frozen['probability_absolute_tolerance'],'parity')
  check(name+' argmax equality',labels[max(range(len(labels)),key=lambda i:direct_p[i])]==row['lmql_argmax']==direct['answer'],'parity')
  if case['candidate_values'] is not None:
   error=abs(math.fsum(x*v for x,v in zip(direct_p,case['candidate_values']))-math.fsum(x*v for x,v in zip(row['lmql_probabilities'],case['candidate_values'])))
   typed.append(error);check(name+' frozen typed-readout tolerance',error<=frozen['typed_readout_absolute_tolerance'],'parity')
  lse_ranges.append(max(lses)-min(lses))
 check('exactly64 consecutive decodes',counters==list(range(1,65)) and receipt['last_total_decode_count']==64)
 check('12 direct 52 LMTP counts',receipt['direct_calls']==12 and receipt['backend_calls']==52)
 check('runtime reported frozen unchanged',receipt['frozen_inputs_unchanged'])
 for name,expected in frozen['files_sha256'].items():check('frozen file '+name,sha(ROOT/name)==expected)
 integrity=[c for c in checks if c['category']=='integrity'];parity=[c for c in checks if c['category']=='parity']
 outcome={'status':'audit_passed' if all(c['passed'] for c in integrity) else 'audit_failed','parity_gate_passed':all(c['passed'] for c in parity),'integrity_checks':len(integrity),'integrity_passed':sum(c['passed'] for c in integrity),'parity_checks':len(parity),'parity_passed':sum(c['passed'] for c in parity),'checks':len(checks),'passed':sum(c['passed'] for c in checks),'case_count':len(rows),'native_decode_calls':64,'max_probability_absolute_error':max(errors),'max_typed_readout_absolute_error':max(typed),'max_native_raw_logit_difference':max(logit_deltas),'max_between_candidate_vocabulary_logsumexp_range':max(lse_ranges),'independent_of_runner':True,'not_independent_model_replication':True,'audit_script_sha256':sha(Path(__file__)),'freeze_sha256':sha(HERE/'FREEZE.json'),'results_sha256':sha(a.run/'results.jsonl'),'individual_checks':checks}
 target.write_text(json.dumps(outcome,indent=2)+'\n');print(json.dumps({k:v for k,v in outcome.items() if k!='individual_checks'}))
if __name__=='__main__':main()
