"""Saved-evidence integrity checks; no models, network, or source mutation."""
from collections import Counter
import copy
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("evidence_exporter", ROOT / "scripts/build_evidence_explorer.py")
exporter = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(exporter)


class FullSavedEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.files = exporter.build()
        cls.index = json.loads(cls.files["index.json"])
        cls.panels = [json.loads(cls.files[d["path"]]) for d in cls.index["panels"]]
        cls.archive = zipfile.ZipFile(exporter.DEFAULT_ZIP)
        cls.source_rows = {}
        for source_id, source in cls.index["sources"].items():
            if source["format"] == "jsonl":
                cls.source_rows[source_id] = [json.loads(line) for line in cls.archive.read(source["member"]).splitlines()]

    @classmethod
    def tearDownClass(cls):
        cls.archive.close()

    def raw(self, source):
        source_id, line = source
        self.assertIs(type(line), int)
        self.assertGreaterEqual(line, 1)
        return self.source_rows[source_id][line - 1]

    def panel(self, study, model, dataset):
        return next(p for p in self.panels if (p["study_id"], p["model_key"], p["dataset"]) == (study, model, dataset))

    def test_all_eligible_records_exactly_once_with_complete_sources(self):
        coverage = self.index["coverage"]
        self.assertEqual(coverage, {"panels": 18, "study_item_model_records": 3600,
                         "physical_records": 22000, "derived_records": 9000,
                         "distinct_source_item_ids": 1200, "excluded_failed_or_missing_records": 0})
        actual = Counter()
        for panel in self.panels:
            self.assertEqual(len(panel["items"]), 200)
            self.assertEqual(len({i["item_id"] for i in panel["items"]}), 200)
            for item in panel["items"]:
                for variant in item["variants"]:
                    actual[tuple(variant["source"])] += 1
        expected = set()
        for source_id, source in self.index["sources"].items():
            if source["member"].endswith(("/predictions.jsonl", "/derived_answers.jsonl")):
                expected.update((source_id, n) for n in range(1, len(self.source_rows[source_id]) + 1))
        self.assertEqual(len(expected), 31000)
        self.assertEqual(set(actual), expected)
        self.assertEqual(set(actual.values()), {1})

    def test_every_source_hash_and_panel_hash(self):
        for source in self.index["sources"].values():
            raw = self.archive.read(source["member"])
            self.assertEqual(hashlib.sha256(raw).hexdigest(), source["sha256"])
            self.assertEqual(len(raw), source["bytes"])
        for descriptor in self.index["panels"]:
            raw = self.files[descriptor["path"]]
            self.assertEqual(hashlib.sha256(raw).hexdigest(), descriptor["sha256"])
            self.assertEqual(len(raw), descriptor["bytes"])

    def test_all_record_semantic_probabilities_values_and_metadata(self):
        for panel in self.panels:
            keys = panel["canonical_keys"]
            for item in panel["items"]:
                for variant in item["variants"]:
                    raw = self.raw(variant["source"])
                    self.assertEqual(raw["item_id"], item["item_id"])
                    self.assertEqual(raw["dataset"], panel["dataset"])
                    self.assertEqual(raw.get("model_key", panel["model_key"]), panel["model_key"])
                    self.assertEqual(variant["probabilities"], [raw["probabilities"][k] for k in keys])
                    self.assertEqual(variant["label"], raw["label"])
                    self.assertAlmostEqual(variant["value"], raw["typed_value"], places=12) if panel["type"] != "choice" else self.assertEqual(variant["value"], raw["typed_value"])
                    if panel["type"] == "score":
                        self.assertEqual(item["gold_score"], raw["gold_score"])
                        self.assertAlmostEqual(variant["value"], math.fsum(float(k)*p for k, p in zip(keys, variant["probabilities"])), places=12)
                        self.assertNotIn("gold_label", item)
                    else:
                        self.assertEqual(item["gold_label"], raw["gold_label"])
                    entropy = -math.fsum(p*math.log(p) for p in variant["probabilities"] if p)
                    self.assertAlmostEqual(variant["concentration"], max(0., 1-entropy/math.log(len(keys))), places=12)
                    if variant["kind"] == "physical":
                        self.assertEqual(item["source_question_sha256"], raw["source_question_sha256"])
                        mapping = self.index["mappings"][variant["mapping"]]
                        self.assertEqual(mapping, {"candidate_keys": raw["candidate_keys"], "candidate_tokens": raw["candidate_tokens"], "display_order": raw.get("display_order")})
                        weights = [math.exp(z-max(raw["logits"])) for z in raw["logits"]]
                        for key, weight in zip(mapping["candidate_keys"], weights):
                            self.assertAlmostEqual(raw["probabilities"][key], weight/sum(weights), places=6)
                        self.assertEqual(variant["calls"], 1)

    def test_all_derived_means_members_costs_and_model_scope(self):
        for panel in self.panels:
            if panel["study_id"] != exporter.ENSEMBLE:
                continue
            for item in panel["items"]:
                variants = {v["id"]: v for v in item["variants"]}
                for variant in variants.values():
                    if variant["kind"] != "derived":
                        continue
                    members = [variants[k] for k in variant["member_ids"]]
                    self.assertEqual(variant["member_sources"], [v["source"] for v in members])
                    self.assertEqual(len({tuple(v["source"]) for v in members}), len(members))
                    self.assertTrue(all(v["kind"] == "physical" for v in members))
                    self.assertEqual(variant["calls"], len(members))
                    self.assertEqual(variant["input_tokens"], sum(v["input_tokens"] for v in members))
                    self.assertEqual(variant["latency_ms"], math.fsum(v["latency_ms"] for v in members))
                    for n in range(len(panel["canonical_keys"])):
                        self.assertEqual(variant["probabilities"][n], math.fsum(v["probabilities"][n] for v in members)/len(members))
                    for member in members:
                        raw = self.raw(member["source"])
                        self.assertEqual(raw["item_id"], item["item_id"])
                        self.assertEqual(raw["model_key"], panel["model_key"])
                    if item["structural_orbit_identity"]:
                        self.assertEqual(set(variants["cyclic_forward"]["member_ids"]), set(variants["cyclic_reverse"]["member_ids"]))
                        self.assertEqual(variants["cyclic_forward"]["probabilities"], variants["cyclic_reverse"]["probabilities"])

    def test_actual_semantic_label_swap(self):
        panel = self.panel(exporter.ROBUST, exporter.NATIVE, "JCoLA")
        item = next(i for i in panel["items"] if i["item_id"].endswith(":8388"))
        variant = next(v for v in item["variants"] if v["id"] == "label_reverse")
        self.assertEqual(self.index["mappings"][variant["mapping"]]["candidate_keys"], ["true", "false"])
        self.assertAlmostEqual(variant["probabilities"][1], .836386, places=5)
        self.assertEqual(variant["label"], "true")

    def test_actual_score_expectation_mode_and_continuous_gold(self):
        panel = self.panel(exporter.ROBUST, exporter.NATIVE, "JSTS")
        item = next(i for i in panel["items"] if i["item_id"] == "jsts:valid:229")
        variant = next(v for v in item["variants"] if v["id"] == "baseline")
        self.assertEqual(item["gold_score"], 3.6)
        self.assertEqual(variant["label"], "4")
        self.assertAlmostEqual(variant["value"], 3.517086994033014, places=12)

    def test_actual_binary_orbit_union_two_calls(self):
        panel = self.panel(exporter.ENSEMBLE, "qwen2.5-0.5b", "JCoLA")
        item = next(i for i in panel["items"] if i["item_id"] == "jcola:in_domain_valid:898")
        variants = {v["id"]: v for v in item["variants"]}
        f, r = variants["cyclic_forward"], variants["cyclic_reverse"]
        self.assertTrue(item["structural_orbit_identity"])
        self.assertEqual(f["probabilities"], r["probabilities"])
        self.assertEqual(len({tuple(s) for s in f["member_sources"] + r["member_sources"]}), 2)
        self.assertAlmostEqual(f["value"], .6102222103731034, places=12)

    def test_featured_rules_full_population_and_scope(self):
        for featured in self.index["featured"]:
            panel = self.panel(featured["study_id"], featured["model_key"], featured["dataset"])
            self.assertEqual(panel["id"], featured["panel_id"])
            eligible = []
            for item in panel["items"]:
                variants = {v["id"]: v for v in item["variants"]}
                a, b = variants[featured["a"]], variants[featured["b"]]
                rule = featured["id"]
                matches = (a["label"] != b["label"]) if rule == "order_flip" else (a["label"] == item["gold_label"] and b["label"] != item["gold_label"]) if rule == "averaging_worse" else abs(a["value"]-float(a["label"])) >= .4 if rule == "expectation_vs_mode" else True
                if matches: eligible.append(item["item_id"])
            self.assertEqual(featured["item_id"], min(eligible))
            self.assertEqual(featured["eligible_items_under_rule"], len(eligible))
            self.assertTrue(featured["selection_rule"] and featured["title"] and featured["description"])

    def test_model_metadata_is_bound_to_runtime_per_study(self):
        for panel in self.panels:
            meta = panel["model_metadata"]
            source = self.index["sources"][meta["source"]]
            runtime = json.loads(self.archive.read(source["member"]))
            self.assertEqual(meta, self.index["models"][panel["study_id"]][panel["model_key"]])
            if meta["backend"] == "transformers":
                self.assertEqual(meta["precision"], runtime["dtype"])
                self.assertEqual(meta["revision"], runtime["revision"])
            else:
                self.assertEqual(meta["precision"], runtime["fingerprint_data"]["dtype"])
                self.assertEqual(meta["revision"], runtime["fingerprint_data"]["revision"])

    def test_full_panel_summaries_include_every_item(self):
        for descriptor, panel in zip(self.index["panels"], self.panels):
            for variant_id, summary in descriptor["variant_summaries"].items():
                rows = [(i, next(v for v in i["variants"] if v["id"] == variant_id)) for i in panel["items"]]
                self.assertEqual(summary["items"], 200)
                self.assertEqual(summary["label_counts"], dict(Counter(v["label"] for _, v in rows)))
                if panel["type"] == "score":
                    mean = sum(v["value"] for _, v in rows)/200
                    self.assertAlmostEqual(summary["value_variance"], sum((v["value"]-mean)**2 for _, v in rows)/200, places=12)
                    self.assertAlmostEqual(summary["mae"], sum(abs(v["value"]-i["gold_score"]) for i, v in rows)/200, places=12)
                else:
                    self.assertEqual(summary["accuracy"], sum(v["label"] == i["gold_label"] for i, v in rows)/200)

    def test_no_benchmark_text_or_model_input_fields(self):
        prohibited = {"state", "messages", "input_ids", "prompt", "question", "text", "criteria", "sentence1", "sentence2"}
        def walk(value):
            if isinstance(value, dict):
                self.assertFalse(prohibited & value.keys())
                for child in value.values(): walk(child)
            elif isinstance(value, list):
                for child in value: walk(child)
        for panel in self.panels: walk(panel)
        walk(self.index)

    def test_checked_in_export_matches_deterministic_rebuild(self):
        exporter.write_files(self.files, exporter.DEFAULT_OUT, check=True)
        self.assertEqual(self.index["exporter_sha256"], hashlib.sha256(Path(exporter.__file__).read_bytes()).hexdigest())


class AlgebraAndFailureTests(unittest.TestCase):
    def test_semantic_alignment_not_token_order(self):
        self.assertEqual(exporter.aligned({"true": .8, "false": .2}, ["false", "true"]), [.2, .8])
        with self.assertRaisesRegex(ValueError, "key mismatch"):
            exporter.aligned({"A": .8, "B": .2}, ["false", "true"])

    def test_ties_zeros_nulls_and_expected_score(self):
        tied = exporter.answer({"true": .5, "false": .5}, ["false", "true"], "noul")
        self.assertEqual(tied["label"], "false")
        self.assertEqual(tied["top_tie_keys"], ["false", "true"])
        self.assertEqual(tied["concentration"], 0.)
        p = {str(i): float(i == 0) for i in range(6)}
        result = exporter.answer(p, list(p), "score", {str(i): i for i in range(6)})
        self.assertEqual(result["value"], 0.)
        self.assertEqual(result["concentration"], 1.)
        self.assertEqual(json.loads(exporter.encode({"zero": 0., "unknown": None})), {"zero": 0., "unknown": None})

    def test_physical_tie_retains_observed_vector_order(self):
        row = {"condition": "label_reverse", "type": "noul", "candidate_keys": ["true", "false"],
               "candidate_tokens": ["A", "B"], "probabilities": {"false": .5, "true": .5},
               "logits": [1., 1.], "label": "true", "typed_value": .5, "concentration": 0.,
               "output_tokens": 0, "forward_calls": 1, "input_tokens": 4, "latency_ms": 0.}
        result = exporter.physical(row, ["false", "true"], ["fixture", 1], exporter.Mappings())
        self.assertEqual(result["label"], "true")
        self.assertEqual(result["top_tie_keys"], ["true", "false"])
        self.assertEqual(result["latency_ms"], 0.)

    def synthetic(self):
        meta = {"model_key": "fixture", "item_id": "item", "dataset": "JCoLA", "type": "noul", "split": "valid", "group": "group", "gold_label": "true", "canonical_key_order": ["false", "true"]}
        rows = {0: {**meta, "probabilities": {"false": .9, "true": .1}, "input_tokens": 1, "latency_ms": 0},
                1: {**meta, "probabilities": {"false": .2, "true": .8}, "input_tokens": 2, "latency_ms": 1}}
        return meta, rows

    def test_probability_mean_not_mean_logits(self):
        meta, rows = self.synthetic()
        result = exporter.derive(meta, [0, 1], rows)
        self.assertAlmostEqual(result["probabilities"][0], .55)
        geometric_false = math.sqrt(.9*.2) / (math.sqrt(.9*.2)+math.sqrt(.1*.8))
        self.assertGreater(abs(result["probabilities"][0]-geometric_false), .04)
        self.assertEqual(result["input_tokens"], 3)
        self.assertEqual(result["latency_ms"], 1)

    def test_incomplete_duplicate_or_cross_model_pool_rejected(self):
        meta, rows = self.synthetic()
        for members in ([0, 2], [0, 0], []):
            with self.assertRaises(ValueError): exporter.derive(meta, members, rows)
        bad = copy.deepcopy(rows); bad[1]["model_key"] = "other"
        with self.assertRaisesRegex(ValueError, "cross-item/model"):
            exporter.derive(meta, [0, 1], bad)
        orbit = {**meta, "forward_request_indices": [0, 1], "reverse_request_indices": [1, 0], "structural_orbit_identity": True, "baseline_request_index": 0, "reverse_single_request_index": 1}
        self.assertEqual(exporter.recipes(orbit)["dihedral"], [0, 1])
        orbit["reverse_request_indices"] = [1, 1]
        with self.assertRaisesRegex(ValueError, "duplicate orbit"): exporter.recipes(orbit)

    def test_output_immutability_and_tamper_detection(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / "new"
            files = {"index.json": b"{}\n", "panels/example.json": b"[]\n"}
            exporter.write_files(files, out)
            exporter.write_files(files, out, check=True)
            with self.assertRaises(FileExistsError): exporter.write_files(files, out)
            (out / "index.json").write_bytes(b"tampered")
            with self.assertRaisesRegex(ValueError, "bytes mismatch"): exporter.write_files(files, out, check=True)

    def test_unpinned_archive_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "other.zip"
            path.write_bytes(b"not the frozen ZIP")
            with self.assertRaisesRegex(ValueError, "pinned artifact"): exporter.Archive(path)


if __name__ == "__main__":
    unittest.main()
