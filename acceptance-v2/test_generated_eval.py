"""CPU-only blind v2 data invariants; no model or prediction files are read."""
import hashlib
import importlib.util
import json
import collections
import random
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("v2_generated_oracle", ROOT / "make_generated_eval.py")
generator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(generator)


class GeneratedV2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases, cls.rejected = generator.build()

    def test_hand_specified_oracle_examples(self):
        self.assertEqual(generator.oracle_unit_tests(), 54)

    def test_every_case_and_distribution(self):
        summary = generator.validate(self.cases)
        self.assertEqual({k: v["count"] for k, v in summary.items()}, {"choice": 740, "noul": 740, "score": 740})
        for kind in ("choice", "score"):
            for counts in summary[kind]["position_counts_by_candidate_count"].values():
                self.assertLessEqual(max(counts.values()) - min(counts.values()), 1)

    def test_byte_equivalent_regeneration_and_saved_file(self):
        again, rejected = generator.build()
        self.assertEqual(rejected, self.rejected)
        self.assertEqual(generator.canonical(self.cases), generator.canonical(again))
        expected = "".join(json.dumps(c, ensure_ascii=False, separators=(",", ":")) + "\n" for c in self.cases)
        self.assertEqual((ROOT / "private" / "generated_2220.jsonl").read_text(), expected)

    def test_all_v1_identities_and_exact_inputs_are_excluded(self):
        old = [json.loads(line) for line in (ROOT.parent / "acceptance" / "private" / "generated_2220.jsonl").read_text().splitlines()]
        normalized_old = {generator.semantic_identity(c["oracle"]["rule"], c["oracle"]["facts"], c["instructions"], c["criteria"]) for c in old}
        old_saved = {c["semantic_sha256"] for c in old}
        actual = {c["semantic_sha256"] for c in self.cases}
        self.assertFalse(actual & normalized_old)
        self.assertFalse(actual & old_saved)
        fields = ("type", "state", "instructions", "criteria")
        old_inputs = {generator.canonical({k: c[k] for k in fields}) for c in old}
        new_inputs = {generator.canonical({k: c[k] for k in fields}) for c in self.cases}
        self.assertFalse(old_inputs & new_inputs)
        self.assertFalse({c["id"] for c in old} & {c["id"] for c in self.cases})

    def test_v1_files_are_unchanged(self):
        baseline = ROOT.parent / "acceptance"
        expected = {
            "make_generated_eval.py": "a210e973782264cd14371501a248488fb8c39db51be05e0fe8b94b2907aadc69",
            "private/generated_2220.jsonl": "141ee4c379fa8d72df6bca3fe793054c9d2847ca7d16d2fa6622bc92558d4bb3",
        }
        for name, digest in expected.items():
            self.assertEqual(hashlib.sha256((baseline / name).read_bytes()).hexdigest(), digest)

    def test_all_45_families_are_preserved(self):
        old = [json.loads(line) for line in (ROOT.parent / "acceptance" / "private" / "generated_2220.jsonl").read_text().splitlines()]
        self.assertEqual({(c["type"], c["family"]) for c in old}, {(c["type"], c["family"]) for c in self.cases})
        self.assertEqual(len({(c["type"], c["family"]) for c in self.cases}), 45)

    def test_choice_positions_balance_after_runtime_key_sort(self):
        for count in range(2, 9):
            counts = collections.Counter(sorted(c["criteria"]).index(c["label"])
                                         for c in self.cases if c["type"] == "choice" and len(c["criteria"]) == count)
            values = [counts[index] for index in range(count)]
            self.assertLessEqual(max(values) - min(values), 1)

    def test_position_rejection_does_not_reduce_candidate_cardinality(self):
        for case in self.cases:
            if case["type"] != "choice":
                continue
            family_index, position = [int(part) - 1 for part in case["id"].split("-")[-2:]]
            seed = generator.SEED + 10000000 + family_index * 100000 + position * 1000
            global_index = sum(50 if index < 5 else 49 for index in range(family_index)) + position
            initial_spec = generator.choice_case(case["family"], random.Random(seed), global_index)
            self.assertEqual(len(case["criteria"]), len(initial_spec[2]))

    def test_checklist_order_does_not_create_a_new_case(self):
        a = {"attributes": ["signed", "dated"], "conditions": [True, False]}
        b = {"attributes": ["dated", "signed"], "conditions": [False, True]}
        self.assertEqual(generator.semantic_identity("and", a, "", {}), generator.semantic_identity("and", b, "", {}))

    def test_set_order_and_repeated_scans_are_not_new_semantics(self):
        a = {"required": ["a", "b"], "provided": ["b"]}
        b = {"required": ["b", "a"], "provided": ["b"]}
        self.assertEqual(generator.semantic_identity("missing_score", a, "", []), generator.semantic_identity("missing_score", b, "", []))
        a = {"entries": ["a", "b", "a"], "minimum": 2}
        b = {"entries": ["b", "a", "a", "a"], "minimum": 2}
        self.assertEqual(generator.semantic_identity("distinct_count", a, "", {}), generator.semantic_identity("distinct_count", b, "", {}))

    def test_meaningful_order_is_preserved(self):
        a = {"order": ["first", "second"], "rank": 1}
        b = {"order": ["second", "first"], "rank": 1}
        self.assertNotEqual(generator.semantic_identity("rank_reference", a, "", {}), generator.semantic_identity("rank_reference", b, "", {}))
        self.assertNotEqual(generator.solve("rank_reference", a), generator.solve("rank_reference", b))


if __name__ == "__main__":
    unittest.main()
