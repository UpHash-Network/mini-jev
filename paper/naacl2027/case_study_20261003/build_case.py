#!/usr/bin/env python3
"""Project an already public synthetic diagnostic; no inference or new outcomes.

Run without arguments to check retained outputs. --write creates/replaces only
the generated files in this new case directory, never the source evidence.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
BUNDLE = HERE.parent / "generality_20261003/publication/bundle_v1"
EARLY = "provenance/earlier_synthetic_only/"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def encoded(obj):
    return json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False) + "\n"


def softmax(logits):
    exps = [math.exp(x - max(logits)) for x in logits]
    return [x / sum(exps) for x in exps]


def build():
    manifest = json.loads((BUNDLE / "MANIFEST.json").read_text())
    sources = {}

    def read(name):
        path = BUNDLE / name
        digest = sha(path)
        assert digest == manifest["files_sha256"][name], name
        sources[str(path.relative_to(REPO))] = digest
        return json.loads(path.read_text())

    diagnostic_name = EARLY + "PHI_SYNTHETIC_FAILURE_DIAGNOSIS.json"
    repeat_name = EARLY + "PHI_FULL_POSITION_REPEAT.json"
    diagnostic = read(diagnostic_name)
    repeat = read(repeat_name)
    original = read(EARLY + "v1_COMPLETION.json")
    original_attempt = read(EARLY + "v1_ATTEMPT.json")
    amendment = read("code/AMENDMENT.json")
    freeze = read("provenance/FREEZE.public.json")
    result = read("RESULTS.json")
    assert original["recorded_requests"] == 0
    assert original["actual_calls_including_excluded"] == 24
    assert diagnostic["forward_calls"] == 24 and repeat["calls"] == 24
    assert len(diagnostic["checks"]) == len(repeat["checks"]) == 12
    assert diagnostic["probability_atol"] == 1e-5
    assert amendment["benchmark_results_available_when_amended"] is False
    assert original["created_at"] < amendment["created_at"] < freeze["created_at"]

    # Each provenance line points to the first line of the original logit array,
    # not to an invented JSONL row in the source JSON object.
    def locations(name, field):
        lines = (BUNDLE / name).read_text().splitlines()
        return [i + 1 for i, line in enumerate(lines)
                if line.strip() == '"' + field + '": [']

    line_maps = {(name, field): locations(name, field) for name, field in [
        (diagnostic_name, "optimized_logits"),
        (diagnostic_name, "full_position_logits"),
        (repeat_name, "a"), (repeat_name, "b")]}
    assert all(len(v) == 12 for v in line_maps.values())
    runtime = read("observations/phi-4-mini/RUNTIME.json")
    assert runtime["logits_to_keep"] == 0
    assert runtime["dtype"] == "float32" and runtime["device"] == "mps"
    model = "Phi-4-mini@" + runtime["revision"] + "/float32-MPS-eager"
    records, fixtures, mapping = [], [], []
    for i, (d, r) in enumerate(zip(diagnostic["checks"], repeat["checks"])):
        assert d["fixture"] == r["fixture"]
        keys = d["candidate_keys"]
        kind = d["fixture"].split("-")[1]
        assert kind in ["choice", "noul", "score"]
        a, b = softmax(d["optimized_logits"]), softmax(d["full_position_logits"])
        delta = max(abs(x - y) for x, y in zip(a, b))
        assert abs(delta - d["max_absolute_probability_difference"]) < 1e-14
        for field, values in [("optimized_probabilities", a), ("full_position_probabilities", b)]:
            assert max(abs(values[j] - d[field][k]) for j, k in enumerate(keys)) < 1e-14
        assert d["labels_equal"] is True
        assert r["a"] == r["b"] and r["max_abs_difference"] == 0
        assert d["passed"] == (delta <= diagnostic["probability_atol"])
        fixtures.append({"fixture": d["fixture"], "type": kind,
                         "diagnostic_max_abs_probability_difference": delta,
                         "diagnostic_max_abs_logit_difference": d["max_absolute_logit_difference"],
                         "diagnostic_labels_equal": True,
                         "diagnostic_passed": d["passed"],
                         "full_repeat_max_abs_logit_difference": 0.0})
        conditions = [
            (diagnostic_name, "optimized_logits", "diagnostic_last_position_only", d),
            (diagnostic_name, "full_position_logits", "diagnostic_stock_full_position", d),
            (repeat_name, "a", "repeat_stock_full_position_a", r),
            (repeat_name, "b", "repeat_stock_full_position_b", r)]
        for name, field, condition, source in conditions:
            path = BUNDLE / name
            digest = sha(path)
            pointer = f"/checks/{i}/{field}"
            record = {"schema_version": 1, "kind": "physical", "model": model,
                      "item_id": d["fixture"], "type": kind, "condition": condition,
                      "source_id": digest + "#checks/" + str(i) + "/" + field,
                      "key_schema": "retained-synthetic-fixture-" + diagnostic["fixtures_sha256"],
                      "candidate_keys": keys, "candidate_count": len(keys),
                      "distribution_scope": "full_candidate_set",
                      "logits": source[field], "temperature": 1,
                      "provenance": {"file_id": str(path.relative_to(REPO)),
                                     "line_1based": line_maps[(name, field)][i],
                                     "file_sha256": digest},
                      "note": "Retrospective projection of a measured synthetic check, not a benchmark or human observation. Original JSON pointer " + pointer + ". The original 24-call failure has no detailed gate; these are subsequent diagnostic/repeat observations. Full-position refers to input positions, not a selected-vocabulary-row optimization. Reference and latency were not recorded."}
            if kind == "score":
                record["score_values"] = [int(k) for k in keys]
            records.append(record)
            mapping.append({"jsonl_line_1based": len(records), "source_id": record["source_id"],
                            "original_json_pointer": pointer, **record["provenance"]})

    completions = {}
    all_rows = 0
    for model_key in ["phi-4-mini", "qwen2.5-1.5b"]:
        completion = read(f"observations/{model_key}/COMPLETION.json")
        gate = read(f"observations/{model_key}/REPEATABILITY_GATE.json")
        attempt = read(f"observations/{model_key}/ATTEMPT.json")
        assert freeze["created_at"] < attempt["created_at"] < completion["created_at"]
        assert completion["status"] == "completed" and completion["failed_requests"] == 0
        assert gate["passed"] and gate["english"]["passed"]
        assert all(c["max_absolute_logit_difference"] == 0 for c in gate["checks"])
        assert gate["english"]["repeat_a_logits"] == gate["english"]["repeat_b_logits"]
        for dataset in ["JCommonsenseQA", "CommonsenseQA"]:
            name = f"observations/{model_key}/{dataset}.jsonl"
            path = BUNDLE / name
            sources[str(path.relative_to(REPO))] = sha(path)
            assert sha(path) == manifest["files_sha256"][name]
            rows = [json.loads(line) for line in path.read_text().splitlines()]
            assert len(rows) == 1200 and all(not row.get("error") for row in rows)
            all_rows += len(rows)
        completions[model_key] = {k: completion[k] for k in [
            "created_at", "recorded_requests", "failed_requests", "actual_calls_including_excluded", "excluded_calls"]}
    assert all_rows == 4800
    assert sum(not f["diagnostic_passed"] for f in fixtures) == 2
    primary = result["strata"]["phi-4-mini/CommonsenseQA"]
    retained_null = {
        "all_four_pair_error_AP_contrasts": {
            key: value["A"]["pair_mean_label_error"]["primary_contrast"]["ap"]
            for key, value in result["strata"].items()},
        "primary_phi_english_720_call_correct_counts": {
            curve["policy"]: curve["correct"] for curve in primary["B"]["curves"]
            if curve["calls"] == 720}}
    assert all(v["difference"] < 0 and v["ci95"]["low"] < 0 < v["ci95"]["high"]
               for v in retained_null["all_four_pair_error_AP_contrasts"].values())
    evidence = {
        "schema_version": 1,
        "case_type": "retrospective_author_and_AI_assisted_engineering_case",
        "new_model_inference_calls": 0, "human_participants": 0,
        "original_detection_route": "CLI synthetic gate and saved logs; no evidence of original GUI discovery",
        "measurement_scope": "One Mac; stock last-position-only versus stock all-position full-vocabulary projection; not selected-row projection.",
        "original_failed_attempt": {"started_at": original_attempt["created_at"],
                                    "completed_at": original["created_at"],
                                    "actual_calls": 24, "benchmark_calls": 0,
                                    "detailed_gate_retained": False,
                                    "receipt_excluded_calls_28_is_planned_not_executed": True},
        "subsequent_diagnosis": {"comparison_calls": 24, "repeat_calls": 24,
                                 "benchmark_calls": 0,
                                 "probability_atol": 1e-5,
                                 "failed_comparisons": 2, "total_comparisons": 12,
                                 "all_labels_equal": True,
                                 "max_abs_probability_difference": max(f["diagnostic_max_abs_probability_difference"] for f in fixtures),
                                 "cause": "Not isolated; shape-dependent floating-point rounding is a hypothesis, not an observed causal explanation.",
                                 "fixtures": fixtures},
        "amendment": {"created_at": amendment["created_at"],
                      "v2_freeze_at": freeze["created_at"],
                      "original_v2_freeze_sha256": manifest["original_v2_freeze_sha256"],
                      "change": amendment["remedy"],
                      "no_benchmark_results_available": True,
                      "independent_preregistration": False},
        "completed_v2": completions,
        "total_call_accounting": {"measured": 4800, "initial_failure": 24,
                                  "subsequent_diagnosis": 48, "v2_checks": 56, "total": 4928},
        "retained_negative_results": retained_null,
        "import_projection": {"records": 48, "groups": 12,
                              "selection": "All 12 recorded fixtures and all four diagnostic/repeat observations; no outcome selection.",
                              "provenance_semantics": "Original JSON file, SHA-256, first logit-array line, and JSON pointer; physical identities are source assertions verified locally by this adapter.",
                              "source_mapping": mapping},
        "baseline_fairness": {"same_data_full_json_available": True,
                              "sources": [str((BUNDLE / diagnostic_name).relative_to(REPO)), str((BUNDLE / repeat_name).relative_to(REPO))],
                              "baseline_equivalence": "JSON contains the same complete logits and diagnostic probabilities; a JSON reader or script can recover every comparison. UI is a retrospective presentation, not privileged evidence.",
                              "not_measured": ["human completion time", "human error rate", "discovery advantage", "online latency gain", "benchmark accuracy repair"]},
        "sources_sha256": sources,
        "public_bundle_manifest_sha256": sha(BUNDLE / "MANIFEST.json")}
    jsonl = "".join(json.dumps(r, ensure_ascii=False, separators=(",", ":"), allow_nan=False) + "\n" for r in records)
    return {"CASE_EVIDENCE.json": encoded(evidence), "diagnostic_import.jsonl": jsonl}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    files = build()
    for name, content in files.items():
        path = HERE / name
        if args.write:
            path.write_text(content)
        else:
            assert path.read_text() == content, name + " differs from source-derived output"
    print(json.dumps({"passed": True, "files": {name: sha(HERE / name) for name in files},
                      "new_inference_calls": 0, "rows": 48, "groups": 12}))


if __name__ == "__main__":
    main()
