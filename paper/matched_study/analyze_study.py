#!/usr/bin/env python3
"""Analyze a completed frozen matched study; standard library, no model calls.

The primary latency statistic is fixed by PROTOCOL.json: median over local
items of the mean within-item HTTP difference across all five repetitions.
"""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import json
import math
from pathlib import Path
import random

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
MODES = ('direct', 'one_token', 'json')
HISTORICAL_TEMPERATURE = 1.3489628825916533
BOOTSTRAP_SEED = 2026092061


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def mean(values):
    return math.fsum(values) / len(values) if values else None


def percentile(values, fraction):
    values = sorted(values)
    if not values:
        return None
    position = (len(values) - 1) * fraction
    lower = int(position)
    upper = min(lower + 1, len(values) - 1)
    return values[lower] + (values[upper] - values[lower]) * (position - lower)


def stats(values):
    return {'n': len(values), 'mean': mean(values), 'p50': percentile(values, .5), 'p95': percentile(values, .95),
            'min': min(values) if values else None, 'max': max(values) if values else None,
            'sum': math.fsum(values)}


def check(condition, message):
    if not condition:
        raise ValueError(message)


def finite(value):
    return type(value) in (int, float) and math.isfinite(value)


def probabilities(logits, temperature=1.):
    maximum = max(logits)
    weights = [math.exp((value - maximum) / temperature) for value in logits]
    denominator = math.fsum(weights)
    return [value / denominator for value in weights]


def nll(logits, index, temperature=1.):
    maximum = max(logits)
    return (maximum - logits[index]) / temperature + math.log(math.fsum(math.exp((value - maximum) / temperature) for value in logits))


def average_ranks(values):
    ordered = sorted(range(len(values)), key=lambda index: values[index])
    ranks = [0.] * len(values)
    start = 0
    while start < len(values):
        end = start + 1
        while end < len(values) and values[ordered[end]] == values[ordered[start]]:
            end += 1
        rank = (start + 1 + end) / 2
        for index in ordered[start:end]:
            ranks[index] = rank
        start = end
    return ranks


def correlation(a, b):
    if len(a) < 2 or len(a) != len(b):
        return None
    ma, mb = mean(a), mean(b)
    x, y = [value - ma for value in a], [value - mb for value in b]
    denominator = math.sqrt(math.fsum(value * value for value in x) * math.fsum(value * value for value in y))
    return math.fsum(i * j for i, j in zip(x, y)) / denominator if denominator else None


def regression(gold, predicted, total):
    check(len(gold) == len(predicted), 'regression length mismatch')
    errors = [estimate - target for target, estimate in zip(gold, predicted)]
    mae = mean([abs(value) for value in errors])
    return {'total': total, 'valid': len(gold), 'invalid': total - len(gold),
            'coverage': len(gold) / total if total else None,
            'mae': mae, 'normalized_mae_divided_by_5': mae / 5 if mae is not None else None,
            'rmse': math.sqrt(mean([value * value for value in errors])) if errors else None,
            'mean_signed_error': mean(errors), 'pearson': correlation(gold, predicted),
            'spearman_average_ranks': correlation(average_ranks(gold), average_ranks(predicted)),
            'scope': 'metrics conditional on valid predictions; total/invalid/coverage retained; continuous gold is never rounded'}


def valid_record(row):
    if row['http_status'] != 200 or 'error' in row.get('native', {}):
        return False
    answer, keys, native = row.get('answer', {}), row.get('keys', []), row.get('native', {})
    index = native.get('label_index')
    return (set(answer) == {'type', 'label'} and answer['type'] == row['type']
            and type(index) is int and 0 <= index < len(keys) and answer['label'] == keys[index])


def audit_probabilities(row):
    if row['mode'] == 'json' or not valid_record(row):
        return None
    values, logits, keys = row['native'].get('probabilities'), row['native'].get('logits'), row['keys']
    if not isinstance(logits, list) or not isinstance(values, list) or len(logits) != len(keys) or len(values) != len(keys):
        return None
    if not all(finite(value) for value in logits) or not all(finite(value) and 0 <= value <= 1 for value in values):
        return None
    if abs(math.fsum(values) - 1) > 1e-8:
        return None
    if max(abs(a - b) for a, b in zip(values, probabilities(logits))) > 1e-8:
        return None
    return logits


def classification(rows, labels):
    confusion = {label: {prediction: 0 for prediction in labels + ['INVALID']} for label in labels}
    valid = correct = 0
    for row in rows:
        gold = row['label']
        check(gold in labels, 'unknown categorical gold')
        prediction = row['answer'].get('label') if valid_record(row) else None
        if prediction not in labels:
            prediction = 'INVALID'
        else:
            valid += 1
        confusion[gold][prediction] += 1
        correct += prediction == gold
    per_label = {}
    for label in labels:
        tp = confusion[label][label]
        support = sum(confusion[label].values())
        predicted = sum(confusion[gold][label] for gold in labels)
        precision = tp / predicted if predicted else 0.
        recall = tp / support if support else None
        f1 = 2 * tp / (support + predicted) if support + predicted else None
        per_label[label] = {'support': support, 'predicted': predicted, 'precision': precision,
                            'recall': recall, 'f1': f1}
    result = {'total': len(rows), 'valid': valid, 'invalid': len(rows) - valid, 'correct': correct,
              'accuracy': correct / len(rows) if rows else None,
              'balanced_accuracy': mean([item['recall'] for item in per_label.values() if item['recall'] is not None]),
              'macro_f1': mean([item['f1'] for item in per_label.values() if item['f1'] is not None]),
              'per_label': per_label, 'confusion': confusion,
              'invalid_policy': 'invalid outputs are errors in accuracy and false negatives in recall/F1; MCC is null if any output invalid'}
    if labels == ['false', 'true']:
        tn, fp = confusion['false']['false'], confusion['false']['true']
        fn, tp = confusion['true']['false'], confusion['true']['true']
        denominator = math.sqrt((tp + fp) * (tp + fn) * (tn + fp) * (tn + fn))
        result['mcc'] = (tp * tn - fp * fn) / denominator if denominator and valid == len(rows) else None
        result['mcc_null_reason'] = ('invalid_outputs' if valid != len(rows) else 'zero_denominator' if not denominator else None)
    return result


def probability_quality(rows, temperature):
    members = [row for row in rows if audit_probabilities(row) is not None]
    if not members:
        return {'total': len(rows), 'valid': 0, 'coverage': 0., 'temperature': temperature,
                'unavailable': 'no audited classification distributions; never computed for JSON'}
    log_losses, brier, binary, bins = [], [], [], [[] for _ in range(10)]
    for row in members:
        keys, logits = row['keys'], row['native']['logits']
        p = probabilities(logits, temperature)
        index = keys.index(row['label'])
        log_losses.append(nll(logits, index, temperature))
        brier.append(math.fsum((value - float(i == index)) ** 2 for i, value in enumerate(p)))
        # The actual tied decision can differ between native sampler and direct
        # candidate-order argmax. ECE evaluates the decision actually returned.
        bins[min(9, int(max(p) * 10))].append((max(p), row['answer']['label'] == row['label']))
        if set(keys) == {'false', 'true'}:
            binary.append((p[keys.index('true')] - float(row['label'] == 'true')) ** 2)
    reliability = [{'lower': i / 10, 'upper': (i + 1) / 10, 'count': len(values),
                    'mean_confidence': mean([p for p, _ in values]),
                    'accuracy': mean([correct for _, correct in values])} for i, values in enumerate(bins)]
    ece = math.fsum(item['count'] / len(members) * abs(item['mean_confidence'] - item['accuracy']) for item in reliability if item['count'])
    return {'total': len(rows), 'valid': len(members), 'coverage': len(members) / len(rows), 'temperature': temperature,
            'nll_logsumexp': mean(log_losses), 'brier_multiclass_sum': mean(brier),
            'brier_binary_true': mean(binary), 'ece_10_equal_width': ece, 'reliability_bins': reliability,
            'semantics': 'conditional probabilities over allowed candidates; not guaranteed correctness or domain calibration'}


def constant_true_baseline(rows):
    # Gold counts alone define this unfitted comparator, independent of model outputs.
    synthetic = [{'label': row['label'], 'type': 'noul', 'http_status': 200,
                  'answer': {'type': 'noul', 'label': 'true'}, 'keys': ['false', 'true'],
                  'native': {'label_index': 1}} for row in rows]
    return {**classification(synthetic, ['false', 'true']), 'prediction': 'true',
            'scope': 'constant unfitted descriptive comparator; one gold observation per item'}


def score_quality(rows, mode):
    total = len(rows)
    valid = [row for row in rows if valid_record(row) and row['answer']['label'] in row.get('keys', [])]
    gold = [row['gold_score'] for row in valid]
    selected = [float(row['answer']['label']) for row in valid]
    result = {'hard_selected_stage': regression(gold, selected, total)}
    if mode != 'json':
        prob_rows = [row for row in rows if audit_probabilities(row) is not None]
        result['expected_score'] = {}
        for name, temperature in (('t1', 1.), ('historical_temperature', HISTORICAL_TEMPERATURE)):
            expected = [math.fsum(float(key) * p for key, p in zip(row['keys'], probabilities(row['native']['logits'], temperature))) for row in prob_rows]
            result['expected_score'][name] = {**regression([row['gold_score'] for row in prob_rows], expected, total), 'temperature': temperature}
    else:
        result['expected_score'] = None
        result['probability_note'] = 'JSON has no model probability vector; no expected-probability metric or categorical NLL/Brier is assigned'
    return result


def quality(rows, dataset, mode):
    if dataset == 'JSTS':
        check(all('gold_score' in row and 'label' not in row for row in rows), 'JSTS must have continuous gold only')
        return score_quality(rows, mode)
    labels = ['false', 'true'] if dataset == 'JCoLA' else ['option_' + str(i) for i in range(5)]
    result = classification(rows, labels)
    result['probability_metrics'] = ({name: probability_quality(rows, temperature) for name, temperature in
                                    (('t1', 1.), ('historical_temperature', HISTORICAL_TEMPERATURE))} if mode != 'json' else None)
    if mode == 'json':
        result['probability_note'] = 'No model probability vector; probability metrics deliberately unavailable'
    return result


def local_quality(rows):
    result = {}
    for mode in MODES:
        selected = [row for row in rows if row['mode'] == mode and row['repetition'] == 0]
        result[mode] = {}
        for kind in ('all', 'choice', 'noul', 'score'):
            group = selected if kind == 'all' else [row for row in selected if row['type'] == kind]
            correct = sum(valid_record(row) and row['answer']['label'] == row['label'] for row in group)
            result[mode][kind] = {'n': len(group), 'valid': sum(valid_record(row) for row in group),
                                  'correct': correct, 'accuracy': correct / len(group) if group else None}
    return result


def latency_tables(rows):
    result, phases = {}, []
    for dataset in ('local_v2', 'JCoLA', 'JSTS', 'JCommonsenseQA'):
        result[dataset] = {}
        for mode in MODES:
            group = [row for row in rows if row['dataset'] == dataset and row['mode'] == mode]
            native = [row['native'] for row in group]
            item = {'requests': len(group), 'http_ms': stats([row['http_ms'] for row in group]),
                    'server_ms': stats([row['server_ms'] for row in group]),
                    'invalid_or_failed': sum(not valid_record(row) for row in group),
                    'http_status_counts': dict(Counter(str(row['http_status']) for row in group)),
                    'request_bytes': stats([row['request_bytes'] for row in group]),
                    'input_tokens': stats([row['input_tokens'] for row in native if 'input_tokens' in row]),
                    'output_tokens': stats([row['output_tokens'] for row in native if 'output_tokens' in row]),
                    'decode_count': stats([row['decode_count'] for row in native if 'decode_count' in row]),
                    'phase_ms': {}}
            for phase in sorted({key for row in native for key in row.get('timing_ms', {})}):
                values = [row['timing_ms'][phase] for row in native if phase in row.get('timing_ms', {})]
                item['phase_ms'][phase] = stats(values)
                phases.append({'dataset': dataset, 'mode': mode, 'phase': phase, **stats(values)})
            result[dataset][mode] = item
    return result, phases


def pair_items(rows):
    groups = defaultdict(dict)
    for row in rows:
        check((row['mode'], row['repetition']) not in groups[row['id']], 'duplicate within-item condition')
        groups[row['id']][(row['mode'], row['repetition'])] = row
    paired = []
    for identifier, group in sorted(groups.items()):
        reference = next(iter(group.values()))
        expected = 5 if reference['dataset'] == 'local_v2' else 1
        check(set(group) == {(mode, repetition) for mode in MODES for repetition in range(expected)}, 'incomplete within-item pairing')
        item = {key: reference[key] for key in ('id', 'dataset', 'type', 'group')}
        item['repetitions'] = expected
        for mode in MODES:
            values = [group[(mode, repetition)]['http_ms'] for repetition in range(expected)]
            item[mode + '_mean_http_ms'] = mean(values)
        item['one_token_minus_direct_ms'] = item['one_token_mean_http_ms'] - item['direct_mean_http_ms']
        item['json_minus_direct_ms'] = item['json_mean_http_ms'] - item['direct_mean_http_ms']
        item['all_conditions_valid'] = all(valid_record(row) for row in group.values())
        paired.append(item)
    return paired


def grouped_bootstrap(local_items, replicates=10000, seed=BOOTSTRAP_SEED):
    check(bool(local_items) and replicates > 0, 'bootstrap needs observed groups and positive replicates')
    groups = defaultdict(list)
    for item in local_items:
        groups[item['group']].append(item)
    names = sorted(groups)
    keys = ('one_token_minus_direct_ms', 'json_minus_direct_ms')
    rng = random.Random(seed)
    draws = {key: [] for key in keys}
    for _ in range(replicates):
        members = [item for _ in names for item in groups[names[rng.randrange(len(names))]]]
        for key in keys:
            draws[key].append(percentile([item[key] for item in members], .5))
    return {'unit': 'whole observed family/tag, every selected item and all five repetitions retained',
            'group_count': len(names), 'item_count': len(local_items),
            'group_sizes': dict(sorted((name, len(items)) for name, items in groups.items())),
            'replicates': replicates, 'seed': seed,
            'estimand': 'median over items of mean within-item HTTP latency difference; not difference of marginal medians',
            'interval_scope': 'conditional percentile sensitivity to observed family/tag composition; one session/hardware/runtime; not population coverage guarantee',
            'assumptions': 'observed families/tags treated exchangeable; cross-group dependence and temporal/thermal/session uncertainty not modeled',
            'comparisons': {key: {'estimate_ms': percentile([item[key] for item in local_items], .5),
                                 'mean_item_difference_ms': mean([item[key] for item in local_items]),
                                 'percentile_95_low_ms': percentile(values, .025), 'percentile_95_high_ms': percentile(values, .975)} for key, values in draws.items()}}


def parity_audit(rows):
    groups = defaultdict(dict)
    for row in rows:
        groups[(row['id'], row['repetition'])][row['mode']] = row
    detail = []
    for (identifier, repetition), group in sorted(groups.items()):
        a, b = group['direct'], group['one_token']
        na, nb = a['native'], b['native']
        valid = valid_record(a) and valid_record(b)
        pa, pb = audit_probabilities(a), audit_probabilities(b)
        logits_comparable = pa is not None and pb is not None and len(pa) == len(pb)
        difference = max(abs(x - y) for x, y in zip(pa, pb)) if logits_comparable else None
        maximum_tie = (sum(value == max(pa) for value in pa) > 1 or sum(value == max(pb) for value in pb) > 1) if logits_comparable else False
        same_label = valid and a['answer']['label'] == b['answer']['label']
        item = {'id': identifier, 'dataset': a['dataset'], 'repetition': repetition, 'both_valid': valid,
                'same_prompt_sha256': na.get('prompt_sha256') is not None and na.get('prompt_sha256') == nb.get('prompt_sha256'),
                'same_input_token_sha256': na.get('input_token_ids_sha256') is not None and na.get('input_token_ids_sha256') == nb.get('input_token_ids_sha256'),
                'same_candidate_ids': na.get('candidate_ids') is not None and na.get('candidate_ids') == nb.get('candidate_ids'),
                'same_candidate_ids_sha256': na.get('candidate_ids_sha256') is not None and na.get('candidate_ids_sha256') == nb.get('candidate_ids_sha256'),
                'same_input_token_count': na.get('input_tokens') is not None and na.get('input_tokens') == nb.get('input_tokens'),
                'max_logit_abs_difference': difference,
                'logits_within_1e_5': difference is not None and difference <= 1e-5,
                'same_label': same_label, 'exact_maximum_tie': maximum_tie,
                'label_mismatch_with_tie': valid and not same_label and maximum_tie,
                'label_mismatch_without_tie': valid and not same_label and not maximum_tie,
                'candidate_boundary_checked_both': na.get('candidate_boundary_checked') is True and nb.get('candidate_boundary_checked') is True}
        detail.append(item)
    booleans = [key for key in detail[0] if isinstance(detail[0][key], bool)]
    summary = {'pairs': len(detail), 'counts_true': {key: sum(row[key] for row in detail) for key in booleans},
               'max_logit_abs_difference': max((row['max_logit_abs_difference'] for row in detail if row['max_logit_abs_difference'] is not None), default=None),
               'logit_comparison_coverage': sum(row['max_logit_abs_difference'] is not None for row in detail) / len(detail),
               'tolerance': 1e-5, 'tie_policy': 'direct first candidate order; one_token native lowest vocabulary token ID'}
    return summary, detail


def repeated_stability(rows):
    groups = defaultdict(list)
    for row in rows:
        groups[(row['id'], row['mode'])].append(row)
    result = {}
    for mode in MODES:
        stable = invalid = changed = 0
        logit_range = []
        for (_, item_mode), members in groups.items():
            if item_mode != mode:
                continue
            if not all(valid_record(row) for row in members):
                invalid += 1
            elif len({row['answer']['label'] for row in members}) == 1:
                stable += 1
            else:
                changed += 1
            if mode != 'json' and all(audit_probabilities(row) is not None for row in members):
                vectors = [row['native']['logits'] for row in members]
                logit_range.append(max(max(values) - min(values) for values in zip(*vectors)))
        result[mode] = {'items': stable + invalid + changed, 'stable_label_all_5_repetitions': stable,
                        'changed_label': changed, 'invalid_in_any_repetition': invalid,
                        'max_within_item_logit_range': max(logit_range) if logit_range else None,
                        'note': 'repeatability, not five times as many independent quality examples'}
    return result


def paired_external(rows):
    result = {}
    by_item = defaultdict(dict)
    for row in rows:
        by_item[row['id']][row['mode']] = row
    for dataset in ('JCoLA', 'JSTS', 'JCommonsenseQA'):
        result[dataset] = {}
        pairs = [modes for modes in by_item.values() if modes['direct']['dataset'] == dataset]
        for mode in ('one_token', 'json'):
            a, b = [pair['direct'] for pair in pairs], [pair[mode] for pair in pairs]
            if dataset == 'JSTS':
                selected = [(x, y) for x, y in zip(a, b) if valid_record(x) and valid_record(y)]
                differences = [abs(float(y['answer']['label']) - x['gold_score']) - abs(float(x['answer']['label']) - x['gold_score']) for x, y in selected]
                probability_comparison = None
                if mode != 'json':
                    prob_pairs = [(x, y) for x, y in zip(a, b) if audit_probabilities(x) is not None and audit_probabilities(y) is not None]
                    probability_comparison = {}
                    for name, temperature in (('t1', 1.), ('historical_temperature', HISTORICAL_TEMPERATURE)):
                        deltas = []
                        for x, y in prob_pairs:
                            expected_a = math.fsum(float(key) * p for key, p in zip(x['keys'], probabilities(x['native']['logits'], temperature)))
                            expected_b = math.fsum(float(key) * p for key, p in zip(y['keys'], probabilities(y['native']['logits'], temperature)))
                            deltas.append(abs(expected_b - x['gold_score']) - abs(expected_a - x['gold_score']))
                        probability_comparison[name] = {'mae_difference': mean(deltas), 'paired_valid': len(prob_pairs),
                            'paired_total': len(pairs), 'coverage': len(prob_pairs) / len(pairs) if pairs else None}
                result[dataset][mode + '_minus_direct'] = {'paired_total': len(pairs), 'paired_valid': len(selected),
                    'coverage': len(selected) / len(pairs) if pairs else None, 'hard_stage_mae_difference': mean(differences),
                    'expected_score_mae_difference': probability_comparison,
                    'note': 'descriptive paired hard-stage error difference; no rounded gold and no IID confidence interval'}
            else:
                correct_a = [valid_record(x) and x['answer']['label'] == x['label'] for x in a]
                correct_b = [valid_record(x) and x['answer']['label'] == x['label'] for x in b]
                result[dataset][mode + '_minus_direct'] = {'n': len(pairs),
                    'both_correct': sum(x and y for x, y in zip(correct_a, correct_b)),
                    'both_wrong_or_invalid': sum(not x and not y for x, y in zip(correct_a, correct_b)),
                    'direct_only_correct': sum(x and not y for x, y in zip(correct_a, correct_b)),
                    'comparator_only_correct': sum(not x and y for x, y in zip(correct_a, correct_b)),
                    'accuracy_difference': (sum(correct_b) - sum(correct_a)) / len(pairs) if pairs else None,
                    'note': 'descriptive paired comparison; invalid decisions retained as errors; no IID confidence interval'}
    return result


def load_completed():
    completion_path = HERE / 'results' / 'COMPLETION.json'
    check(completion_path.is_file(), 'COMPLETION.json is absent; do not analyze an unfinished study')
    paths = {'protocol': HERE / 'PROTOCOL.json', 'freeze': HERE / 'preparation/FREEZE.json',
             'selection': HERE / 'preparation/SELECTION.json', 'schedule': HERE / 'preparation/SCHEDULE.json',
             'run_manifest': HERE / 'results/RUN_MANIFEST.json', 'warmup': HERE / 'results/warmup.jsonl',
             'predictions': HERE / 'results/predictions.jsonl', 'completion': completion_path,
             'external_overlap_audit': ROOT / 'paper/external_expanded/AUDIT.json'}
    raw = {name: path.read_bytes() for name, path in paths.items()}
    objects = {name: json.loads(value) for name, value in raw.items() if name not in ('warmup', 'predictions')}
    rows = [json.loads(line) for line in raw['predictions'].splitlines() if line.strip()]
    warmup = [json.loads(line) for line in raw['warmup'].splitlines() if line.strip()]
    completion, freeze, schedule, selection, manifest = [objects[name] for name in ('completion', 'freeze', 'schedule', 'selection', 'run_manifest')]
    check(sha(raw['predictions']) == completion['predictions_sha256'], 'completion prediction hash mismatch')
    check(sha(raw['freeze']) == manifest['freeze_sha256'], 'run freeze hash mismatch')
    check(sha(canonical(selection).encode()) == freeze['selection_sha256'], 'selection hash mismatch')
    check(sha(canonical(schedule).encode()) == freeze['schedule_sha256'], 'schedule hash mismatch')
    check(sha(raw['protocol']) == freeze['sha256']['protocol'], 'protocol changed')
    check(objects['protocol'] == freeze['protocol'], 'frozen protocol mismatch')
    for name, path in {'runner': HERE / 'run_study.py', 'native_engine': ROOT / 'native_engine.py',
                       'helper_source': ROOT / 'paper/matched_native/llama_matched_helper.cpp',
                       'expanded_protocol': ROOT / 'paper/external_expanded/PROTOCOL.json',
                       'expanded_selection': ROOT / 'paper/external_expanded/SELECTION.json',
                       'expanded_preparation': ROOT / 'paper/external_expanded/PREPARATION.json',
                       'local_questions': ROOT / 'acceptance-v2/questions_2400.jsonl'}.items():
        check(sha(path.read_bytes()) == freeze['sha256'][name], 'frozen source changed: ' + name)
    check(len(rows) == len(schedule) == completion['measured_calls'] == objects['protocol']['measured_requests'] == 4050, 'measured count mismatch')
    check(len(selection) == 750 and len(warmup) == completion['warmup_calls'] == 21, 'item/warmup count mismatch')
    index = {row['id']: row for row in selection}
    check(len(index) == len(selection), 'duplicate selection IDs')
    invariant_failures = []
    counter = manifest['helper_ready']['total_decode_count']
    all_trace_rows = [row['audit']['native'] for row in warmup] + [row['native'] for row in rows]
    missing_counter = 0
    for native in all_trace_rows:
        if 'decode_count' not in native or 'total_decode_count' not in native:
            missing_counter += 1
            continue
        counter += native['decode_count']
        check(counter == native['total_decode_count'], 'decode counter progression mismatch')
    for position, (row, planned) in enumerate(zip(rows, schedule)):
        check(all(row[key] == value for key, value in planned.items()), 'row differs from frozen schedule')
        check(all(row[key] == value for key, value in index[row['id']].items()), 'row metadata differs from frozen selection')
        check(row['request_id'] == position + 22 and row['native']['id'] == row['request_id'], 'request ID mismatch')
        # The helper's error schema contains id/error/counters, but no mode.
        if 'error' not in row['native']:
            check(row['native'].get('mode') == row['mode'], 'native mode mismatch')
        check(finite(row['http_ms']) and row['http_ms'] >= 0 and finite(row['server_ms']) and row['server_ms'] >= 0, 'invalid timing')
        for phase, value in row['native'].get('timing_ms', {}).items():
            check(finite(value) and value >= 0, 'invalid native phase timing: ' + phase)
        if valid_record(row):
            native = row['native']
            checks = {'state_cleared': native.get('state_cleared') is True,
                      'thinking_disabled': native.get('thinking_enabled') is False,
                      'generated_count': native.get('output_tokens') == len(native.get('generated_token_ids', []))}
            if row['mode'] == 'direct':
                checks.update(output_zero=native.get('output_tokens') == 0, decode_one=native.get('decode_count') == 1,
                              probability_vector_valid=audit_probabilities(row) is not None)
            elif row['mode'] == 'one_token':
                checks.update(output_one=native.get('output_tokens') == 1, decode_one=native.get('decode_count') == 1,
                              probability_vector_valid=audit_probabilities(row) is not None,
                              sampled_allowed_token=native.get('generated_token_ids') == [native['candidate_ids'][native['label_index']]])
            else:
                try:
                    parsed = json.loads(native['generated_text'])
                    json_valid = isinstance(parsed, dict) and set(parsed) == {'answer'} and str(parsed['answer']) == native['answer']
                except (ValueError, KeyError, TypeError):
                    json_valid = False
                checks.update(actual_json_valid=json_valid, probability_vector_absent=native.get('probabilities') is None and native.get('logits') is None,
                              bounded_generation=0 < native.get('output_tokens', 0) <= 32,
                              decode_matches_emitted_tokens=native.get('decode_count') == native.get('output_tokens'))
            for check_name, valid in checks.items():
                if not valid:
                    invariant_failures.append({'id': row['id'], 'mode': row['mode'], 'repetition': row['repetition'], 'check': check_name})
    check(dict(Counter(row['mode'] for row in rows)) == completion['counts'], 'mode counts mismatch')
    check(sum(row['http_status'] != 200 for row in rows) == completion['failures'], 'failure count mismatch')
    coverage = {'measured_requests': len(rows), 'unique_items': len(index), 'warmup_requests': len(warmup),
                'mode_counts': dict(Counter(row['mode'] for row in rows)),
                'dataset_counts': dict(Counter(row['dataset'] for row in rows)),
                'http_failures': completion['failures'], 'invalid_or_failed_records': sum(not valid_record(row) for row in rows),
                'native_trace_invariant_failures': invariant_failures,
                'missing_decode_counters': missing_counter, 'final_native_decode_counter': counter,
                'measured_decode_count': sum(row['native'].get('decode_count', 0) for row in rows),
                'warmup_decode_count': sum(row['audit']['native'].get('decode_count', 0) for row in warmup),
                'full_scheduled_data_retained': True, 'hash_and_order_verification': True}
    provenance = {name: {'path': path.relative_to(ROOT).as_posix(), 'sha256': sha(raw[name]), 'bytes': len(raw[name])} for name, path in paths.items()}
    return rows, objects, provenance, coverage


def write_csv(path, records):
    if not records:
        return
    with path.open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(records[0]))
        writer.writeheader(); writer.writerows(records)


def number(value, digits=4):
    return 'unavailable' if value is None else f'{value:.{digits}f}'


def render(summary):
    primary = summary['local_group_bootstrap']['comparisons']
    lines = ['# Matched readout study: completed-run analysis', '',
             'This is an analysis of a locally frozen, single-machine experiment. No model is rerun and no prompt, sample, or temperature is selected by this script.', '',
             '## Main systems result', '',
             'The primary comparison keeps the complete direct/one-token model prefix and candidate tokens identical. '
             'For each of the 150 published local regression items, average complete loopback HTTP latency over its five repetitions, '
             'then compute the within-item condition difference. The primary statistic is the median of those 150 item differences, '
             '**not** a difference of marginal medians. Positive values mean the comparator is slower.', '',
             '| Comparator minus direct | Median item-mean HTTP difference | Conditional 95% family/tag percentile interval |', '|---|---:|---:|']
    for name, values in primary.items():
        lines.append(f"| {name} | {values['estimate_ms']:+.4f} ms | [{values['percentile_95_low_ms']:+.4f}, {values['percentile_95_high_ms']:+.4f}] ms |")
    lines += ['', f"The bootstrap draws {summary['local_group_bootstrap']['group_count']} whole observed family/tag clusters with replacement "
              f"for {summary['local_group_bootstrap']['replicates']:,} replicates, seed {summary['local_group_bootstrap']['seed']}. "
              'Every selected item and all its repetitions/paired conditions stay together. Clusters are treated as exchangeable; '
              'manual AI-authored tags and generated families differ in size. Intervals describe sensitivity to this observed cluster mix, '
              'conditional on this model, machine, software, selected items, schedule, and session. They do not capture independent-session, '
              'thermal, between-machine, or unmeasured cross-family dependence, and are not hardware-population coverage guarantees.', '',
              'JSON uses a serialization-specific prompt and actually emits a grammar-constrained JSON object. Its comparison includes prompt/prefill '
              'and multi-token-generation differences, not isolated sampling overhead. All three measured HTTP responses carry the same '
              '`type` and semantic `label` schema. Native audit serialization, helper-pipe transfer, and Python parsing occur inside the HTTP interval; '
              'only the server-side trace-file write occurs after client timing. This comparison therefore includes audit/runtime overhead and is '
              'not a pure sampler-overhead measurement.', '',
              '## Accounting and parity', '',
              f"All {summary['accounting']['measured_requests']:,} scheduled requests and {summary['accounting']['unique_items']} unique items are retained; "
              f"{summary['accounting']['warmup_requests']} synthetic warm-up requests are excluded from measured latencies. "
              f"HTTP failures: {summary['accounting']['http_failures']}; invalid/failed records: {summary['accounting']['invalid_or_failed_records']}; "
              f"native trace invariant findings: {len(summary['accounting']['native_trace_invariant_failures'])}. "
              f"Measured llama_decode API calls: {summary['accounting']['measured_decode_count']:,}; warm-up calls: {summary['accounting']['warmup_decode_count']}.", '',
              f"There are {summary['parity']['pairs']:,} paired direct/one-token observations. Maximum candidate-logit absolute difference is "
              f"{number(summary['parity']['max_logit_abs_difference'], 10)}; tolerance is 1e-5. "
              f"Prompt-hash matches: {summary['parity']['counts_true']['same_prompt_sha256']}; token-hash matches: {summary['parity']['counts_true']['same_input_token_sha256']}; "
              f"candidate-ID matches: {summary['parity']['counts_true']['same_candidate_ids']}; label matches: {summary['parity']['counts_true']['same_label']}. "
              f"Exact maximum-logit ties: {summary['parity']['counts_true']['exact_maximum_tie']}; mismatches with a tie: "
              f"{summary['parity']['counts_true']['label_mismatch_with_tie']}; mismatches without a tie: {summary['parity']['counts_true']['label_mismatch_without_tie']}.", '',
              'Direct uses candidate-order tie breaking; native one-token greedy sampling uses lowest vocabulary-token ID. '
              'Ties and any parity violation remain in the data. Detailed pair checks are in `parity.csv`.', '',
              '## Complete HTTP latency', '',
              'All scheduled requests, including failures, contribute to these descriptive request-level summaries. Local counts include five '
              'repetitions; external counts include one. These marginal p50/p95 values are not the paired primary estimand. '
              'Native phase timings, tokens, output tokens, decode counts, and data coverage are in SUMMARY.json and the CSV tables.', '',
              '| Dataset | Mode | Requests | Mean ms | p50 ms | p95 ms | Output tokens, total | Decode calls, total |', '|---|---|---:|---:|---:|---:|---:|---:|']
    for dataset, modes in summary['latency'].items():
        for mode, values in modes.items():
            lat = values['http_ms']
            lines.append(f"| {dataset} | {mode} | {values['requests']} | {lat['mean']:.3f} | {lat['p50']:.3f} | {lat['p95']:.3f} | {values['output_tokens']['sum']:.0f} | {values['decode_count']['sum']:.0f} |")
    lines += ['', '## Local quality and repeatability', '',
              'The 150 local questions are previously published development/regression material, selected by an outcome-independent ID hash. '
              'Quality below uses repetition 0 only. Repeated stability is reported separately and does not create 750 independent quality examples.', '',
              '| Mode | First-repetition correct / 150 | Choice / 50 | Noul / 50 | Score top-stage / 50 | Stable label across 5 repeats |', '|---|---:|---:|---:|---:|---:|']
    for mode, values in summary['local_quality_first_repetition'].items():
        stable = summary['local_repeated_stability'][mode]
        lines.append(f"| {mode} | {values['all']['correct']} | {values['choice']['correct']} | {values['noul']['correct']} | {values['score']['correct']} | {stable['stable_label_all_5_repetitions']} / {stable['items']} |")
    lines += ['', '## External task-specific quality', '',
              'The 600 external public-development questions were fixed before inference. Model pretraining/post-training exposure is unknown. '
              'These tasks are not pooled into one accuracy. JCoLA domain names refer to original literature-source splits, not verified unseen model domains. '
              'JSTS has six rows sharing text/images with the earlier JNLI pilot, including three identical ordered sentence pairs; this overlap was '
              'recorded before inference and no examples were replaced. Semantic/source groups are dependence proxies, not proof of independence.', '',
              '### JCoLA: binary grammatical acceptability', '',
              'MCC is primary; a zero denominator is reported as null. An always-true rule gets 158/200 = 79% accuracy on the fixed sample '
              '(88/100 in-domain and 70/100 out-of-domain), balanced accuracy 0.5, and undefined MCC. It is a descriptive constant baseline, '
              'not a fitted system. Confusion matrices, recall/F1, and split-wise results are retained below/in SUMMARY.json.', '',
              '| Split | Mode | Accuracy | Balanced accuracy | Macro F1 | MCC |', '|---|---|---:|---:|---:|---:|']
    for split, modes in summary['external_quality']['JCoLA'].items():
        for mode, values in modes.items():
            lines.append(f"| {split} | {mode} | {number(values['accuracy'])} | {number(values['balanced_accuracy'])} | {number(values['macro_f1'])} | {number(values['mcc'])} |")
    lines += ['', '### JCommonsenseQA: five-way choice', '', '| Mode | Correct / 200 | Accuracy | Macro F1 |', '|---|---:|---:|---:|']
    for mode, values in summary['external_quality']['JCommonsenseQA']['all'].items():
        lines.append(f"| {mode} | {values['correct']} | {number(values['accuracy'])} | {number(values['macro_f1'])} |")
    lines += ['', '### JSTS: continuous semantic similarity', '',
              'Original fractional gold scores remain in [0,5]. Primary MAE compares the probability-weighted expected stage with this continuous '
              'gold. Native one-token probability audits support the same calculation without another model call. JSON has no comparable probability '
              'vector; its expectation/NLL/Brier are deliberately unavailable. The hard-selected stage is compared with the same continuous gold '
              'for **all three modes** as a separate like-for-like secondary measure. No rounded gold stage or classification accuracy is invented.', '',
              '| Mode / prediction | T | Valid / 200 | MAE | RMSE | Pearson | Spearman | MAE / 5 |', '|---|---:|---:|---:|---:|---:|---:|---:|']
    for mode, values in summary['external_quality']['JSTS']['all'].items():
        entries = [('hard stage', None, values['hard_selected_stage'])]
        if values['expected_score']:
            entries.extend((name, value['temperature'], value) for name, value in values['expected_score'].items())
        for name, temperature, value in entries:
            lines.append(f"| {mode} / {name} | {number(temperature, 3)} | {value['valid']} | {number(value['mae'])} | {number(value['rmse'])} | {number(value['pearson'])} | {number(value['spearman_average_ranks'])} | {number(value['normalized_mae_divided_by_5'])} |")
    lines += ['', 'Every metric states its valid-prediction coverage. Invalid outputs remain in accounting; numerical regression metrics are conditional '
              'on valid predictions, never silently assigned an arbitrary score. Categorical accuracy counts invalid outputs as errors. No external '
              'IID confidence intervals or full-benchmark/leaderboard claims are made.', '',
              '### Probability transfer', '',
              'Primary T=1 and the historical T=1.3489628825916533 are applied to the same audit logits. The historical scalar was fitted on the '
              'earlier self-authored calibration set, never on this external sample. Positive temperature preserves labels; changes below do not '
              'establish calibrated probabilities in new domains. NLL uses stable log-sum-exp. Brier sums squared errors over classes; JCoLA also '
              'records the binary true-class form. ECE uses ten equal-width maximum-probability bins.', '',
              '| Dataset / split | Mode | T | NLL | Brier sum | ECE | Coverage |', '|---|---|---:|---:|---:|---:|---:|']
    for dataset in ('JCoLA', 'JCommonsenseQA'):
        for split, modes in summary['external_quality'][dataset].items():
            for mode, values in modes.items():
                for condition, metrics in (values['probability_metrics'] or {}).items():
                    lines.append(f"| {dataset} / {split} | {mode} | {metrics['temperature']:.3f} | {number(metrics.get('nll_logsumexp'))} | {number(metrics.get('brier_multiclass_sum'))} | {number(metrics.get('ece_10_equal_width'))} | {metrics['coverage']:.3f} |")
    lines += ['', 'Paired external changes and discordant classifications are in SUMMARY.json. They are descriptive comparisons on the same items, '
              'not additional independent datasets. Differences for JSON mix readout, completion work, and its serialization-specific prompt.', '',
              '## Reproduction and files', '', '```bash', 'python3 paper/matched_study/analyze_study.py',
              'python3 -m unittest discover -s paper/matched_study -p test_matched_analysis.py -v', '```', '',
              'Python standard library only. The script refuses incomplete runs, verifies completion/selection/schedule/frozen-source hashes, '
              'and checks request ordering and native counters. `SUMMARY.json` records exact input hashes and this analysis script hash. '
              'Derived outputs are overwritten deterministically; protocol, preparation, and results files remain read-only.', '',
              '- `item_latency.csv`: all 750 item-level paired means/differences, with local repetitions retained.',
              '- `latency.csv` and `native_phases.csv`: request-level descriptive latency/token/phase summaries.',
              '- `parity.csv`: every direct/one-token pair, including ties and violations.',
              '- `external_metrics.csv`: task-specific classification/regression/probability metrics and coverage.',
              '- `SUMMARY.json`: full confusion matrices, probability reliability bins, pairing, repeatability, and provenance.', '',
              'The study uses one model, one hardware configuration, one session, a research HTTP server, and a limited public sample. '
              'It is not a production SLA, a comparison with TypeSafe Jev, evidence that zero generated tokens always yields a material speedup, '
              'or proof of new learning-method novelty. Any additional matched model, domain, or independent-session results require separate measurements.', '']
    return '\n'.join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--replicates', type=int, default=10000)
    parser.add_argument('--seed', type=int, default=BOOTSTRAP_SEED)
    args = parser.parse_args(argv)
    check(args.replicates >= 100, 'at least 100 bootstrap replicates required')
    rows, objects, provenance, accounting = load_completed()
    latency, phases = latency_tables(rows)
    items = pair_items(rows)
    local_items = [item for item in items if item['dataset'] == 'local_v2']
    bootstrap = grouped_bootstrap(local_items, args.replicates, args.seed)
    local = [row for row in rows if row['dataset'] == 'local_v2']
    external = [row for row in rows if row['dataset'] != 'local_v2']
    parity, parity_rows = parity_audit(rows)
    external_quality = {}
    for dataset in ('JCoLA', 'JSTS', 'JCommonsenseQA'):
        members = [row for row in external if row['dataset'] == dataset]
        splits = ['all'] + (['in_domain_valid', 'out_of_domain_valid'] if dataset == 'JCoLA' else [])
        external_quality[dataset] = {split: {mode: quality([row for row in members if row['mode'] == mode and (split == 'all' or row['split'] == split)], dataset, mode) for mode in MODES} for split in splits}
    cola_reference = [row for row in external if row['dataset'] == 'JCoLA' and row['mode'] == 'direct']
    cola_baseline = {split: constant_true_baseline([row for row in cola_reference if split == 'all' or row['split'] == split])
                     for split in ('all', 'in_domain_valid', 'out_of_domain_valid')}
    summary = {'schema_version': 1, 'analysis_script_sha256': sha(Path(__file__).read_bytes()), 'input_provenance': provenance,
               'accounting': accounting, 'local_group_bootstrap': bootstrap, 'latency': latency, 'parity': parity,
               'local_quality_first_repetition': local_quality(local), 'local_repeated_stability': repeated_stability(local),
               'external_quality': external_quality, 'external_paired_comparisons': paired_external(external),
               'JCoLA_constant_true_baseline': cola_baseline,
               'external_overlap_audit': objects['external_overlap_audit'],
               'scope': 'single frozen matched session; descriptive external transfer; conditional observed-group bootstrap; no pooled dataset accuracy',
               'temperature_primary': 1., 'temperature_historical_secondary': HISTORICAL_TEMPERATURE,
               'json_probability_metrics': 'unavailable; deliberately not inferred from generated hard labels'}
    (HERE / 'SUMMARY.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2, allow_nan=False) + '\n')
    (HERE / 'REPORT.md').write_text(render(summary), encoding='utf-8')
    write_csv(HERE / 'item_latency.csv', items)
    write_csv(HERE / 'native_phases.csv', phases)
    write_csv(HERE / 'parity.csv', parity_rows)
    latency_rows = []
    for dataset, modes in latency.items():
        for mode, item in modes.items():
            latency_rows.append({'dataset': dataset, 'mode': mode, 'requests': item['requests'],
                                 **{'http_' + key: item['http_ms'][key] for key in ('mean', 'p50', 'p95', 'min', 'max')},
                                 'mean_input_tokens': item['input_tokens']['mean'], 'total_output_tokens': item['output_tokens']['sum'],
                                 'total_decode_calls': item['decode_count']['sum'], 'invalid_or_failed': item['invalid_or_failed']})
    write_csv(HERE / 'latency.csv', latency_rows)
    metric_rows = []
    def append_metric(dataset, split, mode, condition, metric, value, valid, total):
        metric_rows.append({'dataset': dataset, 'split': split, 'mode': mode, 'condition': condition,
                            'metric': metric, 'value': value, 'valid': valid, 'total': total, 'coverage': valid / total if total else None})
    for dataset, splits in external_quality.items():
        for split, modes in splits.items():
            for mode, result in modes.items():
                if dataset == 'JSTS':
                    conditions = {'hard_selected_stage': result['hard_selected_stage'], **(result['expected_score'] or {})}
                    for condition, metrics in conditions.items():
                        for metric in ('mae', 'rmse', 'pearson', 'spearman_average_ranks', 'normalized_mae_divided_by_5'):
                            append_metric(dataset, split, mode, condition, metric, metrics[metric], metrics['valid'], metrics['total'])
                else:
                    for metric in ('accuracy', 'balanced_accuracy', 'macro_f1', 'mcc'):
                        if metric in result:
                            append_metric(dataset, split, mode, 'hard_label', metric, result[metric], result['valid'], result['total'])
                    for condition, metrics in (result['probability_metrics'] or {}).items():
                        for metric in ('nll_logsumexp', 'brier_multiclass_sum', 'brier_binary_true', 'ece_10_equal_width'):
                            append_metric(dataset, split, mode, condition, metric, metrics.get(metric), metrics['valid'], metrics['total'])
    write_csv(HERE / 'external_metrics.csv', metric_rows)
    print(json.dumps({'accounting': accounting, 'primary': bootstrap['comparisons'], 'parity': parity,
                      'external_primary_direct': {'JCoLA_MCC': external_quality['JCoLA']['all']['direct']['mcc'],
                                                 'JCQA_accuracy': external_quality['JCommonsenseQA']['all']['direct']['accuracy'],
                                                 'JSTS_expected_MAE': external_quality['JSTS']['all']['direct']['expected_score']['t1']['mae']}}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
