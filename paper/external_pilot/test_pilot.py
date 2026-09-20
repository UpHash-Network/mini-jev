"""CPU fixtures for sampling and reported metrics; no external dataset access."""
import importlib.util
import math
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location("pilot", Path(__file__).with_name("run_pilot.py"))
pilot = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pilot)


class PilotTests(unittest.TestCase):
    def test_balanced_selection_does_not_depend_on_source_order(self):
        rows = [{"sentence_pair_id": str(i * 10 + j), "label": label}
                for i, label in enumerate(pilot.LABELS) for j in range(5)]
        selected = pilot.select(rows, 2, "fixture:")
        self.assertEqual(selected, pilot.select(list(reversed(rows)), 2, "fixture:"))
        self.assertEqual([sum(r["label"] == label for r in selected) for label in pilot.LABELS], [2, 2, 2])
        with self.assertRaisesRegex(ValueError, "duplicate"):
            pilot.select(rows + [rows[0]], 2, "fixture:")

    def test_known_uniform_predictions(self):
        rows = [{"gold": label, "candidate_logits": [0, 0, 0]} for label in pilot.LABELS]
        result = pilot.metrics(rows, 1)
        self.assertEqual(result["correct"], 1)
        self.assertAlmostEqual(result["nll"], math.log(3))
        self.assertAlmostEqual(result["multiclass_brier_sum"], 2 / 3)
        self.assertAlmostEqual(result["ece_10_equal_width"], 0)
        self.assertAlmostEqual(result["macro_f1"], 1 / 6)

    def test_temperature_preserves_accuracy_and_logsumexp_is_stable(self):
        rows = [{"gold": label, "candidate_logits": [1000 if i == j else -1000 for i in range(3)]}
                for j, label in enumerate(pilot.LABELS)]
        primary, secondary = pilot.metrics(rows, 1), pilot.metrics(rows, 1.3489628825916533)
        self.assertEqual(primary["accuracy"], 1)
        self.assertEqual(primary["accuracy"], secondary["accuracy"])
        wrong = pilot.metrics([{"gold": "neutral", "candidate_logits": [1000, -1000, -1000]}], 1)
        self.assertEqual(wrong["nll"], 2000)

    def test_overlap_counts_shared_text_across_positions(self):
        rows = [{"sentence_pair_id": "1", "sentence1": "a", "sentence2": "b", "yjcaptions_id": "image"},
                {"sentence_pair_id": "2", "sentence1": "c", "sentence2": "a", "yjcaptions_id": "image"}]
        out = pilot.overlap(rows)
        self.assertEqual(out["rows_with_any_shared_sentence"], 2)
        self.assertEqual(out["repeated_sentence_values"], 1)
        self.assertEqual(out["sentence_occurrences_beyond_first"], 1)
        self.assertEqual(out["repeated_yjcaptions_ids"], 1)


if __name__ == "__main__":
    unittest.main()
