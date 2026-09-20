#!/usr/bin/env python3
"""Frozen JNLI pilot. Dataset text stays in an explicitly supplied external cache."""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import platform
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
LABELS = ["contradiction", "entailment", "neutral"]


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value):
    return hashlib.sha256(value).hexdigest()


def now():
    return datetime.now(timezone.utc).isoformat()


def write_new(path, value):
    with Path(path).open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n")


def rank(row, salt):
    return digest((salt + str(row["sentence_pair_id"])).encode())


def select(rows, count, salt):
    ids = [str(row["sentence_pair_id"]) for row in rows]
    if len(set(ids)) != len(ids):
        raise ValueError("duplicate sentence_pair_id")
    if any(row["label"] not in LABELS for row in rows):
        raise ValueError("unknown JNLI label")
    chosen = []
    for label in LABELS:
        pool = sorted((row for row in rows if row["label"] == label), key=lambda r: (rank(r, salt), str(r["sentence_pair_id"])))
        if len(pool) < count:
            raise ValueError("not enough rows for balanced sample")
        chosen.extend(pool[:count])
    return sorted(chosen, key=lambda r: (rank(r, salt), str(r["sentence_pair_id"])))


def pair_hash(row):
    return digest(canonical([row["sentence1"], row["sentence2"]]).encode())


def reference(row, salt):
    return {"sentence_pair_id": str(row["sentence_pair_id"]),
            "row_sha256": digest(canonical(row).encode()), "sentence_pair_sha256": pair_hash(row),
            "sentence1_sha256": digest(row["sentence1"].encode()),
            "sentence2_sha256": digest(row["sentence2"].encode()),
            "sampling_rank_sha256": rank(row, salt), "gold": row["label"]}


def overlap(rows):
    pairs = Counter(pair_hash(row) for row in rows)
    premises = Counter(row["sentence1"] for row in rows)
    hypotheses = Counter(row["sentence2"] for row in rows)
    sentences = premises + hypotheses
    captions = Counter(row["yjcaptions_id"] for row in rows)
    return {"n": len(rows), "distinct_pair_ids": len({str(r["sentence_pair_id"]) for r in rows}),
            "distinct_exact_sentence_pairs": len(pairs),
            "distinct_premises": len(premises), "distinct_hypotheses": len(hypotheses),
            "distinct_sentences_across_both_positions": len(sentences),
            "repeated_sentence_values": sum(n > 1 for n in sentences.values()),
            "sentence_occurrences_beyond_first": sum(n - 1 for n in sentences.values()),
            "rows_with_any_shared_sentence": sum(sentences[r["sentence1"]] > 1 or sentences[r["sentence2"]] > 1 for r in rows),
            "distinct_yjcaptions_ids": len(captions),
            "repeated_yjcaptions_ids": sum(n > 1 for n in captions.values()),
            "warning": "Shared text and image/caption origins can correlate examples; distinct pair IDs do not establish independence."}


def probabilities(logits, temperature):
    peak = max(logits)
    values = [math.exp((x - peak) / temperature) for x in logits]
    total = math.fsum(values)
    return [x / total for x in values]


def metrics(records, temperature):
    confusion = [[0] * 3 for _ in LABELS]
    bins = [[] for _ in range(10)]
    loss, brier, good = 0.0, 0.0, 0
    for row in records:
        p = probabilities(row["candidate_logits"], temperature)
        gold = LABELS.index(row["gold"])
        predicted = max(range(3), key=p.__getitem__)
        ok = predicted == gold
        good += ok
        confusion[gold][predicted] += 1
        # Log-sum-exp computes NLL without clipping underflowed probabilities.
        z = [x / temperature for x in row["candidate_logits"]]
        peak = max(z)
        loss += peak + math.log(math.fsum(math.exp(x - peak) for x in z)) - z[gold]
        brier += math.fsum((x - (i == gold)) ** 2 for i, x in enumerate(p))
        confidence = p[predicted]
        bins[min(9, int(confidence * 10))].append((ok, confidence))
    n = len(records)
    if not n:
        raise ValueError("metrics require records")
    classes, f1s = {}, []
    for i, label in enumerate(LABELS):
        tp, support = confusion[i][i], sum(confusion[i])
        predicted_n = sum(confusion[j][i] for j in range(3))
        precision = tp / predicted_n if predicted_n else 0.0
        recall = tp / support if support else 0.0
        f1 = 2 * tp / (support + predicted_n) if support + predicted_n else 0.0
        f1s.append(f1)
        classes[label] = {"support": support, "correct": tp, "precision": precision, "recall": recall, "f1": f1}
    ece = sum(abs(sum(v[0] for v in group) - sum(v[1] for v in group)) / n for group in bins)
    return {"temperature": temperature, "n": n, "correct": good, "accuracy": good / n,
            "macro_f1": sum(f1s) / 3, "nll": loss / n, "multiclass_brier_sum": brier / n,
            "ece_10_equal_width": ece, "confusion_rows_gold_columns_prediction": confusion,
            "label_order": LABELS, "per_class": classes}


def quantile(values, probability):
    ordered = sorted(values)
    pos = (len(ordered) - 1) * probability
    lower = math.floor(pos)
    return ordered[lower] + (ordered[min(lower + 1, len(ordered) - 1)] - ordered[lower]) * (pos - lower)


def question(row, protocol):
    return {"type": "choice", "state": protocol["prompt"]["state_template"].format(
        premise=row["sentence1"], hypothesis=row["sentence2"]),
        "instructions": protocol["prompt"]["instructions"], "criteria": protocol["prompt"]["criteria"]}


def prepare(args, protocol):
    preparation_dir = Path(args.preparation_dir)
    preparation_dir.mkdir(parents=True, exist_ok=True)
    cache = Path(args.cache_dir).resolve()
    if cache.is_relative_to(ROOT):
        raise ValueError("dataset cache must be outside the Git repository")
    cache.mkdir(parents=True, exist_ok=True)
    source = cache / "jnli-valid-v1.3.json"
    if not source.exists():
        subprocess.run(["curl", "--fail", "--silent", "--show-error", "--location", protocol["source"]["url"], "-o", str(source)], check=True)
    raw = source.read_bytes()
    if digest(raw) != protocol["source"]["sha256"]:
        raise ValueError("pinned source SHA-256 mismatch")
    # Freeze protocol/source bytes/script before parsing labels or selecting rows.
    frozen = {"created_utc": now(), "protocol_sha256": digest((HERE / "PROTOCOL.json").read_bytes()),
              "source_sha256": digest(raw), "runner_sha256": digest(Path(__file__).read_bytes()),
              "native_engine_sha256": digest((ROOT / "native_engine.py").read_bytes()),
              "stage": "before_source_row_parsing_and_before_model_inference", "protocol": protocol}
    write_new(preparation_dir / "PREPARATION.json", frozen)
    rows = [json.loads(line) for line in raw.decode("utf-8").splitlines() if line.strip()]
    chosen = select(rows, protocol["sampling"]["per_class"], protocol["sampling"]["salt"])
    selection = {"source_count": len(rows), "source_label_counts": dict(sorted(Counter(r["label"] for r in rows).items())),
                 "selected_overlap": overlap(chosen), "source_overlap": overlap(rows),
                 "items": [reference(row, protocol["sampling"]["salt"]) for row in chosen]}
    write_new(preparation_dir / "SELECTION.json", selection)
    print(json.dumps({"prepared": len(chosen), "source": len(rows), "protocol_sha256": frozen["protocol_sha256"]}), flush=True)


def run(args, protocol):
    preparation_dir = Path(args.preparation_dir)
    frozen = json.loads((preparation_dir / "PREPARATION.json").read_text())
    for path, key in ((HERE / "PROTOCOL.json", "protocol_sha256"), (Path(__file__), "runner_sha256"), (ROOT / "native_engine.py", "native_engine_sha256")):
        if digest(path.read_bytes()) != frozen[key]:
            raise ValueError(f"frozen artifact changed: {path.name}")
    source = Path(args.cache_dir) / "jnli-valid-v1.3.json"
    raw = source.read_bytes()
    if digest(raw) != frozen["source_sha256"]:
        raise ValueError("source changed")
    rows = [json.loads(line) for line in raw.decode("utf-8").splitlines() if line.strip()]
    selected = select(rows, protocol["sampling"]["per_class"], protocol["sampling"]["salt"])
    saved = json.loads((preparation_dir / "SELECTION.json").read_text())
    if [reference(row, protocol["sampling"]["salt"]) for row in selected] != saved["items"]:
        raise ValueError("selection mismatch")
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=False)
    sys.path.insert(0, str(ROOT))
    from native_engine import NativeEngine
    started = time.perf_counter()
    with NativeEngine(model_file=args.model_file, native_binary=args.native_binary,
                      native_manifest=args.native_manifest, model_manifest=ROOT / "native_model.json",
                      log_file=Path(args.cache_dir) / "native-pilot.log", **protocol["engine"]) as engine:
        startup_ms = (time.perf_counter() - started) * 1000
        run_manifest = {"created_utc": now(), "preparation_sha256": digest((preparation_dir / "PREPARATION.json").read_bytes()),
                        "selection_sha256": digest((preparation_dir / "SELECTION.json").read_bytes()),
                        "runtime_fingerprint": engine.runtime_fingerprint, "fingerprint_data": engine.fingerprint_data,
                        "hardware": protocol["hardware"], "python": platform.python_version(),
                        "startup_ms": startup_ms, "stage": "before_warmup_and_evaluation",
                        "temperature_primary": engine.temperature, "model_ready": engine.ready}
        write_new(out / "RUN_MANIFEST.json", run_manifest)
        for row in protocol["warmup"]:
            engine.decide(question(row, protocol))
        results = []
        with (out / "predictions.jsonl").open("x", encoding="utf-8") as handle:
            for index, (row, ref) in enumerate(zip(selected, saved["items"]), 1):
                tick = time.perf_counter()
                answer = engine.decide(question(row, protocol))
                elapsed = (time.perf_counter() - tick) * 1000
                if answer["candidate_keys"] != LABELS:
                    raise ValueError("candidate order mismatch")
                result = {**ref, "prediction": answer["label"], "candidate_keys": answer["candidate_keys"],
                          "candidate_logits": answer["candidate_logits"], "candidate_ids": answer["candidate_ids"],
                          "probabilities_T1": answer["probabilities"], "input_tokens": answer["input_tokens"],
                          "latency_ms": elapsed, "native_model_ms": answer["model_ms"],
                          "native_decode_count": answer["native_decode_count"]}
                handle.write(canonical(result) + "\n")
                handle.flush()
                results.append(result)
                if index % 50 == 0:
                    print(json.dumps({"completed": index, "total": len(selected)}), flush=True)
        summary = {"completed_utc": now(), "n": len(results), "warmup_n": len(protocol["warmup"]),
                   "decode_count": engine.total_decode_count, "primary_T1": metrics(results, 1.0),
                   "historical_temperature_transfer": metrics(results, protocol["secondary_temperature"]),
                   "latency_ms": {"p50": quantile([r["latency_ms"] for r in results], .5),
                                  "p95": quantile([r["latency_ms"] for r in results], .95),
                                  "max": max(r["latency_ms"] for r in results)},
                   "input_tokens": {"min": min(r["input_tokens"] for r in results), "max": max(r["input_tokens"] for r in results),
                                    "n_above_512": sum(r["input_tokens"] > 512 for r in results)},
                   "predictions_sha256": digest((out / "predictions.jsonl").read_bytes()),
                   "selection_overlap": saved["selected_overlap"]}
        write_new(out / "METRICS.json", summary)
        print(json.dumps(summary, ensure_ascii=False), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["prepare", "run"])
    parser.add_argument("--cache-dir", required=True)
    parser.add_argument("--preparation-dir", default=str(HERE))
    parser.add_argument("--output-dir")
    parser.add_argument("--model-file")
    parser.add_argument("--native-binary")
    parser.add_argument("--native-manifest")
    args = parser.parse_args()
    if args.mode == "run" and not all((args.output_dir, args.model_file, args.native_binary, args.native_manifest)):
        parser.error("run requires --output-dir, --model-file, --native-binary, --native-manifest")
    protocol = json.loads((HERE / "PROTOCOL.json").read_text())
    (prepare if args.mode == "prepare" else run)(args, protocol)


if __name__ == "__main__":
    main()
