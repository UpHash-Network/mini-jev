#!/usr/bin/env python3
"""Export text-free, per-item saved evidence from the pinned NAACL source ZIP.

No archive extraction, model imports, network access, fitting or inference.
Run with --check to compare the checked-in export with a deterministic rebuild.
An ordinary build refuses an existing output directory.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
import math
from pathlib import Path
import re
import zipfile

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ZIP = ROOT / "paper/naacl2027/reproducibility/naacl-repro-v1-20260925.zip"
EXPECTED_ZIP_SHA256 = "a15e0699a54be15d56bd99ed8181429b71fdfc7ace756d6e065a75538786c053"
DEFAULT_OUT = ROOT / "docs/explorer/data"
PREFIX = "mini-jev/"
NATIVE = "qwen3.6-35b-a3b"
MODELS = (NATIVE, "qwen2.5-0.5b", "qwen2.5-1.5b")
DATASETS = {
    "JCoLA": ("noul", ["false", "true"]),
    "JCommonsenseQA": ("choice", [f"option_{i}" for i in range(5)]),
    "JSTS": ("score", [str(i) for i in range(6)]),
}
ROBUST = "presentation_robustness"
ENSEMBLE = "order_ensemble"
METHODS = ("baseline", "reverse_single", "cyclic_forward", "cyclic_reverse", "dihedral")
ROBUST_DEFINITIONS = {
    "baseline": ("Original presentation", "The saved original presentation."),
    "baseline_repeat": ("Exact input repeat", "A separate execution of the identical input, providing a numerical variation control."),
    "display_reverse": ("Reversed candidate rows", "Reverse only the displayed rows, preserving answer-token, key, and meaning bindings."),
    "display_rotate": ("Rotated candidate rows", "Rotate displayed rows by one position, preserving answer-token, key, and meaning bindings."),
    "label_reverse": ("Reassigned answer labels", "Keep semantic row order but reverse answer-letter bindings. Values are restored to semantic keys; this is not a pure position manipulation."),
    "opaque_keys": ("Opaque displayed keys", "Replace displayed keys with slot names while retaining semantic correspondence. The original keys have task-dependent meanings."),
    "instruction_reword": ("Reworded instruction", "One fixed alternative instruction. Semantic equivalence is a hypothesis without independent human verification."),
    "definition_reword": ("Reworded definitions", "Fixed alternative candidate definitions. Semantic equivalence is a hypothesis without independent human verification."),
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def encode(value):
    return (json.dumps(value, ensure_ascii=False, separators=(",", ":"),
                       allow_nan=False) + "\n").encode()


def finite(value):
    return type(value) in (float, int) and math.isfinite(value)


def close(a, b):
    if isinstance(a, str) or isinstance(b, str) or a is None or b is None:
        return a == b
    return finite(a) and finite(b) and math.isclose(a, b, rel_tol=1e-12, abs_tol=1e-12)


def aligned(probabilities, keys):
    """Use semantic dict keys, never the raw token vector's position."""
    require(len(keys) >= 2 and len(set(keys)) == len(keys), "invalid semantic keys")
    require(set(probabilities) == set(keys), "candidate key mismatch")
    values = [probabilities[k] for k in keys]
    require(all(finite(v) and 0 <= v <= 1 for v in values), "invalid probability")
    require(math.isclose(math.fsum(values), 1, abs_tol=1e-6), "probability sum mismatch")
    return values


def answer(probabilities, keys, kind, score_values=None):
    p = aligned(probabilities, keys)
    peak = max(p)
    ties = [key for key, value in zip(keys, p) if value == peak]
    label = ties[0]
    if kind == "choice":
        value = label
    elif kind == "noul":
        require(set(keys) == {"false", "true"}, "invalid Noul meaning")
        value = probabilities["true"]
    elif kind == "score":
        require(isinstance(score_values, dict) and set(score_values) == set(keys), "missing score scale")
        require(all(finite(v) for v in score_values.values()), "invalid score scale")
        value = math.fsum(probabilities[k] * score_values[k] for k in keys)
    else:
        raise ValueError("unknown type")
    entropy = -math.fsum(v * math.log(v) for v in p if v > 0)
    # Avoid a negative rounding residue for an exactly uniform distribution.
    concentration = min(1.0, max(0.0, 1 - entropy / math.log(len(keys))))
    return {"probabilities": p, "label": label, "value": value,
            "concentration": concentration, "top_tie_keys": ties}


def recipes(meta):
    """Same membership algebra as the frozen order_ensemble/analyze.py."""
    k = len(meta["canonical_key_order"])
    f, r = meta["forward_request_indices"], meta["reverse_request_indices"]
    require(len(f) == len(r) == len(set(f)) == len(set(r)) == k, "incomplete/duplicate orbit")
    require(meta["structural_orbit_identity"] is (k == 2), "structural flag mismatch")
    require((set(f) == set(r)) if k == 2 else not (set(f) & set(r)), "orbit intersection mismatch")
    require(meta["baseline_request_index"] == f[0] and meta["reverse_single_request_index"] == r[0], "baseline membership mismatch")
    return {"baseline": [f[0]], "reverse_single": [r[0]], "cyclic_forward": f,
            "cyclic_reverse": r, "dihedral": list(dict.fromkeys(f + r))}


def derive(meta, members, lookup):
    require(members and len(members) == len(set(members)), "empty/duplicate members")
    require(all(index in lookup for index in members), "missing member")
    rows = [lookup[index] for index in members]
    for row in rows:
        for field in ("model_key", "item_id", "dataset", "type", "split", "group", "gold_label", "gold_score", "score_values"):
            require(row.get(field) == meta.get(field), f"cross-item/model/study member: {field}")
        aligned(row["probabilities"], meta["canonical_key_order"])
    keys = meta["canonical_key_order"]
    probabilities = {key: math.fsum(row["probabilities"][key] for row in rows) / len(rows) for key in keys}
    result = answer(probabilities, keys, meta["type"], meta.get("score_values"))
    return {**result, "calls": len(rows), "input_tokens": sum(row["input_tokens"] for row in rows),
            "latency_ms": math.fsum(row["latency_ms"] for row in rows)}


class Archive:
    def __init__(self, path):
        raw = Path(path).read_bytes()
        require(sha(raw) == EXPECTED_ZIP_SHA256, "source ZIP SHA256 does not match pinned artifact")
        self.zip = zipfile.ZipFile(path)
        require(len(self.zip.namelist()) == len(set(self.zip.namelist())), "duplicate ZIP member")
        manifest = json.loads(self.zip.read(PREFIX + "BUNDLE_MANIFEST.json"))
        self.manifest = {PREFIX + row["path"]: row for row in manifest["files"]}
        self.sources = {}
        self.ids = {}

    def source(self, member):
        if member not in self.ids:
            raw = self.zip.read(member)
            if member in self.manifest:
                expected = self.manifest[member]
                require(sha(raw) == expected["sha256"] and len(raw) == expected["bytes"], "bundle member hash mismatch")
            else:
                require(member == PREFIX + "BUNDLE_MANIFEST.json", "unlisted bundle member")
            key = f"s{len(self.ids):02d}"
            self.ids[member] = key
            self.sources[key] = {"member": member, "sha256": sha(raw), "bytes": len(raw),
                                 "format": "jsonl" if member.endswith(".jsonl") else "json" if member.endswith(".json") else "source"}
        return self.ids[member]

    def json(self, member):
        self.source(member)
        return json.loads(self.zip.read(member))

    def rows(self, member):
        source = self.source(member)
        for line, raw in enumerate(self.zip.read(member).splitlines(), 1):
            require(bool(raw.strip()), "blank JSONL line")
            row = json.loads(raw)
            require(isinstance(row, dict), "invalid JSONL object")
            yield row, [source, line]


class Mappings:
    def __init__(self):
        self.values = {}; self.lookup = {}

    def add(self, row):
        mapping = {"candidate_keys": row["candidate_keys"], "candidate_tokens": row["candidate_tokens"],
                   "display_order": row.get("display_order")}
        require(len(mapping["candidate_keys"]) == len(mapping["candidate_tokens"]), "mapping size mismatch")
        encoded = encode(mapping)
        if encoded not in self.lookup:
            key = f"m{len(self.values):02d}"; self.lookup[encoded] = key; self.values[key] = mapping
        return self.lookup[encoded]


def runtime_model(runtime, source):
    if runtime.get("backend") == "transformers":
        return {"name": runtime["repo_id"], "backend": "transformers", "precision": runtime["dtype"],
                "revision": runtime["revision"], "revision_kind": "checkpoint_repository_revision",
                "device": runtime["device"], "source": source}
    data = runtime["fingerprint_data"]
    return {"name": data["model"], "backend": "llama.cpp", "precision": data["dtype"],
            "revision": data["revision"], "revision_kind": "GGUF_distribution_revision",
            "model_sha256": data["model_sha256"], "device": data["device"], "source": source}


def check_completion(archive, results, expected):
    completion = archive.json(results + "/COMPLETION.json")
    require(completion["status"] == "completed" and completion["failed_requests"] == 0
            and completion["recorded_requests"] == completion["expected_requests"] == expected,
            "incomplete source run; records must not be silently dropped")
    for filename, digest in completion["file_sha256"].items():
        member = results + "/" + filename
        require(archive.sources[archive.source(member)]["sha256"] == digest, "completion hash mismatch")


def physical(row, keys, source, mappings):
    require(row.get("error") is None and row["output_tokens"] == 0, "failed physical row")
    require(row.get("native_decode_count", row.get("forward_calls")) == 1, "physical call count mismatch")
    aligned(row["probabilities"], keys)
    require(set(row["candidate_keys"]) == set(keys), "physical semantic keys mismatch")
    logits = row["logits"]
    require(len(logits) == len(keys) and all(finite(z) for z in logits), "invalid logits")
    weights = [math.exp(z - max(logits)) for z in logits]
    denominator = math.fsum(weights)
    require(all(math.isclose(row["probabilities"][key], weight / denominator, abs_tol=1e-6)
                for key, weight in zip(row["candidate_keys"], weights)), "raw semantic softmax mismatch")
    ties = [key for key, z in zip(row["candidate_keys"], logits) if z == max(logits)]
    require(row["label"] == ties[0], "raw argmax does not follow candidate vector order")
    result = answer(row["probabilities"], keys, row["type"], row.get("score_values"))
    # Physical ties obey the observed candidate-token vector, derived ties use canonical keys.
    result["label"] = row["label"]; result["top_tie_keys"] = ties
    if row["type"] == "choice": result["value"] = row["label"]
    require(close(result["value"], row["typed_value"]), "raw typed-value mismatch")
    require(close(result["concentration"], row["concentration"]), "raw concentration mismatch")
    require(type(row["input_tokens"]) is int and row["input_tokens"] > 0, "invalid input tokens")
    require(finite(row["latency_ms"]) and row["latency_ms"] >= 0, "invalid saved latency")
    return {"id": row["condition"], "kind": "physical", **result, "calls": 1,
            "input_tokens": row["input_tokens"], "latency_ms": row["latency_ms"],
            "source": source, "mapping": mappings.add(row)}


def item_metadata(row):
    require(re.fullmatch(r"[0-9a-f]{64}", row["source_question_sha256"]) is not None, "invalid source item hash")
    result = {k: row[k] for k in ("item_id", "source_question_sha256", "split", "group")}
    if row["type"] == "score":
        require(finite(row["gold_score"]) and 0 <= row["gold_score"] <= 5, "invalid continuous gold")
        result["gold_score"] = row["gold_score"]
    else:
        result["gold_label"] = row["gold_label"]
    return result


def variant_summaries(panel):
    groups = defaultdict(list)
    for item in panel["items"]:
        for variant in item["variants"]: groups[variant["id"]].append((item, variant))
    result = {}
    for key, rows in groups.items():
        n = len(rows)
        counts = dict(sorted(Counter(v["label"] for _, v in rows).items()))
        value = {"items": n, "label_counts": counts, "unique_labels": len(counts),
                 "max_label_share": max(counts.values()) / n,
                 "calls_per_answer": rows[0][1]["calls"]}
        if panel["type"] == "score":
            values = [v["value"] for _, v in rows]; mean = math.fsum(values) / n
            value.update(mae=math.fsum(abs(v["value"] - item["gold_score"]) for item, v in rows)/n,
                         value_variance=math.fsum((v - mean)**2 for v in values)/n,
                         value_min=min(values), value_max=max(values))
        else:
            value["accuracy"] = sum(v["label"] == item["gold_label"] for item, v in rows)/n
        result[key] = value
    return result


def definitions():
    robust = {key: {"id": key, "label": value[0], "description": value[1], "kind": "physical"}
              for key, value in ROBUST_DEFINITIONS.items()}
    ensemble = {}
    for orientation in ("forward", "reverse"):
        for shift in range(6):
            key = f"{orientation}_{shift}"
            ensemble[key] = {"id": key, "label": f"{orientation.capitalize()} rotation {shift}",
                             "description": "One executed presentation preserving token, key, and meaning bindings; one physical call.", "kind": "physical"}
    for key, label, description in (
        ("baseline", "Original single call", "Reuse the forward_0 probabilities; this is not an additional execution."),
        ("reverse_single", "Reversed single call", "A single reverse-oriented presentation; for binary items, reuse forward_1."),
        ("cyclic_forward", "Forward cyclic average", "Equal-weight average of K semantic probability vectors, not an average of logits."),
        ("cyclic_reverse", "Reverse cyclic average", "Average K reverse-oriented probability vectors. For binary items, these are the same two calls as the forward pool."),
        ("dihedral", "Both-orientation average", "Average the union of physical calls: 2 for binary, 10 for five-choice, and 12 for six-stage items."),
    ):
        ensemble[key] = {"id": key, "label": label, "description": description, "kind": "derived"}
    return {ROBUST: robust, ENSEMBLE: ensemble}


def make_featured(panels):
    examples = []
    copy = {
        "order_flip": ("Same item, different decision", "Reversing candidate rows changes this saved semantic decision. All eligible items remain available."),
        "averaging_worse": ("More calls can be worse", "This outcome-selected example changes from a correct single answer to an incorrect cyclic average."),
        "concentrated_labels": ("Concentrated labels need context", "Inspect the full 200-item label distribution and score variance; one item cannot establish collapse."),
        "expectation_vs_mode": ("Expected score is not the mode", "The continuous expected score, most probable stage, and continuous gold score are different quantities."),
    }
    specs = [
        ("order_flip", ROBUST, NATIVE, "JCommonsenseQA", "baseline", "display_reverse",
         "Lexicographically first item ID with different baseline and display-reverse semantic labels, regardless of correctness.",
         lambda i, a, b: a["label"] != b["label"]),
        ("averaging_worse", ENSEMBLE, NATIVE, "JCommonsenseQA", "baseline", "cyclic_forward",
         "Lexicographically first item ID for which the original single call is correct and the cyclic average is wrong; an outcome-conditioned illustration.",
         lambda i, a, b: a["label"] == i["gold_label"] and b["label"] != i["gold_label"]),
        ("concentrated_labels", ENSEMBLE, "qwen2.5-0.5b", "JSTS", "baseline", "cyclic_forward",
         "Lexicographically first 0.5B JSTS item ID. Assess concentration using all 200 items' label counts and score variance, not this example alone.",
         lambda i, a, b: True),
        ("expectation_vs_mode", ROBUST, NATIVE, "JSTS", "baseline", "display_reverse",
         "Lexicographically first item ID whose baseline expected score differs from its modal stage by at least 0.4. Continuous gold is not rounded.",
         lambda i, a, b: abs(a["value"] - float(a["label"])) >= 0.4),
    ]
    for key, study, model, dataset, left, right, rule, predicate in specs:
        panel = next(p for p in panels if p["study_id"] == study and p["model_key"] == model and p["dataset"] == dataset)
        matches = []
        for item in panel["items"]:
            variants = {v["id"]: v for v in item["variants"]}
            if predicate(item, variants[left], variants[right]): matches.append(item)
        require(matches, f"no eligible featured example: {key}")
        examples.append({"id": key, "panel_id": panel["id"], "study_id": study, "model_key": model,
                         "dataset": dataset, "item_id": matches[0]["item_id"], "a": left, "b": right,
                         "title": copy[key][0], "description": copy[key][1],
                         "left": left, "right": right, "selection_rule": rule,
                         "eligible_items_under_rule": len(matches)})
    return examples


def build(zip_path=DEFAULT_ZIP):
    archive = Archive(zip_path); mappings = Mappings(); panels = {}; model_info = {ROBUST: {}, ENSEMBLE: {}}
    for path in ("BUNDLE_MANIFEST.json", "paper/journal_robustness/PROTOCOL.json",
                 "paper/journal_robustness/cross_model/PROTOCOL.json", "paper/order_ensemble/PROTOCOL.json",
                 "paper/order_ensemble/analyze.py"):
        archive.source(PREFIX + path)
    for path in ("paper/journal_robustness/study_v1/AUDIT.json",
                 "paper/journal_robustness/cross_model/study_v1/AUDIT.json", "paper/order_ensemble/study_v1/AUDIT.json"):
        audit = archive.json(PREFIX + path)
        require(audit["passed"] is True and all(c["passed"] for c in audit["checks"]), "source audit did not pass")
    ensemble_meta = {r["item_id"]: r for r in archive.json(PREFIX + "paper/order_ensemble/study_v1/ENSEMBLES.json")}
    physical_count = derived_count = 0
    for study in (ROBUST, ENSEMBLE):
        for model in MODELS:
            if study == ENSEMBLE:
                base = PREFIX + "paper/order_ensemble/study_v1"; results = base + "/results/" + model; expected = 4800
            elif model == NATIVE:
                base = PREFIX + "paper/journal_robustness/study_v1"; results = base + "/results"; expected = 4000
            else:
                base = PREFIX + "paper/journal_robustness/cross_model/study_v1"; results = base + "/results/" + model; expected = 1800
            check_completion(archive, results, expected)
            runtime = archive.json(results + "/RUNTIME.json")
            model_info[study][model] = runtime_model(runtime, archive.source(results + "/RUNTIME.json"))
            freeze = archive.json(base + "/FREEZE.json")
            schedule = archive.json(base + "/SCHEDULE.json")
            if study == ROBUST and model != NATIVE:
                schedule = [r for r in schedule if r["model_key"] == model]
            require(len(schedule) == expected, "schedule count mismatch")
            items = {}; lookup = {}; source_lookup = {}; item_datasets = {}
            raw_rows = list(archive.rows(results + "/predictions.jsonl"))
            require(len(raw_rows) == expected, "raw record count mismatch")
            for (row, source), scheduled in zip(raw_rows, schedule):
                require(all(row.get(k) == value for k, value in scheduled.items()), "frozen schedule/physical mismatch")
                require(row.get("model_key", model) == model, "physical model mismatch")
                kind, keys = DATASETS[row["dataset"]]
                require(row["type"] == kind, "dataset/type mismatch")
                if kind == "score": require(row["score_values"] == {str(i): i for i in range(6)}, "score scale mismatch")
                meta = item_metadata(row)
                item_datasets[row["item_id"]] = row["dataset"]
                if row["item_id"] not in items:
                    items[row["item_id"]] = {**meta, "variants": []}
                item = items[row["item_id"]]
                require(all(item.get(k) == v for k, v in meta.items()), "per-item metadata inconsistency")
                require(row["condition"] not in {v["id"] for v in item["variants"]}, "duplicate item condition")
                item["variants"].append(physical(row, keys, source, mappings))
                require(row["request_index"] not in lookup, "duplicate request index within model")
                lookup[row["request_index"]] = row; source_lookup[row["request_index"]] = source
                physical_count += 1
            if study == ENSEMBLE:
                derived_member = base + "/analysis/" + model + "/derived_answers.jsonl"
                saved_rows = list(archive.rows(derived_member))
                require(len(saved_rows) == 3000, "derived row count mismatch")
                seen = set()
                for saved, source in saved_rows:
                    item = items[saved["item_id"]]
                    meta = {**ensemble_meta[saved["item_id"]], "model_key": model}
                    method = saved["method"]; members = recipes(meta)[method]
                    require((saved["item_id"], method) not in seen, "duplicate derived method")
                    seen.add((saved["item_id"], method))
                    require(members == saved["physical_member_indices"], "saved ensemble recipe mismatch")
                    calculated = derive(meta, members, lookup)
                    require(calculated["probabilities"] == aligned(saved["probabilities"], meta["canonical_key_order"]), "derived probabilities mismatch")
                    for output, original in (("label", "label"), ("value", "typed_value"), ("calls", "physical_forwards_per_answer"),
                                             ("input_tokens", "input_tokens_sum"), ("latency_ms", "observed_forward_latency_sum_ms")):
                        require(close(calculated[output], saved[original]), f"derived field mismatch: {output}")
                    require(calculated["top_tie_keys"] == saved["tie_keys"], "derived tie mismatch")
                    item["structural_orbit_identity"] = meta["structural_orbit_identity"]
                    item["variants"].append({"id": method, "kind": "derived", **calculated, "source": source,
                                             "member_ids": [lookup[i]["condition"] for i in members],
                                             "member_sources": [source_lookup[i] for i in members]})
                    derived_count += 1
                require(len(seen) == 3000 and set(items) == set(ensemble_meta), "missing derived answers")
            for dataset, (kind, keys) in DATASETS.items():
                selected = [items[k] for k in sorted(items) if item_datasets[k] == dataset]
                require(len(selected) == 200, "panel must retain all 200 source items")
                panel_id = f"{study}--{model}--{dataset.lower()}"
                order = list(ROBUST_DEFINITIONS) if study == ROBUST else list(METHODS) + [f"{d}_{i}" for d in ("forward", "reverse") for i in range(6)]
                for item in selected: item["variants"].sort(key=lambda v: order.index(v["id"]))
                panel = {"id": panel_id, "study_id": study, "model_key": model, "dataset": dataset,
                         "type": kind, "canonical_keys": keys, "score_values": list(range(6)) if kind == "score" else None,
                         "model_metadata": model_info[study][model],
                         "items": selected}
                panels[panel_id] = panel
    require(physical_count == 22000 and derived_count == 9000 and len(panels) == 18, "eligible records not fully exported")
    files = {}; descriptors = []
    for panel in panels.values():
        raw = encode(panel); path = "panels/" + panel["id"] + ".json"; files[path] = raw
        counts = Counter(v["kind"] for i in panel["items"] for v in i["variants"])
        descriptors.append({k: panel[k] for k in ("id", "study_id", "model_key", "dataset", "type", "canonical_keys", "score_values", "model_metadata")})
        descriptors[-1].update(path=path, sha256=sha(raw), bytes=len(raw), item_count=200,
                               physical_record_count=counts["physical"], derived_record_count=counts["derived"],
                               variant_ids=[v["id"] for v in panel["items"][0]["variants"]],
                               default_left="baseline", default_right="display_reverse" if panel["study_id"] == ROBUST else "cyclic_forward",
                               variant_summaries=variant_summaries(panel))
    index = {"schema_version": 1, "bundle": {"filename": Path(zip_path).name, "sha256": EXPECTED_ZIP_SHA256,
              "artifact_version": "naacl-repro-v1-20260925"}, "exporter_sha256": sha(Path(__file__).read_bytes()),
             "studies": {ROBUST: {"label": "Presentation sensitivity", "physical_records": 7600, "unique_source_items": 600,
                                    "description": "Reuse of 600 public items across three checkpoints; available conditions differ by checkpoint."},
                         ENSEMBLE: {"label": "Fixed-binding cyclic averaging", "physical_records": 14400, "unique_source_items": 600,
                                    "description": "Another 600 public items across three checkpoints. Binary orientation agreement follows structurally from the same two physical calls."}},
             "models": model_info, "sources": archive.sources, "mappings": mappings.values,
             "variant_definitions": definitions(), "panels": descriptors,
             "featured": make_featured(list(panels.values())),
             "coverage": {"panels": 18, "study_item_model_records": 3600, "physical_records": physical_count,
                          "derived_records": derived_count, "distinct_source_item_ids": len({i["item_id"] for p in panels.values() for i in p["items"]}),
                          "excluded_failed_or_missing_records": 0},
             "definitions": {"probabilities": "Candidate-normalized probabilities in panel canonical_keys order, restored to semantic keys; not calibrated correctness probabilities.",
                             "value": "Choice: semantic label; Noul: p(true); Score: expectation over stages 0–5. A Score label is the modal stage and differs from value.",
                             "concentration": "1−H(p)/log(K), concentration within the candidate set; not correctness probability or calibrated confidence.",
                             "calls": "Physical calls needed for one answer. Derived and physical variants share members; summing displayed calls double-counts shared execution.",
                             "latency_ms": "Saved sequential call time; derived time sums its members. Not live performance or batched service response time.",
                             "source": "[source_id, one-based JSONL line within the ZIP member]. File hashes are shared in sources.",
                             "mapping": "Raw candidate vector's key/token bindings. display_order=null means that field was absent from the original record.",
                             "featured": "Explicitly selected illustrations, sometimes outcome-conditioned. They are not random or representative samples; all eligible items are also included."},
             "limitations": ["Browsing saved evidence performs no new inference, training, or live execution.",
                             "Compare only the same study, item, and model; do not infer effects by crossing studies, items, or checkpoints.",
                             "Benchmark source text and answer content are omitted. Item IDs and source_question_sha256 identify records.",
                             "New item IDs do not establish semantic independence or absence from pretraining.",
                             "Rewording equivalence is an AI hypothesis without independent human assessment.",
                             "Checkpoints differ in architecture, quantization, and runtime. No speed ranking or causal size claim is made."]}
    files["index.json"] = encode(index)
    archive.zip.close()
    return files


def write_files(files, output, check=False):
    output = Path(output)
    if check:
        require(output.is_dir(), "no existing export to check")
        existing = {str(p.relative_to(output)) for p in output.rglob("*") if p.is_file()}
        require(existing == set(files), "export file inventory mismatch")
        for name, data in files.items(): require((output / name).read_bytes() == data, f"export bytes mismatch: {name}")
    else:
        output.mkdir(parents=True, exist_ok=False)
        for name, data in files.items():
            target = output / name; target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(data)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--zip", type=Path, default=DEFAULT_ZIP)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.out.exists() and not args.check: parser.error("existing export refused; use --check or a new directory")
    files = build(args.zip); write_files(files, args.out, args.check)
    print(json.dumps({"passed": True, "files": len(files), "bytes": sum(map(len, files.values())),
                      "physical_records": 22000, "derived_records": 9000, "check_only": args.check}))


if __name__ == "__main__":
    main()
