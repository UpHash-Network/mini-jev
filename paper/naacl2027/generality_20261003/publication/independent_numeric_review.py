"""Independent raw-logit review of the bilingual four-stratum study.

Imports no experiment, runner, metric or analysis implementation.  The reviewer
reconstructs candidate probabilities, scores and policies, then compares stored
outputs.  Primary Phi-English bootstrap uses weighted empirical resamples and
independently implemented AP/AUROC.  Does not load a model or modify observations.
"""
from __future__ import annotations

import argparse
from bisect import bisect_left, bisect_right
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import random
import statistics

KEYS = ["option_" + str(i) for i in range(5)]
SCORES = ["first_maxprob_uncertainty", "first_margin_uncertainty", "first_entropy",
          "order_flip", "order_tv", "pair_mean_entropy", "first_entropy_tv_rank",
          "pair_entropy_tv_rank"]
POLICIES = ["pair_entropy_tv_rank", "pair_mean_entropy", "pair_random", "first_entropy"]
TARGETS = ["pair_mean_label_error", "first_label_error"]
MAX_DIFFERENCE = 0.0
COMPARISONS = 0


def digest(data):
    return hashlib.sha256(data).hexdigest()


def canonical(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def read_json(path):
    return json.loads(Path(path).read_text())


def check_equal(actual, expected, context, atol=2e-12):
    global MAX_DIFFERENCE, COMPARISONS
    COMPARISONS += 1
    if isinstance(actual, dict) and isinstance(expected, dict):
        assert set(actual) == set(expected), (context, "dict keys", set(actual) ^ set(expected))
        for key in actual:
            check_equal(actual[key], expected[key], context + "/" + str(key), atol)
    elif isinstance(actual, (list, tuple)) and isinstance(expected, (list, tuple)):
        assert len(actual) == len(expected), (context, "length", len(actual), len(expected))
        for index, (a, b) in enumerate(zip(actual, expected)):
            check_equal(a, b, context + "/" + str(index), atol)
    elif type(actual) in (int, float) and type(expected) in (int, float):
        assert math.isfinite(actual) and math.isfinite(expected), (context, "non-finite")
        difference = abs(actual - expected)
        MAX_DIFFERENCE = max(MAX_DIFFERENCE, difference)
        assert math.isclose(actual, expected, rel_tol=1e-12, abs_tol=atol), (context, actual, expected, difference)
    else:
        assert actual == expected, (context, actual, expected)


def empirical_metrics(scores, errors, weights=None):
    """AP at complete tied thresholds; AUC via ascending negative mass.

    Weights are integer multiplicities in a bootstrap sample.  AP is the
    expectation, over positive thresholds, of precision at that threshold.
    """
    if weights is None:
        weights = [1] * len(scores)
    positive_total = sum(w for e, w in zip(errors, weights) if e)
    negative_total = sum(w for e, w in zip(errors, weights) if not e)
    by_value = defaultdict(lambda: [0, 0])
    for score, error, weight in zip(scores, errors, weights):
        if weight:
            by_value[score][int(bool(error))] += weight
    ascending = sorted(by_value)
    negatives_below = 0
    wins = 0.0
    positive_below = 0
    total_weight = positive_total + negative_total
    terms = []
    for value in ascending:
        negative_tied, positive_tied = by_value[value]
        wins += positive_tied * (negatives_below + negative_tied / 2)
        predicted_positive = total_weight - negatives_below - positive_below
        positives_at_or_above = positive_total - positive_below
        if positive_tied:
            terms.append(positive_tied * positives_at_or_above / predicted_positive)
        negatives_below += negative_tied
        positive_below += positive_tied
    return {
        "ap": math.fsum(terms) / positive_total if positive_total else None,
        "auroc": wins / (positive_total * negative_total) if positive_total and negative_total else None,
    }


def percentile_interval(values):
    valid = [value for value in values if value is not None]
    if len(valid) > 1:
        quantiles = statistics.quantiles(valid, n=40, method="inclusive")
        low, high = quantiles[0], quantiles[-1]
    elif valid:
        low = high = valid[0]
    else:
        low = high = None
    return {"low": low, "high": high, "valid_resamples": len(valid),
            "invalid_resamples": len(values) - len(valid)}


def softmax(logits):
    largest = max(logits)
    unnormalized = [math.exp(value - largest) for value in logits]
    denominator = math.fsum(unnormalized)
    return [value / denominator for value in unnormalized]


def entropy(probabilities):
    return math.fsum(-p * math.log(p) for p in probabilities if p) / math.log(5)


def prediction(probabilities):
    largest = max(probabilities)
    return KEYS[probabilities.index(largest)]


def midranks(values):
    ordered = sorted(values)
    n = len(values)
    return [(bisect_left(ordered, value) + bisect_right(ordered, value)) / (2 * n)
            for value in values]


def make_records(rows, model, dataset, selected, schedule):
    assert len(rows) == len(schedule) == 1200
    by_item = defaultdict(dict)
    for index, (row, scheduled) in enumerate(zip(rows, schedule)):
        assert scheduled["request_index"] == row["request_index"] == index
        for key, value in scheduled.items():
            assert row[key] == value, ("schedule", model, dataset, index, key)
        assert row["model_key"] == model and row["dataset"] == dataset
        assert row["error"] is None and row["backend"] == "transformers"
        assert row["forward_calls"] == 1 and row["output_tokens"] == 0 and row["temperature"] == 1
        assert row["logits_to_keep"] == 0 and row["use_cache"] is False and row["batch_size"] == 1
        assert row["canonical_keys"] == row["candidate_keys"] == KEYS
        assert len(row["logits"]) == 5 and all(math.isfinite(x) for x in row["logits"])
        probabilities = softmax(row["logits"])
        check_equal(probabilities, [row["probabilities"][key] for key in KEYS], "saved probabilities")
        assert row["label"] == prediction(probabilities)
        identity = row["item_id"]
        assert identity in selected and selected[identity]["dataset"] == dataset
        assert row["group"] == selected[identity]["group"]
        assert row["source_question_sha256"] == selected[identity]["question_sha256"]
        assert row["replicate"] not in by_item[identity]
        assert type(row["input_tokens"]) is int and row["input_tokens"] > 0
        assert math.isfinite(row["latency_ms"]) and row["latency_ms"] >= 0
        by_item[identity][row["replicate"]] = (row, probabilities)
    assert len(by_item) == 240
    assert set(by_item) == {key for key, row in selected.items() if row["dataset"] == dataset}
    records = []
    for identity in sorted(by_item):
        assert set(by_item[identity]) == set(range(5))
        members = [by_item[identity][i][0] for i in range(5)]
        vectors = [by_item[identity][i][1] for i in range(5)]
        reference = members[0]["gold_label"]
        assert reference in KEYS and all(row["gold_label"] == reference for row in members)
        means = {count: [math.fsum(vector[k] for vector in vectors[:count]) / count for k in range(5)]
                 for count in (1, 2, 5)}
        labels = {count: prediction(value) for count, value in means.items()}
        largest = sorted(vectors[0], reverse=True)
        scores = {
            "first_maxprob_uncertainty": 1 - largest[0],
            "first_margin_uncertainty": 1 - (largest[0] - largest[1]),
            "first_entropy": entropy(vectors[0]),
            "order_flip": int(prediction(vectors[0]) != prediction(vectors[1])),
            "order_tv": math.fsum(abs(x - y) for x, y in zip(vectors[0], vectors[1])) / 2,
            "pair_mean_entropy": entropy(means[2]),
        }
        records.append({"item_id": identity, "dataset": dataset, "model": model,
                        "gold_label": reference, "probability_vectors": vectors,
                        "first_label": labels[1], "pair_mean_label": labels[2], "full_mean_label": labels[5],
                        "pair_mean_label_error": int(labels[2] != reference),
                        "first_label_error": int(labels[1] != reference),
                        "group": members[0]["group"], "source_question_sha256": members[0]["source_question_sha256"],
                        "scores": scores, "members": members})
    tv = midranks([row["scores"]["order_tv"] for row in records])
    for source, composite in [("first_entropy", "first_entropy_tv_rank"),
                              ("pair_mean_entropy", "pair_entropy_tv_rank")]:
        rank = midranks([row["scores"][source] for row in records])
        for row, first, second in zip(records, rank, tv):
            row["scores"][composite] = (first + second) / 2
    return records


def pick_items(records, policy, budget, config):
    base = 1 if policy == "first_entropy" else 2
    numerator = int(budget * len(records)) - base * len(records)
    assert numerator % (5 - base) == 0
    count = numerator // (5 - base)
    assert 0 <= count <= len(records)
    if policy == "pair_random":
        ordering = sorted((digest((config["random_salt"] + r["item_id"]).encode()), r["item_id"])
                          for r in records)
    else:
        ordering = sorted((-r["scores"][policy], digest((config["tie_salt"] + r["item_id"]).encode()), r["item_id"])
                          for r in records)
    return {entry[-1] for entry in ordering[:count]}, base


def reconstruct_policy(records, policy, budget, config):
    chosen, base = pick_items(records, policy, budget, config)
    paid_calls = []; outcome = []
    for row in records:
        count = 5 if row["item_id"] in chosen else base
        field = {1: "first_label", 2: "pair_mean_label", 5: "full_mean_label"}[count]
        paid = row["members"][:count]
        paid_calls.extend(paid)
        outcome.append({"item_id": row["item_id"], "selected": count == 5,
                        "calls": count, "prediction": row[field],
                        "correct": int(row[field] == row["gold_label"]),
                        "paid_request_indices": [member["request_index"] for member in paid]})
    assert len({member["request_index"] for member in paid_calls}) == len(paid_calls) == int(budget * len(records))
    correct = sum(row["correct"] for row in outcome)
    return {"policy": policy, "budget_calls_per_item": budget, "selected_count": len(chosen),
            "accuracy": correct / len(records), "correct": correct,
            "calls": len(paid_calls), "input_tokens": sum(member["input_tokens"] for member in paid_calls),
            "recorded_serial_latency_ms": math.fsum(member["latency_ms"] for member in paid_calls), "outcomes": outcome}


def compare_stratum(records, published, stored_records, config):
    points = {}
    for row in records:
        stored = stored_records[(row["model"], row["dataset"], row["item_id"])]
        for key in ["gold_label", "probability_vectors", "first_label", "pair_mean_label", "full_mean_label",
                    "pair_mean_label_error", "first_label_error", "group", "source_question_sha256", "scores"]:
            check_equal(row[key], stored[key], row["item_id"] + "/" + key)
    for target in TARGETS:
        errors = [row[target] for row in records]
        assert published["A"][target]["n"] == 240 and published["A"][target]["errors"] == sum(errors)
        points[target] = {}
        for name in SCORES:
            values = [row["scores"][name] for row in records]
            metrics = empirical_metrics(values, errors)
            points[target][name] = metrics
            saved = published["A"][target]["scores"][name]
            check_equal(metrics, {key: saved[key] for key in ("ap", "auroc")}, target + "/" + name)
            boundary = sorted(values)[-20]
            indices = [i for i, value in enumerate(values) if value >= boundary]
            check_equal({"reviewed": len(indices), "errors_found": sum(errors[i] for i in indices)},
                        saved["top20_with_ties"], target + "/" + name + "/top20")
            assert saved["feature_calls"] == (1 if name in SCORES[:3] else 2)
            assert saved["prediction_calls"] == (2 if target == TARGETS[0] else 1)
        left, right = config["A"]["primary_contrast"]
        for metric in ("ap", "auroc"):
            a, b = points[target][left][metric], points[target][right][metric]
            check_equal(None if a is None or b is None else a - b,
                        published["A"][target]["primary_contrast"][metric]["difference"], "A point contrast")
    curve_map = {(r["policy"], r["budget_calls_per_item"]): r for r in published["B"]["curves"]}
    assert len(curve_map) == 20
    rebuilt = {}
    for budget in config["B"]["budgets_calls_per_item"]:
        for policy in POLICIES:
            result = reconstruct_policy(records, policy, budget, config["B"])
            rebuilt[(policy, budget)] = result
            saved = curve_map[(policy, budget)]
            check_equal(result, {key: saved[key] for key in result}, "B/" + str(budget) + "/" + policy, atol=1e-6)
            # Selection API has only legal observed scores/IDs: no future member
            # logits, gold, correctness labels, costs or mean-five decisions.
            minimal = [{"item_id": r["item_id"], "scores": {policy: r["scores"][policy]} if policy != "pair_random" else {}}
                       for r in records]
            assert pick_items(minimal, policy, budget, config["B"]) == pick_items(records, policy, budget, config["B"])
        left, right = config["B"]["primary_contrast"]
        differences = [a["correct"] - b["correct"] for a, b in zip(rebuilt[(left, budget)]["outcomes"], rebuilt[(right, budget)]["outcomes"])]
        contrast = next(row for row in published["B"]["paired_contrasts"] if row["budget_calls_per_item"] == budget)
        check_equal(sum(differences) / len(records), contrast["accuracy_difference"], "B contrast")
        assert contrast["reference_wrong_score_correct"] == differences.count(1)
        assert contrast["reference_correct_score_wrong"] == differences.count(-1)
    accuracy = {field: sum(row[field] == row["gold_label"] for row in records) / len(records)
                for field in ("first_label", "pair_mean_label", "full_mean_label")}
    check_equal(accuracy, published["B"]["reference_accuracy"], "reference accuracy")
    return points, rebuilt


def weighted_resamples(count, seed):
    rng = random.Random(seed)
    for _ in range(2000):
        counts = Counter(rng.randrange(count) for _ in range(count))
        yield [counts.get(i, 0) for i in range(count)]


def verify_primary_bootstrap(records, published, rebuilt, protocol):
    target = "pair_mean_label_error"
    errors = [row[target] for row in records]
    score, reference = protocol["A"]["primary_contrast"]
    left = [row["scores"][score] for row in records]
    right = [row["scores"][reference] for row in records]
    differences = {metric: [] for metric in ("ap", "auroc")}
    own_draws = {score: {metric: [] for metric in differences}, reference: {metric: [] for metric in differences}}
    for weights in weighted_resamples(240, protocol["A"]["seed"]):
        x, y = empirical_metrics(left, errors, weights), empirical_metrics(right, errors, weights)
        for metric in differences:
            own_draws[score][metric].append(x[metric]); own_draws[reference][metric].append(y[metric])
            differences[metric].append(None if x[metric] is None or y[metric] is None else x[metric] - y[metric])
    ci = {}
    for metric in differences:
        ci[metric] = percentile_interval(differences[metric])
        check_equal(ci[metric], published["A"][target]["primary_contrast"][metric]["ci95"], "primary A bootstrap/" + metric)
        for name in (score, reference):
            check_equal(percentile_interval(own_draws[name][metric]), published["A"][target]["scores"][name]["ci95"][metric], "primary score CI/" + name + "/" + metric)
    budget = protocol["B"]["primary_budget_calls_per_item"]
    left_policy, right_policy = protocol["B"]["primary_contrast"]
    left_outcomes = rebuilt[(left_policy, budget)]["outcomes"]
    right_outcomes = rebuilt[(right_policy, budget)]["outcomes"]
    delta = [x["correct"] - y["correct"] for x, y in zip(left_outcomes, right_outcomes)]
    draws = [sum(d * w for d, w in zip(delta, weights)) / 240
             for weights in weighted_resamples(240, protocol["B"]["seed"])]
    ci["B_accuracy_difference"] = percentile_interval(draws)
    contrast = next(row for row in published["B"]["paired_contrasts"] if row["budget_calls_per_item"] == budget)
    check_equal(ci["B_accuracy_difference"], contrast["ci95"], "primary B bootstrap")
    return ci


def self_test():
    check_equal(empirical_metrics([0, 0, 0, 0], [1, 0, 0, 0]), {"ap": .25, "auroc": .5}, "constant score")
    check_equal(empirical_metrics([4, 3, 2, 1], [1, 1, 0, 0]), {"ap": 1, "auroc": 1}, "perfect")
    check_equal(empirical_metrics([4, 3, 2, 1], [0, 0, 1, 1]), {"ap": (1 / 3 + 1 / 2) / 2, "auroc": 0}, "reverse")
    check_equal(empirical_metrics([4, 3, 2], [0, 1, 1], [2, 1, 0]), {"ap": 1 / 3, "auroc": 0}, "weighted sample")
    check_equal(empirical_metrics([2, 1, 1], [0, 0, 1]), {"ap": 1 / 3, "auroc": .25}, "partial tie")
    check_equal(empirical_metrics([1, 2], [0, 0]), {"ap": None, "auroc": None}, "no positives")
    check_equal(empirical_metrics([1, 2], [1, 1]), {"ap": 1, "auroc": None}, "no negatives")
    check_equal(midranks([2, 1, 1, 3]), [.625, .25, .25, .875], "midranks")
    check_equal(percentile_interval([0, 1, 2, None]), {"low": .05, "high": 1.95, "valid_resamples": 3, "invalid_resamples": 1}, "CI")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--study", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    self_test()
    if args.self_test:
        print("Independent numerical reviewer synthetic controls: PASS")
        return
    assert args.study is not None and args.out is not None
    assert not args.out.exists(), "Review output already exists"
    study = args.study.resolve(); source = study.parent
    frozen = read_json(study / "FREEZE.json")
    schedule = read_json(study / "SCHEDULES.json")
    protocol = read_json(source / "PROTOCOL.json")
    selected = {row["id"]: row for row in read_json(source / "SELECTION.json")["items"]}
    published = read_json(study / "analysis_v1/RESULTS.json")
    assert published["protocol"] == protocol
    assert published["freeze_sha256"] == digest((study / "FREEZE.json").read_bytes())
    assert digest(canonical(schedule)) == frozen["schedule_sha256"]
    source_checks = 0
    for filename, expected in frozen["source_sha256"].items():
        assert digest(Path(filename).read_bytes()) == expected, ("frozen input changed", filename)
        source_checks += 1
    question_rows = {}
    for filename in frozen["source_sha256"]:
        if Path(filename).name.startswith("questions-") and Path(filename).suffix == ".jsonl":
            for line in Path(filename).read_text().splitlines():
                row = json.loads(line)
                assert digest(canonical(row)) == selected[row["id"]]["question_sha256"]
                question_rows[row["id"]] = row
    assert len(question_rows) == len(selected) == 480
    stored_records = {}
    for line in (study / "analysis_v1/records.jsonl").read_text().splitlines():
        row = json.loads(line)
        key = (row["model"], row["dataset"], row["item_id"])
        assert key not in stored_records
        stored_records[key] = row
    assert len(stored_records) == 960
    reports = {}; total_rows = 0; observation_hashes = {}
    for model in protocol["models"]:
        folder = study / "observations" / model
        receipt = read_json(folder / "COMPLETION.json")
        assert receipt["status"] == "completed" and receipt["model_closed"] and receipt["source_unchanged"]
        assert receipt["recorded_requests"] == 2400 and receipt["failed_requests"] == 0
        assert receipt["actual_calls_including_excluded"] == 2428
        assert read_json(folder / "ATTEMPT.json")["freeze_sha256"] == digest((study / "FREEZE.json").read_bytes())
        for dataset in protocol["datasets"]:
            path = folder / (dataset + ".jsonl")
            raw = path.read_bytes()
            assert digest(raw) == receipt["file_sha256"][path.name]
            observation_hashes[str(path.relative_to(study))] = digest(raw)
            rows = [json.loads(line) for line in raw.splitlines()]
            for row in rows:
                assert row["gold_label"] == question_rows[row["item_id"]]["label"]
            records = make_records(rows, model, dataset, selected, schedule[dataset])
            total_rows += len(rows)
            key = model + "/" + dataset
            points, rebuilt = compare_stratum(records, published["strata"][key], stored_records, protocol)
            report = {"items": len(records), "physical_rows": len(rows), "point_metrics": points,
                      "policy_budget_points_verified": 20,
                      "primary_B_correct": {name: rebuilt[(name, 3)]["correct"] for name in POLICIES}}
            if model == protocol["primary_model"] and dataset == protocol["primary_dataset"]:
                report["primary_bootstrap_verified"] = verify_primary_bootstrap(records, published["strata"][key], rebuilt, protocol)
            reports[key] = report
            print(json.dumps({"stratum_verified": key, "rows": len(rows)}), flush=True)
    assert total_rows == 4800 and len(reports) == 4
    # Outputs are written only after every comparison succeeds.
    args.out.mkdir(parents=True)
    result = {"checked_at_utc": datetime.now(timezone.utc).isoformat(), "status": "PASS",
              "reviewer_sha256": digest(Path(__file__).read_bytes()),
              "implementation_independence": "No imports from primary analysis/runner/metric code. Raw logits -> independent softmax, semantic labels, bisect cohort ranks, weighted threshold AP and ascending concordance AUROC; independent policy-cost reconstruction.",
              "scope": "AI numerical replay review, not independent model inference, independent hardware or human validation.",
              "frozen_source_files_verified": source_checks, "physical_rows_verified": total_rows,
              "distinct_questions": 480, "model_item_records": 960,
              "point_AP_AUROC_values_verified": 128, "policy_budget_points_verified": 80,
              "bootstrap_scope": "Phi-English primary pair-mean-error AP/AUROC contrast, both component-score CIs, and primary 3-call accuracy contrast; 2000 paired whole-question draws each.",
              "recursive_value_comparisons": COMPARISONS, "maximum_absolute_numeric_difference": MAX_DIFFERENCE,
              "observations_sha256": observation_hashes,
              "analysis_results_sha256": digest((study / "analysis_v1/RESULTS.json").read_bytes()),
              "strata": reports}
    (args.out / "REVIEW.json").write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"status": "PASS", "physical_rows": total_rows, "maximum_absolute_numeric_difference": MAX_DIFFERENCE}))


if __name__ == "__main__":
    main()
