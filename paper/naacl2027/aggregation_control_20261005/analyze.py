#!/usr/bin/env python3
"""Post-hoc aggregation-only control. Standard library; saved outputs only."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import random
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
METHODS = ("first_order", "arithmetic_mean5", "geometric_mean5")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    return json.loads(path.read_text())


def write_json(path, value):
    with path.open("x") as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write("\n")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def mean(vectors):
    require(bool(vectors) and bool(vectors[0]), "Empty vectors")
    width = len(vectors[0])
    require(all(len(v) == width and all(math.isfinite(x) for x in v) for v in vectors),
            "Ragged or nonfinite vectors")
    return [math.fsum(v[k] for v in vectors) / len(vectors) for k in range(width)]


def log_softmax(logits):
    require(bool(logits) and all(math.isfinite(x) for x in logits), "Invalid logits")
    shifted = [x - max(logits) for x in logits]
    log_z = math.log(math.fsum(math.exp(x) for x in shifted))
    return [x - log_z for x in shifted]


def softmax(logits):
    return [math.exp(x) for x in log_softmax(logits)]


def geometric_mean(logit_vectors):
    """Normalized geometric probability mean, robust to saved-p underflow."""
    return softmax(mean([log_softmax(v) for v in logit_vectors]))


def top_index(vector):
    return max(range(len(vector)), key=vector.__getitem__)


def percentile(values, fraction):
    require(bool(values) and 0 <= fraction <= 1, "Invalid quantile")
    values = sorted(values)
    position = (len(values) - 1) * fraction
    low = math.floor(position)
    high = math.ceil(position)
    weight = position - low
    return values[low] * (1 - weight) + values[high] * weight


def interval(values):
    valid = [x for x in values if x is not None and math.isfinite(x)]
    return {"low": percentile(valid, .025) if valid else None,
            "high": percentile(valid, .975) if valid else None,
            "valid_draws": len(valid), "invalid_draws": len(values) - len(valid)}


def paired_counts(alternative, reference, gold):
    require(len(alternative) == len(reference) == len(gold) > 0, "Mismatched paired labels")
    transitions = {"reference_wrong_alternative_correct": 0,
                   "reference_correct_alternative_wrong": 0,
                   "both_correct": 0, "both_wrong": 0, "label_disagreements": 0}
    differences = []
    for alt, ref, truth in zip(alternative, reference, gold):
        ac, rc = alt == truth, ref == truth
        differences.append(int(ac) - int(rc))
        key = ("both_correct" if ac and rc else "both_wrong" if not ac and not rc else
               "reference_wrong_alternative_correct" if ac else "reference_correct_alternative_wrong")
        transitions[key] += 1
        transitions["label_disagreements"] += int(alt != ref)
    return {**transitions, "accuracy_difference": math.fsum(differences) / len(gold)}


def verified_inputs():
    protocol = load(HERE / "PROTOCOL.json")
    freeze = load(HERE / "FREEZE.json")
    for relative, expected in freeze["files_sha256"].items():
        require(not Path(relative).is_absolute(), "Absolute freeze path")
        require(sha(HERE / relative) == expected, "Control source changed: " + relative)
    for entry in load(HERE / "INPUTS.json")["files"]:
        require(not Path(entry["path"]).is_absolute(), "Absolute input path")
        path = HERE / entry["path"]
        require(sha(path) == entry["sha256"] and path.stat().st_size == entry["bytes"],
                "Input changed: " + entry["path"])
    root = (HERE / protocol["bundle_relative_path"]).resolve()
    manifest = load(root / "MANIFEST.json")
    # Also verify every published bundle asset against its already-published manifest.
    for relative, expected in manifest["files_sha256"].items():
        path = root / relative
        require(not Path(relative).is_absolute() and path.resolve().is_relative_to(root)
                and not path.is_symlink(), "Unsafe published bundle path")
        require(sha(path) == expected, "Published bundle changed: " + relative)
    original_freeze = load(root / "provenance/FREEZE.public.json")
    for relative, expected in manifest["frozen_code_bindings"].items():
        require(original_freeze["source_sha256"][relative] == expected,
                "Original frozen source binding changed")
    require(original_freeze["stage"] == "before_any_generality_model_forward", "Original freeze stage")
    spec = importlib.util.spec_from_file_location("generality_frozen_reader", root / "code/analysis.py")
    reader = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(reader)
    schedules = load(root / "data/SCHEDULES.json")
    require(reader.digest(reader.canonical(schedules)) == original_freeze["schedule_sha256"],
            "Original schedule mismatch")
    original_results = load(root / "RESULTS.json")
    require(original_results["freeze_sha256"] == manifest["original_v2_freeze_sha256"],
            "Original result freeze mismatch")
    selection = {r["id"]: r for r in load(root / "code/SELECTION.json")["items"]}
    strata, identities = [], {}
    for model in protocol["models"]:
        folder = root / "observations" / model
        receipt, attempt = load(folder / "COMPLETION.json"), load(folder / "ATTEMPT.json")
        require(receipt["status"] == "completed" and receipt["recorded_requests"] == 2400
                and receipt["failed_requests"] == 0 and receipt["model_closed"]
                and receipt["source_unchanged"] and receipt["actual_calls_including_excluded"] == 2428,
                "Original collection incomplete")
        require(attempt["freeze_sha256"] == manifest["original_v2_freeze_sha256"], "Original attempt mismatch")
        for relative, expected in receipt["file_sha256"].items():
            require(sha(folder / relative) == expected, "Original receipt file mismatch")
        for dataset in protocol["datasets"]:
            key = model + "/" + dataset
            rows = [json.loads(line) for line in (folder / (dataset + ".jsonl")).read_text().splitlines()]
            reader.verify_schedule(rows, schedules[dataset])
            records = reader.records_from_rows(rows, model, protocol["n_items_per_stratum"], dataset)
            for row in rows:
                selected = selection[row["item_id"]]
                require(selected["dataset"] == dataset and selected["group"] == row["group"]
                        and selected["question_sha256"] == row["source_question_sha256"], "Selection mismatch")
                require(row["logits_to_keep"] == 0 and row["candidate_boundary_verified"], "Original readout mismatch")
                require(row["candidate_tokens"] == ["A", "B", "C", "D", "E"], "Token binding mismatch")
                expected_order = row["canonical_keys"][row["replicate"]:] + row["canonical_keys"][:row["replicate"]]
                require(row["display_order"] == expected_order, "Cyclic display order mismatch")
            identity = [(r["item_id"], r["group"], r["source_question_sha256"], r["gold_label"]) for r in records]
            require(dataset not in identities or identities[dataset] == identity, "Model panels differ")
            identities[dataset] = identity
            by_item = {}
            for row in rows:
                by_item.setdefault(row["item_id"], {})[row["replicate"]] = row
            # Reproduce the original endpoint before the new comparison.
            expected = original_results["strata"][key]["B"]["reference_accuracy"]
            for field in ("first_label", "full_mean_label"):
                require(sum(r[field] == r["gold_label"] for r in records) / len(records) == expected[field],
                        "Original accuracy not reproduced")
            strata.append((key, records, by_item))
    return protocol, strata


def analyze_stratum(key, records, by_item, protocol, stratum_index):
    n = len(records)
    outcomes, equivalence_errors, distribution_tv = [], [], []
    for r in records:
        members = [by_item[r["item_id"]][i] for i in range(5)]
        logits = [m["logits"] for m in members]
        arithmetic = mean(r["probability_vectors"])
        geometric = geometric_mean(logits)
        mean_logit_distribution = softmax(mean(logits))
        error = max(abs(x - y) for x, y in zip(geometric, mean_logit_distribution))
        require(error <= 1e-12, "Geometric / mean-logit identity failed")
        require(top_index(geometric) == top_index(mean_logit_distribution), "Geometric identity label mismatch")
        equivalence_errors.append(error)
        vectors = {"first_order": r["probability_vectors"][0],
                   "arithmetic_mean5": arithmetic, "geometric_mean5": geometric}
        labels = {name: r["canonical_keys"][top_index(vector)] for name, vector in vectors.items()}
        require(labels["arithmetic_mean5"] == r["full_mean_label"]
                and labels["first_order"] == r["first_label"], "Original prediction changed")
        for vector in vectors.values():
            require(all(math.isfinite(x) and 0 <= x <= 1 for x in vector)
                    and abs(math.fsum(vector) - 1) <= 1e-12, "Invalid output distribution")
        tv = .5 * math.fsum(abs(x - y) for x, y in zip(arithmetic, geometric))
        distribution_tv.append(tv)
        outcomes.append({"stratum": key, "item_id": r["item_id"], "group": r["group"],
                         "source_question_sha256": r["source_question_sha256"],
                         "gold_label": r["gold_label"], "canonical_keys": r["canonical_keys"],
                         "predictions": labels, "probabilities": vectors,
                         "correct": {name: int(label == r["gold_label"]) for name, label in labels.items()},
                         "exact_top_tie_counts": {name: sum(p == max(v) for p in v) for name, v in vectors.items()},
                         "arithmetic_geometric_tv": tv, "members": r["members"]})
    rng = random.Random(protocol["uncertainty"]["seed"] + stratum_index)
    bootstraps = {name: [] for name in METHODS}
    # The same resampled indices are shared by all methods on every draw.
    for _ in range(protocol["uncertainty"]["draws"]):
        indices = [rng.randrange(n) for _ in range(n)]
        for name in METHODS:
            bootstraps[name].append(sum(outcomes[i]["correct"][name] for i in indices) / n)
    methods = {}
    for name in METHODS:
        chosen_members = [m for r in records for m in r["members"][:1 if name == "first_order" else 5]]
        correct = sum(r["correct"][name] for r in outcomes)
        methods[name] = {"correct": correct, "n": n, "accuracy": correct / n,
                         "accuracy_ci95": interval(bootstraps[name]),
                         "questions_with_exact_top_ties": sum(r["exact_top_tie_counts"][name] > 1 for r in outcomes),
                         "reused_physical_calls": len(chosen_members), "new_forward_calls": 0,
                         "reused_input_tokens": sum(m["input_tokens"] for m in chosen_members),
                         "reused_recorded_serial_latency_ms": math.fsum(m["latency_ms"] for m in chosen_members)}
    contrasts = []
    gold = [r["gold_label"] for r in outcomes]
    for alternative, reference in protocol["outcomes"]["contrasts"]:
        paired = paired_counts([r["predictions"][alternative] for r in outcomes],
                               [r["predictions"][reference] for r in outcomes], gold)
        # Paired bootstrap means share exactly the same question indices.
        draws = [a - b for a, b in zip(bootstraps[alternative], bootstraps[reference])]
        contrasts.append({"alternative": alternative, "reference": reference, **paired,
                          "accuracy_difference_ci95": interval(draws)})
    return {"n": n, "methods": methods, "paired_contrasts": contrasts,
            "arithmetic_geometric_distribution_tv": {"mean": math.fsum(distribution_tv) / n,
                                                      "maximum": max(distribution_tv)},
            "maximum_geometric_mean_logit_identity_absolute_error": max(equivalence_errors),
            "saved_collection_calls": 5 * n, "new_forward_calls": 0}, outcomes


def report(results):
    lines = ["# Post-hoc fixed-binding aggregation control", "",
             "**Exploratory, already-seen saved panel; no new inference.** This is an aggregation-only control, not an AnyJev reproduction. "
             "The same five physical responses, fixed token-to-option binding, candidate sets, temperature and prompts are used by both five-member methods. "
             "Geometric averaging adds no token reassignment or prior correction.", "",
             "The specification in `../PROTOCOL.json` was locally recorded before calculating these new contrasts. The underlying data and original arithmetic results "
             "were already seen, so this is not preregistered or unseen confirmation. All four strata are retained separately; the models share 480 distinct questions.", "",
             "Arithmetic: a(k) = mean_r p_r(k). Normalized geometric: g(k) = exp(mean_r log p_r(k)) / sum_j exp(mean_r log p_r(j)). "
             "Stable log-softmax uses saved logits at T=1; the calculation is checked against softmax of mean logits. Labels use the first canonical option in exact ties. "
             "First order means frozen replicate 0, independent of the physical execution order.", "",
             "| Model / dataset | First order | Arithmetic mean, 5 | Geometric mean, 5 | Geometric − arithmetic, pp [95% CI] | G fixes / breaks A | Label disagreements |",
             "|---|---:|---:|---:|---:|---:|---:|"]
    for key, result in results["strata"].items():
        methods = result["methods"]
        c = result["paired_contrasts"][0]
        ci = c["accuracy_difference_ci95"]
        counts = [f"{methods[name]['correct']}/{result['n']}" for name in METHODS]
        lines.append(f"| {key} | {' | '.join(counts)} | {100*c['accuracy_difference']:+.2f} "
                     f"[{100*ci['low']:+.2f}, {100*ci['high']:+.2f}] | "
                     f"{c['reference_wrong_alternative_correct']} / {c['reference_correct_alternative_wrong']} | {c['label_disagreements']} |")
    lines += ["", "Both five-member methods reuse 1,200 physical responses per stratum (4,800 total); these shared calls are counted once. "
              "First order reuses 240 per stratum. This analysis adds **0 model forwards and 0 model downloads**. "
              "Saved token and serial-latency sums in `RESULTS.json` are historical bookkeeping, not newly measured performance or online speedups.", "",
              "| Model / dataset | Contrast | Accuracy difference, pp [95% CI] | Reference wrong → correct | Reference correct → wrong | Both wrong | Label disagreements |",
              "|---|---|---:|---:|---:|---:|---:|"]
    for key, result in results["strata"].items():
        for c in result["paired_contrasts"]:
            ci = c["accuracy_difference_ci95"]
            lines.append(f"| {key} | {c['alternative']} − {c['reference']} | {100*c['accuracy_difference']:+.2f} "
                         f"[{100*ci['low']:+.2f}, {100*ci['high']:+.2f}] | {c['reference_wrong_alternative_correct']} | "
                         f"{c['reference_correct_alternative_wrong']} | {c['both_wrong']} | {c['label_disagreements']} |")
    lines += ["", "Intervals are 10,000 paired whole-question percentile bootstrap draws within each stratum, with fixed predictions and common question indices across methods. "
              "They are exploratory and unadjusted across contrasts and strata. They do not support a multiplicity-adjusted winner declaration or a population equivalence claim. "
              "No questions, methods or strata were selected using these results.", "",
              "This control isolates the aggregation operation only. It does not test permutation-dependent token bindings, content-free priors or complete external systems. "
              "The two tasks are different public validation datasets, the model sizes differ, and collection used one machine. "
              "It supplies no independent participant evidence, causal language comparison, calibration validation or universal utility claim.", "",
              "Input hashes and relative source paths: `../INPUTS.json`. Locally recorded analysis and code hashes: `../FREEZE.json`. "
              "Full method accuracies, all three paired contrasts, probability-change diagnostics, saved costs and numerical identity checks: `RESULTS.json`. "
              "Every item prediction, distribution and physical-member reference: `records.jsonl`."]
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=HERE / "results")
    args = parser.parse_args()
    require(not args.out.exists(), "Refusing to overwrite an earlier result directory")
    protocol, strata = verified_inputs()
    results = {"schema_version": 1, "created_at": datetime.now(timezone.utc).isoformat(),
               "status": "post_hoc_exploratory", "protocol_sha256": sha(HERE / "PROTOCOL.json"),
               "inputs_sha256": sha(HERE / "INPUTS.json"), "freeze_sha256": sha(HERE / "FREEZE.json"),
               "new_forward_calls": 0, "saved_collection_calls_total": 4800,
               "distinct_questions": 480, "model_item_observations": 960,
               "uncertainty": protocol["uncertainty"], "strata": {}}
    all_outcomes = []
    for index, (key, records, by_item) in enumerate(strata):
        result, outcomes = analyze_stratum(key, records, by_item, protocol, index)
        results["strata"][key] = result
        all_outcomes.extend(outcomes)
    args.out.mkdir(parents=True)
    write_json(args.out / "RESULTS.json", results)
    with (args.out / "records.jsonl").open("x") as stream:
        for outcome in all_outcomes:
            stream.write(json.dumps(outcome, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n")
    with (args.out / "REPORT.md").open("x") as stream:
        stream.write(report(results))
    write_json(args.out / "MANIFEST.json", {"files_sha256": {name: sha(args.out / name)
               for name in ("RESULTS.json", "records.jsonl", "REPORT.md")}})
    print(json.dumps({"status": "completed", "strata": len(strata), "model_item_observations": len(all_outcomes),
                      "new_forward_calls": 0, "saved_collection_calls_total": 4800}))


if __name__ == "__main__":
    main()
