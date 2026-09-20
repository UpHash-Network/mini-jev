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


class FakeEngine:
    """Synthetic deterministic engine exercises runner logic, never model quality."""
    model_id = "unit-fixture"
    model_revision = "unit-revision"
    runtime_fingerprint = "unit-fingerprint"
    dtype = "Q4_K_M"
    device = "metal"
    prompt_style = "compact"
    attention = "llama.cpp_flash"
    max_input_tokens = 2048
    temperature = 1.0
    temperature_calibration_applied = False
    model_file = Path("fixture.gguf")
    native_binary = Path("fake-native-helper")
    threads = 6

    def __init__(self):
        self.total_decode_count = 0
        self.closed = False
        self.seen_questions = []

    def synchronize(self):
        pass

    def decide(self, q):
        self.seen_questions.append(q)
        self.total_decode_count += 1
        kind = q["type"]
        keys = sorted(q["criteria"]) if kind != "score" else [str(i) for i in range(len(q["criteria"]))]
        # The toy fixture asks to select a directly supplied key. This is not
        # connected to the evaluation corpus or the production NativeEngine.
        target = q["state"].get("target", keys[0]) if isinstance(q["state"], dict) else keys[0]
        logits = [2.0 if k == target else 0.0 for k in keys]
        probs = dict(zip(keys, runner.softmax(logits, self.temperature)))
        answer = {"type": kind, "label": target, "probabilities": probs,
                  "candidate_keys": keys, "candidate_logits": logits,
                  "batch_size": 1, "input_tokens": 100, "output_tokens": 0,
                  "latency_ms": 1., "model_ms": .8, "confidence": .4,
                  "native_decode_count": 1, "native_total_decode_count": self.total_decode_count}
        if kind == "choice":
            answer["choice"] = target
        elif kind == "noul":
            answer["noul"] = probs["true"]
        else:
            answer["score"] = sum(int(k)*probs[k] for k in keys)
        return answer

    def close(self):
        self.closed = True


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
    def setUp(self):
        # Fixtures do not depend on real runtime files being packaged yet.
        source_patch = patch.object(runner, "source_paths", return_value=[Path(__file__).resolve()])
        source_patch.start()
        self.addCleanup(source_patch.stop)

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
        with self.assertRaisesRegex(RuntimeError, "0 llama_decode API calls"):
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
            self.assertEqual(result["actual_llama_decode_calls"], 3207)
            self.assertEqual(result["decode_count_semantics"], "llama_decode_API_calls")
            self.assertEqual(result["overall"]["count"], 2400)
            self.assertEqual(result["manual"]["count"], 180)
            self.assertEqual(result["candidate_order"]["consistency"], 1.)
            self.assertEqual(len((out / "predictions.jsonl").read_text().splitlines()), 2400)
            self.assertTrue(all(set(q) == set(runner.INPUT_KEYS) for q in engine.seen_questions))
            self.assertTrue(engine.closed)

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
            self.assertEqual(result["actual_llama_decode_calls"], 127)
            self.assertEqual(result["temperature"], .1)
            self.assertLess(result["nll_after"], result["nll_before"])

    def test_returned_decode_counter_must_match_live_counter(self):
        engine = FakeEngine()
        counter = runner.ForwardCounter(engine)
        original = engine.decide
        def wrong(q):
            result = original(q)
            result["native_total_decode_count"] = 999
            return result
        engine.decide = wrong
        with self.assertRaisesRegex(RuntimeError, "counters do not match"):
            runner.actual_forward(engine, counter, runner.question(fixture_case()))
        counter.close()

    def test_native_config_paths_resolve_against_config_directory(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)/"config.json"
            p.write_text(json.dumps({"engine":{"model_file":"models/a.gguf","native_binary":"native/bin/helper",
                                                "model_manifest":"native_model.json","native_manifest":"native/BUILD.json","threads":6,"device":"metal","dtype":"Q4_K_M"}}))
            result = runner.load_config(p)
            self.assertEqual(result["model_file"], str((Path(td)/"models/a.gguf").resolve()))
            self.assertEqual(result["native_binary"], str((Path(td)/"native/bin/helper").resolve()))
            self.assertEqual(result["native_manifest"], str((Path(td)/"native/BUILD.json").resolve()))
            self.assertEqual(result["device"], "metal")

    def test_engine_closes_if_freeze_creation_fails(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            calibration, config = base/"cal.jsonl", base/"config.json"
            write_fixture(calibration, 40, "cal")
            config.write_text("{}")
            args = argparse.Namespace(command="calibrate", config=config,
                                      calibration=calibration, output_dir=base)
            engine = FakeEngine()
            with patch.object(runner,"setup_engine",return_value=(engine,{},0.)), patch.object(runner,"FreezeGuard",side_effect=RuntimeError("freeze failure")):
                with self.assertRaisesRegex(RuntimeError,"freeze failure"):
                    runner.run_calibrate(args)
            self.assertTrue(engine.closed)

    def test_cli_preserves_failure_and_refuses_existing_run(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td)/"new-run"
            argv = ["runner","calibrate","--config",str(Path(td)/"config.json"),"--output-dir",str(out)]
            with patch.object(runner.sys,"argv",argv), patch.object(runner,"run_calibrate",side_effect=RuntimeError("fixture failure")) as run, contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(runner.main(),2)
                failure = (out/"failure.json").read_bytes()
                self.assertIn(b"fixture failure",failure)
                self.assertEqual(runner.main(),2)
                self.assertEqual((out/"failure.json").read_bytes(),failure)
                self.assertEqual(run.call_count,1)


def artifact_fixture(base):
    binary = base/"native/bin/llama-decision-helper"
    binary.parent.mkdir(parents=True)
    binary.write_bytes(b"fake binary fixture")
    lib = binary.with_name("libfixture.dylib")
    lib.write_bytes(b"fake dylib fixture")
    cpp = base/"native/llama_decision_helper.cpp"
    cpp.write_text("// fake source fixture\n")
    build = base/"native/BUILD.json"
    build.write_text(json.dumps({"llama_cpp_commit":"fixture", "sha256":{
        binary.name:runner.sha256(binary),lib.name:runner.sha256(lib)}}))
    model = base/"fixture.gguf"
    model.write_bytes(b"fake weights fixture")
    meta = base/"native_model.json"
    meta.write_text(json.dumps({"schema_version":1,"role":"decision_model","repo_id":"unit-fixture",
        "revision":"unit-revision","filename":model.name,"bytes":model.stat().st_size,
        "sha256":runner.sha256(model),"quantization":"Q4_K_M"}))
    kwargs = {"model_file":str(model),"native_binary":str(binary),"model_manifest":str(meta),
              "model":"unit-fixture","revision":"unit-revision","dtype":"Q4_K_M"}
    return kwargs, model, binary, lib, cpp, build, meta


class ArtifactTests(unittest.TestCase):
    def test_extended_build_files_and_symlinks_are_pinned(self):
        with tempfile.TemporaryDirectory() as td:
            kwargs, model, binary, lib, cpp, build, *_ = artifact_fixture(Path(td))
            alias = lib.with_name("libalias.dylib")
            alias.symlink_to(lib.name)
            license_file = build.with_name("LICENSE.txt")
            license_file.write_text("fixture license")
            metadata = json.loads(build.read_text())
            metadata["files_sha256"] = {"LICENSE.txt":runner.sha256(license_file),cpp.name:runner.sha256(cpp)}
            metadata["symlinks"] = {"bin/"+alias.name:lib.name}
            build.write_text(json.dumps(metadata))
            kwargs["native_manifest"] = str(build)
            snapshot = runner.NativeArtifacts(kwargs)
            self.assertIn(license_file,snapshot.small_paths)
            self.assertIn(alias,snapshot.small_paths)
            alias.unlink()
            alias.symlink_to(binary.name)
            with self.assertRaisesRegex(RuntimeError,"artifact changed"):
                snapshot.check()
            with self.assertRaisesRegex(ValueError,"symlink mismatch"):
                runner.NativeArtifacts(kwargs)

    def test_source_edit_during_weight_verification_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            kwargs, model, binary, lib, cpp, *_ = artifact_fixture(Path(td))
            original = runner.sha256
            def mutate_during_model_hash(path):
                result = original(path)
                if Path(path) == model:
                    cpp.write_text("// changed during model verification\n")
                return result
            with patch.object(runner,"sha256",side_effect=mutate_during_model_hash):
                with self.assertRaisesRegex(RuntimeError,"changed during initial verification"):
                    runner.NativeArtifacts(kwargs)

    def test_model_is_hashed_once_and_stat_replacement_detected(self):
        with tempfile.TemporaryDirectory() as td:
            kwargs, model, *_ = artifact_fixture(Path(td))
            original = runner.sha256
            calls = []
            def counted(path):
                if Path(path) == model:calls.append(path)
                return original(path)
            with patch.object(runner,"sha256",side_effect=counted):
                snapshot = runner.NativeArtifacts(kwargs)
                snapshot.check();snapshot.check()
            self.assertEqual(len(calls),1)
            model.write_bytes(b"changed weights fixture")
            with self.assertRaisesRegex(RuntimeError,"weight file changed"):
                snapshot.check()

    def test_small_artifacts_inventory_and_hash_are_enforced(self):
        with tempfile.TemporaryDirectory() as td:
            kwargs, model, binary, lib, cpp, *_ = artifact_fixture(Path(td))
            snapshot = runner.NativeArtifacts(kwargs)
            self.assertIn(cpp,snapshot.small_paths)
            extra = lib.with_name("additional.dylib")
            extra.write_bytes(b"unexpected")
            with self.assertRaisesRegex(RuntimeError,"inventory changed"):
                snapshot.check()
            extra.unlink()
            lib.write_bytes(b"changed")
            with self.assertRaisesRegex(RuntimeError,"artifact changed"):
                snapshot.check()

    def test_pinned_manifest_mismatch_rejected_before_engine_load(self):
        with tempfile.TemporaryDirectory() as td:
            kwargs, model, *_ = artifact_fixture(Path(td))
            model.write_bytes(b"same bytes different identity")
            with self.assertRaisesRegex(ValueError,"size mismatch|checksum mismatch"):
                runner.NativeArtifacts(kwargs)

    def test_extra_artifact_manifest_and_loaded_engine_identity(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            kwargs, model, binary, *_ = artifact_fixture(base)
            additional = base/"settings.txt"
            additional.write_text("fixture")
            manifest = base/"extra.json"
            manifest.write_text(json.dumps({"artifacts":[{"role":"build_settings","path":"settings.txt","sha256":runner.sha256(additional)}]}))
            snapshot = runner.NativeArtifacts(kwargs,manifest)
            self.assertIn(additional.resolve(),[p.resolve() for p in snapshot.small_paths])
            engine = FakeEngine()
            engine.model_file=model;engine.native_binary=binary
            snapshot.bind_engine(engine)
            engine.model_revision="wrong-revision"
            with self.assertRaisesRegex(ValueError,"identity does not match"):
                snapshot.bind_engine(engine)


if __name__ == "__main__":
    unittest.main()
