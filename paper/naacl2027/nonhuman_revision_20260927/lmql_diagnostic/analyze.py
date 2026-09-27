"""Post-hoc diagnostics of the frozen 12-case LMQL run; stdlib, no inference.

Run with Python 3. Outputs are confined to this directory. Original study files
are read-only. This is an arithmetic reanalysis, not an independent replication.
"""
import hashlib
import json
import math
import struct
from pathlib import Path

HERE = Path(__file__).resolve().parent
STUDY = HERE.parents[1] / "comparator_study"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def softmax(xs):
    exps = [math.exp(x - max(xs)) for x in xs]
    total = math.fsum(exps)
    return [x / total for x in exps]


def f32(x):
    return struct.unpack("f", struct.pack("f", x))[0]


def linf(a, b):
    return max(abs(x - y) for x, y in zip(a, b))


def load(name):
    return json.loads((STUDY / name).read_text())


def main():
    # Hash only the local evidence used here, not the original model/environment.
    names = ["CASES.json", "FREEZE.json", "PROTOCOL.ja.md", "run.py",
             "make_cases.py", "llama_lmql_helper.cpp", "run_v1/results.jsonl",
             "run_v1/SUMMARY.json", "run_v1/AUDIT.json"]
    before = {n: sha(STUDY / n) for n in names}
    receipt, freeze = load("run_v1/SUMMARY.json"), load("FREEZE.json")
    cases = load("CASES.json")
    rows = [json.loads(line) for line in
            (STUDY / "run_v1/results.jsonl").read_text().splitlines()]
    assert before["run_v1/results.jsonl"] == receipt["results_sha256"] == \
        "7d26f5b873ba8c495573275da470a91d5f87c6b5b04af34c31b70935c57fa9ea"
    assert before["FREEZE.json"] == receipt["freeze_sha256"]
    for name in ["CASES.json", "PROTOCOL.ja.md", "run.py", "make_cases.py",
                 "llama_lmql_helper.cpp"]:
        key = "outputs/mini-jev-naacl2027/paper/naacl2027/comparator_study/" + name
        assert before[name] == freeze["files_sha256"][key]
    assert receipt["status"] == "complete" and not receipt["fixture_only_not_model_evidence"]
    assert len(cases) == len(rows) == 12
    assert [r["case_id"] for r in rows] == [c["case_id"] for c in cases]

    diagnostic_rows, counters = [], []
    for case, row in zip(cases, rows):
        direct = row["native_direct"]
        labels, ids = row["candidate_labels"], row["candidate_token_ids"]
        assert labels == case["request"]["candidates"]
        assert ids == direct["candidate_ids"]
        assert row["input_token_ids"] == direct["input_token_ids"]
        assert direct["prompt"] == case["prompt"]
        assert hashlib.sha256(case["prompt"].encode()).hexdigest() == row["prompt_sha256"]
        assert row["lmql_num_value_tokens"] == [1] * len(labels)
        assert len(row["lmql_backend_trace"]) == len(labels)
        counters.append(direct["total_decode_count"])
        trace_by_id = {}
        for trace in row["lmql_backend_trace"]:
            req, resp = trace["request"], trace["response"]
            assert req["input_token_ids"][:-1] == row["input_token_ids"]
            assert resp["input_token_ids"] == req["input_token_ids"]
            assert resp["state_cleared"] and resp["decode_count"] == 1
            assert len(resp["scores"]) == len(req["input_token_ids"])
            assert abs(resp["scores"][-1] -
                       (resp["final_logit"] - resp["final_vocabulary_logsumexp"])) < 1e-12
            tid = req["input_token_ids"][-1]
            assert tid not in trace_by_id
            trace_by_id[tid] = resp
            counters.append(resp["total_decode_count"])
        assert set(trace_by_id) == set(ids)
        raw_logits = [trace_by_id[t]["final_logit"] for t in ids]
        logprobs = [trace_by_id[t]["scores"][-1] for t in ids]
        lses = [trace_by_id[t]["final_vocabulary_logsumexp"] for t in ids]
        assert row["lmql_scores"] == [f32(x) for x in logprobs]
        p, q = direct["probabilities"], row["lmql_probabilities"]
        assert all(math.isfinite(x) and 0 <= x <= 1 for x in p + q)
        assert abs(math.fsum(p) - 1) < 1e-12 and abs(math.fsum(q) - 1) < 1e-12
        assert linf(softmax(direct["logits"]), p) < 1e-12
        assert linf(softmax(row["lmql_scores"]), q) < 1e-12
        raw_probability = softmax(raw_logits)
        assert linf(raw_probability, softmax(logprobs)) < 1e-12
        order_p = sorted(range(len(p)), key=lambda i: -p[i])
        order_q = sorted(range(len(q)), key=lambda i: -q[i])
        winner, runner = order_p[:2]
        error, tv = linf(p, q), math.fsum(abs(a - b) for a, b in zip(p, q)) / 2
        margin = p[winner] - p[runner]
        assert abs(error - row["max_probability_absolute_error"]) < 1e-14
        assert labels[winner] == direct["answer"] == row["lmql_argmax"] == labels[order_q[0]]
        deltas = [a - b for a, b in zip(raw_logits, direct["logits"])]
        values = case["candidate_values"]
        typed = None
        if values is not None:
            native_value = math.fsum(a * b for a, b in zip(p, values))
            lmql_value = math.fsum(a * b for a, b in zip(q, values))
            typed_error = abs(lmql_value - native_value)
            assert abs(typed_error - row["typed_readout_absolute_error"]) < 1e-14
            assert typed_error <= (max(values) - min(values)) * tv + 1e-14
            typed = {"native_value": native_value, "lmql_value": lmql_value,
                     "signed_difference_lmql_minus_native": lmql_value - native_value,
                     "absolute_error": typed_error,
                     "prespecified_tolerance_passed": typed_error <= freeze["typed_readout_absolute_tolerance"],
                     "candidate_values": values,
                     "range_times_total_variation_upper_bound": (max(values) - min(values)) * tv}
        content = case["request"]["messages"][1]["content"]
        half = content[:(len(content) - 2) // 2]
        repeated_twice = content == half + "\n\n" + half
        diagnostic_rows.append({
            "case_id": row["case_id"], "task_type": row["task_type"], "language": row["language"],
            "candidate_count": len(labels), "candidate_labels": labels,
            "input_tokens": len(row["input_token_ids"]),
            "assistant_prefix": case["request"]["assistant_prefix"],
            "user_content_repeated_twice": repeated_twice,
            "argmax_label_both": labels[winner], "native_runner_up_label": labels[runner],
            "native_top_probability": p[winner], "lmql_top_probability": q[order_q[0]],
            "native_probability_margin": margin,
            "lmql_probability_margin": q[order_q[0]] - q[order_q[1]],
            "native_logit_margin": direct["logits"][winner] - direct["logits"][runner],
            "lmql_native_logit_margin": raw_logits[order_q[0]] - raw_logits[order_q[1]],
            "max_probability_absolute_error": error,
            "probability_tolerance_passed": error <= freeze["probability_absolute_tolerance"],
            "total_variation_distance": tv,
            "native_margin_minus_twice_observed_probability_linf": margin - 2 * error,
            "typed_readout": typed,
            "raw_native_logit_max_absolute_difference": max(abs(x) for x in deltas),
            "raw_native_logit_difference_range": max(deltas) - min(deltas),
            "lmql_between_candidate_vocabulary_logsumexp_range": max(lses) - min(lses),
            "probability_error_from_saved_native_logit_paths_only": linf(p, raw_probability),
            "residual_lmql_probability_vs_softmax_of_lmtp_raw_logits": linf(q, raw_probability),
            "lmtp_score_float32_rounding_max_absolute_error": linf(logprobs, row["lmql_scores"]),
            "candidates": [
                {"label": label, "native_probability": p[i], "lmql_probability": q[i],
                 "signed_probability_difference": q[i] - p[i],
                 "native_logit": direct["logits"][i], "lmtp_final_logit": raw_logits[i],
                 "native_logit_difference": deltas[i],
                 "saved_lmtp_logit_path_probability_component": raw_probability[i] - p[i],
                 "saved_lmql_arithmetic_residual_component": q[i] - raw_probability[i]}
                for i, label in enumerate(labels)]})
    assert counters == list(range(1, 65))
    assert before == {n: sha(STUDY / n) for n in names}
    failures = [r["case_id"] for r in diagnostic_rows if not r["probability_tolerance_passed"]]
    assert failures == ["score-01", "score-03", "score-04"]
    assert all(r["user_content_repeated_twice"] for r in diagnostic_rows)
    summary = {
        "case_count": len(rows), "probability_failure_case_ids": failures,
        "probability_tolerance": freeze["probability_absolute_tolerance"],
        "typed_readout_tolerance": freeze["typed_readout_absolute_tolerance"],
        "probability_pass_count": len(rows) - len(failures), "argmax_match_count": len(rows),
        "typed_readout_pass_count": sum(r["typed_readout"] is not None and
            r["typed_readout"]["prespecified_tolerance_passed"] for r in diagnostic_rows),
        "max_probability_absolute_error": max(r["max_probability_absolute_error"] for r in diagnostic_rows),
        "max_typed_readout_absolute_error": max(r["typed_readout"]["absolute_error"] for r in diagnostic_rows if r["typed_readout"]),
        "min_native_top_probability": min(r["native_top_probability"] for r in diagnostic_rows),
        "min_native_probability_margin": min(r["native_probability_margin"] for r in diagnostic_rows),
        "min_lmql_probability_margin": min(r["lmql_probability_margin"] for r in diagnostic_rows),
        "max_probability_arithmetic_residual_after_saved_lmtp_logits": max(r["residual_lmql_probability_vs_softmax_of_lmtp_raw_logits"] for r in diagnostic_rows),
        "max_native_raw_logit_difference": max(r["raw_native_logit_max_absolute_difference"] for r in diagnostic_rows),
        "max_between_candidate_lse_range": max(r["lmql_between_candidate_vocabulary_logsumexp_range"] for r in diagnostic_rows),
        "all_observed_argmax_stability_bounds_positive": all(r["native_margin_minus_twice_observed_probability_linf"] > 0 for r in diagnostic_rows),
        "all_12_user_contents_repeated_twice": True,
        "original_parity_gate_remains_failed": True}
    result = {"schema_version": 1, "analysis_date": "2026-09-27", "post_hoc": True,
              "new_model_inference_calls": 0, "new_human_participants": 0,
              "independent_model_replication": False,
              "original_evidence_unchanged": True,
              "original_runtime_and_weights_rehashed": False,
              "original_decode_calls_not_new_requests": {"direct": 12, "lmtp": 52, "total": 64},
              "local_source_sha256": before, "analysis_script_sha256": sha(Path(__file__)),
              "summary": summary, "cases": diagnostic_rows}
    (HERE / "DIAGNOSTIC.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
