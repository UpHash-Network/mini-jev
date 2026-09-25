"""Real LMQL 0.7.3 scoring with an explicitly custom, pinned LMTP native backend.

--preflight uses a labelled synthetic backend ONLY to exercise library/tokenizer
plumbing without model inference. It is not comparator evidence.
"""
import argparse, asyncio, hashlib, importlib.metadata, json, os, subprocess, time
from pathlib import Path
import numpy as np
import lmql
from lmql.models.lmtp.backends.lmtp_model import LMTPModel
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[4]
WORK=ROOT/'work/naacl-finalization/comparator'
ENGINE=None
class NativeProcess:
 def __init__(self, log):
  self.trace=[]; self.stderr=log.open('w'); self.closed=False
  self.p=subprocess.Popen([str(WORK/'native-runtime/bin/llama-lmql-helper'),'--model',str(ROOT/'work/models/qwen3.6-35b-a3b-gguf/Qwen3.6-35B-A3B-Q4_K_M.gguf'),'--ctx','2048','--gpu-layers','99','--threads','6'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=self.stderr,text=True,bufsize=1)
  self.ready=json.loads(self.p.stdout.readline()); assert self.ready['ready']
 def request(self,q):
  self.p.stdin.write(json.dumps(q,ensure_ascii=False)+'\n');self.p.stdin.flush()
  r=json.loads(self.p.stdout.readline());self.trace.append({'request':q,'response':r})
  if 'error' in r:raise RuntimeError(r['error'])
  return r
 def close(self):
  self.p.stdin.close();self.p.wait(timeout=30);self.stderr.close();self.closed=self.p.returncode==0
class PlumbingFixture:
 def __init__(self):self.trace=[];self.closed=True
 def request(self,q):
  ids=q['input_token_ids'];r={'scores':[0.]+[-float(t%17)-0.25 for t in ids[1:]],'input_token_ids':ids,'fixture_only':True}
  self.trace.append({'request':q,'response':r});return r
class PinnedNativeBackend(LMTPModel):
 max_batch_size=1
 def __init__(self,model_identifier,**kwargs):
  self.model_identifier=model_identifier
  if ENGINE is None:raise RuntimeError('Native engine was not initialized by the caller')
 def model_info(self):return {'backend':'custom LMTP pinned llama.cpp C API bridge','lmql':importlib.metadata.version('lmql'),'not_stock_llama_cpp_python_backend':True}
 def eos_token_id(self):return 248046
 def score(self,input_ids,attention_mask,**kwargs):
  input_ids=np.asarray(input_ids);attention_mask=np.asarray(attention_mask)
  assert input_ids.shape[0]==1 and np.all(attention_mask==1)
  r=ENGINE.request({'mode':'lmql_score','id':f'LMTP-{len(ENGINE.trace)}','input_token_ids':[int(t) for t in input_ids[0]]})
  return np.array([r['scores']],dtype=np.float64)
 def generate(self,*a,**kw):raise NotImplementedError('This diagnostic adapter only exposes scoring')
LMTPModel.registry['mini-jev-pinned']=PinnedNativeBackend

def digest(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for chunk in iter(lambda:f.read(8*1024*1024),b''):h.update(chunk)
 return h.hexdigest()
def pinned_model():
 return lmql.model('local:mini-jev-pinned:qwen3.6-q4km',tokenizer=str(WORK/'tokenizer'),async_transport=True)

def verify_freeze():
 freeze=json.loads((HERE/'FREEZE.json').read_text())
 for name,expected in freeze['files_sha256'].items():
  if digest(ROOT/name)!=expected:raise ValueError('Frozen file hash mismatch: '+name)
 return digest(HERE/'FREEZE.json')

async def run(args):
 global ENGINE
 freeze_sha=None if args.preflight else verify_freeze()
 cases=json.loads((HERE/'CASES.json').read_text())
 ENGINE=PlumbingFixture() if args.preflight else NativeProcess(args.output/'native.log')
 rows=[]
 try:
  model=pinned_model();tok=model.get_tokenizer()
  for case in cases:
   prompt=case['prompt'];labels=case['request']['candidates']
   ids=tok.convert_bytes_to_ids(tok.tokenize(prompt,asbytes=True))
   candidate_ids=[tok.convert_bytes_to_ids(tok.tokenize(label,asbytes=True)) for label in labels]
   assert all(len(x)==1 for x in candidate_ids)
   assert tok.bos_token_id is None or ids[0]==tok.bos_token_id, 'LMQL would prepend unmatched BOS'
   for label,cid in zip(labels,candidate_ids):assert tok.convert_bytes_to_ids(tok.tokenize(prompt+label,asbytes=True))==ids+cid
   direct=None
   if not args.preflight:
    direct=ENGINE.request(dict(case['request'],mode='direct'))
    assert direct['prompt']==prompt and direct['input_token_ids']==ids
    assert direct['candidate_ids']==[c[0] for c in candidate_ids]
   before=len(ENGINE.trace);start=time.perf_counter()
   result=await model.score(prompt,labels)
   wall=time.perf_counter()-start
   calls=ENGINE.trace[before:]
   assert len(calls)==len(labels), (len(calls),len(labels))
   assert sorted(c['request']['input_token_ids'][-1] for c in calls)==sorted(c[0] for c in candidate_ids)
   assert all(c['request']['input_token_ids'][:-1]==ids for c in calls)
   probs=result.probs(agg='sum').tolist()
   scores=result.scores(agg='sum').tolist()
   row={'case_id':case['case_id'],'task_type':case['task_type'],'language':case['language'],'prompt_sha256':hashlib.sha256(prompt.encode()).hexdigest(),'input_token_ids':ids,'candidate_labels':labels,'candidate_token_ids':[c[0] for c in candidate_ids],'lmql_scores':scores,'lmql_probabilities':probs,'lmql_argmax':result.argmax(),'lmql_num_value_tokens':result.num_value_tokens,'lmql_seconds':wall,'lmql_backend_calls':len(calls),'native_direct':direct,'lmql_backend_trace':calls}
   if not args.preflight:
    expected=np.array(direct['probabilities']);actual=np.array(probs)
    row['max_probability_absolute_error']=float(np.max(np.abs(expected-actual)))
    row['total_variation_distance']=float(np.abs(expected-actual).sum()/2)
    row['argmax_matches']=result.argmax()==direct['answer']
    values=case['candidate_values']
    row['typed_readout_absolute_error']=None if values is None else abs(float(expected@values)-float(actual@values))
    row['within_prespecified_tolerance']=row['max_probability_absolute_error']<=1e-5 and row['argmax_matches'] and (values is None or row['typed_readout_absolute_error']<=1e-4)
   rows.append(row)
   (args.output/'results.jsonl').open('a').write(json.dumps(row,ensure_ascii=False)+'\n')
   print(json.dumps({'case':row['case_id'],'lmql_backend_calls':len(calls),'probability_error':row.get('max_probability_absolute_error'),'fixture_only':args.preflight}),flush=True)
 finally:
  if isinstance(ENGINE,NativeProcess):ENGINE.close()
  freeze_unchanged=args.preflight or verify_freeze()==freeze_sha
  summary={'freeze_sha256':freeze_sha,'frozen_inputs_unchanged':freeze_unchanged,'status':'complete' if len(rows)==len(cases) else 'incomplete','fixture_only_not_model_evidence':args.preflight,'cases_completed':len(rows),'expected_cases':len(cases),'backend_calls':sum(r['lmql_backend_calls'] for r in rows),'direct_calls':sum(r['native_direct'] is not None for r in rows),'model_closed':ENGINE.closed,'last_total_decode_count':None if args.preflight else ENGINE.trace[-1]['response'].get('total_decode_count'),'all_prefix_and_candidate_token_checks_passed':len(rows)==len(cases),'all_probability_checks_passed':None if args.preflight else all(r['within_prespecified_tolerance'] for r in rows),'max_probability_absolute_error':None if args.preflight or not rows else max(r['max_probability_absolute_error'] for r in rows),'lmql_version':importlib.metadata.version('lmql'),'custom_backend':True,'results_sha256':digest(args.output/'results.jsonl') if rows else None,'cases_sha256':digest(HERE/'CASES.json'),'runner_sha256':digest(Path(__file__))}
  (args.output/'SUMMARY.json').write_text(json.dumps(summary,indent=2)+'\n')
  print(json.dumps(summary),flush=True)
 if not args.preflight and not summary['all_probability_checks_passed']:raise RuntimeError('Prespecified parity tolerance failed; preserve result and investigate')

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--preflight',action='store_true');p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 if a.output.exists():raise ValueError('Output already exists; do not overwrite study evidence')
 a.output.mkdir(parents=True)
 asyncio.run(run(a))
