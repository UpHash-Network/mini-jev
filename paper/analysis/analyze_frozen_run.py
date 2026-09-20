#!/usr/bin/env python3
"""Recompute the frozen v2 run and describe uncertainty over observed families.

Standard library only. No model calls, fitting, threshold selection, or IID-item
confidence intervals. Outputs are derived artifacts inside paper/analysis.
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

ROOT = Path(__file__).resolve().parents[2]
SEED = 2026092037
METRICS = ('nll', 'brier', 'score_mae', 'score_normalized_mae')


def digest_file(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def mean(values):
    return math.fsum(values) / len(values) if values else None


def quantile(values, p):
    ordered = sorted(values)
    position = (len(ordered) - 1) * p
    low = int(position)
    high = min(low + 1, len(ordered) - 1)
    return ordered[low] + (ordered[high] - ordered[low]) * (position - low)


def softmax(logits, temperature):
    scaled = [z / temperature for z in logits]
    high = max(scaled)
    weights = [math.exp(z - high) for z in scaled]
    total = math.fsum(weights)
    return [p / total for p in weights]


def distribution_metrics(keys, probabilities, gold, kind):
    gold_index = keys.index(gold)
    best = max(range(len(keys)), key=lambda index: probabilities[index])
    result = {
        'nll': -math.log(max(probabilities[gold_index], 1e-300)),
        'brier': math.fsum((p - float(index == gold_index)) ** 2 for index, p in enumerate(probabilities)),
        'max_probability': max(probabilities),
        'entropy_confidence': 1 + math.fsum(p * math.log(p) for p in probabilities if p > 0) / math.log(len(keys)),
        'predicted': keys[best],
    }
    if kind == 'score':
        expectation = math.fsum(int(key) * p for key, p in zip(keys, probabilities))
        result.update(score_expectation=expectation, score_mae=abs(expectation - int(gold)),
                      score_normalized_mae=abs(expectation - int(gold)) / (len(keys) - 1))
    return result


def ece(rows, condition):
    bins = []
    for index in range(10):
        members = [row for row in rows if min(9, int(row[condition]['max_probability'] * 10)) == index]
        entry = {'lower': index / 10, 'upper': (index + 1) / 10, 'count': len(members)}
        if members:
            entry.update(mean_confidence=mean([row[condition]['max_probability'] for row in members]),
                         accuracy=mean([row['correct'] for row in members]))
        bins.append(entry)
    value = math.fsum(b['count'] / len(rows) * abs(b['mean_confidence'] - b['accuracy']) for b in bins if b['count'])
    return value, bins


def summarize(rows):
    output = {'count': len(rows), 'correct': sum(row['correct'] for row in rows),
              'accuracy': mean([row['correct'] for row in rows])}
    for condition in ('t1', 'fitted'):
        output[condition] = {metric: mean([row[condition][metric] for row in rows if metric in row[condition]]) for metric in METRICS}
        output[condition]['ece_10_equal_width'], output[condition]['reliability_bins'] = ece(rows, condition)
    output['delta_fitted_minus_t1'] = {metric: (
        output['fitted'][metric] - output['t1'][metric] if output['t1'][metric] is not None else None) for metric in METRICS}
    return output


def load_and_verify():
    paths = {name: ROOT / relative for name, relative in (
        ('summary', 'results/native-acceptance/summary.json'),
        ('predictions', 'results/native-acceptance/predictions.jsonl'),
        ('questions', 'acceptance-v2/questions_2400.jsonl'))}
    summary = json.loads(paths['summary'].read_text())
    predictions = [json.loads(line) for line in paths['predictions'].read_text().splitlines() if line.strip()]
    questions = [json.loads(line) for line in paths['questions'].read_text().splitlines() if line.strip()]
    assert len(predictions) == len(questions) == 2400
    assert digest_file(paths['predictions']) == summary['predictions_sha256'], 'frozen predictions hash mismatch'
    by_id = {row['id']: row for row in questions}
    assert len(by_id) == len(questions) == len({row['id'] for row in predictions})
    assert set(by_id) == {row['id'] for row in predictions}
    rows, maximum_probability_error, maximum_score_error = [], 0., 0.
    temperatures = set()
    for prediction in predictions:
        question = by_id[prediction['id']]
        answer = prediction['answer']
        for key in ('type', 'source', 'family'):
            assert prediction[key] == question[key], (prediction['id'], key)
        assert prediction['valid'] and not prediction['validation_errors']
        assert prediction['gold'] == str(question['label']).lower() if isinstance(question['label'], bool) else prediction['gold'] == str(question['label'])
        assert prediction['correct'] == (prediction['gold'] == answer['label'])
        assert answer['native_decode_count'] == 1 and answer['output_tokens'] == 0
        keys, logits = answer['candidate_keys'], answer['candidate_logits']
        assert len(keys) == len(logits) == len(answer['probabilities'])
        assert all(math.isfinite(z) for z in logits)
        expected_keys = ({str(i) for i in range(len(question['criteria']))} if prediction['type'] == 'score' else set(question['criteria']))
        assert set(keys) == expected_keys
        temperature = answer['temperature']
        temperatures.add(temperature)
        assert temperature > 0
        p1, fitted = softmax(logits, 1.), softmax(logits, temperature)
        maximum_probability_error = max(maximum_probability_error, *(abs(p - answer['probabilities'][key]) for key, p in zip(keys, fitted)))
        row = {key: prediction[key] for key in ('id', 'type', 'source', 'family', 'gold', 'correct')}
        row.update(t1=distribution_metrics(keys, p1, row['gold'], row['type']),
                   fitted=distribution_metrics(keys, fitted, row['gold'], row['type']),
                   input_tokens=prediction['input_tokens'], wall_ms=prediction['wall_ms'], question=question)
        assert row['t1']['predicted'] == row['fitted']['predicted'] == answer['label']
        assert abs(row['fitted']['entropy_confidence'] - answer['confidence']) < 1e-12
        if row['type'] == 'score':
            maximum_score_error = max(maximum_score_error, abs(row['fitted']['score_expectation'] - answer['score']))
        rows.append(row)
    assert len(temperatures) == 1 and maximum_probability_error < 1e-12 and maximum_score_error < 1e-12
    subsets = {'all': rows, 'generated': [r for r in rows if r['source'] == 'generated'],
               'manual_ai_authored': [r for r in rows if r['source'] == 'manual']}
    subsets.update({kind: [r for r in rows if r['type'] == kind] for kind in ('choice', 'noul', 'score')})
    results = {name: summarize(members) for name, members in subsets.items()}
    assert results['all']['correct'] == summary['overall']['correct']
    for kind in ('choice', 'noul', 'score'):
        assert results[kind]['correct'] == summary['by_type'][kind]['correct']
    metric_map = {'nll': 'nll', 'brier': 'brier_multiclass_sum', 'score_mae': 'score_expectation_mae',
                  'score_normalized_mae': 'score_normalized_expectation_mae', 'ece_10_equal_width': 'ece_10_equal_width'}
    differences = {}
    for condition, original in (('t1', 'probability_metrics_uncalibrated'), ('fitted', 'probability_metrics_calibrated')):
        for metric, source in metric_map.items():
            difference = abs(results['all'][condition][metric] - summary[original][source])
            differences[f'{condition}.{metric}'] = difference
            assert difference < 1e-12, (condition, metric, difference)
    latencies = {}
    for name, condition in (('input_tokens_le_512', lambda r: r['input_tokens'] <= 512),
                            ('input_tokens_gt_512', lambda r: r['input_tokens'] > 512)):
        values = [r['wall_ms'] for r in rows if condition(r)]
        latencies[name] = {'count': len(values), 'p50_ms': quantile(values, .5), 'p95_ms': quantile(values, .95), 'max_ms': max(values)}
        for metric, value in latencies[name].items():
            assert abs(value - summary['latency'][name][metric]) < 1e-9
    reverse = [p['reverse'] for p in predictions if 'reverse' in p]
    assert len(reverse) == 800 and all(r['valid'] and r['same_label'] for r in reverse)
    families = defaultdict(list)
    for row in rows:
        families[(row['source'], row['family'])].append(row)
    assert Counter(source for source, _ in families) == {'generated': 45, 'manual': 26}
    macro = mean([summarize(members)['accuracy'] for (source, _), members in families.items() if source == 'generated'])
    assert abs(macro - summary['generated_family_macro_accuracy']) < 1e-12
    provenance = {name: {'path': path.relative_to(ROOT).as_posix(), 'sha256': digest_file(path)} for name, path in paths.items()}
    verification = {'passed': True, 'probability_max_absolute_difference': maximum_probability_error,
                    'score_expectation_max_absolute_difference': maximum_score_error,
                    'summary_absolute_differences': differences,
                    'original_predictions_sha256_matches_summary': True,
                    'positive_temperature_preserved_all_2400_top_labels': True,
                    'reverse_choice_valid_and_same_label': len(reverse)}
    return rows, subsets, results, latencies, families, temperatures.pop(), provenance, verification


def family_aggregate(members):
    result = {'accuracy': (math.fsum(row['correct'] for row in members), len(members))}
    for metric in METRICS:
        values = [row['fitted'][metric] - row['t1'][metric] for row in members if metric in row['t1']]
        result['delta_' + metric] = (math.fsum(values), len(values))
    return result


def cluster_bootstrap(families, repetitions, seed):
    """Whole-family, with-replacement resampling; paired conditions share draws."""
    rng = random.Random(seed)
    groups = {source: [family_aggregate(members) for (s, _), members in sorted(families.items()) if s == source]
              for source in ('generated', 'manual')}
    keys = ('accuracy',) + tuple('delta_' + metric for metric in METRICS)
    totals = {source: {key: (math.fsum(family[key][0] for family in entries), sum(family[key][1] for family in entries))
                       for key in keys} for source, entries in groups.items()}
    point = {source: {key: value / count for key, (value, count) in metrics.items()} for source, metrics in totals.items()}
    point['combined_source_standardized'] = {key: sum(totals[source][key][0] for source in groups) / sum(totals[source][key][1] for source in groups) for key in keys}
    point['generated']['family_macro_accuracy'] = mean([total / n for total, n in (family['accuracy'] for family in groups['generated'])])
    draws = {source: {key: [] for key in metrics} for source, metrics in point.items()}
    for _ in range(repetitions):
        replicate = {}
        for source, entries in groups.items():
            chosen = [entries[rng.randrange(len(entries))] for _ in entries]
            replicate[source] = {}
            for key in keys:
                numerator = math.fsum(family[key][0] for family in chosen)
                denominator = sum(family[key][1] for family in chosen)
                if not denominator:
                    raise ValueError('resampled source has no applicable cases; change method before reporting')
                replicate[source][key] = numerator / denominator
                draws[source][key].append(numerator / denominator)
            if source == 'generated':
                draws[source]['family_macro_accuracy'].append(mean([family['accuracy'][0] / family['accuracy'][1] for family in chosen]))
        for key in keys:
            original_total = sum(totals[source][key][1] for source in groups)
            value = math.fsum(replicate[source][key] * totals[source][key][1] / original_total for source in groups)
            draws['combined_source_standardized'][key].append(value)
    result = {}
    for source, metrics in draws.items():
        result[source] = {}
        for key, values in metrics.items():
            result[source][key] = {'estimate': point[source][key], 'percentile_95_low': quantile(values, .025),
                                   'percentile_95_high': quantile(values, .975), 'replicates': repetitions}
    return result


def risk_rows(rows, subset_name):
    curves, grids, thresholds = [], [], []
    for condition in ('t1', 'fitted'):
        for score_name in ('max_probability', 'entropy_confidence'):
            ordered = sorted(rows, key=lambda row: (-row[condition][score_name], row['id']))
            kept = errors = 0
            points = []
            while kept < len(ordered):
                threshold = ordered[kept][condition][score_name]
                while kept < len(ordered) and ordered[kept][condition][score_name] == threshold:
                    errors += not ordered[kept]['correct']
                    kept += 1
                point = {'subset': subset_name, 'condition': condition, 'score': score_name,
                         'threshold': threshold, 'accepted': kept, 'errors': errors,
                         'coverage': kept / len(rows), 'risk': errors / kept}
                points.append(point)
            curves.extend(points)
            for requested in (.1, .2, .3, .4, .5, .6, .7, .8, .9, 1.):
                point = next(p for p in points if p['coverage'] >= requested - 1e-15)
                grids.append({**point, 'requested_coverage': requested})
            # These descriptive cutoffs are encoded as a fixed list, not optimized
            # to meet a test-set risk target. None is recommended for deployment.
            for threshold in (0., .5, .6, .7, .8, .9, .95, .99):
                selected = [row for row in rows if row[condition][score_name] >= threshold]
                error_count = sum(not row['correct'] for row in selected)
                thresholds.append({'subset': subset_name, 'condition': condition, 'score': score_name,
                                   'threshold': threshold, 'accepted': len(selected), 'errors': error_count,
                                   'coverage': len(selected) / len(rows), 'risk': error_count / len(selected) if selected else None})
    return curves, grids, thresholds


def write_csv(path, rows):
    if not rows:
        return
    with path.open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def pct(value):
    return f'{100 * value:.2f}%'


def interval_text(value, percent=False):
    format_value = pct if percent else lambda v: f'{v:+.6f}'
    return f"{format_value(value['estimate'])} [{format_value(value['percentile_95_low'])}, {format_value(value['percentile_95_high'])}]"


def render_report(result, family_rows, failures, grid):
    boot = result['family_resampling']
    lines = ['# Post-hoc analysis of the frozen v2 run', '',
             'This analysis makes no new model calls and does not modify prompts, weights, temperature, labels, or acceptance criteria. '
             'It recomputes the existing run and describes sensitivity to the composition of its observed task families.', '',
             '## Reproduction', '', '```sh', 'python3 paper/analysis/analyze_frozen_run.py', '```', '',
             f"Standard library only. Seed `{result['bootstrap_seed']}`; `{result['bootstrap_repetitions']:,}` replicates. "
             'Input and script SHA-256 values are recorded in `analysis.json`. Existing derived outputs in this directory are overwritten; source data remain read-only.', '',
             '## Verification and estimands', '',
             'All 2,400 IDs, source/family/type metadata, gold labels, correctness indicators, candidate probabilities, Score expectations, '
             'summary losses, and latency quantiles were cross-checked. The original prediction-file hash matches the frozen summary. '
             'The reconstructed probabilities and reported losses differ by less than 1e-12.', '',
             '| Subset | Correct / n | Accuracy |', '|---|---:|---:|']
    for name, data in result['recomputed'].items():
        lines.append(f"| {name} | {data['correct']} / {data['count']} | {pct(data['accuracy'])} |")
    lines += ['', '## Family-aware uncertainty', '',
              '**These are conditional empirical family-resampling percentile intervals, not guarantees of 95% coverage for an external population.** '
              'Families and examples were deliberately authored and were not sampled randomly from a defined deployment population. '
              'The bootstrap assumes the observed family clusters are exchangeable within each source; dependencies between different families are not modeled. '
              'It measures sensitivity to reweighting these observed families. It does not establish generalization to new families, domains, authors, languages, or machines.', '',
              'For generated-only estimates, draw 45 family IDs uniformly with replacement and include every member of each drawn family. '
              'For macro accuracy, average the 45 drawn family accuracies with equal family weight. For micro accuracy and losses, aggregate '
              'the drawn family totals and divide by their applicable item counts. Generated families contain 49 or 50 questions; each family belongs to one type. '
              'The family draw is not stratified by type, so its mixture of Choice/Noul/Score can vary.', '',
              'For combined probability-loss differences, independently draw 45 generated families and 26 individually AI-authored `manual` tags. '
              'Preserve each drawn cluster intact, including multiple types within a manual tag. Compute within-source item-weighted means, then '
              'keep the original source mixture fixed: 2,220:180 for NLL/Brier/accuracy, and 740:60 for Score-only MAE. '
              'The same sampled clusters are used for T=1 and fitted T; the difference is paired at the item level. '
              'Manual-only estimates are also provided, but 26 heterogeneous tags, some with one item, give especially fragile uncertainty summaries. '
              '`manual` denotes AI-agent construction and review, not human annotation. There is no IID bootstrap over 2,400 individual examples.', '',
              '| Generated-only estimand | Estimate [conditional 95% percentile interval] |', '|---|---:|',
              f"| Equal-family macro accuracy | {interval_text(boot['generated']['family_macro_accuracy'], True)} |",
              f"| Item-weighted micro accuracy | {interval_text(boot['generated']['accuracy'], True)} |", '',
              '## Paired temperature comparison', '',
              f"Fitted temperature was frozen from the separate 120-item calibration set: T = {result['temperature']:.16g}. "
              'It is held fixed in every replicate. These intervals therefore omit uncertainty from calibration-set sampling, temperature fitting, '
              'model selection, authoring, and runtime reruns. Positive deltas mean fitted temperature is worse. '
              'The intervals below describe the original 2,400-item source mixture using source-standardized family resampling.', '',
              '| Metric | T=1 | Fitted T | Paired delta [conditional 95% interval] |', '|---|---:|---:|---:|']
    all_data = result['recomputed']['all']
    for metric in METRICS:
        lines.append(f"| {metric} | {all_data['t1'][metric]:.6f} | {all_data['fitted'][metric]:.6f} | {interval_text(boot['combined_source_standardized']['delta_' + metric])} |")
    lines += ['', 'Small changes in NLL/Brier should not be presented as established improvements if the family-resampling interval crosses zero. '
              'Score MAE measures the continuous expected stage, whose value changes under temperature scaling even though every top label is unchanged. '
              'ECE is recomputed descriptively but is not given a paired bootstrap interval here; bin membership changes with temperature.', '',
              '## Descriptive risk–coverage', '',
              'Risk is the observed error proportion among accepted top-label decisions; coverage is the accepted fraction. '
              'We include two distinct sorting scores: maximum allowed-candidate probability and the API’s `1 − normalized entropy`. '
              'Neither is asserted to be a correctness probability. Curves are produced for both temperatures and each source/type subset. '
              'All exact-score ties are accepted together, so realized coverage can exceed the requested grid point. '
              'The full curves and fixed numerical cutoffs are descriptive post-hoc analysis only. No cutoff is selected to achieve a target risk, '
              'no abstention policy is fitted, and no deployment threshold is recommended from these test outcomes.', '',
              '| Fitted T, maximum probability; requested coverage | Actual coverage | Errors / accepted | Observed risk |', '|---:|---:|---:|---:|']
    for row in grid:
        if row['subset'] == 'all' and row['condition'] == 'fitted' and row['score'] == 'max_probability':
            lines.append(f"| {pct(row['requested_coverage'])} | {pct(row['coverage'])} | {row['errors']} / {row['accepted']} | {pct(row['risk'])} |")
    lines += ['', 'Curves and the fixed-cutoff table expose this run’s ranking behavior; they supply no operational risk guarantee. '
              'A deployable cutoff must be selected on separate development/calibration data and evaluated on a fresh external test set.', '',
              '## Weak families and failure examples', '',
              'The family table is sorted by observed accuracy. This ordering is post hoc, without multiple-comparison significance claims. '
              'No causal failure diagnosis is inferred from a family name. `failures.csv` contains all 162 failed items with their original state, '
              'question, candidate criteria, gold, predicted label, and fitted confidence scores.', '',
              '| Source | Family | Correct / n | Accuracy |', '|---|---|---:|---:|']
    for row in sorted(family_rows, key=lambda row: (row['accuracy'], row['source'], row['family']))[:12]:
        lines.append(f"| {row['source']} | {row['family']} | {row['correct']} / {row['count']} | {pct(row['accuracy'])} |")
    lines += ['', 'The following examples are the highest maximum-candidate-probability errors, sorted post hoc to expose overconfident mistakes. '
              'They are illustrative, not a representative subsample or a threshold-development set.', '',
              '| ID | Type / family | Gold → prediction | Max candidate probability |', '|---|---|---|---:|']
    for row in failures[:12]:
        lines.append(f"| {row['id']} | {row['type']} / {row['family']} | {row['gold']} → {row['predicted']} | {row['max_probability']:.6f} |")
    lines += ['', '## Files', '',
              '- `analysis.json`: recomputed metrics, cluster-resampling intervals, methods, and input hashes.',
              '- `family_metrics.csv`: all 45 generated families and 26 AI-authored tags, with paired loss differences.',
              '- `paired_metrics.csv`: per-item probability-loss contributions and both confidence scores.',
              '- `risk_coverage.csv`: complete tie-aware descriptive curves.',
              '- `risk_coverage_grid.csv`: fixed requested coverage values from 10% to 100%.',
              '- `risk_fixed_thresholds.csv`: descriptive results for fixed cutoffs, without cutoff selection.',
              '- `failures.csv`: all errors, sorted by fitted maximum candidate probability.',
              '- `test_analysis.py`: numerical fixtures and cluster-unit regression checks.', '']
    return '\n'.join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--replicates', type=int, default=20000)
    parser.add_argument('--seed', type=int, default=SEED)
    parser.add_argument('--output-dir', type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args(argv)
    if args.replicates < 100:
        parser.error('at least 100 replicates are required')
    rows, subsets, recomputed, latency, families, temperature, provenance, verification = load_and_verify()
    bootstrap = cluster_bootstrap(families, args.replicates, args.seed)
    output = args.output_dir.resolve()
    if not output.is_relative_to(ROOT / 'paper' / 'analysis'):
        parser.error('derived output directory must remain under paper/analysis')
    output.mkdir(parents=True, exist_ok=True)
    family_rows = []
    for (source, family), members in sorted(families.items()):
        data = summarize(members)
        family_rows.append({'source': source, 'family': family,
                            'types': ','.join(sorted({row['type'] for row in members})),
                            **{key: data[key] for key in ('count', 'correct', 'accuracy')},
                            **{'delta_' + metric: data['delta_fitted_minus_t1'][metric] for metric in METRICS}})
    item_rows, failures = [], []
    for row in rows:
        item_rows.append({**{key: row[key] for key in ('id', 'source', 'type', 'family', 'correct')},
                          **{condition + '_' + metric: row[condition].get(metric) for condition in ('t1', 'fitted') for metric in (*METRICS, 'max_probability', 'entropy_confidence')}})
        if not row['correct']:
            q = row['question']
            failures.append({**{key: row[key] for key in ('id', 'source', 'type', 'family', 'gold')},
                             'predicted': row['fitted']['predicted'],
                             'max_probability': row['fitted']['max_probability'],
                             'entropy_confidence': row['fitted']['entropy_confidence'],
                             'gold_nll': row['fitted']['nll'], 'score_mae': row['fitted'].get('score_mae'),
                             'state': q['state'] if isinstance(q['state'], str) else json.dumps(q['state'], ensure_ascii=False),
                             'instructions': q['instructions'], 'criteria': json.dumps(q['criteria'], ensure_ascii=False)})
    failures.sort(key=lambda row: (-row['max_probability'], row['id']))
    curves, grids, thresholds = [], [], []
    for name, members in subsets.items():
        curve, grid, cutoff = risk_rows(members, name)
        curves.extend(curve); grids.extend(grid); thresholds.extend(cutoff)
    result = {'schema_version': 1, 'analysis_type': 'post_hoc_frozen_predictions_no_new_model_calls',
              'provenance': provenance, 'script_sha256': digest_file(Path(__file__)),
              'temperature': temperature, 'bootstrap_seed': args.seed, 'bootstrap_repetitions': args.replicates,
              'bootstrap_method': {
                  'unit': 'source-specific family clusters; every member retained; with replacement',
                  'generated_clusters': 45, 'manual_ai_authored_clusters': 26,
                  'paired_conditions': 'same clusters and same item-level T-fitted minus T=1 differences',
                  'combined_estimand': 'within-source item means standardized to original source weights',
                  'source_weights_all': {'generated': 2220 / 2400, 'manual': 180 / 2400},
                  'source_weights_score': {'generated': 740 / 800, 'manual': 60 / 800},
                  'interval': '2.5th and 97.5th percentiles; linear interpolation',
                  'assumption': 'exchangeable observed families within source; cross-family dependence ignored',
                  'scope': 'sensitivity to observed-family composition; not IID item uncertainty or new-domain generalization',
                  'conditioned_on': 'fixed authored corpus, fitted temperature, model, prompt, gold, and single runtime run'},
              'verification': verification, 'recomputed': recomputed, 'latency_recomputed': latency,
              'family_resampling': bootstrap, 'failure_count': len(failures),
              'risk_coverage_policy': 'descriptive post-hoc; fixed grids; all ties retained; no optimized or recommended threshold',
              'top_failure_ids': [row['id'] for row in failures[:12]]}
    (output / 'analysis.json').write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + '\n')
    for name, data in (('family_metrics.csv', family_rows), ('paired_metrics.csv', item_rows),
                       ('risk_coverage.csv', curves), ('risk_coverage_grid.csv', grids),
                       ('risk_fixed_thresholds.csv', thresholds), ('failures.csv', failures)):
        write_csv(output / name, data)
    (output / 'REPORT.md').write_text(render_report(result, family_rows, failures, grids), encoding='utf-8')
    print(json.dumps({'verified': True, 'items': len(rows), 'generated_family_macro': bootstrap['generated']['family_macro_accuracy'],
                      'paired_deltas_all': {key: value for key, value in bootstrap['combined_source_standardized'].items() if key.startswith('delta_')},
                      'output': output.relative_to(ROOT).as_posix()}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
