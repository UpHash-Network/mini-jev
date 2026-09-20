#!/usr/bin/env python3
"""Verify saved artifacts and distinguish within-pair from cross-example overlap."""
import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache-dir", required=True)
    parser.add_argument("--output-file", default=str(HERE / "AUDIT.json"))
    args = parser.parse_args()
    prep = json.loads((HERE / "PREPARATION.json").read_text())
    selection = json.loads((HERE / "SELECTION.json").read_text())
    summary = json.loads((HERE / "results/METRICS.json").read_text())
    source = Path(args.cache_dir) / "jnli-valid-v1.3.json"
    for path, expected in [(source, prep["source_sha256"]),
                           (HERE / "PROTOCOL.json", prep["protocol_sha256"]),
                           (HERE / "run_pilot.py", prep["runner_sha256"]),
                           (HERE / "results/predictions.jsonl", summary["predictions_sha256"])]:
        if sha(path) != expected:
            raise ValueError("artifact SHA mismatch: " + path.name)
    rows = {str(row["sentence_pair_id"]): row for row in map(json.loads, source.read_text().splitlines())}
    predictions = list(map(json.loads, (HERE / "results/predictions.jsonl").read_text().splitlines()))
    if len(predictions) != 300 or Counter(p["gold"] for p in predictions) != {"contradiction": 100, "entailment": 100, "neutral": 100}:
        raise ValueError("incorrect selected class count")
    if [p["sentence_pair_id"] for p in predictions] != [p["sentence_pair_id"] for p in selection["items"]]:
        raise ValueError("selection order differs from predictions")
    for p in predictions:
        source_row = rows[p["sentence_pair_id"]]
        canonical = json.dumps(source_row, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
        if hashlib.sha256(canonical.encode()).hexdigest() != p["row_sha256"] or source_row["label"] != p["gold"]:
            raise ValueError("source row differs from recorded reference")
        probabilities = p["probabilities_T1"]
        if len(probabilities) != 3 or abs(sum(probabilities.values()) - 1) > 1e-12:
            raise ValueError("invalid probabilities")
        if max(probabilities, key=probabilities.get) != p["prediction"]:
            raise ValueError("prediction differs from probability argmax")
    correct = sum(p["prediction"] == p["gold"] for p in predictions)
    if correct != summary["primary_T1"]["correct"] or sum(p["native_decode_count"] for p in predictions) != 300:
        raise ValueError("accuracy/decode accounting mismatch")
    chosen = [rows[p["sentence_pair_id"]] for p in predictions]
    sentence_ids = defaultdict(set)
    for row in chosen:
        for sentence in (row["sentence1"], row["sentence2"]):
            sentence_ids[sentence].add(str(row["sentence_pair_id"]))
    cross_shared = [str(row["sentence_pair_id"]) for row in chosen
                    if any(len(sentence_ids[sentence]) > 1 for sentence in (row["sentence1"], row["sentence2"]))]
    self_identical = [str(row["sentence_pair_id"]) for row in chosen if row["sentence1"] == row["sentence2"]]
    # Full source sentence strings, not mere generic short substrings, must not
    # appear in the public pilot artifacts. Hashes and IDs are allowed.
    sentences = [sentence for sentence in sentence_ids if len(sentence) >= 8]
    scanned = []
    for path in HERE.rglob("*"):
        if path.is_file() and path.suffix in {".json", ".jsonl", ".md", ".py"}:
            text = path.read_text()
            if any(sentence in text for sentence in sentences):
                raise ValueError("source sentence leaked in public file: " + path.name)
            scanned.append(str(path.relative_to(HERE)))
    audit = {"created_utc": datetime.now(timezone.utc).isoformat(), "result": "passed",
             "audit_script_sha256": sha(Path(__file__)), "correct": correct, "n": len(predictions),
             "source_and_freeze_hashes_verified": True, "source_rows_gold_and_predictions_verified": True,
             "public_files_scanned_for_source_sentences": sorted(scanned),
             "overlap_clarification": {
                 "frozen_runner_rows_with_any_shared_sentence": summary["selection_overlap"]["rows_with_any_shared_sentence"],
                 "frozen_field_definition": "Counts rows containing text with multiple occurrences, including within the same row.",
                 "rows_sharing_sentence_with_another_selected_row": len(cross_shared),
                 "cross_example_shared_row_ids": cross_shared,
                 "rows_with_identical_premise_and_hypothesis": len(self_identical),
                 "identical_within_pair_row_ids": self_identical,
                 "distinct_strings_shared_across_different_rows": sum(len(ids) > 1 for ids in sentence_ids.values()),
                 "note": "This post-run descriptive audit clarifies overlap counting; it does not change selection, prompting, predictions, or accuracy."}}
    with Path(args.output_file).open("x", encoding="utf-8") as handle:
        json.dump(audit, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    print(json.dumps({"result": "passed", "correct": correct, "n": len(predictions), "cross_example_shared_rows": len(cross_shared)}))


if __name__ == "__main__":
    main()
