"""CPU-only fixtures for estimands, invalid coverage, ties, and completion gate."""
import copy
import importlib.util
import math
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location('matched_analysis', Path(__file__).with_name('analyze_study.py'))
A = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(A)


def row(identifier='x', mode='direct', repetition=0, dataset='JCoLA',
        label='true', predicted='true', http_ms=10., logits=None):
    if dataset == 'JSTS':
        keys, kind = [str(i) for i in range(6)], 'score'
    elif dataset == 'JCommonsenseQA':
        keys, kind = ['option_' + str(i) for i in range(5)], 'choice'
    else:
        keys, kind = ['false', 'true'], 'noul'
    if logits is None:
        logits = [float(key == predicted) for key in keys]
    native = {'label_index': keys.index(predicted), 'logits': logits if mode != 'json' else None,
              'probabilities': A.probabilities(logits) if mode != 'json' else None,
              'prompt_sha256': 'prompt', 'input_token_ids_sha256': 'tokens',
              'candidate_ids': list(range(len(keys))), 'candidate_ids_sha256': 'candidates',
              'input_tokens': 30, 'candidate_boundary_checked': mode != 'json'}
    result = {'id': identifier, 'mode': mode, 'dataset': dataset, 'group': 'family:x',
              'repetition': repetition, 'type': kind, 'http_ms': http_ms,
              'http_status': 200, 'answer': {'type': kind, 'label': predicted},
              'native': native, 'keys': keys}
    result['gold_score' if dataset == 'JSTS' else 'label'] = label
    return result


class MatchedAnalysisTests(unittest.TestCase):
    def test_stable_nll_does_not_clip_wrong_extreme_probability(self):
        self.assertEqual(A.nll([0., -1000.], 1), 1000.)
        self.assertEqual(A.probabilities([0., -1000.]), [1., 0.])
        self.assertAlmostEqual(A.nll([10000., 10000.], 1), math.log(2))

    def test_confusion_and_invalid_denominator(self):
        rows = [row(label=gold, predicted=prediction) for gold, prediction, count in
                [('false', 'false', 40), ('false', 'true', 10),
                 ('true', 'false', 20), ('true', 'true', 30)] for _ in range(count)]
        result = A.classification(rows, ['false', 'true'])
        self.assertEqual(result['accuracy'], .7)
        self.assertEqual(result['balanced_accuracy'], .7)
        self.assertAlmostEqual(result['mcc'], 1000 / math.sqrt(40 * 50 * 50 * 60))
        self.assertAlmostEqual(result['per_label']['true']['f1'], 60 / 90)
        broken = copy.deepcopy(rows[0]); broken['http_status'] = 500
        result = A.classification(rows + [broken], ['false', 'true'])
        self.assertEqual(result['accuracy'], 70 / 101)
        self.assertEqual(result['confusion']['false']['INVALID'], 1)
        self.assertIsNone(result['mcc'])
        self.assertEqual(result['mcc_null_reason'], 'invalid_outputs')

    def test_constant_true_baseline_uses_gold_even_if_model_failed(self):
        rows = [row(label='true') for _ in range(158)] + [row(label='false') for _ in range(42)]
        rows[0]['http_status'] = 500
        result = A.constant_true_baseline(rows)
        self.assertEqual(result['accuracy'], .79)
        self.assertEqual(result['balanced_accuracy'], .5)
        self.assertIsNone(result['mcc'])
        self.assertEqual(result['valid'], 200)

    def test_continuous_gold_and_json_have_no_invented_distribution(self):
        direct = row(dataset='JSTS', label=2.7, predicted='2', logits=[-1000., -1000., 0., 0., -1000., -1000.])
        result = A.quality([direct], 'JSTS', 'direct')
        self.assertAlmostEqual(result['expected_score']['t1']['mae'], .2)
        self.assertAlmostEqual(result['hard_selected_stage']['mae'], .7)
        self.assertAlmostEqual(result['expected_score']['t1']['normalized_mae_divided_by_5'], .04)
        generated = row(mode='json', dataset='JSTS', label=2.7, predicted='3')
        result = A.quality([generated], 'JSTS', 'json')
        self.assertIsNone(result['expected_score'])
        self.assertAlmostEqual(result['hard_selected_stage']['mae'], .3)
        self.assertIsNone(A.quality([row(mode='json')], 'JCoLA', 'json')['probability_metrics'])

    def test_invalid_regression_is_visible_coverage(self):
        good = row(dataset='JSTS', label=2.7, predicted='3')
        bad = row(dataset='JSTS', label=2.7, predicted='3'); bad['http_status'] = 500
        result = A.score_quality([good, bad], 'direct')
        self.assertEqual(result['hard_selected_stage']['coverage'], .5)
        self.assertEqual(result['expected_score']['t1']['invalid'], 1)

    def test_tied_ranks_and_constant_correlation(self):
        self.assertEqual(A.average_ranks([1, 1, 3]), [1.5, 1.5, 3.])
        self.assertAlmostEqual(A.correlation(A.average_ranks([1, 1, 3]), A.average_ranks([3, 3, 1])), -1.)
        self.assertIsNone(A.correlation([2, 2], [1, 2]))

    def test_primary_is_median_of_paired_item_means(self):
        rows = []
        for index, (direct, one) in enumerate([(1, 100), (100, 101), (101, 1)]):
            for repetition in range(5):
                for mode, value in [('direct', direct), ('one_token', one), ('json', direct + 10)]:
                    rows.append(row(str(index), mode, repetition, 'local_v2', http_ms=value + repetition))
        items = A.pair_items(rows)
        self.assertEqual(A.percentile([r['one_token_minus_direct_ms'] for r in items], .5), 1)
        marginal_difference = A.percentile([r['one_token_mean_http_ms'] for r in items], .5) - A.percentile([r['direct_mean_http_ms'] for r in items], .5)
        self.assertEqual(marginal_difference, 0)
        with self.assertRaisesRegex(ValueError, 'incomplete'):
            A.pair_items(rows[:-1])
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            A.pair_items(rows + [rows[0]])

    def test_bootstrap_keeps_large_cluster_intact(self):
        items = [{'group': 'large', 'one_token_minus_direct_ms': 10., 'json_minus_direct_ms': 100.} for _ in range(100)]
        items.append({'group': 'small', 'one_token_minus_direct_ms': -10., 'json_minus_direct_ms': -100.})
        result = A.grouped_bootstrap(items, replicates=1000, seed=17)
        self.assertEqual(result, A.grouped_bootstrap(items, replicates=1000, seed=17))
        primary = result['comparisons']['one_token_minus_direct_ms']
        self.assertEqual(primary['estimate_ms'], 10.)
        # Cluster draws can select only the one-item group despite its tiny item mass.
        self.assertEqual(primary['percentile_95_low_ms'], -10.)
        self.assertEqual(primary['percentile_95_high_ms'], 10.)
        self.assertEqual(result['group_count'], 2)

    def test_parity_exposes_tie_mismatch_and_hash_violation(self):
        direct = row(logits=[0., 0.], predicted='false')
        one = row(mode='one_token', logits=[0., 0.], predicted='true')
        summary, detail = A.parity_audit([direct, one])
        self.assertEqual(summary['counts_true']['label_mismatch_with_tie'], 1)
        self.assertEqual(summary['counts_true']['label_mismatch_without_tie'], 0)
        self.assertEqual(summary['max_logit_abs_difference'], 0.)
        one['native']['prompt_sha256'] = 'different'
        summary, detail = A.parity_audit([direct, one])
        self.assertFalse(detail[0]['same_prompt_sha256'])

    def test_ece_uses_actual_tied_decision(self):
        one = row(mode='one_token', logits=[0., 0.], predicted='true', label='true')
        result = A.probability_quality([one], 1.)
        self.assertEqual(result['reliability_bins'][5]['accuracy'], 1.)
        self.assertEqual(result['ece_10_equal_width'], .5)

    def test_quality_first_repetition_is_separate_from_stability(self):
        rows = [row(mode=mode, repetition=repetition, dataset='local_v2',
                    label='true', predicted='true' if repetition == 0 else 'false')
                for mode in A.MODES for repetition in range(5)]
        quality = A.local_quality(rows)
        stability = A.repeated_stability(rows)
        for mode in A.MODES:
            self.assertEqual(quality[mode]['all']['n'], 1)
            self.assertEqual(quality[mode]['all']['accuracy'], 1.)
            self.assertEqual(stability[mode]['changed_label'], 1)

    def test_expected_score_paired_difference_is_computed_not_assumed_zero(self):
        direct = row(dataset='JSTS', label=2.7, predicted='2', logits=[-1000., -1000., 0., 0., -1000., -1000.])
        one = row(mode='one_token', dataset='JSTS', label=2.7, predicted='3', logits=[-1000., -1000., -1000., 0., -1000., -1000.])
        generated = row(mode='json', dataset='JSTS', label=2.7, predicted='3')
        result = A.paired_external([direct, one, generated])['JSTS']
        self.assertAlmostEqual(result['one_token_minus_direct']['expected_score_mae_difference']['t1']['mae_difference'], .1)
        self.assertIsNone(result['json_minus_direct']['expected_score_mae_difference'])

    def test_incomplete_study_is_rejected_before_reading_predictions(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(A, 'HERE', Path(directory)):
            with self.assertRaisesRegex(ValueError, 'COMPLETION.json is absent'):
                A.load_completed()


if __name__ == '__main__':
    unittest.main()
