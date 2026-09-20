#!/usr/bin/env python3
"""Validate a saved residual head and time real baseline/head model forwards.

Uses one HeadMiniJev instance; no model selection or fitting occurs here.
Latency cases are taken in file order and their gold labels are discarded.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import platform
import random
import statistics
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def latency_summary(values: list[float]) -> dict:
    ordered = sorted(values)
    point = (len(ordered) - 1) * 0.95
    lo, hi = math.floor(point), math.ceil(point)
    return {
        "n": len(values),
        "median_ms": statistics.median(values),
        "p95_ms": ordered[lo] + (ordered[hi] - ordered[lo]) * (point - lo),
        "mean_ms": statistics.mean(values),
        "min_ms": min(values),
        "max_ms": max(values),
    }


def run(args: argparse.Namespace, result: dict) -> None:
    import torch
    from safetensors.torch import load_file

    from head_jev import HeadMiniJev
    from mini_jev import MiniJev, options_for
    from train_head import extract, get_logits, masked_logits, read_cases

    def check(name: str, passed: bool, **details) -> None:
        result["checks"].append({"name": name, "passed": bool(passed), **details})
        print(f"[{'PASS' if passed else 'FAIL'}] {name}", flush=True)

    checkpoint = args.head
    config_path = checkpoint / "config.json"
    weight_path = checkpoint / "head.safetensors"
    before = {"config.json": sha256(config_path), "head.safetensors": sha256(weight_path)}
    config = json.loads(config_path.read_text())
    weights = load_file(str(weight_path), device="cpu")
    result["checkpoint"] = {
        "path": str(checkpoint.resolve()),
        "sha256_before": before,
        "model": config["model"],
        "model_revision": config["model_revision"],
        "temperature": config["temperature"],
        "config_trainable_parameters": config["trainable_parameters"],
        "tensors": {
            key: {"shape": list(value.shape), "dtype": str(value.dtype), "numel": value.numel()}
            for key, value in weights.items()
        },
    }
    check("checkpoint_tensor_keys", set(weights) == {"delta_weight", "delta_bias"})
    check("six_candidate_head", config["max_choices"] == 6)
    check("head_parameter_count_9222", sum(value.numel() for value in weights.values()) == 9222,
          actual=sum(value.numel() for value in weights.values()), expected=9222)
    check("config_parameter_count_matches", config["trainable_parameters"] == sum(value.numel() for value in weights.values()))
    check("checkpoint_weights_finite", all(bool(torch.isfinite(value).all()) for value in weights.values()))

    experiment_path = checkpoint.parent / "experiment.json"
    if experiment_path.exists():
        experiment = json.loads(experiment_path.read_text())
        recorded = experiment.get("checkpoint_sha256_before_and_after_test")
        check("training_checkpoint_sha_matches", recorded == before["head.safetensors"],
              recorded=recorded, actual=before["head.safetensors"])

    print(f"Loading one HeadMiniJev instance: {checkpoint}", flush=True)
    started = time.perf_counter()
    engine = HeadMiniJev(checkpoint, device=args.device, use_temperature=True)
    result["runtime"] = {
        "model": engine.model_id,
        "device": str(engine.device),
        "dtype": str(engine.dtype),
        "torch": torch.__version__,
        "python": platform.python_version(),
        "platform": platform.platform(),
        "model_instances_loaded": 1,
        "load_seconds_excluded_from_latency": time.perf_counter() - started,
    }
    hidden_size = int(engine.model.config.hidden_size)
    check("head_shapes", list(weights["delta_weight"].shape) == [6, hidden_size]
          and list(weights["delta_bias"].shape) == [6], hidden_size=hidden_size,
          expected_weight_shape=[6, hidden_size], expected_bias_shape=[6])
    check("backbone_frozen", not any(parameter.requires_grad for parameter in engine.model.parameters()))
    check("backbone_no_accumulated_gradients", all(parameter.grad is None for parameter in engine.model.parameters()))
    check("backbone_eval_mode", not engine.model.training)
    check("temperature_positive_finite", math.isfinite(engine.temperature) and engine.temperature > 0)

    # Select by type and token length only. Targets cannot influence selection.
    dev = read_cases(args.dev)
    prepared = [(case, len(engine._prepare(case)[1])) for case in dev]
    chosen = []
    for kind in ("choice", "noul", "score"):
        candidates = sorted(
            [(case, length) for case, length in prepared if case["type"] == kind],
            key=lambda item: (item[1], item[0]["id"]),
        )
        if len(candidates) < 2:
            raise ValueError(f"Need at least two dev cases of type {kind}")
        chosen.extend([candidates[0][0], candidates[-1][0]])
    token_lengths = [len(engine._prepare(case)[1]) for case in chosen]
    counts = [len(options_for(case)) for case in chosen]
    result["dev_validation"] = {
        "data_path": str(args.dev.resolve()),
        "data_sha256": sha256(args.dev),
        "selection": "shortest and longest tokenized case per type; ties by ID; labels unused",
        "case_ids": [case["id"] for case in chosen],
        "input_tokens": token_lengths,
        "candidate_counts": counts,
        "absolute_tolerance": args.atol,
        "relative_tolerance": 0,
        "reference": "CPU feature tensors plus saved CPU residual weights; no target values used in probability calculation",
    }
    check("six_dev_cases", len(chosen) == 6)
    check("variable_length_batch", len(set(token_lengths)) > 1, token_lengths=token_lengths)
    check("variable_candidate_counts", len(set(counts)) > 1, candidate_counts=counts)

    features = extract(engine, chosen, args.cache, "validation_dev6", batch_size=1, max_choices=6)
    check("reference_features_on_cpu", all(value.device.type == "cpu" for value in features.values()))
    reference_logits = get_logits(features, weights["delta_weight"], weights["delta_bias"])
    reference_probabilities = masked_logits(reference_logits / engine.temperature, features["count"]).softmax(-1)
    raw_probabilities = masked_logits(reference_logits, features["count"]).softmax(-1)
    check("temperature_preserves_cached_argmax",
          bool(reference_probabilities.argmax(-1).eq(raw_probabilities.argmax(-1)).all()))

    # These calls run the backbone again, independently from cached features.
    singles = [engine.decide(case) for case in chosen]
    batched = engine.decide_many(chosen)
    saved_temperature, saved_applied = engine.temperature, engine.temperature_applied
    try:
        engine.temperature, engine.temperature_applied = 1.0, False
        without_temperature = engine.decide_many(chosen)
    finally:
        engine.temperature, engine.temperature_applied = saved_temperature, saved_applied
    check("temperature_preserves_api_argmax", all(
        before_result["label"] == after_result["label"]
        for before_result, after_result in zip(without_temperature, batched)
    ))

    maximum_differences = {"single_vs_cpu_cache": 0.0, "batch_vs_cpu_cache": 0.0,
                           "batch_vs_single": 0.0, "no_temperature_vs_cpu_cache": 0.0}
    case_details = []
    keys_match = True
    for index, (case, single, batch, no_temperature) in enumerate(zip(chosen, singles, batched, without_temperature)):
        keys = [key for key, _ in options_for(case)]
        expected = reference_probabilities[index, :len(keys)].tolist()
        expected_raw = raw_probabilities[index, :len(keys)].tolist()
        for output in (single, batch, no_temperature):
            keys_match = keys_match and list(output["probabilities"]) == keys and output["candidate_keys"] == keys
        p_single = [single["probabilities"][key] for key in keys]
        p_batch = [batch["probabilities"][key] for key in keys]
        p_raw = [no_temperature["probabilities"][key] for key in keys]
        differences = {
            "single_vs_cpu_cache": max(abs(a - b) for a, b in zip(p_single, expected)),
            "batch_vs_cpu_cache": max(abs(a - b) for a, b in zip(p_batch, expected)),
            "batch_vs_single": max(abs(a - b) for a, b in zip(p_batch, p_single)),
            "no_temperature_vs_cpu_cache": max(abs(a - b) for a, b in zip(p_raw, expected_raw)),
        }
        for key, value in differences.items():
            maximum_differences[key] = max(maximum_differences[key], value)
        case_details.append({
            "case_id": case["id"], "type": case["type"], "candidate_keys": keys,
            "reference_probabilities": dict(zip(keys, expected)),
            "single_probabilities": single["probabilities"],
            "batch_probabilities": batch["probabilities"],
            "without_temperature_probabilities": no_temperature["probabilities"],
            "absolute_differences": differences,
            "single_label": single["label"], "batch_label": batch["label"],
            "without_temperature_label": no_temperature["label"],
        })
    check("semantic_candidate_keys_match", keys_match)
    for name, difference in maximum_differences.items():
        check(name, difference <= args.atol, maximum_absolute_difference=difference, atol=args.atol)
    result["dev_validation"].update(maximum_absolute_differences=maximum_differences, cases=case_details)

    # Only prompt inputs are compared: mutation of an ignored field must not
    # change token IDs or option mappings. This does not depend on model output.
    gold_checks = []
    for case in chosen:
        altered = copy.deepcopy(case)
        altered["label"] = "__GOLD_LABEL_MUST_NOT_ENTER_PROMPT_7391__"
        removed = {key: value for key, value in case.items() if key != "label"}
        original_prepared = engine._prepare(case)
        unchanged = original_prepared == engine._prepare(altered) == engine._prepare(removed)
        gold_checks.append({"case_id": case["id"], "unchanged": unchanged})
    check("gold_label_excluded_from_prompt", all(item["unchanged"] for item in gold_checks), cases=gold_checks)

    oversized = {"type": "choice", "state": "7候補の入力上限検証。", "instructions": "適切なものを選んでください。",
                 "criteria": {f"key_{index}": f"候補{index}" for index in range(7)}}
    for name, call in (
        ("single_rejects_more_than_six_choices", lambda: engine.decide(oversized)),
        ("batch_rejects_more_than_six_choices", lambda: engine.decide_many([chosen[0], oversized])),
    ):
        try:
            call()
        except ValueError as error:
            check(name, "at most 6 choices" in str(error), error=str(error))
        else:
            check(name, False, error="No ValueError was raised")

    # The latency set is opened only after validation selection and comparisons.
    # Discard labels immediately and never calculate test accuracy in this file.
    latency_cases = []
    for line in args.latency_data.read_text().splitlines():
        if line.strip():
            case = json.loads(line)
            latency_cases.append({key: value for key, value in case.items() if key != "label"})
        if len(latency_cases) == 12:
            break
    if len(latency_cases) != 12:
        raise ValueError("Latency dataset must contain at least 12 cases")

    def forward(method: str, case: dict) -> dict:
        if method == "baseline":
            # Explicit base implementation avoids dispatching to the trained
            # override while reusing this one frozen backbone in memory.
            return MiniJev.decide_many(engine, [case], projection="selected")[0]
        return engine.decide(case)

    rng = random.Random(args.seed)
    for repetition in range(2):
        for method in ("baseline", "head"):
            forward(method, latency_cases[0])
            print(f"[latency warmup {repetition + 1}/2] {method}", flush=True)
    measurements = []
    for repetition in range(3):
        for index, case in enumerate(latency_cases):
            order = ["baseline", "head"]
            rng.shuffle(order)
            for method in order:
                output = forward(method, case)
                measurements.append({
                    "case_id": case.get("id", str(index)), "type": case["type"],
                    "repetition": repetition + 1, "method": method, "execution_order": order,
                    "input_tokens": output["input_tokens"], "latency_ms": output["latency_ms"],
                    "model_ms": output["model_ms"],
                })
            print(f"[latency repetition {repetition + 1}/3] {index + 1}/12 {case.get('id', index)}", flush=True)
    latency = {
        "data_path": str(args.latency_data.resolve()), "data_sha256": sha256(args.latency_data),
        "case_ids": [case.get("id") for case in latency_cases],
        "selection": "first 12 cases in file order; labels discarded before forward calls",
        "case_count": 12, "repetitions_per_case_method": 3, "warmup_calls_per_method": 2,
        "methods_were_also_used_during_validation": True,
        "seed": args.seed, "gold_labels_used": False, "model_selection_performed": False,
        "measurement": "real device-synchronized backbone forward for every call; no feature cache",
        "device": str(engine.device), "gpu_forward": engine.device.type in ("cuda", "mps"),
        "baseline_call": "MiniJev.decide_many(engine, [case], projection='selected')[0]",
        "head_temperature": engine.temperature,
        "load_warmup_and_feature_extraction_excluded": True,
        "p95_definition": "linear interpolation over 36 sequential calls per method",
        "summary": {}, "measurements": measurements,
    }
    for method in ("baseline", "head"):
        rows = [row for row in measurements if row["method"] == method]
        latency["summary"][method] = {
            "latency": latency_summary([row["latency_ms"] for row in rows]),
            "model": latency_summary([row["model_ms"] for row in rows]),
        }
    latency["head_over_baseline_median_latency_ratio"] = (
        latency["summary"]["head"]["latency"]["median_ms"]
        / latency["summary"]["baseline"]["latency"]["median_ms"]
    )
    result["latency"] = latency
    check("latency_measurements_complete", len(measurements) == 72)
    check("latency_measurements_finite_positive", all(
        math.isfinite(row[key]) and row[key] > 0
        for row in measurements for key in ("latency_ms", "model_ms")
    ))
    check("backbone_still_frozen_after_inference", not any(parameter.requires_grad for parameter in engine.model.parameters()))
    check("backbone_still_has_no_gradients", all(parameter.grad is None for parameter in engine.model.parameters()))
    after = {"config.json": sha256(config_path), "head.safetensors": sha256(weight_path)}
    result["checkpoint"]["sha256_after"] = after
    check("checkpoint_unchanged", before == after)


def main() -> None:
    here = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--head", type=Path, default=here / "results/head/checkpoint")
    parser.add_argument("--dev", type=Path, default=here / "data/head_dev.jsonl")
    parser.add_argument("--latency-data", type=Path, default=here / "data/head_test_ja.jsonl")
    parser.add_argument("--output", type=Path, default=here / "results/head/validation.json")
    parser.add_argument("--cache", type=Path, default=here / ".cache/head_validation_features")
    parser.add_argument("--device", default="auto")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--atol", type=float, default=1e-4)
    args = parser.parse_args()
    if not math.isfinite(args.atol) or args.atol <= 0:
        parser.error("--atol must be finite and positive")
    result = {
        "schema_version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "purpose": "implementation validation and actual inference latency; no fitting or model selection",
        "checks": [],
        "passed": False,
    }
    try:
        run(args, result)
        result["passed"] = bool(result["checks"]) and all(check["passed"] for check in result["checks"])
    except Exception as error:
        result["error"] = {"type": type(error).__name__, "message": str(error), "traceback": traceback.format_exc()}
        print(result["error"]["traceback"], flush=True)
    finally:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
        print(f"Saved validation: {args.output.resolve()} (passed={result['passed']})", flush=True)
    if not result["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
