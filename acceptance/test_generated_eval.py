"""CPU-only tests for the independent generated acceptance block."""
import unittest

from make_generated_eval import build, canonical, oracle_unit_tests, semantic_identity, solve, validate


class GeneratedAcceptanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases, cls.rejected = build()

    def test_hand_specified_oracle_examples(self):
        self.assertEqual(oracle_unit_tests(), 54)

    def test_every_case_and_distribution(self):
        result = validate(self.cases)
        self.assertEqual({kind: report["count"] for kind, report in result.items()},
                         {"choice": 740, "noul": 740, "score": 740})

    def test_byte_equivalent_regeneration(self):
        again, rejected = build()
        self.assertEqual(self.rejected, rejected)
        self.assertEqual(canonical(self.cases), canonical(again))

    def test_checklist_order_does_not_create_a_new_problem(self):
        a = {"attributes": ["signed", "dated"], "conditions": [True, False]}
        b = {"attributes": ["dated", "signed"], "conditions": [False, True]}
        self.assertEqual(semantic_identity("and", a, "", {}), semantic_identity("and", b, "", {}))
        self.assertEqual(solve("and", a), solve("and", b))

    def test_record_order_does_not_create_a_new_problem(self):
        a = {"updates": [{"time": 9, "value": "first"}, {"time": 12, "value": "second"}]}
        b = {"updates": list(reversed(a["updates"]))}
        self.assertEqual(semantic_identity("latest", a, "", {}), semantic_identity("latest", b, "", {}))
        self.assertEqual(solve("latest", a), solve("latest", b))

    def test_meaningful_order_is_preserved(self):
        a = {"order": ["first", "second"], "rank": 1}
        b = {"order": ["second", "first"], "rank": 1}
        self.assertNotEqual(semantic_identity("rank_reference", a, "", {}), semantic_identity("rank_reference", b, "", {}))
        self.assertNotEqual(solve("rank_reference", a), solve("rank_reference", b))


if __name__ == "__main__":
    unittest.main()
