#!/usr/bin/env python3
"""Create a new sanitized derivative; never alter frozen study inputs or outputs."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import replay

SCHEDULE_FIELDS = {'item_id','dataset','split','group','type','gold_label','canonical_keys','source_question_sha256','condition','method','anchor','replicate','candidate_keys','display_order','permutation','request_index','candidate_tokens','request_sha256'}
PREDICTION_FIELDS = SCHEDULE_FIELDS | {'model_key','backend','error','forward_calls','forward_calls_total','native_decode_count','state_cleared','input_tokens','output_tokens','label','typed_value','probabilities','logits','temperature','latency_ms','model_ms','revision','rendered_sha256','tokenized_input_sha256','prepared_integrity_sha256','candidate_boundary_verified','top_logit_tie_count','tie_break','batch_size','projection','use_cache','past_key_values_returned','grad_enabled','inference_mode_enabled','model_training','parameters_require_grad','logits_to_keep','concentration'}

def sha(data):
    return hashlib.sha256(data).hexdigest()

def canonical(value):
    return replay.canonical(value)

def load(path):
    return json.loads(path.read_text(encoding='utf-8'))

def sanitizer(repository, workspace, home):
    prefixes = sorted([(str(repository.resolve()), '{REPOSITORY}'), (str(workspace.resolve()), '{WORKSPACE}'), (str(home.resolve()), '{HOME}')], key=lambda x: -len(x[0]))
    def string(value):
        for private, public in prefixes:
            value = value.replace(private+'/', public+'/')
            if value == private:
                value = public
        if value.startswith('/'):
            # Preserve identity without exposing unrecognized system/external paths.
            return '{ABSOLUTE_PATH_SHA256}/'+sha(value.encode())
        return value
    def clean(value):
        if isinstance(value, str):
            return string(value)
        if isinstance(value, list):
            return [clean(x) for x in value]
        if isinstance(value, dict):
            result = {string(k): clean(v) for k, v in value.items()}
            replay.require(len(result) == len(value), 'Sanitized path collision')
            return result
        return value
    return clean

def build(source, study, analysis, out, repository, workspace, allow_pending=False):
    replay.require(not out.exists(), 'Refusing to overwrite an existing bundle')
    protocol = load(source/'PROTOCOL.json')
    freeze_bytes = (study/'FREEZE.json').read_bytes()
    freeze = json.loads(freeze_bytes)
    clean = sanitizer(repository, workspace, Path.home())
    payloads = {}; originals = {}; transforms = []
    def put_json(name, value):
        payloads[name] = json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False).encode()+b'\n'
    def original(path, target, transform='byte-identical'):
        raw = path.read_bytes()
        originals[target] = {'source_identifier': clean(str(path.resolve())), 'original_sha256': sha(raw), 'transformation': transform}
        payloads[target] = raw if transform == 'byte-identical' else json.dumps(clean(json.loads(raw)), ensure_ascii=False, indent=2, allow_nan=False).encode()+b'\n'
        return raw
    frozen_sources = []
    for src, target in [(source/'PROTOCOL.json','frozen/confirmation/PROTOCOL.json'), (source/'analyze.py','frozen/confirmation/analyze.py'), (source.parent/'exploratory/analyze.py','frozen/exploratory/analyze.py'), (source.parent/'exploratory/SPECIFICATION.json','frozen/exploratory/SPECIFICATION.json')]:
        raw = original(src, target)
        replay.require(freeze['source_sha256'][str(src.resolve())] == sha(raw), 'Frozen source changed: '+src.name)
        frozen_sources.append({'published_path':target,'source_identifier':clean(str(src.resolve())),'original_sha256':sha(raw)})
    audit_path = source.parent/'data_inventory/CONFIRMATION_ANALYSIS_AUDIT.json'
    audit = json.loads(original(audit_path, 'provenance/CONFIRMATION_ANALYSIS_AUDIT.json'))
    audited_sources = []
    for entry in frozen_sources[:3]:
        src = next(p for p in (source/'PROTOCOL.json', source/'analyze.py', source.parent/'exploratory/analyze.py') if sha(p.read_bytes()) == entry['original_sha256'])
        identifier = str(src.relative_to(repository))
        replay.require(audit['reviewed_source_sha256'][identifier] == entry['original_sha256'], 'Independent audited source differs')
        audited_sources.append({'audit_identifier': identifier, 'original_sha256':entry['original_sha256']})
    for src, target in [(source/'SELECTION.json','data/SELECTION.json'), (study/'SCHEDULE.json','data/SCHEDULE.json')]:
        original(src,target)
    selection = load(source/'SELECTION.json')
    replay.require(freeze['source_sha256'][str((source/'SELECTION.json').resolve())] == sha((source/'SELECTION.json').read_bytes()), 'Selection changed after freeze')
    schedule = load(study/'SCHEDULE.json')
    replay.require(all(set(row) <= SCHEDULE_FIELDS for row in schedule), 'Unexpected schedule fields; requires privacy review')
    replay.require(sha(canonical(schedule)) == freeze['schedule_sha256'], 'Schedule differs from original freeze')
    original(study/'FREEZE.json','provenance/FREEZE.public.json','recursive absolute-path identifier substitution; original bytes retained only by SHA256 witness')
    original(source/'DATA_FREEZE.json','provenance/DATA_FREEZE.public.json','recursive absolute-path identifier substitution; original bytes retained only by SHA256 witness')
    original(HERE/'replay.py','replay.py')
    original(HERE/'README.md','README.md')
    models = {}; all_complete = True
    for key in protocol['models']:
        folder = study/'results'/key
        if not (folder/'COMPLETION.json').exists():
            models[key] = {'status':'pending','published_predictions':0}
            all_complete = False
            continue
        receipt = load(folder/'COMPLETION.json')
        if receipt['status'] != 'completed':
            models[key] = {'status':'incomplete','published_predictions':0,'recorded_requests':receipt['recorded_requests']}
            all_complete = False
            original(folder/'COMPLETION.json',f'models/{key}/COMPLETION.public.json','recursive absolute-path identifier substitution')
            continue
        prediction_bytes = (folder/'predictions.jsonl').read_bytes()
        attempt_bytes = (folder/'ATTEMPT.json').read_bytes()
        replay.require(sha(prediction_bytes) == receipt['file_sha256']['predictions.jsonl'], 'Original completed predictions changed')
        replay.require(sha(attempt_bytes) == receipt['file_sha256']['ATTEMPT.json'], 'Original attempt changed')
        rows = [json.loads(line) for line in prediction_bytes.splitlines()]
        public_rows = [{k:v for k,v in r.items() if k in PREDICTION_FIELDS} for r in rows]
        # Full schedule equality and frozen analyzer validation before publication.
        a = replay.module_at(source/'analyze.py')
        a.verify_schedule(public_rows,schedule)
        a.records_from_rows(public_rows,key,protocol['n_items'])
        name = f'models/{key}/predictions.jsonl'
        payloads[name] = b''.join(canonical(row)+b'\n' for row in public_rows)
        dropped = sorted(set().union(*(set(r) for r in rows))-PREDICTION_FIELDS)
        originals[name] = {'source_identifier':clean(str((folder/'predictions.jsonl').resolve())), 'original_sha256':sha(prediction_bytes),'transformation':'allowlisted physical scoring metadata only; row order and all retained numeric values unchanged','dropped_fields':dropped}
        transforms.append({'model':key,'dropped_prediction_fields':dropped})
        original(folder/'ATTEMPT.json',f'models/{key}/ATTEMPT.public.json','recursive absolute-path identifier substitution')
        original(folder/'COMPLETION.json',f'models/{key}/COMPLETION.public.json','recursive absolute-path identifier substitution; file_sha256 still refers to ORIGINAL files')
        models[key] = {'status':'completed','published_predictions':len(public_rows),'original_predictions_sha256':sha(prediction_bytes),'original_attempt_sha256':sha(attempt_bytes)}
    status = 'measurements_complete_analysis_pending' if all_complete else 'pending_measurements'
    result_sha = None
    if analysis is not None:
        replay.require(all_complete, 'Cannot publish reference results with incomplete model pools')
        raw = original(analysis/'RESULTS.json','reference/RESULTS.public.json','recursive absolute-path identifier substitution; numerical models object unchanged')
        result = json.loads(raw)
        replay.require(result['protocol'] == protocol and set(result['models']) == set(protocol['models']), 'Original results design differs')
        replay.require(result['source_sha256'][str((study/'FREEZE.json').resolve())] == sha(freeze_bytes), 'Original results belong to different freeze')
        for key,state in models.items():
            replay.require(result['source_sha256'][str((study/'results'/key/'predictions.jsonl').resolve())] == state['original_predictions_sha256'], 'Original results prediction source differs')
        status = 'complete_reference_available'; result_sha = sha(raw)
    replay.require(allow_pending or status == 'complete_reference_available', 'Study/reference pending; use --allow-pending for an explicitly pending snapshot')
    manifest = {'schema_version':1,'created_at':datetime.now(timezone.utc).isoformat(), 'status':status,
        'scope':'Portable saved-record replay, not inference reproduction or independent replication.',
        'original_freeze_sha256':sha(freeze_bytes),'original_results_sha256':result_sha,
        'original_selection_sha256':sha((source/'SELECTION.json').read_bytes()),
        'n_shared_questions':protocol['n_items'],'expected_measured_predictions':protocol['measured_requests_per_model']*len(protocol['models']),
        'models':models,'frozen_sources':frozen_sources,'audited_sources':audited_sources,
        'original_file_witnesses':originals,'prediction_transformations':transforms,
        'path_transformation':'Recursive keys and values: repository/workspace/home absolute prefixes become {REPOSITORY}/{WORKSPACE}/{HOME}; other absolute paths become {ABSOLUTE_PATH_SHA256}/hash. No reverse mapping published.',
        'omitted':'Raw questions/answers text, input token IDs, candidate token IDs, tokenization artifacts, weights, runtime binaries, logs and credentials are not included. Gold labels option_0..4 remain necessary for outcome metrics.',
        'wrapper_timing':'build_bundle.py and replay.py were created after inference started. They are not part of the pre-inference freeze. Copied analysis functions and metric helper retain exact pre-inference bytes.',
        'publication_is_derivative':True,'independent_public_preregistration':False,
        'numerical_comparison':'Structure, identities and integers exact; finite floats absolute tolerance1e-12; exact equality and maximum deviation reported.',
        'files_sha256':{name:sha(data) for name,data in sorted(payloads.items())}}
    # Check every outgoing byte for workstation path leakage and forbidden token-ID keys.
    for name, data in payloads.items():
        if name.endswith('.py') or name == 'README.md':
            continue
        text = data.decode('utf-8')
        replay.require(str(Path.home()) not in text and str(workspace) not in text and not re.search(r'/(?:Users|home)/[^/\s]+/',text), 'Private path in outgoing file: '+name)
        replay.require(not re.search(r'"(?:candidate_ids|input_ids|token_ids)"\s*:',text), 'Original token IDs in outgoing file: '+name)
    out.mkdir(parents=True)
    for name,data in payloads.items():
        target=out/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
    (out/'MANIFEST.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    replay.verify_bundle(out)
    return manifest

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,default=HERE.parent/'confirmation')
    p.add_argument('--study',type=Path,required=True)
    p.add_argument('--analysis',type=Path)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--repository',type=Path,default=HERE.parents[3])
    p.add_argument('--workspace',type=Path,default=HERE.parents[5])
    p.add_argument('--allow-pending',action='store_true')
    args=p.parse_args()
    m=build(args.source.resolve(),args.study.resolve(),args.analysis.resolve() if args.analysis else None,args.out.resolve(),args.repository.resolve(),args.workspace.resolve(),args.allow_pending)
    print(json.dumps({'status':m['status'],'published_predictions':sum(x['published_predictions'] for x in m['models'].values()),'original_results_sha256':m['original_results_sha256'],'model_calls':0}))

if __name__=='__main__':main()
