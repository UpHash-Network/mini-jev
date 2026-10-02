#!/usr/bin/env python3
"""Portable saved-record replay. No inference, model package or network required."""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys

sys.dont_write_bytecode = True

def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()

def sha(data):
    return hashlib.sha256(data).hexdigest()

def load(path):
    return json.loads(path.read_text(encoding='utf-8'))

def module_at(path):
    spec = importlib.util.spec_from_file_location('frozen_confirmation_analysis', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def require(condition, message):
    if not condition:
        raise ValueError(message)

def numeric_compare(actual, expected, tolerance=1e-12, path='models'):
    """Structural identities/counts exact; finite float values absolute tolerance."""
    if isinstance(expected, dict):
        require(isinstance(actual, dict) and set(actual) == set(expected), 'Keys differ: '+path)
        return max((numeric_compare(actual[k], v, tolerance, path+'/'+k) for k, v in expected.items()), default=0.0)
    if isinstance(expected, list):
        require(isinstance(actual, list) and len(actual) == len(expected), 'Length differs: '+path)
        return max((numeric_compare(a, b, tolerance, path+'/'+str(i)) for i, (a, b) in enumerate(zip(actual, expected))), default=0.0)
    if type(expected) is float:
        require(type(actual) in (float, int) and math.isfinite(actual) and math.isfinite(expected), 'Nonfinite/nonnumeric: '+path)
        delta = abs(actual-expected)
        require(delta <= tolerance, 'Numerical difference exceeds tolerance: '+path)
        return delta
    require(type(actual) is type(expected) and actual == expected, 'Exact value differs: '+path)
    return 0.0

def verify_bundle(root):
    root = root.resolve()
    manifest = load(root/'MANIFEST.json')
    require(manifest['schema_version'] == 1, 'Unknown bundle schema')
    for name, expected in manifest['files_sha256'].items():
        path = root/name
        require(not Path(name).is_absolute() and path.resolve().is_relative_to(root), 'Unsafe bundle path')
        require(path.is_file() and not path.is_symlink(), 'Missing or linked bundle file: '+name)
        require(sha(path.read_bytes()) == expected, 'Published bytes differ: '+name)
    protocol = load(root/'frozen/confirmation/PROTOCOL.json')
    freeze = load(root/'provenance/FREEZE.public.json')
    schedule = load(root/'data/SCHEDULE.json')
    require(sha(canonical(schedule)) == freeze['schedule_sha256'], 'Schedule hash differs')
    require(freeze['stage'] == 'before_any_new_study_model_forward', 'Wrong freeze stage')
    require(freeze['models'] == protocol['models'], 'Model list differs')
    require(freeze['n_items'] == protocol['n_items'], 'Panel size differs')
    require(len(schedule) == protocol['measured_requests_per_model'], 'Schedule count differs')
    for entry in manifest['frozen_sources']:
        require(sha((root/entry['published_path']).read_bytes()) == entry['original_sha256'], 'Frozen source bytes differ')
        require(freeze['source_sha256'][entry['source_identifier']] == entry['original_sha256'], 'Source absent from original freeze')
    audit = load(root/'provenance/CONFIRMATION_ANALYSIS_AUDIT.json')
    for entry in manifest['audited_sources']:
        require(audit['reviewed_source_sha256'][entry['audit_identifier']] == entry['original_sha256'], 'Independent audit differs')
    selection = load(root/'data/SELECTION.json')
    selected = {r['id']: r for r in selection['items']}
    require(len(selected) == selection['count'] == protocol['n_items'], 'Selection size differs')
    for row in schedule:
        ref = selected[row['item_id']]
        require((row['group'], row['source_question_sha256']) == (ref['group'], ref['question_sha256']), 'Schedule differs from selection')
    pools = {}
    for key, state in manifest['models'].items():
        if state['status'] != 'completed':
            continue
        folder = root/'models'/key
        completion = load(folder/'COMPLETION.public.json')
        attempt = load(folder/'ATTEMPT.public.json')
        require(completion['model_key'] == key and attempt['model_key'] == key, 'Receipt model differs')
        require(completion['status'] == 'completed' and completion['model_closed_before_receipt'] and completion['source_unchanged'], 'Unfinished/unclosed/changed-source model')
        require(completion['failed_requests'] == 0 and completion['fatal_error_type'] is None, 'Failed measurement')
        n = protocol['measured_requests_per_model']
        require(completion['expected_requests'] == completion['recorded_requests'] == attempt['expected_requests'] == n, 'Receipt counts differ')
        require(completion['expected_excluded_calls'] == (27 if key == 'qwen2.5-1.5b' else 3), 'Excluded parity/warmup count differs')
        require(completion['actual_calls_including_gate_and_warmup'] == n+completion['expected_excluded_calls'], 'Actual call count differs')
        require(completion['last_observed_cumulative_call_count'] == completion['actual_calls_including_gate_and_warmup'], 'Cumulative call count differs')
        require(attempt['freeze_sha256'] == manifest['original_freeze_sha256'], 'Attempt belongs to different original freeze')
        require(completion['file_sha256']['predictions.jsonl'] == state['original_predictions_sha256'], 'Original prediction witness differs')
        require(completion['file_sha256']['ATTEMPT.json'] == state['original_attempt_sha256'], 'Original attempt witness differs')
        rows = [json.loads(line) for line in (folder/'predictions.jsonl').read_text().splitlines()]
        require(len(rows) == n, 'Published pool count differs')
        pools[key] = rows
    return manifest, protocol, schedule, pools

def replay(root):
    manifest, protocol, schedule, pools = verify_bundle(root)
    require(manifest['status'] == 'complete_reference_available', 'Bundle is pending; no verified numerical result available')
    require(set(pools) == set(protocol['models']), 'All model pools are required')
    a = module_at(root/'frozen/confirmation/analyze.py')
    a.metric.check_metrics()
    models = {}
    identity = None
    for key in protocol['models']:
        a.verify_schedule(pools[key], schedule)
        records = a.records_from_rows(pools[key], key, protocol['n_items'])
        panel = [(r['item_id'], r['group'], r['source_question_sha256'], r['gold_label']) for r in records]
        require(identity is None or panel == identity, 'Model panels differ')
        identity = panel
        models[key] = {'A': a.analyze_a(records, protocol['A']), 'B': a.analyze_b(records, protocol['B'])}
    reference = load(root/'reference/RESULTS.public.json')
    require(reference['protocol'] == protocol, 'Reference protocol differs')
    difference = numeric_compare(models, reference['models'])
    return {'created_at': datetime.now(timezone.utc).isoformat(),
        'scope': 'Portable saved-record replay via byte-identical frozen analysis functions; no new inference.',
        'original_results_sha256': manifest['original_results_sha256'],
        'reference_models_sha256': sha(canonical(reference['models'])),
        'replayed_models_sha256': sha(canonical(models)),
        'comparison': {'passed': True, 'exact_equal': models == reference['models'], 'absolute_float_tolerance': 1e-12, 'max_absolute_difference': difference},
        'model_item_records': protocol['n_items']*len(protocol['models']), 'model_calls': 0, 'models': models}

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--bundle', type=Path, default=Path(__file__).resolve().parent)
    p.add_argument('--out', type=Path)
    p.add_argument('--verify-only', action='store_true')
    args = p.parse_args()
    root = args.bundle.resolve()
    if args.verify_only:
        m, _, _, pools = verify_bundle(root)
        print(json.dumps({'verified': True, 'status': m['status'], 'completed_pools': list(pools), 'model_calls': 0}))
    else:
        require(args.out is not None, '--out is required for numerical replay')
        require(not args.out.exists(), 'Refusing to overwrite replay output')
        result = replay(root)
        with args.out.open('x', encoding='utf-8') as f:
            f.write(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False)+'\n')
        print(json.dumps({'comparison': result['comparison'], 'model_item_records': result['model_item_records'], 'model_calls': 0}))

if __name__ == '__main__':
    main()
