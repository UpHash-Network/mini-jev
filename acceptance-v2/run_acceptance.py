#!/usr/bin/env python3
"""Freeze, calibrate, and evaluate Mini Jev without exposing test text on stdout.

Only NativeEngine performs inference. Every measured request has batch size one
and must execute exactly one llama_decode API call. Test failures remain in the new run
directory; existing run directories are never reused or overwritten.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import math
import platform
import random
import statistics
import subprocess
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PRIVATE = Path(__file__).resolve().parent / "private"
SEED = 20260920
LATENCY_TOKEN_LIMIT = 512
TYPES = ("choice", "noul", "score")
INPUT_KEYS = ("type", "state", "instructions", "criteria")
GRID = [10 ** (-1 + 2 * i / 200) for i in range(201)]


def utcnow():
    return datetime.now(timezone.utc).isoformat()


def sha256(path: Path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json_new(path: Path, data):
    with path.open("x", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, allow_nan=False)
        f.write("\n")


def numeric(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def no_duplicate_object_keys(pairs):
    obj = {}
    for key, value in pairs:
        if key in obj:
            raise ValueError(f"duplicate JSON object key: {key}")
        obj[key] = value
    return obj


def read_json(text):
    def reject_constant(_):
        raise ValueError("non-finite JSON number")
    return json.loads(text, object_pairs_hook=no_duplicate_object_keys,
                      parse_constant=reject_constant)


def load_config(path: Path):
    data = read_json(path.read_text())
    if not isinstance(data, dict):
        raise ValueError("config must be a JSON object")
    kwargs = data["engine"] if "engine" in data else data
    if not isinstance(kwargs, dict):
        raise ValueError("config.engine must be a NativeEngine kwargs object")
    kwargs = dict(kwargs)
    if "temperature_config" in kwargs:
        raise ValueError("pass temperature_config with the CLI, not inside engine config")
    if kwargs.get("temperature", 1.0) != 1.0:
        raise ValueError("engine config temperature must be 1.0; calibration is separate")
    for field in ("model_file", "native_binary", "model_manifest", "native_manifest", "log_file"):
        if field in kwargs and kwargs[field] is not None:
            p = Path(kwargs[field]).expanduser()
            kwargs[field] = str((path.parent / p).resolve() if not p.is_absolute() else p.resolve())
    return kwargs


def question(case):
    # Gold labels, case IDs, source names, and family tags never enter the model.
    return {key: case[key] for key in INPUT_KEYS}


def candidate_keys(case):
    if case["type"] == "score":
        return [str(i) for i in range(len(case["criteria"]))]
    return list(case["criteria"])


def load_cases(path: Path, source: str, expected_each: int):
    rows = []
    ids = set()
    for line_no, line in enumerate(path.read_text().splitlines(), 1):
        if not line.strip():
            continue
        case = read_json(line)
        if not isinstance(case, dict) or not all(k in case for k in (*INPUT_KEYS, "id", "label")):
            raise ValueError(f"invalid case schema at {path.name}:{line_no}")
        if not isinstance(case["id"], str) or not case["id"] or case["id"] in ids:
            raise ValueError(f"invalid or duplicate ID at {path.name}:{line_no}")
        ids.add(case["id"])
        kind = case["type"]
        criteria = case["criteria"]
        if kind not in TYPES or not isinstance(case["instructions"], str) or not case["instructions"].strip():
            raise ValueError(f"invalid type/instructions at {path.name}:{line_no}")
        if kind == "score":
            if not isinstance(criteria, list):
                raise ValueError("Score criteria must be an ordered list")
            values = criteria
        else:
            if not isinstance(criteria, dict):
                raise ValueError("Choice/Noul criteria must be mappings")
            if kind == "noul" and set(criteria) != {"false", "true"}:
                raise ValueError("Noul keys must be false and true")
            if any(not isinstance(k, str) or not k for k in criteria):
                raise ValueError("candidate keys must be nonempty strings")
            values = list(criteria.values())
        if not 2 <= len(criteria) <= 8 or any(not isinstance(x, str) or not x.strip() for x in values):
            raise ValueError("acceptance cases need 2--8 nonempty descriptions")
        case["label"] = str(case["label"]).lower() if isinstance(case["label"], bool) else str(case["label"])
        if case["label"] not in candidate_keys(case):
            raise ValueError(f"gold label outside candidates at {path.name}:{line_no}")
        case["source"] = source
        case["family"] = str(case.get("family", case.get("tag", kind)))
        rows.append(case)
    counts = collections.Counter(x["type"] for x in rows)
    expected = {kind: expected_each for kind in TYPES}
    if counts != expected:
        raise ValueError(f"{source} counts {dict(counts)} do not match {expected}")
    return rows


def source_paths():
    paths = [ROOT / "native_engine.py", Path(__file__).resolve(),
             ROOT / "COMPLETION_CRITERIA.md"]
    for name in ("requirements-native.txt", "requirements-native.lock.txt", "build_native.sh"):
        if (ROOT / name).is_file():
            paths.append(ROOT / name)
    return paths


def file_hashes(paths):
    return {str(p.absolute()): sha256(p) for p in paths}


def file_identity(path):
    """Detect replacement/touch/truncation and symlink retargeting without rereading GGUF."""
    stat = path.stat()
    link = path.lstat()
    return {"resolved_path": str(path.resolve()), "bytes": stat.st_size,
            "device": stat.st_dev, "inode": stat.st_ino,
            "mtime_ns": stat.st_mtime_ns, "ctime_ns": stat.st_ctime_ns,
            "link_inode": link.st_ino, "link_mtime_ns": link.st_mtime_ns}


def valid_sha(value):
    return isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


class NativeArtifacts:
    """Hash model weights once; continuously verify metadata and all small artifacts.

    Expected GGUF identity comes from the pinned native_model.json. A completed
    download receipt is not a trusted hash cache. The full file is streamed once
    at the start of each calibration/evaluation run. Later checks compare file
    identity and stat metadata; this limitation is recorded in freeze.json.
    """
    def __init__(self, kwargs, extra_manifest=None):
        started = time.perf_counter()
        for key in ("model_file", "native_binary"):
            if not isinstance(kwargs.get(key), str):
                raise ValueError(f"native config requires {key}")
        self.model_file = Path(kwargs["model_file"]).absolute()
        self.binary = Path(kwargs["native_binary"]).absolute()
        self.bin_dir = self.binary.parent
        self.package_dir = self.bin_dir.parent
        manifest = Path(kwargs.get("model_manifest") or ROOT / "native_model.json").absolute()
        build_path = Path(kwargs.get("native_manifest") or self.package_dir / "BUILD.json").absolute()
        cpp_path = self.package_dir / "llama_decision_helper.cpp"
        for path in (self.model_file, self.binary, manifest, build_path, cpp_path):
            if not path.is_file():
                raise ValueError(f"required native artifact is missing: {path.name}")
        self.inventory = self._inventory()
        initial_paths = [manifest, build_path, cpp_path, self.binary] + list(self.inventory)
        initial_hashes = file_hashes(initial_paths)
        meta = read_json(manifest.read_text())
        if (not isinstance(meta, dict) or meta.get("schema_version") != 1
                or not valid_sha(meta.get("sha256")) or type(meta.get("bytes")) is not int
                or meta["bytes"] <= 0 or meta.get("filename") != self.model_file.name):
            raise ValueError("model manifest has an invalid schema, hash, size, or filename")
        for field, expected in (("model", meta.get("repo_id")), ("revision", meta.get("revision")),
                                ("dtype", meta.get("quantization"))):
            if field in kwargs and kwargs[field] != expected:
                raise ValueError(f"config {field} does not match the pinned model manifest")
        self.model_meta = meta
        self.large = {}
        self._verify_large(self.model_file, "model_weights", meta["sha256"], meta["bytes"])
        self.small_paths = list(initial_paths)
        verified_hashes = {}
        build = read_json(build_path.read_text())
        declared = build.get("sha256") if isinstance(build, dict) else None
        if not isinstance(declared, dict) or self.binary.name not in declared:
            raise ValueError("BUILD.json must pin the helper binary and its libraries")
        for name, expected in declared.items():
            if not isinstance(name, str) or Path(name).name != name or not valid_sha(expected):
                raise ValueError("invalid BUILD artifact name or checksum")
            artifact = self.bin_dir / name
            if not artifact.is_file() or sha256(artifact) != expected:
                raise ValueError(f"native BUILD checksum mismatch: {name}")
            self.small_paths.append(artifact)
            verified_hashes[str(artifact.absolute())] = expected
        declared_files, declared_links = build.get("files_sha256", {}), build.get("symlinks", {})
        if not isinstance(declared_files, dict) or not isinstance(declared_links, dict):
            raise ValueError("BUILD files_sha256 and symlinks must be mappings")
        for name, expected in declared_files.items():
            artifact = self._package_path(name)
            if not valid_sha(expected) or not artifact.is_file() or sha256(artifact) != expected:
                raise ValueError(f"native package checksum mismatch: {name}")
            self.small_paths.append(artifact)
            verified_hashes[str(artifact.absolute())] = expected
        for name, target in declared_links.items():
            artifact = self._package_path(name)
            if (not isinstance(target, str) or not artifact.is_symlink()
                    or str(artifact.readlink()) != target or not artifact.is_file()
                    or not artifact.resolve().is_relative_to(self.package_dir.resolve())):
                raise ValueError(f"native package symlink mismatch: {name}")
            self.small_paths.append(artifact)
        self.extra_roles = {}
        if extra_manifest is not None:
            extra_manifest = Path(extra_manifest).resolve()
            verified_hashes[str(extra_manifest)] = sha256(extra_manifest)
            entries = read_json(extra_manifest.read_text())
            entries = entries.get("artifacts") if isinstance(entries, dict) else entries
            if not isinstance(entries, list):
                raise ValueError("artifact manifest must be a list or an object with an artifacts list")
            self.small_paths.append(extra_manifest)
            for entry in entries:
                if (not isinstance(entry, dict) or not isinstance(entry.get("role"), str)
                        or not isinstance(entry.get("path"), str) or not valid_sha(entry.get("sha256"))):
                    raise ValueError("each artifact needs role, path and sha256")
                path = Path(entry["path"]).expanduser()
                path = (extra_manifest.parent / path).absolute() if not path.is_absolute() else path
                self.extra_roles[str(path)] = entry["role"]
                if entry["role"] in {"model", "model_weights", "weights"}:
                    self._verify_large(path, entry["role"], entry["sha256"], entry.get("bytes"))
                else:
                    if sha256(path) != entry["sha256"]:
                        raise ValueError(f"artifact checksum mismatch: {path.name}")
                    self.small_paths.append(path)
                    verified_hashes[str(path.absolute())] = entry["sha256"]
        self.small_paths = list(dict.fromkeys(p.absolute() for p in self.small_paths))
        self.small_hashes = file_hashes(self.small_paths)
        self.small_identities = {str(p): file_identity(p) for p in self.small_paths}
        if (self._inventory() != self.inventory
                or any(self.small_hashes.get(path) != digest for path, digest in initial_hashes.items())
                or any(self.small_hashes.get(path) != digest for path, digest in verified_hashes.items())):
            raise RuntimeError("native artifacts changed during initial verification")
        self.document = {"model_manifest": str(manifest), "model_manifest_metadata": meta,
                         "native_build": build, "large_artifacts": self.large,
                         "small_artifact_sha256": self.small_hashes,
                         "extra_artifact_roles": self.extra_roles,
                         "verification_seconds": time.perf_counter()-started,
                         "large_file_check_policy": "Full SHA256 once before loading; file size, inode, mtime, ctime and resolved path at each checkpoint. No periodic full rehash.",
                         "library_inventory": [str(p) for p in sorted(self.inventory)]}

    def _inventory(self):
        return tuple(sorted(p.absolute() for p in self.bin_dir.rglob("*")
                            if p.is_file() and p.suffix in {".dylib", ".metallib", ".metal"}))

    def _package_path(self, name):
        if not isinstance(name, str) or not name or Path(name).is_absolute() or ".." in Path(name).parts:
            raise ValueError("native package paths must stay inside the package")
        return self.package_dir / name

    def _verify_large(self, path, role, expected_sha, expected_bytes):
        key = str(path.absolute())
        if key in self.large:
            previous = self.large[key]
            if previous["sha256"] != expected_sha or (expected_bytes is not None and previous["identity"]["bytes"] != expected_bytes):
                raise ValueError("conflicting weight artifact declarations")
            return
        before = file_identity(path)
        if expected_bytes is not None and before["bytes"] != expected_bytes:
            raise ValueError(f"weight artifact size mismatch: {path.name}")
        digest = sha256(path)
        after = file_identity(path)
        if before != after or digest != expected_sha:
            raise ValueError(f"weight artifact changed or checksum mismatch: {path.name}")
        self.large[key] = {"role": role, "sha256": digest, "identity": after}

    def bind_engine(self, engine):
        if (engine.model_id != self.model_meta["repo_id"] or engine.model_revision != self.model_meta["revision"]
                or str(engine.dtype) != self.model_meta["quantization"]
                or Path(engine.model_file).resolve() != self.model_file.resolve()
                or Path(engine.native_binary).resolve() != self.binary.resolve()):
            raise ValueError("loaded engine identity does not match verified native artifacts")

    def check(self):
        for path, info in self.large.items():
            if file_identity(Path(path)) != info["identity"]:
                raise RuntimeError(f"frozen weight file changed: {Path(path).name}")
        if self._inventory() != self.inventory:
            raise RuntimeError("native library inventory changed after freeze")
        for path, expected in self.small_identities.items():
            if file_identity(Path(path)) != expected:
                raise RuntimeError(f"native artifact changed: {Path(path).name}")
        if file_hashes(self.small_paths) != self.small_hashes:
            raise RuntimeError("native artifact bytes changed after verification")


def hardware():
    info = {"platform": platform.platform(), "machine": platform.machine(),
            "processor": platform.processor(), "python": platform.python_version()}
    if platform.system() == "Darwin":
        for key in ("machdep.cpu.brand_string", "hw.memsize"):
            try:
                info[key] = subprocess.check_output(["sysctl", "-n", key], text=True).strip()
            except (OSError, subprocess.CalledProcessError):
                pass
    info["runtime"] = "Python standard library + native llama.cpp/Metal helper"
    return info


def runtime_identity(engine):
    return {"model": engine.model_id, "model_revision": engine.model_revision,
            "runtime_fingerprint": engine.runtime_fingerprint,
            "dtype": str(engine.dtype), "device": str(engine.device),
            "prompt_style": engine.prompt_style, "attention": engine.attention,
            "max_input_tokens": engine.max_input_tokens,
            "model_file": str(engine.model_file), "native_binary": str(engine.native_binary),
            "threads": getattr(engine, "threads", None),
            "temperature": engine.temperature,
            "temperature_calibration_applied": engine.temperature_calibration_applied}


class FreezeGuard:
    def __init__(self, paths, engine, kwargs, out, mode, extra=None):
        self.artifacts = getattr(engine, "_acceptance_artifacts", None)
        if self.artifacts is not None:
            self.artifacts.check()
            paths = list(dict.fromkeys(paths + self.artifacts.small_paths))
        self.paths = paths
        self.hashes = file_hashes(self.paths)
        self.engine = engine
        self.identity = runtime_identity(engine)
        self.document = {"frozen_at": utcnow(), "mode": mode, "seed": SEED,
                         "engine_kwargs": kwargs, "runtime": self.identity,
                         "sha256": self.hashes, "hardware": hardware(),
                         "temperature_grid": GRID if mode == "calibrate" else None,
                         "candidate_order_test": "reverse input mapping, actual forward; runtime may canonicalize keys",
                         "latency_token_limit": LATENCY_TOKEN_LIMIT, **(extra or {})}
        self.document["native_artifacts"] = self.artifacts.document if self.artifacts else None
        self.document["decode_count_semantics"] = "llama_decode_API_calls"
        self.freeze_path = out / "freeze.json"
        write_json_new(self.freeze_path, self.document)
        self.freeze_hash = sha256(self.freeze_path)

    def check(self):
        if self.artifacts is not None:
            self.artifacts.check()
        if sha256(self.freeze_path) != self.freeze_hash:
            raise RuntimeError("freeze.json changed after its exclusive creation")
        now = file_hashes(self.paths)
        changed = [path for path, digest in self.hashes.items() if now.get(path) != digest]
        if changed:
            raise RuntimeError("frozen files changed during run: " + ", ".join(Path(p).name for p in changed))
        if runtime_identity(self.engine) != self.identity:
            raise RuntimeError("engine configuration changed after freeze")


class ForwardCounter:
    def __init__(self, engine):
        self.engine = engine
        if type(engine.total_decode_count) is not int or engine.total_decode_count != 0:
            raise ValueError("new native helper must begin with total_decode_count=0")

    @property
    def count(self):
        value = self.engine.total_decode_count
        if type(value) is not int or value < 0:
            raise RuntimeError("invalid native total_decode_count")
        return value

    def close(self):
        self.engine.close()


def actual_forward(engine, counter, payload):
    before = counter.count
    engine.synchronize()
    started = time.perf_counter()
    result = engine.decide(payload)
    engine.synchronize()
    wall_ms = (time.perf_counter() - started) * 1000
    if counter.count - before != 1:
        raise RuntimeError(f"request executed {counter.count-before} llama_decode API calls; expected exactly 1")
    if not isinstance(result, dict) or result.get("batch_size") != 1:
        raise RuntimeError("result was not a single-question forward")
    if (type(result.get("native_decode_count")) is not int or result["native_decode_count"] != 1
            or type(result.get("native_total_decode_count")) is not int
            or result["native_total_decode_count"] != counter.count):
        raise RuntimeError("native result counters do not match the engine total")
    return result, wall_ms


def warmup(engine, counter):
    # Public synthetic warmup only; no held-out question supplies a warmup example.
    durations = []
    for count in range(2, 9):
        q = {"type": "choice", "state": "対象の番号は1です。", "instructions": "対象の番号を選ぶ。",
             "criteria": {f"k{i}": f"番号{i}" for i in range(1, count + 1)}}
        _, elapsed = actual_forward(engine, counter, q)
        durations.append(elapsed)
    return {"count": len(durations), "latency_ms": durations}


def softmax(logits, temperature=1.0):
    scaled = [x / temperature for x in logits]
    peak = max(scaled)
    exp = [math.exp(x - peak) for x in scaled]
    total = sum(exp)
    return [x / total for x in exp]


def validate_answer(case, answer):
    errors = []
    if not isinstance(answer, dict):
        return ["answer is not an object"]
    kind = case["type"]
    keys = candidate_keys(case)
    if answer.get("type") != kind:
        errors.append("type mismatch")
    label = answer.get("label")
    if not isinstance(label, str) or label not in keys:
        errors.append("label outside candidates")
    probs = answer.get("probabilities")
    probs_valid = isinstance(probs, dict) and set(probs) == set(keys)
    if not probs_valid:
        errors.append("probability keys mismatch")
    else:
        if not all(numeric(p) and 0 <= p <= 1 for p in probs.values()):
            errors.append("probabilities must be finite numbers in [0,1]")
            probs_valid = False
        elif abs(sum(probs.values()) - 1) > 1e-5:
            errors.append("probabilities do not sum to one")
            probs_valid = False
        if probs_valid and label in probs and probs[label] < max(probs.values()) - 1e-7:
            errors.append("label does not maximize probability")
    if kind == "choice" and answer.get("choice") != label:
        errors.append("choice field does not match label")
    if kind == "noul":
        value = answer.get("noul")
        if not numeric(value) or not 0 <= value <= 1:
            errors.append("invalid noul scalar")
        elif probs_valid and abs(value - probs["true"]) > 1e-6:
            errors.append("noul scalar does not equal P(true)")
    if kind == "score":
        value = answer.get("score")
        if not numeric(value) or not 0 <= value <= len(keys)-1:
            errors.append("invalid score scalar")
        elif probs_valid and abs(value - sum(int(k)*probs[k] for k in keys)) > 1e-5:
            errors.append("score does not equal probability-weighted stage")
    logits, ordered_keys = answer.get("candidate_logits"), answer.get("candidate_keys")
    if not isinstance(ordered_keys, list) or len(ordered_keys) != len(keys) or set(ordered_keys) != set(keys):
        errors.append("candidate_keys mismatch")
    if not isinstance(logits, list) or len(logits) != len(keys) or not all(numeric(x) for x in logits):
        errors.append("candidate logits invalid")
    if not isinstance(answer.get("input_tokens"), int) or isinstance(answer.get("input_tokens"), bool) or answer["input_tokens"] < 1:
        errors.append("invalid input_tokens")
    if answer.get("output_tokens") != 0:
        errors.append("inference generated output tokens")
    if answer.get("batch_size") != 1:
        errors.append("batch_size is not one")
    for key in ("latency_ms", "model_ms"):
        if not numeric(answer.get(key)) or answer[key] < 0:
            errors.append(f"invalid {key}")
    if "confidence" in answer and (not numeric(answer["confidence"]) or not 0 <= answer["confidence"] <= 1):
        errors.append("confidence outside [0,1]")
    return errors


def percentile(values, q):
    if not values:
        return None
    ordered = sorted(values)
    p = (len(ordered)-1)*q
    lo = int(math.floor(p))
    hi = int(math.ceil(p))
    return ordered[lo] + (ordered[hi]-ordered[lo])*(p-lo)


def distribution(values):
    return {"count": len(values), "p50_ms": percentile(values, .5),
            "p95_ms": percentile(values, .95), "max_ms": max(values) if values else None}


def calibration_metrics(rows, temperature=None):
    nll, brier, confidence_correct, score_mae, norm_score_mae = [], [], [], [], []
    for row in rows:
        if not row.get("valid"):
            continue
        answer = row["answer"]
        keys = answer["candidate_keys"]
        probs = answer["probabilities"] if temperature is None else dict(zip(keys, softmax(answer["candidate_logits"], temperature)))
        gold = row["gold"]
        pred = max(keys, key=lambda key: probs[key])
        nll.append(-math.log(max(probs[gold], 1e-300)))
        brier.append(sum((probs[k] - float(k == gold)) ** 2 for k in keys))
        confidence_correct.append((max(probs.values()), pred == gold))
        if row["type"] == "score":
            err = abs(sum(int(k)*probs[k] for k in keys) - int(gold))
            score_mae.append(err)
            norm_score_mae.append(err/(len(keys)-1))
    bins = []
    n = len(confidence_correct)
    ece = 0.0
    for i in range(10):
        subset = [(p, ok) for p, ok in confidence_correct if min(9, int(p*10)) == i]
        item = {"lower": i/10, "upper": (i+1)/10, "count": len(subset)}
        if subset:
            item.update(mean_confidence=statistics.mean(x[0] for x in subset), accuracy=statistics.mean(x[1] for x in subset))
            ece += len(subset)/n*abs(item["mean_confidence"]-item["accuracy"])
        bins.append(item)
    return {"valid_metric_count": n, "nll": statistics.mean(nll) if nll else None,
            "brier_multiclass_sum": statistics.mean(brier) if brier else None,
            "ece_10_equal_width": ece if n else None, "reliability_bins": bins,
            "score_count": len(score_mae), "score_expectation_mae": statistics.mean(score_mae) if score_mae else None,
            "score_normalized_expectation_mae": statistics.mean(norm_score_mae) if norm_score_mae else None}


def accuracy(rows):
    return {"count": len(rows), "correct": sum(x["correct"] for x in rows),
            "accuracy": sum(x["correct"] for x in rows)/len(rows) if rows else None,
            "valid": sum(x["valid"] for x in rows)}


def summarize(rows, freeze, warmup_info, forwards):
    by_type = {kind: accuracy([x for x in rows if x["type"] == kind]) for kind in TYPES}
    manual = [x for x in rows if x["source"] == "manual"]
    manual_types = {kind: accuracy([x for x in manual if x["type"] == kind]) for kind in TYPES}
    by_source = {s: accuracy([x for x in rows if x["source"] == s]) for s in sorted({x["source"] for x in rows})}
    families = sorted({f'{x["source"]}:{x["family"]}' for x in rows})
    by_family = {family: accuracy([x for x in rows if f'{x["source"]}:{x["family"]}' == family]) for family in families}
    reversed_rows = [x for x in rows if x["type"] == "choice"]
    reverse_valid = sum(x.get("reverse", {}).get("valid", False) for x in reversed_rows)
    consistent = sum(x.get("reverse", {}).get("same_label", False) for x in reversed_rows)
    reverse_correct = sum(x.get("reverse", {}).get("correct", False) for x in reversed_rows)
    eligible = [x for x in rows if numeric(x.get("input_tokens")) and x["input_tokens"] <= LATENCY_TOKEN_LIMIT and numeric(x.get("wall_ms"))]
    over = [x for x in rows if numeric(x.get("input_tokens")) and x["input_tokens"] > LATENCY_TOKEN_LIMIT and numeric(x.get("wall_ms"))]
    latency = {"input_tokens_le_512": distribution([x["wall_ms"] for x in eligible]),
               "input_tokens_gt_512": distribution([x["wall_ms"] for x in over]),
               "unmeasured_or_failed": len(rows)-len(eligible)-len(over),
               "reverse_choice": distribution([x["reverse"]["wall_ms"] for x in reversed_rows if numeric(x.get("reverse", {}).get("wall_ms"))])}
    brand = freeze["hardware"].get("machdep.cpu.brand_string", "")
    memory_bytes = freeze["hardware"].get("hw.memsize")
    hardware_target = ("Apple M5 Pro" in brand and freeze["runtime"]["device"] == "metal"
                       and str(memory_bytes) == str(64 * 1024**3))
    p95 = latency["input_tokens_le_512"]["p95_ms"]
    all_valid = all(x["valid"] for x in rows) and reverse_valid == len(reversed_rows)
    criteria = {"counts_2400_800_each": len(rows) == 2400 and all(by_type[k]["count"] == 800 for k in TYPES),
                "overall_accuracy_ge_90pct": accuracy(rows)["accuracy"] >= .9,
                "each_type_accuracy_ge_85pct": all(by_type[k]["accuracy"] >= .85 for k in TYPES),
                "manual_180_accuracy_ge_90pct": len(manual) == 180 and accuracy(manual)["accuracy"] >= .9,
                "manual_each_type_accuracy_ge_85pct": all(manual_types[k]["count"] == 60 and manual_types[k]["accuracy"] >= .85 for k in TYPES),
                "choice_order_semantic_consistency_ge_90pct": len(reversed_rows) == 800 and consistent/len(reversed_rows) >= .9,
                "all_answers_type_valid": all_valid,
                "latency_le_512_p95_le_500ms": p95 is not None and p95 <= 500,
                "target_hardware_m5_pro_64gb_metal": hardware_target,
                "every_measured_call_executed_one_llama_decode": forwards == len(rows)+len(reversed_rows)+warmup_info["count"]}
    return {"completed_at": utcnow(), "all_evaluation_criteria_passed": all(criteria.values()),
            "criteria": criteria, "overall": accuracy(rows), "by_type": by_type,
            "manual": accuracy(manual), "manual_by_type": manual_types, "by_source": by_source,
            "by_family": by_family, "family_macro_accuracy": statistics.mean(x["accuracy"] for x in by_family.values()),
            "generated_family_macro_accuracy": statistics.mean(x["accuracy"] for k, x in by_family.items() if k.startswith("generated:")),
            "candidate_order": {"count": len(reversed_rows), "same_semantic_label": consistent,
                                "consistency": consistent/len(reversed_rows) if reversed_rows else None,
                                "correct_after_reverse": reverse_correct,
                                "accuracy_after_reverse": reverse_correct/len(reversed_rows) if reversed_rows else None,
                                "valid_after_reverse": reverse_valid,
                                "method": "reverse Choice input map; runtime canonicalizes keys before prompt; independent real forward"},
            "probability_metrics_calibrated": calibration_metrics(rows),
            "probability_metrics_uncalibrated": calibration_metrics(rows, 1.0),
            "latency": latency, "warmup": warmup_info, "actual_llama_decode_calls": forwards,
            "decode_count_semantics": "llama_decode_API_calls",
            "scope": "This is a limited hand-authored/template-generated acceptance suite, not a general capability guarantee.",
            "completion_note": "Only evaluation criteria are covered here. API, restart, SDK, numerical equivalence, documentation and operational checks require separate verification."}


def setup_engine(args, paths, expected_hashes=None):
    # Hash before loading: detect an edit that races with model initialization.
    initial_hashes = expected_hashes if expected_hashes is not None else file_hashes(paths)
    if file_hashes(paths) != initial_hashes:
        raise RuntimeError("frozen inputs changed while loading cases")
    kwargs = load_config(args.config)
    artifacts = NativeArtifacts(kwargs, getattr(args, "artifact_manifest", None))
    if args.command == "evaluate":
        kwargs["temperature_config"] = str(args.temperature_config.resolve())
    sys.path.insert(0, str(ROOT))
    from native_engine import NativeEngine
    started = time.perf_counter()
    engine = NativeEngine(**kwargs)
    engine._acceptance_artifacts = artifacts
    load_seconds = time.perf_counter() - started
    try:
        artifacts.bind_engine(engine)
        artifacts.check()
        if file_hashes(paths) != initial_hashes:
            raise RuntimeError("frozen inputs changed while loading the model")
        if not engine.model_revision:
            raise ValueError("acceptance requires a resolved immutable model revision")
    except Exception:
        engine.close()
        raise
    return engine, kwargs, load_seconds


def progress(index, total, rows, started):
    done = {"event": "progress", "completed": index, "total": total,
            "elapsed_seconds": round(time.perf_counter()-started, 1),
            "correct": sum(x["correct"] for x in rows), "valid": sum(x["valid"] for x in rows)}
    print(json.dumps(done), flush=True)


def run_calibrate(args):
    paths = source_paths() + [args.config, args.calibration]
    initial_hashes = file_hashes(paths)
    cases = load_cases(args.calibration, "calibration", 40)
    engine, kwargs, load_seconds = setup_engine(args, paths, initial_hashes)
    try:
        guard = FreezeGuard(paths, engine, kwargs, args.output_dir, "calibrate",
                            {"calibration_cases": len(cases), "model_load_seconds": load_seconds})
        counter = ForwardCounter(engine)
        rows = []
        warmup_info = warmup(engine, counter)
        guard.check()
        random.Random(SEED).shuffle(cases)
        started = time.perf_counter()
        with (args.output_dir / "calibration_predictions.jsonl").open("x") as f:
            for i, case in enumerate(cases, 1):
                answer, wall_ms = actual_forward(engine, counter, question(case))
                errors = validate_answer(case, answer)
                row = {"id": case["id"], "type": case["type"], "source": "calibration",
                       "family": case["family"], "gold": case["label"], "answer": answer,
                       "wall_ms": wall_ms, "valid": not errors, "validation_errors": errors,
                       "correct": not errors and answer["label"] == case["label"]}
                f.write(json.dumps(row, ensure_ascii=False, allow_nan=False)+"\n")
                f.flush()
                rows.append(row)
                if errors:
                    raise RuntimeError(f"calibration answer {i} failed typed validation")
                if i % 100 == 0 or i == len(cases):
                    guard.check()
                    progress(i, len(cases), rows, started)
        losses = []
        for temperature in GRID:
            nll = []
            for row in rows:
                answer = row["answer"]
                probs = softmax(answer["candidate_logits"], temperature)
                nll.append(-math.log(max(probs[answer["candidate_keys"].index(row["gold"])], 1e-300)))
            losses.append((statistics.mean(nll), abs(math.log(temperature)), temperature))
        best_nll, _, temperature = min(losses)
        calibrated_rows = []
        for row in rows:
            copied = dict(row)
            answer = dict(row["answer"])
            answer["probabilities"] = dict(zip(answer["candidate_keys"], softmax(answer["candidate_logits"], temperature)))
            copied["answer"] = answer
            calibrated_rows.append(copied)
        guard.check()
        result = {"temperature": temperature, "runtime_fingerprint": engine.runtime_fingerprint,
                  "model": engine.model_id, "model_revision": engine.model_revision,
                  "created_at": utcnow(), "method": "single positive temperature minimizing multiclass NLL",
                  "calibration_count": len(rows), "calibration_sha256": sha256(args.calibration),
                  "grid": {"min": .1, "max": 10., "count": len(GRID), "spacing": "logarithmic"},
                  "nll_before": calibration_metrics(rows, 1.0)["nll"], "nll_after": best_nll,
                  "metrics_before": calibration_metrics(rows, 1.0), "metrics_after": calibration_metrics(calibrated_rows),
                  "actual_llama_decode_calls": counter.count, "decode_count_semantics": "llama_decode_API_calls", "warmup": warmup_info,
                  "generalization_validated": False, "freeze_sha256": sha256(args.output_dir / "freeze.json")}
        write_json_new(args.output_dir / "temperature.json", result)
        write_json_new(args.output_dir / "summary.json", result)
        print(json.dumps({"event": "calibration_complete", "count": len(rows), "temperature": temperature,
                          "nll_before": result["nll_before"], "nll_after": best_nll}), flush=True)
    finally:
        engine.close()


def run_evaluate(args):
    paths = source_paths() + [args.config, args.temperature_config, args.manual, args.generated]
    initial_hashes = file_hashes(paths)
    cases = load_cases(args.manual, "manual", 60) + load_cases(args.generated, "generated", 740)
    if len({x["id"] for x in cases}) != 2400:
        raise ValueError("test IDs must be unique across all 2400 cases")
    serialized = [json.dumps(question(x), ensure_ascii=False, sort_keys=True) for x in cases]
    if len(set(serialized)) != 2400:
        raise ValueError("exact duplicate questions in combined acceptance suite")
    engine, kwargs, load_seconds = setup_engine(args, paths, initial_hashes)
    try:
        guard = FreezeGuard(paths, engine, kwargs, args.output_dir, "evaluate",
                            {"test_cases": len(cases), "counts": {kind: 800 for kind in TYPES},
                             "model_load_seconds": load_seconds})
        counter = ForwardCounter(engine)
        rows = []
        warmup_info = warmup(engine, counter)
        guard.check()
        random.Random(SEED).shuffle(cases)
        started = time.perf_counter()
        with (args.output_dir / "predictions.jsonl").open("x", encoding="utf-8") as f:
            for i, case in enumerate(cases, 1):
                row = {"id": case["id"], "type": case["type"], "source": case["source"],
                       "family": case["family"], "gold": case["label"], "valid": False, "correct": False}
                try:
                    answer, wall_ms = actual_forward(engine, counter, question(case))
                    errors = validate_answer(case, answer)
                    row.update(answer=answer, wall_ms=wall_ms, input_tokens=answer.get("input_tokens"),
                               valid=not errors, validation_errors=errors,
                               correct=not errors and answer["label"] == case["label"])
                except Exception as exc:
                    row["error"] = f"{type(exc).__name__}: {exc}"
                if case["type"] == "choice":
                    reversed_q = question(case)
                    reversed_q["criteria"] = dict(reversed(list(case["criteria"].items())))
                    reverse = {"valid": False, "correct": False, "same_label": False}
                    try:
                        answer, wall_ms = actual_forward(engine, counter, reversed_q)
                        errors = validate_answer(case, answer)
                        reverse.update(answer=answer, wall_ms=wall_ms, valid=not errors, validation_errors=errors,
                                       correct=not errors and answer["label"] == case["label"],
                                       same_label=not errors and row["valid"] and answer["label"] == row["answer"]["label"])
                    except Exception as exc:
                        reverse["error"] = f"{type(exc).__name__}: {exc}"
                    row["reverse"] = reverse
                f.write(json.dumps(row, ensure_ascii=False, allow_nan=False)+"\n")
                f.flush()
                rows.append(row)
                if i % 100 == 0 or i == len(cases):
                    guard.check()
                    progress(i, len(cases), rows, started)
        guard.check()
        result = summarize(rows, guard.document, warmup_info, counter.count)
        result["freeze_sha256"] = sha256(args.output_dir / "freeze.json")
        result["predictions_sha256"] = sha256(args.output_dir / "predictions.jsonl")
        write_json_new(args.output_dir / "summary.json", result)
        print(json.dumps({"event": "evaluation_complete", "passed": result["all_evaluation_criteria_passed"],
                          "overall": result["overall"], "by_type": result["by_type"],
                          "manual": result["manual"], "criteria": result["criteria"],
                          "latency": result["latency"]}), flush=True)
        return result["all_evaluation_criteria_passed"]
    finally:
        engine.close()


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for command in ("calibrate", "evaluate"):
        p = sub.add_parser(command)
        p.add_argument("--config", type=Path, required=True)
        p.add_argument("--output-dir", type=Path, required=True, help="Must not already exist")
        p.add_argument("--artifact-manifest", type=Path, help="Optional extra role/path/sha256 artifact list; packaged model and native artifacts are always frozen")
        if command == "calibrate":
            p.add_argument("--calibration", type=Path, default=PRIVATE / "calibration.jsonl")
        else:
            p.add_argument("--temperature-config", type=Path, required=True)
            p.add_argument("--manual", type=Path, default=PRIVATE / "acceptance_test.jsonl")
            p.add_argument("--generated", type=Path, default=PRIVATE / "generated_2220.jsonl")
    return parser


def main():
    args = build_parser().parse_args()
    # Refuse an existing directory before writing anything, including a failure log.
    try:
        args.output_dir.mkdir(parents=True, exist_ok=False)
    except FileExistsError:
        print("ERROR: --output-dir already exists; choose a new directory", file=sys.stderr)
        return 2
    try:
        if args.command == "calibrate":
            run_calibrate(args)
            return 0
        return 0 if run_evaluate(args) else 1
    except Exception as exc:
        failure = {"failed_at": utcnow(), "command": args.command, "error_type": type(exc).__name__,
                   "message": str(exc), "traceback": traceback.format_exc(),
                   "note": "Run was not completed. Partial predictions and any freeze file are preserved."}
        write_json_new(args.output_dir / "failure.json", failure)
        print(json.dumps({"event": "run_failed", "error_type": type(exc).__name__, "message": str(exc)}), file=sys.stderr, flush=True)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
