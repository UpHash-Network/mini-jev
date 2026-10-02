"""Five fixed-binding canonical rotations; formatting only, no model inference."""
from collections import defaultdict
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
K=5
MAX_INPUT_TOKENS=2048
CANONICAL_KEYS=tuple(f'option_{i}' for i in range(K))
AVERAGING_RULE='uniform_mean_after_mapping_T1_probabilities_to_canonical_meanings'

def _load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    if spec is None or spec.loader is None: raise ImportError(str(path))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module

def configure_runtime(root):
    global DEPENDENCY_ROOT,DEPENDENCY_FILES,NativeEngine,options_for,_replace_option_lines
    DEPENDENCY_ROOT=Path(root).resolve()
    DEPENDENCY_FILES=(DEPENDENCY_ROOT/'native_engine.py',DEPENDENCY_ROOT/'paper/journal_robustness/conditions.py')
    native=_load('_diagnostic_native_formatter',DEPENDENCY_FILES[0])
    saved=sys.modules.get('native_engine');saved_path=list(sys.path)
    try:
        sys.modules['native_engine']=native
        old=_load('_diagnostic_old_conditions',DEPENDENCY_FILES[1])
    finally:
        sys.path[:]=saved_path
        if saved is None:sys.modules.pop('native_engine',None)
        else:sys.modules['native_engine']=saved
    NativeEngine=native.NativeEngine;options_for=native.options_for
    _replace_option_lines=old._replace_option_lines

configure_runtime(HERE/'runtime_source')

def _validate_row(row):
    if not isinstance(row,dict) or row.get('type')!='choice':
        raise ValueError('Only five-choice inputs are supported')
    for key in ('id','state','instructions'):
        if not isinstance(row.get(key),str) or not row[key].strip():
            raise ValueError('Nonempty '+key+' required')
    options=options_for(row)
    if tuple(key for key,_ in options)!=CANONICAL_KEYS:
        raise ValueError('Exactly option_0 through option_4 are required')
    return options

def _cyclic_orders(sequence):
    seq=tuple(sequence)
    return [seq[i:]+seq[:i] for i in range(K)]

def variants(row):
    options=_validate_row(row)
    formatter=object.__new__(NativeEngine);formatter.prompt_style='repeat_typed_score'
    candidates,prefix,_=formatter._candidate_spec(row,options)
    if candidates!=list('ABCDE'):raise ValueError('Expected five A..E candidate tokens')
    base={'messages':formatter._messages(row,options),'candidates':candidates,'max_input_tokens':MAX_INPUT_TOKENS}
    if prefix:base['assistant_prefix']=prefix
    lines=[f'{token}. {key}: {meaning}' for token,(key,meaning) in zip(candidates,options)]
    records=[]
    for replicate,order in enumerate(_cyclic_orders(range(K))):
        records.append({'condition':f'fixed_cyclic:canonical:{replicate}',
            'method':'fixed_cyclic','anchor':'canonical','replicate':replicate,
            'request':_replace_option_lines(base,lines,[lines[i] for i in order]),
            'candidate_keys':list(CANONICAL_KEYS),'canonical_keys':list(CANONICAL_KEYS),
            'display_order':[CANONICAL_KEYS[i] for i in order],'permutation':list(order)})
    return records

def canonical_probabilities(values,candidate_keys,canonical_keys=CANONICAL_KEYS):
    keys,target,values=list(candidate_keys),list(canonical_keys),list(values)
    if len(values)!=K or len(keys)!=K or len(set(keys))!=K or tuple(target)!=CANONICAL_KEYS or set(keys)!=set(target):
        raise ValueError('Invalid semantic mapping')
    if any(type(x) not in (int,float) or not math.isfinite(x) or not 0<=x<=1 for x in values) or not math.isclose(sum(values),1,abs_tol=1e-6,rel_tol=0):
        raise ValueError('Expected finite normalized probabilities')
    p=dict(zip(keys,values))
    return [p[key] for key in target]

def metadata(row):
    records=variants(row);groups=defaultdict(list)
    for r in records:
        digest=hashlib.sha256(json.dumps(r['request'],ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
        groups[digest].append(r['condition'])
    return {'physical_forward_count':5,'unique_request_count':len(groups),
        'single_members':{'canonical':'fixed_cyclic:canonical:0'},
        'two_call_probe_members':['fixed_cyclic:canonical:0','fixed_cyclic:canonical:1'],
        'five_call_members':[r['condition'] for r in records],
        'duplicate_request_groups':[g for g in groups.values() if len(g)>1],
        'averaging_rule':AVERAGING_RULE}
