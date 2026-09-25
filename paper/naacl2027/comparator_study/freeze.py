"""Pin local diagnostic inputs before inference; refuses overwriting a freeze."""
import hashlib, importlib.metadata, json, platform, sys
from datetime import datetime, timezone
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[4];WORK=ROOT/'work/naacl-finalization/comparator'
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for chunk in iter(lambda:f.read(8*1024*1024),b''):h.update(chunk)
 return h.hexdigest()
if (HERE/'FREEZE.json').exists():raise RuntimeError('Do not overwrite freeze')
source=(HERE/'llama_lmql_helper.cpp').read_text();start=source.index('                // LMQL LMTP backend:');stop=source.index('                if (mode != "direct"',start)
base=ROOT/'outputs/mini-jev-naacl2027/paper/matched_native/llama_matched_helper.cpp'
assert source[:start]+source[stop:]==base.read_text()
pre=json.loads((WORK/'preflight-v5/SUMMARY.json').read_text());assert pre['status']=='complete' and pre['fixture_only_not_model_evidence'] and pre['cases_completed']==12 and pre['backend_calls']==52
import lmql
lmql_root=Path(lmql.__file__).resolve().parent
paths=[p for p in HERE.iterdir() if p.is_file()]
paths += list((WORK/'tokenizer').glob('*.json'))+list((WORK/'tokenizer').glob('*.txt'))
paths += [p for p in (WORK/'native-runtime').rglob('*') if p.is_file() and not p.is_symlink()]
paths += list(lmql_root.rglob('*.py'))
paths += [base,WORK/'preflight-v5/SUMMARY.json',ROOT/'work/qwen3.6-tokenizer-metadata/gguf_chat_template.jinja',ROOT/'work/models/qwen3.6-35b-a3b-gguf/Qwen3.6-35B-A3B-Q4_K_M.gguf']
files={str(p.relative_to(ROOT)):sha(p) for p in sorted(set(paths))}
model_key='work/models/qwen3.6-35b-a3b-gguf/Qwen3.6-35B-A3B-Q4_K_M.gguf'
assert files[model_key]=='671e47e0ec53c665d048b98c3ecbfd5236b5ca9c3e02ed19fc8f81f7b85140c7'
receipt={'schema_version':1,'frozen_at_utc':datetime.now(timezone.utc).isoformat(),'purpose':'12-case custom LMQL native backend integration diagnostic','no_model_inference_before_freeze':True,'lmql_version':importlib.metadata.version('lmql'),'python':sys.version,'platform':platform.platform(),'custom_backend_not_stock':True,'direct_path_equals_pinned_baseline_outside_added_branch':True,'cases':12,'expected_native_direct_calls':12,'expected_lmql_continuation_calls':52,'expected_total_decode_calls':64,'probability_absolute_tolerance':1e-5,'typed_readout_absolute_tolerance':1e-4,'files_sha256':files,'dependencies':{d.metadata['Name']:d.version for d in importlib.metadata.distributions()}}
(HERE/'FREEZE.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
print(json.dumps({'frozen':True,'files':len(files),'sha256':sha(HERE/'FREEZE.json')}))
