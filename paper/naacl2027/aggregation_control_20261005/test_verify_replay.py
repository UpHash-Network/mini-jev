"""Fault injection for the unfrozen CI verifier, with hash-valid altered fixtures."""
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest

import verify_replay as v


def update_manifest(folder):
    hashes = {name: hashlib.sha256((folder / name).read_bytes()).hexdigest() for name in v.ARTIFACTS}
    (folder / "MANIFEST.json").write_text(json.dumps({"files_sha256": hashes}), encoding="utf-8")


def fixture(folder):
    folder.mkdir()
    results = {"created_at": "original", "methods": {"accuracy": .75, "calls": 1200},
               "nested": {"created_at": "must-not-be-ignored"}, "enabled": True}
    (folder / "RESULTS.json").write_text(json.dumps(results), encoding="utf-8")
    records = [{"item_id": str(i), "calls": 5, "probability": .125} for i in range(960)]
    (folder / "records.jsonl").write_text("\n".join(json.dumps(row) for row in records) + "\n", encoding="utf-8")
    (folder / "REPORT.md").write_text("# Fixed report\n", encoding="utf-8")
    update_manifest(folder)


class ReplayVerifierTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="aggregation-verifier-fixture-")
        self.addCleanup(self.temp.cleanup)
        self.expected = Path(self.temp.name) / "expected"
        self.actual = Path(self.temp.name) / "actual"
        fixture(self.expected)
        shutil.copytree(self.expected, self.actual)

    def change_results(self, callback, folder=None):
        folder = self.actual if folder is None else folder
        path = folder / "RESULTS.json"
        value = json.loads(path.read_text(encoding="utf-8"))
        callback(value)
        path.write_text(json.dumps(value), encoding="utf-8")
        update_manifest(folder)

    def test_timestamp_and_small_float_differences_accepted(self):
        def change(value):
            value["created_at"] = "replay"
            value["methods"]["accuracy"] += 5e-13
        self.change_results(change)
        report = v.verify(self.actual, self.expected)
        self.assertEqual(report["status"], "passed")
        self.assertLessEqual(report["maximum_results_absolute_difference"], 1e-12)
        self.assertGreater(report["maximum_results_absolute_difference"], 0)

    def test_hash_valid_accuracy_perturbation_rejected(self):
        self.change_results(lambda value: value["methods"].update(accuracy=.75001))
        with self.assertRaisesRegex(ValueError, "Number differs beyond tolerance"):
            v.verify(self.actual, self.expected)

    def test_hash_valid_cost_perturbation_rejected(self):
        self.change_results(lambda value: value["methods"].update(calls=1201))
        with self.assertRaisesRegex(ValueError, "Value differs.*calls"):
            v.verify(self.actual, self.expected)

    def test_integer_to_float_and_boolean_type_changes_rejected(self):
        for field, value in [("calls", 1200.0), ("calls", True)]:
            with self.subTest(value=value):
                self.change_results(lambda result: result["methods"].update({field: value}))
                with self.assertRaisesRegex(ValueError, "Type differs"):
                    v.verify(self.actual, self.expected)

    def test_nested_timestamp_and_missing_keys_rejected(self):
        self.change_results(lambda value: value["nested"].update(created_at="changed"))
        with self.assertRaisesRegex(ValueError, "Value differs.*nested/created_at"):
            v.verify(self.actual, self.expected)
        self.change_results(lambda value: value.pop("enabled"))
        with self.assertRaisesRegex(ValueError, "Keys differ"):
            v.verify(self.actual, self.expected)

    def test_record_probability_and_record_count_changes_rejected(self):
        path = self.actual / "records.jsonl"
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
        rows[0]["probability"] += .001
        path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
        update_manifest(self.actual)
        with self.assertRaisesRegex(ValueError, "Number differs beyond tolerance.*records"):
            v.verify(self.actual, self.expected)
        path.write_text("\n".join(json.dumps(row) for row in rows[:-1]) + "\n", encoding="utf-8")
        update_manifest(self.actual)
        with self.assertRaisesRegex(ValueError, "exactly 960"):
            v.verify(self.actual, self.expected)

    def test_nonfinite_values_rejected_in_both_artifacts(self):
        self.change_results(lambda value: value["methods"].update(accuracy=float("nan")))
        with self.assertRaisesRegex(ValueError, "Nonfinite"):
            v.verify(self.actual, self.expected)
        self.change_results(lambda value: value["methods"].update(accuracy=.75))
        self.change_results(lambda value: value["methods"].update(accuracy=float("inf")), self.expected)
        with self.assertRaisesRegex(ValueError, "Nonfinite"):
            v.verify(self.actual, self.expected)

    def test_overflow_and_duplicate_json_keys_rejected(self):
        path = self.actual / "RESULTS.json"
        for raw, message in [(' {"created_at":"x","number":1e999}', "Nonfinite"),
                             ('{"created_at":"x","created_at":"y"}', "Duplicate")]:
            with self.subTest(raw=raw):
                path.write_text(raw, encoding="utf-8")
                update_manifest(self.actual)
                with self.assertRaisesRegex(ValueError, message):
                    v.verify(self.actual, self.expected)

    def test_expected_and_actual_manifest_hashes_checked(self):
        for folder, label in [(self.expected, "expected"), (self.actual, "actual")]:
            with self.subTest(label=label):
                path = folder / "REPORT.md"
                original = path.read_bytes()
                path.write_bytes(original + b"changed\n")
                with self.assertRaisesRegex(ValueError, label + " manifest hash differs"):
                    v.verify(self.actual, self.expected)
                path.write_bytes(original)

    def test_hash_valid_report_change_rejected(self):
        (self.actual / "REPORT.md").write_text("# Altered report\n", encoding="utf-8")
        update_manifest(self.actual)
        with self.assertRaisesRegex(ValueError, "REPORT.md differs byte-for-byte"):
            v.verify(self.actual, self.expected)


if __name__ == "__main__":
    unittest.main()
