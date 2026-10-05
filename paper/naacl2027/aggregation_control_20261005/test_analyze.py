"""Independent numerical fixtures and integrity failures for the aggregation control."""
from decimal import Decimal, localcontext
import math
import unittest

import analyze as a


class AggregationTests(unittest.TestCase):
    def assertVectorClose(self, actual, expected, tolerance=1e-13):
        self.assertEqual(len(actual), len(expected))
        for x, y in zip(actual, expected):
            self.assertLessEqual(abs(x - y), tolerance)

    def test_decimal_probability_product_fixture_disagrees_with_arithmetic(self):
        # One near-zero response penalizes candidate 0 geometrically despite its larger mean.
        strings = [["0.01", "0.99"]] + [["0.625", "0.375"]] * 4
        probabilities = [[float(x) for x in row] for row in strings]
        actual = a.geometric_mean([[math.log(x) for x in row] for row in probabilities])
        with localcontext() as context:
            context.prec = 70
            weights = []
            for k in range(2):
                product = Decimal(1)
                for row in strings:
                    product *= Decimal(row[k])
                weights.append(context.power(product, Decimal(1) / Decimal(5)))
            expected = [float(x / sum(weights)) for x in weights]
        self.assertVectorClose(actual, expected)
        self.assertEqual(a.top_index(a.mean(probabilities)), 0)
        self.assertEqual(a.top_index(actual), 1)

    def test_identical_members_and_single_member_are_unchanged(self):
        logits = [3.0, 1.0, -1.0, 2.0, 0.0]
        for count in [1, 5]:
            self.assertVectorClose(a.geometric_mean([logits] * count), a.softmax(logits))

    def test_shift_and_member_permutation_invariance(self):
        logits = [[2, -2, 1], [0, 5, -1], [1, 0, -3], [2, 1, 4], [-1, 3, 2]]
        shifted = [[x + shift for x in row] for row, shift in zip(logits, [100, -80, 7, -3, 11])]
        original = a.geometric_mean(logits)
        self.assertVectorClose(a.geometric_mean(shifted), original)
        self.assertVectorClose(a.geometric_mean(list(reversed(logits))), original)

    def test_underflow_robustness_and_candidate_alignment(self):
        logits = [[-10000., 0.], [0., -10000.]]
        self.assertVectorClose(a.geometric_mean(logits), [.5, .5])
        self.assertEqual(a.top_index(a.geometric_mean(logits)), 0)
        logits = [[4, 2, -1], [-2, 3, 1], [1, -3, 2]]
        permutation = [2, 0, 1]
        self.assertVectorClose(a.geometric_mean([[v[i] for i in permutation] for v in logits]),
                               [a.geometric_mean(logits)[i] for i in permutation])

    def test_normalization_and_mean_logit_identity(self):
        logits = [[0.5, -1., 0.25, 8., -9.], [-2., 3., 0., 6., 2.], [4., -7., 2., 1., 0.]]
        actual = a.geometric_mean(logits)
        self.assertAlmostEqual(math.fsum(actual), 1., places=14)
        self.assertVectorClose(actual, a.softmax(a.mean(logits)))

    def test_paired_transition_accounting_includes_wrong_to_wrong(self):
        got = a.paired_counts([0, 0, 1, 2, 0], [1, 0, 0, 1, 0], [0] * 5)
        self.assertEqual(got, {"reference_wrong_alternative_correct": 1,
                              "reference_correct_alternative_wrong": 1,
                              "both_correct": 2, "both_wrong": 1,
                              "label_disagreements": 3, "accuracy_difference": 0.})

    def test_quantile_convention_and_undefined_accounting(self):
        self.assertEqual(a.percentile([0, 10, 20, 30, 40], .025), 1.)
        self.assertEqual(a.interval([0, 0, 0, None]), {"low": 0., "high": 0., "valid_draws": 3, "invalid_draws": 1})

    def test_invalid_inputs_fail(self):
        for vectors in [[], [[]], [[1, 2], [1]], [[float("nan")]]]:
            with self.assertRaises(ValueError):
                a.mean(vectors)
        with self.assertRaises(ValueError):
            a.log_softmax([float("inf"), 0])
        with self.assertRaises(ValueError):
            a.paired_counts([0], [], [0])


if __name__ == "__main__":
    unittest.main()
