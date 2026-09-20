"""Correctness checks against the actual cached model, not mocked inference."""
import copy
import json
import os
from pathlib import Path
import unittest

import torch
from mini_jev import MiniJev, options_for, typed_answer


class SchemaTests(unittest.TestCase):
    def test_score_is_expectation_and_noul_is_yes_probability(self):
        result = typed_answer("score", ["0", "1", "2"], [.1, .2, .7])
        self.assertAlmostEqual(result["score"], 1.6)
        self.assertEqual(result["label"], "2")
        result = typed_answer("noul", ["false", "true"], [.8, .2])
        self.assertAlmostEqual(result["noul"], .2)
        self.assertFalse(result["calibrated"])

    def test_invalid_distributions_and_schema_are_rejected(self):
        for probabilities in ([float("nan"), 0], [-.1, 1.1], [.2, .2]):
            with self.assertRaises(ValueError):
                typed_answer("choice", ["a", "b"], probabilities)
        with self.assertRaises(ValueError):
            options_for({"type": "noul", "state": "x", "instructions": "x",
                         "criteria": {"yes": "yes", "no": "no"}})


class ModelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = MiniJev(model=os.environ.get("MINI_JEV_TEST_MODEL", "Qwen/Qwen2.5-0.5B-Instruct"))
        cls.cases = json.loads(Path(__file__).with_name("example.json").read_text())

    def test_selected_projection_matches_normal_model_forward(self):
        case = self.cases[0]
        options, ids = self.engine._prepare(case)
        inputs = self.engine._batch([ids])
        with torch.inference_mode():
            usual = self.engine.model(**inputs, use_cache=False).logits[0, -1, :]
            expected = usual[self.engine.symbol_ids[:len(options)]].float().cpu()
        for projection in ("selected", "full"):
            actual = self.engine.decide(case, projection=projection)
            torch.testing.assert_close(torch.tensor(actual["candidate_logits"]), expected,
                                       atol=2e-4, rtol=2e-4)
            torch.testing.assert_close(torch.tensor(list(actual["probabilities"].values())),
                                       expected.softmax(0), atol=2e-5, rtol=2e-4)
        self.assertGreater(actual["candidate_mass"], 0)
        self.assertLessEqual(actual["candidate_mass"], 1.00001)

    def test_left_padded_batch_matches_single_questions(self):
        batch = self.engine.decide_many(self.cases)
        for case, batched in zip(self.cases, batch):
            single = self.engine.decide(case)
            self.assertEqual(single["label"], batched["label"])
            torch.testing.assert_close(torch.tensor(list(single["probabilities"].values())),
                                       torch.tensor(list(batched["probabilities"].values())),
                                       atol=2e-4, rtol=2e-4)

    def test_evaluation_label_never_enters_prompt(self):
        a, b = copy.deepcopy(self.cases[0]), copy.deepcopy(self.cases[0])
        a["label"], b["label"] = "billing", "technical"
        self.assertEqual(self.engine._prepare(a), self.engine._prepare(b))

    def test_choice_key_meaning_enters_prompt(self):
        a, b = copy.deepcopy(self.cases[0]), copy.deepcopy(self.cases[0])
        a["criteria"] = {"返品": "担当へ回す", "配送": "担当へ回す"}
        b["criteria"] = {"配送": "担当へ回す", "返品": "担当へ回す"}
        self.assertNotEqual(self.engine._prepare(a)[1], self.engine._prepare(b)[1])

    def test_input_limit_fails_instead_of_silently_truncating(self):
        original = self.engine.max_input_tokens
        self.engine.max_input_tokens = 2
        try:
            with self.assertRaisesRegex(ValueError, "no truncation"):
                self.engine.decide(self.cases[0])
        finally:
            self.engine.max_input_tokens = original


if __name__ == "__main__":
    unittest.main(verbosity=2)
