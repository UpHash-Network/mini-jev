"""Numerical fixtures for the family-resampling analysis (stdlib only)."""
import importlib.util
import math
from pathlib import Path
import unittest

SPEC = importlib.util.spec_from_file_location('frozen_analysis', Path(__file__).with_name('analyze_frozen_run.py'))
analysis = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(analysis)


def row(correct, score, delta=0.0):
    one = {'nll': 1.0, 'brier': .5, 'score_mae': .25, 'score_normalized_mae': .25,
           'max_probability': score, 'entropy_confidence': score}
    fitted = dict(one)
    for key in analysis.METRICS:
        fitted[key] += delta
    return {'id': str(correct) + str(score), 'correct': correct, 't1': one, 'fitted': fitted}


class AnalysisTests(unittest.TestCase):
    def test_known_probability_losses(self):
        result = analysis.distribution_metrics(['0', '1'], [.25, .75], '1', 'score')
        self.assertAlmostEqual(result['nll'], -math.log(.75))
        self.assertAlmostEqual(result['brier'], .125)
        self.assertAlmostEqual(result['score_mae'], .25)
        self.assertAlmostEqual(result['score_normalized_mae'], .25)
        self.assertEqual(result['predicted'], '1')

    def test_positive_temperature_preserves_argmax(self):
        for temperature in (.1, 1., 1.3489628825916533, 10.):
            probabilities = analysis.softmax([10000., 10001., -10000.], temperature)
            self.assertAlmostEqual(sum(probabilities), 1.)
            self.assertEqual(probabilities.index(max(probabilities)), 1)

    def test_percentile_linear_interpolation(self):
        self.assertEqual(analysis.quantile([10., 20., 30.], .95), 29.)

    def test_zero_paired_difference_stays_zero_in_every_cluster_interval(self):
        families = {('generated', 'a'): [row(True, .9)] * 50,
                    ('generated', 'b'): [row(False, .8)],
                    ('manual', 'c'): [row(True, .7)]}
        result = analysis.cluster_bootstrap(families, 1000, 1)
        for source in result:
            for name, value in result[source].items():
                if name.startswith('delta_'):
                    self.assertEqual(value['estimate'], 0.)
                    self.assertEqual(value['percentile_95_low'], 0.)
                    self.assertEqual(value['percentile_95_high'], 0.)
        self.assertEqual(result['generated']['family_macro_accuracy']['estimate'], .5)
        self.assertAlmostEqual(result['generated']['accuracy']['estimate'], 50 / 51)
        # Whole clusters are resampled; the highly unequal family sizes do not
        # create an artificially narrow interval from 51 supposedly IID items.
        self.assertEqual(result['generated']['accuracy']['percentile_95_low'], 0.)
        self.assertEqual(result['generated']['accuracy']['percentile_95_high'], 1.)

    def test_paired_sign_and_source_weighting(self):
        families = {('generated', 'a'): [row(True, .9, .2)] * 3,
                    ('manual', 'b'): [row(False, .8, -.2)]}
        result = analysis.cluster_bootstrap(families, 100, 2)
        combined = result['combined_source_standardized']['delta_nll']
        self.assertAlmostEqual(combined['estimate'], .1)
        self.assertAlmostEqual(combined['percentile_95_low'], .1)
        self.assertAlmostEqual(combined['percentile_95_high'], .1)

    def test_bootstrap_reproducible(self):
        families = {('generated', 'a'): [row(True, .9, .1)],
                    ('generated', 'b'): [row(False, .8, -.2)],
                    ('manual', 'c'): [row(True, .7, .3)]}
        self.assertEqual(analysis.cluster_bootstrap(families, 100, 7),
                         analysis.cluster_bootstrap(families, 100, 7))

    def test_risk_curve_retains_ties_without_using_gold_to_break_them(self):
        rows = [row(True, .9), row(False, .9), row(True, .4)]
        curve, grid, thresholds = analysis.risk_rows(rows, 'fixture')
        selected = [r for r in curve if r['condition'] == 'fitted' and r['score'] == 'max_probability']
        self.assertEqual(selected[0]['accepted'], 2)
        self.assertEqual(selected[0]['risk'], .5)
        self.assertEqual(selected[-1]['accepted'], 3)
        cutoff = [r for r in thresholds if r['condition'] == 'fitted' and r['score'] == 'max_probability' and r['threshold'] == .95][0]
        self.assertEqual(cutoff['coverage'], 0.)
        self.assertIsNone(cutoff['risk'])

    def test_recomputed_source_evidence_agrees(self):
        rows, _, results, latency, families, temperature, provenance, verification = analysis.load_and_verify()
        self.assertEqual(len(rows), 2400)
        self.assertEqual(results['all']['correct'], 2238)
        self.assertEqual(len(families), 71)
        self.assertEqual(latency['input_tokens_le_512']['count'], 2291)
        self.assertGreater(temperature, 1)
        self.assertTrue(verification['passed'])
        self.assertEqual(len(provenance), 3)


if __name__ == '__main__':
    unittest.main()
