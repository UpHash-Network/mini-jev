"""CPU tests for split hygiene, cache identity, selection boundaries and reload."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import training_cli as cli


def case(identifier="a", state="alpha", kind="choice"):
    row = {"id": identifier, "type": kind, "state": state, "instructions": "Choose.",
           "criteria": {"yes": "Accept", "no": "Reject"}, "label": "yes",
           "group": identifier, "family": identifier}
    if kind == "noul":
        row.update(criteria={"false": "No", "true": "Yes"}, label=True)
    if kind == "score":
        row.update(criteria=["Low", "High"], label=1)
    return row


class ValidationTests(unittest.TestCase):
    def test_valid_types(self):
        for kind in ("choice", "noul", "score"):
            cli.validate_case(case(kind=kind))

    def test_bad_schema_and_label(self):
        variants = []
        for key, value in (("label", 1), ("type", "unknown"), ("instructions", " "),
                           ("criteria", {"one": "Only"}), ("state", float("nan")),
                           ("extra", True), ("id", "")):
            row = case(); row[key] = value; variants.append(row)
        row = case(kind="score"); row["label"] = True; variants.append(row)
        row = case(kind="noul"); row["label"] = 1; variants.append(row)
        row = case(); del row["state"]; variants.append(row)
        row = case(); row["criteria"] = {"Ａ": "a", "A": "b"}; row["label"] = "A"; variants.append(row)
        for row in variants:
            with self.subTest(row=row), self.assertRaises((ValueError, UnicodeError)):
                cli.validate_case(row)

    def test_duplicate_keys_nan_and_infinity(self):
        for text in ('{"x":1,"x":2}', '{"x":NaN}', '{"x":Infinity}'):
            with self.assertRaises(ValueError):
                cli.parse_json(text)
        row = case(); row["state"] = cli.parse_json('{"x":1e999}')
        with self.assertRaises(ValueError):
            cli.validate_case(row)

    def test_depth_and_unicode(self):
        row = case(); row["state"] = "\ud800"
        with self.assertRaises(UnicodeError): cli.validate_case(row)
        row = case(); value = "x"
        for _ in range(34): value = [value]
        row["state"] = value
        with self.assertRaises(ValueError): cli.validate_case(row)

    def test_same_split_duplicates_and_cross_split_permutation(self):
        a, b = case(), case("b")
        b["criteria"] = dict(reversed(list(b["criteria"].items())))
        with self.assertRaisesRegex(ValueError, "duplicate normalized"):
            cli.audit_splits({"train": [a], "test": [b]})
        with self.assertRaisesRegex(ValueError, "duplicate normalized"):
            cli.audit_splits({"train": [a, b]})

    def test_normalization_catches_unicode_whitespace_and_object_order(self):
        a, b = case(), case("b")
        a["state"] = {"number": 1, "name": "Ａ  B"}
        b["state"] = {"name": "A\tB", "number": 1.0}
        self.assertEqual(cli.input_signature(a), cli.input_signature(b))

    def test_score_order_is_semantic(self):
        a, b = case(kind="score"), case("b", kind="score")
        b["criteria"].reverse()
        self.assertNotEqual(cli.input_signature(a), cli.input_signature(b))

    def test_structured_state_and_rendered_string_are_not_independent(self):
        for state in ({"x": 1}, [1, 2], True, 42, None):
            a, b = case(), case("b")
            a["state"] = state
            b["state"] = json.dumps(state, ensure_ascii=False)
            self.assertEqual(cli.input_signature(a), cli.input_signature(b))
            with self.assertRaisesRegex(ValueError, "duplicate normalized"):
                cli.audit_splits({"train": [a], "test": [b]})

    def test_id_overlap_rejected_even_if_inputs_differ(self):
        with self.assertRaisesRegex(ValueError, "duplicate id"):
            cli.audit_splits({"train": [case()], "test": [case(state="different")]})

    def test_groups_and_family_checks(self):
        a, b = case(), case("b", "beta")
        b["group"] = a["group"]
        with self.assertRaisesRegex(ValueError, "group"):
            cli.audit_splits({"train": [a], "test": [b]}, "group")
        cli.audit_splits({"train": [a], "test": [b]}, "family")
        del b["family"]
        b["group"] = "b"
        with self.assertRaisesRegex(ValueError, "lacks required"):
            cli.audit_splits({"train": [a], "test": [b]}, "both")

    def test_existing_output_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(FileExistsError): cli.new_output(temp)

    def test_unlabeled_prediction_input_and_gold_rejection(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "input.json"
            row = {key: case(kind="score")[key] for key in ("type", "state", "instructions", "criteria")}
            path.write_text(json.dumps(row))
            self.assertEqual(len(cli.load_prediction_cases(path, 2)), 1)
            row["label"] = 1
            path.write_text(json.dumps(row))
            with self.assertRaisesRegex(ValueError, "no gold label"):
                cli.load_prediction_cases(path, 2)

    def test_evaluation_cannot_reuse_fit_data(self):
        groups = {split: [case(split, split)] for split in cli.SPLITS}
        config = {"split_audit": cli.audit_splits(groups, "both")}
        cli.audit_evaluation(groups["test"], config)
        with self.assertRaisesRegex(ValueError, "overlaps"):
            cli.audit_evaluation(groups["dev"], config)

    def test_invalid_data_precedes_ml_import(self):
        # -S removes site packages, so an accidental torch import would fail.
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "invalid.jsonl"; path.write_text('{"bad":true}\n')
            command = [sys.executable, "-S", str(ROOT / "training_cli.py"), "train",
                       "--model", "not-a-model", "--revision", "a" * 40, "--seed", "5",
                       "--output", str(Path(temp) / "out")]
            for split in cli.SPLITS: command.extend(["--" + split, str(path)])
            result = subprocess.run(command, text=True, capture_output=True)
            self.assertEqual(result.returncode, 2)
            self.assertIn("missing fields", result.stderr)
            self.assertNotIn("torch", result.stderr)
            self.assertFalse((Path(temp) / "out").exists())

    def test_fixture_validates_without_ml_and_rejects_family_claim(self):
        command = [sys.executable, "-S", str(ROOT / "training_cli.py"), "validate"]
        for split in cli.SPLITS:
            command.extend(["--" + split, str(ROOT / "examples/training" / (split + ".jsonl"))])
        result = subprocess.run(command + ["--disjoint-groups", "group"], text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        result = subprocess.run(command + ["--disjoint-groups", "family"], text=True, capture_output=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn("crosses", result.stderr)


class FeatureAndTrainingTests(unittest.TestCase):
    def setUp(self):
        import torch
        self.torch = torch
        torch.set_num_threads(2)
        self.data = {"x": torch.tensor([[1., 0.], [0., 1.], [-1., 0.], [0., -1.]]),
                     "base": torch.zeros(4, 2), "target": torch.tensor([0, 1, 1, 0]),
                     "count": torch.tensor([2, 2, 2, 2])}
        self.cases = [case(str(i), str(i)) for i in range(4)]
        for row, label in zip(self.cases, ("yes", "no", "no", "yes")): row["label"] = label

    def test_feature_validation_rejects_corruption(self):
        cli.validate_features(self.data, 4, 2)
        bad = dict(self.data); bad["target"] = self.torch.tensor([2, 0, 0, 0])
        with self.assertRaises(ValueError): cli.validate_features(bad, 4, 2)
        bad = dict(self.data); bad["base"] = self.torch.full((4, 2), float("nan"))
        with self.assertRaises(ValueError): cli.validate_features(bad, 4, 2)

    def test_cache_identity_preserves_candidate_order_and_runtime(self):
        a = case(); b = copy.deepcopy(a); b["criteria"] = dict(reversed(list(b["criteria"].items())))
        self.assertNotEqual(cli.digest([a], sort_keys=False), cli.digest([b], sort_keys=False))
        base = {"cases_sha256": cli.digest([a], sort_keys=False), "runtime": {"device": "cpu", "dtype": "float32"}}
        alternate = copy.deepcopy(base); alternate["runtime"]["dtype"] = "float16"
        self.assertNotEqual(cli.digest(base), cli.digest(alternate))

    def test_matmul_precision_changes_runtime_identity(self):
        engine = SimpleNamespace(model_id="fixture", device=self.torch.device("cpu"),
                    dtype=self.torch.float32, max_input_tokens=512, symbol_ids=[1, 2],
                    model=SimpleNamespace(config=SimpleNamespace(_commit_hash="a" * 40)),
                    tokenizer=SimpleNamespace(get_vocab=lambda: {"A": 1, "B": 2}, chat_template="fixture"))
        with patch.object(self.torch, "get_float32_matmul_precision", return_value="highest"):
            first = cli.runtime_provenance(engine, 2, 2)
        with patch.object(self.torch, "get_float32_matmul_precision", return_value="high"):
            second = cli.runtime_provenance(engine, 2, 2)
        self.assertNotEqual(cli.digest(first), cli.digest(second))
        for flag in ("cuda_matmul_allow_tf32", "cudnn_allow_tf32", "cudnn_deterministic", "cudnn_benchmark"):
            self.assertIn(flag, first)

    def test_cache_tampering_fails(self):
        from safetensors.torch import save_file
        runtime = {"device": "cpu", "dtype": "float32"}
        identity = {"schema": cli.SCHEMA_VERSION, "cases_sha256": cli.digest(self.cases, sort_keys=False), "runtime": runtime}
        fingerprint = cli.digest(identity)
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / (fingerprint + ".safetensors")
            save_file(self.data, str(path))
            cli.write_json(Path(temp) / (fingerprint + ".json"), {"identity": identity, "sha256": cli.sha_file(path)})
            data, details = cli.extract_features(None, self.cases, temp, 2, 2, runtime)
            self.assertTrue(details["cache_hit"])
            self.torch.testing.assert_close(data["base"], self.data["base"])
            path.write_bytes(path.read_bytes() + b"corrupt")
            with self.assertRaisesRegex(ValueError, "mismatch"):
                cli.extract_features(None, self.cases, temp, 2, 2, runtime)

    def test_fullbatch_selection_and_bias_control(self):
        residual, trials = cli.train_control(self.data, self.data, self.cases, "residual", 10, [.1], [.01])
        self.assertLess(residual["selection"]["dev_nll"], .69)
        bias, _ = cli.train_control(self.data, self.data, self.cases, "bias", 10, [.1], [.01])
        self.assertTrue(self.torch.equal(bias["weight"], self.torch.zeros(2, 2)))
        self.assertIn(0, [row["epoch"] for row in trials[0]["history"]])

    def test_test_labels_do_not_enter_selection_function(self):
        # Changed test labels cannot affect a function whose inputs are only train/dev.
        one, _ = cli.train_control(self.data, self.data, self.cases, "residual", 5, [.1], [.01])
        self.torch.manual_seed(9876)
        two, _ = cli.train_control(self.data, self.data, self.cases, "residual", 5, [.1], [.01])
        self.torch.testing.assert_close(one["weight"], two["weight"], rtol=0, atol=0)
        self.assertEqual(one["selection"], two["selection"])

    def test_real_pipeline_with_stub_features_and_checkpoint_reload(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "run"
            args = cli.parser().parse_args(["train", "--model", "fixture", "--revision", "a" * 40,
                    "--seed", "42", "--output", str(output), "--epochs", "2", "--max-candidates", "2",
                    "--learning-rates", ".1", "--penalties", ".01"] +
                    sum((["--" + split, str(Path(temp) / (split + ".jsonl"))] for split in cli.SPLITS), []))
            for split in cli.SPLITS:
                rows = copy.deepcopy(self.cases)
                for row in rows: row["id"] = split + row["id"]; row["state"] = split + row["state"]
                getattr(args, split).write_text("\n".join(json.dumps(row) for row in rows))
            seen = []
            def fake_extract(engine, cases, cache, batch_size, maximum, runtime):
                split = cases[0]["id"].rstrip("0123456789"); seen.append(split)
                if split == "test":
                    self.assertTrue((output / "checkpoint/config.json").exists())
                    cli.load_checkpoint(output / "checkpoint")
                return self.data, {"fixture": True}
            with patch.object(cli, "make_engine", return_value=SimpleNamespace(device="cpu")), \
                 patch.object(cli, "runtime_provenance", return_value={"fixture": True}), \
                 patch.object(cli, "extract_features", side_effect=fake_extract):
                cli.train_command(args)
            self.assertEqual(seen, ["train", "dev", "calibration", "test"])
            config, controls = cli.load_checkpoint(output / "checkpoint")
            report = cli.parse_json((output / "report.json").read_text())
            self.assertTrue(report["checkpoint_reload_exact"])
            self.assertTrue(report["checkpoint_unchanged_after_test"])
            self.assertEqual(set(controls), {"baseline", "bias", "residual"})
            weights = output / "checkpoint/residual.safetensors"
            weights.write_bytes(weights.read_bytes() + b"bad")
            with self.assertRaisesRegex(ValueError, "SHA256"):
                cli.load_checkpoint(output / "checkpoint")


if __name__ == "__main__":
    unittest.main()
