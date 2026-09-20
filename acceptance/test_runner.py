"""CPU-only harness checks. No real models or private acceptance data are read."""
import argparse
import contextlib
import importlib.util
import io
import json
import math
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location("runner", Path(__file__).with_name("run_acceptance.py"))
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


class HookModel:
    def __init__(self):
        self.hooks = []
        self.base_model = self

    def register_forward_pre_hook(self, fn):
        self.hooks.append(fn)
        class Handle:
            def remove(inner):
                self.hooks.remove(fn)
        return Handle()

    def forward(self):
        for hook in self.hooks:
            hook(self, ())


class FakeEngine:
    """Synthetic deterministic engine exercises runner logic, never model quality."""
    model_id = "unit-fixture"
    model_revision = "unit-revision"
    runtime_fingerprint = "unit-fingerprint"
    dtype = "float32"
    device = "mps"
    prompt_style = "compact"
    attention = "eager"
    max_input_tokens = 2048
    temperature = 1.0
    temperature_calibration_applied = False

    def __init__(self):
        self.model = HookModel()
        self.seen_questions = []

    def synchronize(self):
        pass

    def decide(self, q):
        self.seen_questions.append(q)
        self.model.forward()
        kind = q["type"]
        keys = sorted(q["criteria"]) if kind != "score" else [str(i) for i in range(len(q["criteria"]))]
        # The toy fixture asks to select a directly supplied key. This is not
        # connected to the evaluation corpus or the production ReleaseEngine.
        target = q["state"].get("target", keys[0]) if isinstance(q["state"], dict) else keys[0]
        logits = [2.0 if k == target else 0.0 for k in keys]
        probs = dict(zip(keys, runner.softmax(logits, self.temperature)))
        answer = {"type": kind, "label": target, "probabilities": probs,
                  "candidate_keys": keys, "candidate_logits": logits,
                  "batch_size": 1, "input_tokens": 100, "output_tokens": 0,
                  "latency_ms": 1., "model_ms": .8, "confidence": .4}
        if kind == "choice":
            answer["choice"] = target
        elif kind == "noul":
            answer["noul"] = probs["true"]
        else:
            answer["score"] = sum(int(k)*probs[k] for k in keys)
        return answer


def fixture_case(kind="choice", index=0, prefix="unit"):
    criteria = {"a": "one", "b": "two"}
    if kind == "noul":
        criteria = {"false": "no", "true": "yes"}
    elif kind == "score":
        criteria = ["one", "two"]
    keys = list(criteria) if isinstance(criteria, dict) else ["0", "1"]
    target = keys[index % 2]
    return {"id": f"{prefix}_{kind}_{index}", "type": kind,
            "state": {"target": target, "fixture_id": f"{prefix}_{kind}_{index}"},
            "instructions": "Select the named target.", "criteria": criteria,
            "label": target, "family": f"toy_{kind}"}


def write_fixture(path, count, prefix):
    rows = [fixture_case(kind, i, prefix) for kind in runner.TYPES for i in range(count)]
    path.write_text("".join(json.dumps(x)+"\n" for x in rows))


class RunnerTests(unittest.TestCase):
    def test_question_excludes_gold_metadata(self):
        case = fixture_case()
        self.assertEqual(set(runner.question(case)), {"type", "state", "instructions", "criteria"})

    def test_strict_json_rejects_duplicates_and_nonfinite(self):
        for text in ('{"a":1,"a":2}', '{"a":NaN}', '{"a":Infinity}'):
            with self.assertRaises(ValueError):
                runner.read_json(text)

    def test_validation_rejects_wrong_scalar_sum_and_argmax(self):
        engine = FakeEngine()
        case = fixture_case("score")
        answer = engine.decide(runner.question(case))
        self.assertEqual(runner.validate_answer(case, answer), [])
        answer["score"] = 1.0
        self.assertIn("score does not equal probability-weighted stage", runner.validate_answer(case, answer))
        answer = engine.decide(runner.question(case))
        answer["probabilities"]["0"] = float("nan")
        self.assertTrue(runner.validate_answer(case, answer))
        answer = engine.decide(runner.question(case))
        answer["label"] = "1"
        self.assertIn("label does not maximize probability", runner.validate_answer(case, answer))

    def test_forward_counter_detects_cached_reply(self):
        engine = FakeEngine()
        counter = runner.ForwardCounter(engine)
        q = runner.question(fixture_case())
        answer, wall = runner.actual_forward(engine, counter, q)
        self.assertEqual(counter.count, 1)
        self.assertGreaterEqual(wall, 0)
        engine.decide = lambda _: answer
        with self.assertRaisesRegex(RuntimeError, "0 backbone forwards"):
            runner.actual_forward(engine, counter, q)
        counter.close()

    def test_known_metrics_and_percentile(self):
        row = {"valid": True, "type": "score", "gold": "1",
               "answer": {"candidate_keys": ["0", "1"], "candidate_logits": [0, math.log(3)],
                          "probabilities": {"0": .25, "1": .75}}}
        metrics = runner.calibration_metrics([row])
        self.assertAlmostEqual(metrics["nll"], -math.log(.75))
        self.assertAlmostEqual(metrics["brier_multiclass_sum"], .125)
        self.assertAlmostEqual(metrics["ece_10_equal_width"], .25)
        self.assertAlmostEqual(metrics["score_expectation_mae"], .25)
        self.assertAlmostEqual(runner.percentile([10, 20, 30], .95), 29)

    def test_freeze_detects_source_and_identity_changes(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td)
            source = out / "source.py"
            source.write_text("original")
            engine = FakeEngine()
            guard = runner.FreezeGuard([source], engine, {}, out, "unit")
            guard.check()
            source.write_text("modified")
            with self.assertRaisesRegex(RuntimeError, "files changed"):
                guard.check()
            source.write_text("original")
            engine.temperature = 2.0
            with self.assertRaisesRegex(RuntimeError, "configuration changed"):
                guard.check()
            engine.temperature = 1.0
            guard.freeze_path.write_text("{}")
            with self.assertRaisesRegex(RuntimeError, "freeze.json changed"):
                guard.check()

    def test_end_to_end_2400_single_forward_and_reverse(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            manual, generated = base / "manual.jsonl", base / "generated.jsonl"
            config, temperature = base / "config.json", base / "temperature.json"
            write_fixture(manual, 60, "manual")
            write_fixture(generated, 740, "generated")
            config.write_text("{}")
            temperature.write_text("{}")
            out = base / "run"
            out.mkdir()
            args = argparse.Namespace(command="evaluate", config=config, temperature_config=temperature,
                                      manual=manual, generated=generated, output_dir=out)
            engine = FakeEngine()
            hw = {"machdep.cpu.brand_string": "Apple M5 Pro", "hw.memsize": str(64*1024**3)}
            with patch.object(runner, "setup_engine", return_value=(engine, {}, 0.)), patch.object(runner, "hardware", return_value=hw), contextlib.redirect_stdout(io.StringIO()):
                passed = runner.run_evaluate(args)
            self.assertTrue(passed)
            result = json.loads((out / "summary.json").read_text())
            self.assertEqual(result["actual_backbone_forwards"], 3207)
            self.assertEqual(result["overall"]["count"], 2400)
            self.assertEqual(result["manual"]["count"], 180)
            self.assertEqual(result["candidate_order"]["consistency"], 1.)
            self.assertEqual(len((out / "predictions.jsonl").read_text().splitlines()), 2400)
            self.assertTrue(all(set(q) == set(runner.INPUT_KEYS) for q in engine.seen_questions))

    def test_calibration_uses_only_120_and_saves_fingerprint(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            calibration, config = base / "cal.jsonl", base / "config.json"
            write_fixture(calibration, 40, "cal")
            config.write_text("{}")
            out = base / "run"
            out.mkdir()
            args = argparse.Namespace(command="calibrate", config=config, calibration=calibration, output_dir=out)
            engine = FakeEngine()
            with patch.object(runner, "setup_engine", return_value=(engine, {}, 0.)), contextlib.redirect_stdout(io.StringIO()):
                runner.run_calibrate(args)
            result = json.loads((out / "temperature.json").read_text())
            self.assertEqual(result["calibration_count"], 120)
            self.assertEqual(result["runtime_fingerprint"], "unit-fingerprint")
            self.assertEqual(result["actual_backbone_forwards"], 127)
            self.assertEqual(result["temperature"], .1)
            self.assertLess(result["nll_after"], result["nll_before"])


if __name__ == "__main__":
    unittest.main()
