"""Auditable user-data experiment: validate, train, and reload/evaluate.

Validation is standard-library-only and precedes model loading/downloads.
The frozen Qwen2/Qwen2.5 backbone emits features; only a CPU residual head
or candidate-position bias is learned. No compatibility with native GGUF
weights or the native 35B release is implied.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import importlib.metadata
import json
import math
import platform
import random
import re
import subprocess
import sys
import time
import unicodedata
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCHEMA_VERSION = 1
SPLITS = ("train", "dev", "calibration", "test")


def sha_file(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def digest(value, *, sort_keys=True):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=sort_keys,
                                    separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def strict_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def parse_json(text):
    def invalid(value):
        raise ValueError(f"non-finite JSON number: {value}")
    return json.loads(text, object_pairs_hook=strict_pairs, parse_constant=invalid)


def write_json(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def text_value(value, name):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a nonempty string")
    value.encode("utf-8", errors="strict")


def check_json_value(value, depth=0):
    if depth > 32:
        raise ValueError("JSON nesting exceeds 32")
    if isinstance(value, str):
        value.encode("utf-8", errors="strict")
    elif value is None or isinstance(value, bool):
        pass
    elif isinstance(value, (int, float)):
        if not math.isfinite(value):
            raise ValueError("state numbers must be finite")
    elif isinstance(value, list):
        for child in value:
            check_json_value(child, depth + 1)
    elif isinstance(value, dict):
        for key, child in value.items():
            text_value(key, "state object key")
            check_json_value(child, depth + 1)
    else:
        raise ValueError("state must be a JSON value")


def case_keys(case):
    if case["type"] == "noul":
        return ["false", "true"]
    if case["type"] == "score":
        return [str(i) for i in range(len(case["criteria"]))]
    return list(case["criteria"])


def label_key(case):
    value = case["label"]
    return str(value).lower() if isinstance(value, bool) else str(value)


def validate_case(case, max_candidates=26):
    if not isinstance(case, dict):
        raise ValueError("each line must be an object")
    required = {"id", "type", "state", "instructions", "criteria", "label"}
    if not required <= set(case):
        raise ValueError(f"missing fields: {sorted(required - set(case))}")
    if set(case) - required - {"group", "family"}:
        raise ValueError(f"unknown fields: {sorted(set(case) - required - {'group', 'family'})}")
    for key in ("id", "instructions"):
        text_value(case[key], key)
    for key in ("group", "family"):
        if key in case:
            text_value(case[key], key)
    check_json_value(case["state"])
    kind, criteria, label = case["type"], case["criteria"], case["label"]
    if kind == "choice":
        if not isinstance(criteria, dict) or not isinstance(label, str):
            raise ValueError("choice requires an object of options and a string label key")
        for key in criteria:
            text_value(key, "choice key")
        values = list(criteria.values())
    elif kind == "noul":
        if not isinstance(criteria, dict) or set(criteria) != {"false", "true"}:
            raise ValueError("noul criteria must contain exactly false and true")
        if not (isinstance(label, bool) or isinstance(label, str) and label in ("false", "true")):
            raise ValueError("noul label must be a boolean or false/true string")
        values = list(criteria.values())
    elif kind == "score":
        if not isinstance(criteria, list) or type(label) is not int:
            raise ValueError("score criteria must be an ordered array and label an integer stage")
        values = criteria
    else:
        raise ValueError("type must be choice, noul, or score")
    if not 2 <= len(values) <= max_candidates:
        raise ValueError(f"candidate count must be 2..{max_candidates}")
    for description in values:
        text_value(description, "candidate description")
    if label_key(case) not in case_keys(case):
        raise ValueError("gold label is not an allowed candidate")
    # Catch normalization collisions before using canonical signatures.
    normalize_value({"state": case["state"], "criteria": criteria})
    return case


def normalize_text(value):
    return " ".join(unicodedata.normalize("NFKC", value).split())


def normalize_value(value):
    if isinstance(value, str):
        return normalize_text(value)
    if isinstance(value, list):
        return [normalize_value(child) for child in value]
    if isinstance(value, dict):
        result = {}
        for key, child in value.items():
            key = normalize_text(key)
            if key in result:
                raise ValueError("object keys collide after Unicode/whitespace normalization")
            result[key] = normalize_value(child)
        return result
    # Match 1 and 1.0, but preserve booleans.
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value


def input_signature(case):
    # Order-independent Choice mappings; Score order stays meaningful.
    value = {key: case[key] for key in ("type", "state", "instructions", "criteria")}
    state = case["state"]
    # The model sees serialized JSON for structured state. A string containing
    # that serialization is not an independent input. Also keep object-key
    # order independent and normalize structured-string aliases consistently.
    if isinstance(state, str):
        try:
            parsed = parse_json(state)
            check_json_value(parsed)
            state = parsed
        except (ValueError, TypeError, UnicodeError, RecursionError, OverflowError):
            value["state"] = {"text": normalize_text(state)}
            return digest(normalize_value(value))
    value["state"] = {"json": normalize_value(state)}
    return digest(normalize_value(value))


def load_cases(path, max_candidates=26):
    rows = []
    with Path(path).open("r", encoding="utf-8-sig") as stream:
        for line_no, line in enumerate(stream, 1):
            if not line.strip():
                continue
            try:
                if len(line.encode("utf-8")) > 1024 * 1024:
                    raise ValueError("a JSONL record exceeds 1 MiB")
                rows.append(validate_case(parse_json(line), max_candidates))
            except (ValueError, TypeError, UnicodeError, RecursionError, OverflowError) as error:
                raise ValueError(f"{path}:{line_no}: {error}") from error
    if not rows:
        raise ValueError(f"empty dataset: {path}")
    return rows


def group_fields(policy):
    return {"none": (), "group": ("group",), "family": ("family",),
            "both": ("group", "family")}[policy]


def audit_splits(groups, policy="none"):
    ids, inputs, tags = {}, {}, {}
    records = {}
    for split, cases in groups.items():
        split_records = []
        for case in cases:
            case_id = normalize_text(case["id"])
            signature = input_signature(case)
            if case_id in ids:
                raise ValueError(f"duplicate id {case['id']!r}: {ids[case_id]} and {split}")
            if signature in inputs:
                raise ValueError(f"duplicate normalized input: {inputs[signature]} and {split}/{case['id']}")
            ids[case_id] = split
            inputs[signature] = f"{split}/{case['id']}"
            record = {"id": case_id, "input_sha256": signature}
            for field in group_fields(policy):
                if field not in case:
                    raise ValueError(f"{split}/{case['id']} lacks required {field}")
                tag = normalize_text(case[field])
                key = (field, tag)
                if key in tags and tags[key] != split:
                    raise ValueError(f"{field} {tag!r} crosses {tags[key]} and {split}")
                tags[key] = split
                record[field] = tag
            split_records.append(record)
        records[split] = split_records
    return {"policy": policy, "records": records,
            "note": "Canonical input equality is not a semantic paraphrase detector. Use group/family separation and human audit."}


def load_splits(args):
    groups = {split: load_cases(getattr(args, split), args.max_candidates) for split in SPLITS}
    audit = audit_splits(groups, args.disjoint_groups)
    return groups, audit


def split_summary(groups, args):
    return {name: {"records": len(cases), "by_type": dict(Counter(c["type"] for c in cases)),
                   "file_sha256": sha_file(getattr(args, name)), "records_sha256": digest(cases, sort_keys=False)}
            for name, cases in groups.items()}


def new_output(path):
    path = Path(path)
    # A failed/interrupted run remains for audit; use a new destination to retry.
    path.mkdir(parents=True, exist_ok=False)
    return path


def source_hashes():
    return {name: sha_file(HERE / name) for name in
            ("training_cli.py", "mini_jev.py", "head_jev.py", "train_head.py")}


def runtime_provenance(engine, batch_size, max_candidates):
    import torch
    from head_jev import feature_fingerprint
    device_name = platform.processor() or platform.machine()
    if engine.device.type == "cuda":
        device_name = torch.cuda.get_device_name(engine.device)
    elif platform.system() == "Darwin":
        try:
            device_name = subprocess.run(["sysctl", "-n", "machdep.cpu.brand_string"],
                                         capture_output=True, text=True, check=True).stdout.strip()
        except (OSError, subprocess.CalledProcessError):
            pass
    return {"model": engine.model_id, "revision": engine.model.config._commit_hash,
            "device": str(engine.device), "device_name": device_name,
            "dtype": str(engine.dtype), "python": platform.python_version(), "platform": platform.platform(),
            "packages": {name: importlib.metadata.version(name) for name in
                         ("torch", "transformers", "tokenizers", "safetensors")},
            "torch_threads": torch.get_num_threads(), "torch_build": torch.__config__.show(),
            "mps_available": torch.backends.mps.is_available(), "cuda_version": torch.version.cuda,
            "deterministic_algorithms": torch.are_deterministic_algorithms_enabled(),
            "float32_matmul_precision": torch.get_float32_matmul_precision(),
            "cuda_matmul_allow_tf32": torch.backends.cuda.matmul.allow_tf32,
            "cudnn_allow_tf32": torch.backends.cudnn.allow_tf32,
            "cudnn_deterministic": torch.backends.cudnn.deterministic,
            "cudnn_benchmark": torch.backends.cudnn.benchmark,
            "attention_implementation": getattr(engine.model.config, "_attn_implementation", None),
            "max_input_tokens": engine.max_input_tokens, "max_candidates": max_candidates,
            "feature_batch_size": batch_size, "symbol_ids": engine.symbol_ids[:max_candidates],
            "tokenizer_vocab_sha256": digest(engine.tokenizer.get_vocab()),
            "chat_template_sha256": digest(engine.tokenizer.chat_template),
            "feature_fingerprint": feature_fingerprint(), "source_sha256": source_hashes()}


def validate_features(data, n, maximum):
    import torch
    if set(data) != {"x", "base", "target", "count"}:
        raise ValueError("invalid cached feature keys")
    if data["x"].ndim != 2 or data["x"].shape[0] != n or data["x"].shape[1] < 1:
        raise ValueError("invalid hidden feature shape")
    if tuple(data["base"].shape) != (n, maximum):
        raise ValueError("invalid baseline shape")
    for key in ("x", "base"):
        if data[key].dtype != torch.float32 or not torch.isfinite(data[key]).all():
            raise ValueError(f"invalid or non-finite {key}")
    for key in ("count", "target"):
        if tuple(data[key].shape) != (n,) or data[key].dtype != torch.int64:
            raise ValueError(f"invalid {key} shape/dtype")
    if not ((data["count"] >= 2) & (data["count"] <= maximum)).all():
        raise ValueError("invalid candidate counts")
    if not ((data["target"] >= 0) & (data["target"] < data["count"])).all():
        raise ValueError("invalid target indexes")


def extract_features(engine, cases, cache, batch_size, maximum, runtime):
    import torch
    from safetensors.torch import load_file, save_file
    from head_jev import normalize_hidden
    identity = {"schema": SCHEMA_VERSION, "cases_sha256": digest(cases, sort_keys=False), "runtime": runtime}
    fingerprint = digest(identity)
    cache = Path(cache)
    cache.mkdir(parents=True, exist_ok=True)
    path = cache / f"{fingerprint}.safetensors"
    metadata = cache / f"{fingerprint}.json"
    if path.exists() or metadata.exists():
        if not path.is_file() or not metadata.is_file():
            raise ValueError("incomplete feature cache; remove this cache pair or use a new cache directory")
        saved = parse_json(metadata.read_text())
        if saved.get("identity") != identity or saved.get("sha256") != sha_file(path):
            raise ValueError("feature cache fingerprint/content mismatch")
        data = load_file(str(path))
        validate_features(data, len(cases), maximum)
        return data, {"fingerprint": fingerprint, "cache_hit": True}
    xs, bases, targets, counts = [], [], [], []
    with torch.inference_mode():
        _, weight, bias = engine._head(maximum)
        for start in range(0, len(cases), batch_size):
            chunk = cases[start:start + batch_size]
            prepared = [engine._prepare(case) for case in chunk]
            inputs = engine._batch([ids for _, ids in prepared])
            hidden = engine.model.base_model(**inputs, use_cache=False, return_dict=True).last_hidden_state[:, -1, :]
            xs.append(normalize_hidden(hidden).cpu())
            bases.append(torch.nn.functional.linear(hidden, weight, bias).float().cpu())
            for case, (options, _) in zip(chunk, prepared):
                targets.append([key for key, _ in options].index(label_key(case)))
                counts.append(len(options))
            print(f"features: {min(start + batch_size, len(cases))}/{len(cases)}", flush=True)
    data = {"x": torch.cat(xs), "base": torch.cat(bases),
            "target": torch.tensor(targets), "count": torch.tensor(counts)}
    validate_features(data, len(cases), maximum)
    temporary = path.with_suffix(".tmp")
    save_file(data, str(temporary), metadata={"fingerprint": fingerprint})
    temporary.replace(path)
    write_json(metadata, {"identity": identity, "sha256": sha_file(path)})
    return data, {"fingerprint": fingerprint, "cache_hit": False}


def train_control(train, dev, dev_cases, mode, epochs, learning_rates, penalties):
    import torch
    from train_head import masked_logits, get_logits, metrics
    shape = (train["base"].shape[1], train["x"].shape[1])
    best, trials = None, []
    for lr in learning_rates:
        for penalty in penalties:
            weight = torch.nn.Parameter(torch.zeros(shape), requires_grad=mode == "residual")
            bias = torch.nn.Parameter(torch.zeros(shape[0]))
            parameters = [weight, bias] if mode == "residual" else [bias]
            optimizer = torch.optim.AdamW(parameters, lr=lr, weight_decay=0)
            history = []
            for epoch in range(epochs + 1):
                if epoch:
                    optimizer.zero_grad()
                    delta = torch.nn.functional.linear(train["x"], weight, bias)
                    valid = torch.arange(shape[0])[None, :] < train["count"][:, None]
                    loss = torch.nn.functional.cross_entropy(masked_logits(train["base"] + delta,
                                                                           train["count"]), train["target"])
                    loss = loss + penalty * delta[valid].square().mean()
                    loss.backward()
                    torch.nn.utils.clip_grad_norm_(parameters, 5.0)
                    optimizer.step()
                if epoch % 5 == 0 or epoch == epochs:
                    with torch.no_grad():
                        result = metrics(get_logits(dev, weight, bias), dev, dev_cases)
                    if not math.isfinite(result["nll"]):
                        raise ValueError("training produced a non-finite dev loss")
                    history.append({"epoch": epoch, "dev_nll": result["nll"]})
                    if best is None or result["nll"] < best["selection"]["dev_nll"]:
                        best = {"weight": weight.detach().clone(), "bias": bias.detach().clone(),
                                "selection": {"epoch": epoch, "learning_rate": lr, "penalty": penalty,
                                              "dev_nll": result["nll"]}}
            trials.append({"learning_rate": lr, "penalty": penalty, "history": history})
    return best, trials


def assess_controls(data, cases, controls, temperatures):
    from train_head import get_logits, metrics, case_outputs
    output = {}
    for name, control in controls.items():
        logits = get_logits(data, control["weight"], control["bias"])
        for suffix, temperature in (("", 1.0), ("_temperature", temperatures[name])):
            output[name + suffix] = {"temperature": temperature,
                                     "metrics": metrics(logits, data, cases, temperature),
                                     "cases": case_outputs(logits, data, cases, temperature)}
    return output


def load_checkpoint(path):
    import torch
    from safetensors.torch import load_file
    path = Path(path)
    config = parse_json((path / "config.json").read_text())
    if config.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("unsupported checkpoint schema")
    if config["source_sha256"] != source_hashes():
        raise ValueError("training/runtime code changed; use the source revision saved with this checkpoint")
    controls = {}
    for name in ("baseline", "bias", "residual"):
        filename = f"{name}.safetensors"
        if sha_file(path / filename) != config["weight_sha256"][filename]:
            raise ValueError("checkpoint weight SHA256 mismatch")
        tensors = load_file(str(path / filename))
        if set(tensors) != {"weight", "bias"}:
            raise ValueError("invalid checkpoint tensors")
        expected = (config["model_args"]["max_candidates"], config["hidden_size"])
        if tuple(tensors["weight"].shape) != expected or tuple(tensors["bias"].shape) != expected[:1]:
            raise ValueError("invalid checkpoint dimensions")
        if any(t.dtype != torch.float32 or not torch.isfinite(t).all() for t in tensors.values()):
            raise ValueError("invalid checkpoint values")
        temperature = config["temperatures"][name]
        if not isinstance(temperature, (int, float)) or not math.isfinite(temperature) or temperature <= 0:
            raise ValueError("invalid checkpoint temperature")
        controls[name] = tensors
    return config, controls


def make_engine(model_args, allow_download=False, device=None):
    from mini_jev import MiniJev
    engine = MiniJev(model=model_args["model"], revision=model_args["revision"],
                     device=device or model_args["device"], dtype=model_args["dtype"],
                     max_input_tokens=model_args["max_input_tokens"], local_files_only=not allow_download)
    if engine.model.config._commit_hash != model_args["revision"]:
        raise ValueError("loaded model revision does not match the pinned commit")
    engine.model.requires_grad_(False)
    if any(p.requires_grad for p in engine.model.parameters()):
        raise ValueError("backbone was not frozen")
    return engine


def train_command(args):
    # Validate ALL records and leakage before importing ML packages/model downloads.
    groups, audit = load_splits(args)
    output = new_output(args.output)
    write_json(output / "data_audit.json", {"splits": split_summary(groups, args), **audit})
    import torch
    from safetensors.torch import save_file
    from train_head import get_logits, fit_temperature
    random.seed(args.seed)
    torch.manual_seed(args.seed)
    torch.set_num_threads(args.threads)
    started = time.perf_counter()
    model_args = {key: getattr(args, key) for key in
                  ("model", "revision", "device", "dtype", "max_input_tokens", "max_candidates", "batch_size")}
    engine = make_engine(model_args, args.allow_download)
    runtime = runtime_provenance(engine, args.batch_size, args.max_candidates)
    model_args["device"] = str(engine.device)
    cache = args.cache or output / "feature-cache"
    features, extraction = {}, {}
    # Test labels were read solely for schema/leak validation; no test feature or
    # metric enters the following fit/selection/calibration functions.
    for split in ("train", "dev", "calibration"):
        features[split], extraction[split] = extract_features(engine, groups[split], cache, args.batch_size,
                                                             args.max_candidates, runtime)
    hidden = features["train"]["x"].shape[1]
    controls = {"baseline": {"weight": torch.zeros(args.max_candidates, hidden),
                             "bias": torch.zeros(args.max_candidates)}}
    trials, selections = {}, {}
    for name in ("bias", "residual"):
        best, trials[name] = train_control(features["train"], features["dev"], groups["dev"], name,
                                          args.epochs, args.learning_rates, args.penalties)
        selections[name] = best.pop("selection")
        controls[name] = best
    temperatures, calibration = {}, {}
    for name, control in controls.items():
        temperatures[name], calibration[name] = fit_temperature(
            get_logits(features["calibration"], control["weight"], control["bias"]), features["calibration"])
    checkpoint = output / "checkpoint"
    checkpoint.mkdir()
    weight_hashes = {}
    for name, weights in controls.items():
        filename = f"{name}.safetensors"
        save_file(weights, str(checkpoint / filename))
        weight_hashes[filename] = sha_file(checkpoint / filename)
    config = {"schema_version": SCHEMA_VERSION, "model_args": model_args, "runtime": runtime,
              "source_sha256": source_hashes(), "hidden_size": hidden, "temperatures": temperatures,
              "weight_sha256": weight_hashes, "selections": selections, "seed": args.seed,
              "threads": args.threads, "backbone_frozen": True,
              "trainable_parameters": {"baseline": 0, "bias": args.max_candidates,
                                       "residual": args.max_candidates * (hidden + 1)},
              "optimizer": {"name": "AdamW", "epochs": args.epochs, "learning_rates": args.learning_rates,
                            "penalties": args.penalties, "full_batch": True, "zero_initialization": True},
              "split_audit": audit, "datasets": split_summary(groups, args),
              "probability_semantics": "conditional_on_allowed_label_tokens",
              "calibration_generalization_validated": False,
              "seed_note": "CPU full-batch zero-initialized head training has no randomized sampling; different seeds are not independent training trials.",
              "selection_policy": "dev NLL selects weights including epoch 0; calibration NLL selects temperature; test never selects either"}
    write_json(checkpoint / "config.json", config)
    config_hash = sha_file(checkpoint / "config.json")
    # Reload serialized weights, then evaluate. No mutable training objects survive.
    loaded_config, reloaded = load_checkpoint(checkpoint)
    for name in controls:
        for key in ("weight", "bias"):
            torch.testing.assert_close(controls[name][key], reloaded[name][key], rtol=0, atol=0)
    print("Checkpoint and temperatures frozen and reloaded. Evaluating held-out test now.", flush=True)
    features["test"], extraction["test"] = extract_features(engine, groups["test"], cache, args.batch_size,
                                                           args.max_candidates, runtime)
    evaluation = {split: assess_controls(features[split], groups[split], reloaded, loaded_config["temperatures"])
                  for split in ("dev", "calibration", "test")}
    if sha_file(checkpoint / "config.json") != config_hash or any(
            sha_file(checkpoint / name) != checksum for name, checksum in weight_hashes.items()):
        raise ValueError("checkpoint changed during evaluation")
    report = {"schema_version": SCHEMA_VERSION, "checkpoint_config_sha256": config_hash,
              "checkpoint_unchanged_after_test": True, "checkpoint_reload_exact": True,
              "calibration": calibration, "selection_trials": trials, "feature_extraction": extraction,
              "evaluation": evaluation, "elapsed_seconds": time.perf_counter() - started,
              "seed_note": config["seed_note"]}
    write_json(output / "report.json", report)
    print(json.dumps({"output": str(output), "test": {k: v["metrics"] for k, v in evaluation["test"].items()}}, indent=2))


def audit_evaluation(cases, config):
    policy = config["split_audit"]["policy"]
    new = audit_splits({"evaluation": cases}, policy)
    original = config["split_audit"]["records"]
    protected = [row for split in ("train", "dev", "calibration") for row in original[split]]
    forbidden_ids = {r["id"] for r in protected}
    forbidden_inputs = {r["input_sha256"] for r in protected}
    for row in new["records"]["evaluation"]:
        if row["id"] in forbidden_ids or row["input_sha256"] in forbidden_inputs:
            raise ValueError("evaluation overlaps train/dev/calibration")
        for field in group_fields(policy):
            if row[field] in {r[field] for r in protected}:
                raise ValueError(f"evaluation {field} overlaps train/dev/calibration")
    return new


def evaluate_command(args):
    # Read JSON metadata and validate evaluation before ML imports/model downloads.
    config_path = args.checkpoint / "config.json"
    raw = parse_json(config_path.read_text())
    cases = load_cases(args.test, raw["model_args"]["max_candidates"])
    audit = audit_evaluation(cases, raw)
    output = new_output(args.output)
    config, controls = load_checkpoint(args.checkpoint)
    import torch
    torch.set_num_threads(config["threads"])
    engine = make_engine(config["model_args"], args.allow_download, args.device)
    model_args = config["model_args"]
    runtime = runtime_provenance(engine, model_args["batch_size"], model_args["max_candidates"])
    same_runtime = runtime == config["runtime"]
    if not same_runtime and not args.allow_runtime_change:
        raise ValueError("runtime provenance differs from training; explicit --allow-runtime-change required (temperature portability is unvalidated)")
    features, extraction = extract_features(engine, cases, args.cache or output / "feature-cache",
                                             model_args["batch_size"], model_args["max_candidates"], runtime)
    report = {"schema_version": SCHEMA_VERSION, "checkpoint_config_sha256": sha_file(config_path),
              "test_file_sha256": sha_file(args.test), "runtime": runtime, "runtime_exact_match": same_runtime,
              "calibration_generalization_validated": False, "split_audit": audit,
              "feature_extraction": extraction,
              "evaluation": assess_controls(features, cases, controls, config["temperatures"])}
    write_json(output / "report.json", report)
    print(json.dumps({"output": str(output), "evaluation": {k: v["metrics"] for k, v in report["evaluation"].items()}}, indent=2))


def load_prediction_cases(path, maximum):
    value = parse_json(Path(path).read_text(encoding="utf-8-sig"))
    rows = value if isinstance(value, list) else [value]
    if not rows:
        raise ValueError("prediction input cannot be empty")
    cases = []
    for index, row in enumerate(rows):
        if not isinstance(row, dict) or set(row) != {"type", "state", "instructions", "criteria"}:
            raise ValueError("prediction questions require exactly type/state/instructions/criteria; no gold label")
        case = dict(row, id=f"prediction-{index}")
        # Targets are unused; extraction shares the same validated feature path.
        if row["type"] == "score":
            case["label"] = 0
        elif row["type"] == "noul":
            case["label"] = False
        elif isinstance(row["criteria"], dict) and row["criteria"]:
            case["label"] = next(iter(row["criteria"]))
        else:
            raise ValueError("invalid prediction criteria")
        cases.append(validate_case(case, maximum))
    return cases


def predict_command(args):
    raw = parse_json((args.checkpoint / "config.json").read_text())
    cases = load_prediction_cases(args.input, raw["model_args"]["max_candidates"])
    output = new_output(args.output)
    config, controls = load_checkpoint(args.checkpoint)
    import torch
    from mini_jev import typed_answer
    from train_head import get_logits, masked_logits
    torch.set_num_threads(config["threads"])
    model_args = config["model_args"]
    engine = make_engine(model_args, args.allow_download, args.device)
    runtime = runtime_provenance(engine, model_args["batch_size"], model_args["max_candidates"])
    same_runtime = runtime == config["runtime"]
    if not same_runtime and not args.allow_runtime_change:
        raise ValueError("runtime provenance differs; explicit --allow-runtime-change required")
    data, extraction = extract_features(engine, cases, args.cache or output / "feature-cache",
                                        model_args["batch_size"], model_args["max_candidates"], runtime)
    control = controls[args.control]
    temperature = 1.0 if args.without_temperature else config["temperatures"][args.control]
    logits = get_logits(data, control["weight"], control["bias"])
    probabilities = masked_logits(logits / temperature, data["count"]).softmax(-1)
    results = []
    for index, case in enumerate(cases):
        keys = case_keys(case)
        answer = typed_answer(case["type"], keys, probabilities[index, :len(keys)].tolist())
        answer.update(control=args.control, temperature=temperature, output_tokens=0,
                      temperature_calibration_applied=not args.without_temperature,
                      calibration_generalization_validated=False)
        if case["type"] == "score":
            answer["legend"] = dict(enumerate(case["criteria"]))
        results.append(answer)
    write_json(output / "predictions.json", {"results": results, "runtime": runtime,
               "runtime_exact_match": same_runtime, "feature_extraction": extraction,
               "checkpoint_config_sha256": sha_file(args.checkpoint / "config.json")})
    print(json.dumps(results, ensure_ascii=False, indent=2))


def positive_int(value):
    result = int(value)
    if result < 1:
        raise argparse.ArgumentTypeError("must be positive")
    return result


def candidates(value):
    result = int(value)
    if not 2 <= result <= 26:
        raise argparse.ArgumentTypeError("must be 2..26")
    return result


def finite_list(value):
    try:
        values = [float(v) for v in value.split(",")]
    except ValueError as error:
        raise argparse.ArgumentTypeError("expected comma-separated numbers") from error
    if not values or any(not math.isfinite(v) or v <= 0 for v in values):
        raise argparse.ArgumentTypeError("all numbers must be finite and positive")
    return values


def commit_sha(value):
    if not re.fullmatch(r"[0-9a-f]{40}", value):
        raise argparse.ArgumentTypeError("revision must be a full 40-character lowercase commit SHA")
    return value


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    commands = p.add_subparsers(dest="command", required=True)
    for name in ("validate", "train"):
        command = commands.add_parser(name)
        for split in SPLITS:
            command.add_argument("--" + split, required=True, type=Path)
        command.add_argument("--max-candidates", type=candidates, default=6)
        command.add_argument("--disjoint-groups", choices=("none", "group", "family", "both"), default="none")
        if name == "validate":
            command.add_argument("--output", type=Path, help="new JSON audit file; never overwritten")
        else:
            command.add_argument("--output", type=Path, required=True, help="new directory; existing destinations rejected")
            command.add_argument("--model", required=True, help="Qwen2/Qwen2.5 Hugging Face model ID")
            command.add_argument("--revision", type=commit_sha, required=True)
            command.add_argument("--device", choices=("auto", "cpu", "mps", "cuda"), default="auto")
            command.add_argument("--dtype", choices=("float32", "float16", "bfloat16"), default="float32")
            command.add_argument("--seed", type=int, required=True)
            command.add_argument("--max-input-tokens", type=positive_int, default=2048)
            command.add_argument("--batch-size", type=positive_int, default=8)
            command.add_argument("--epochs", type=positive_int, default=120)
            command.add_argument("--threads", type=positive_int, default=4)
            command.add_argument("--learning-rates", type=finite_list, default=[.001, .003])
            command.add_argument("--penalties", type=finite_list, default=[.01, .1])
            command.add_argument("--cache", type=Path)
            command.add_argument("--allow-download", action="store_true")
    evaluate = commands.add_parser("evaluate")
    evaluate.add_argument("--checkpoint", required=True, type=Path)
    evaluate.add_argument("--test", required=True, type=Path)
    evaluate.add_argument("--output", required=True, type=Path)
    evaluate.add_argument("--cache", type=Path)
    evaluate.add_argument("--device", choices=("auto", "cpu", "mps", "cuda"))
    evaluate.add_argument("--allow-runtime-change", action="store_true")
    evaluate.add_argument("--allow-download", action="store_true")
    predict = commands.add_parser("predict")
    predict.add_argument("--checkpoint", required=True, type=Path)
    predict.add_argument("--input", required=True, type=Path, help="JSON question object or array, without labels/ids")
    predict.add_argument("--output", required=True, type=Path)
    predict.add_argument("--control", choices=("baseline", "bias", "residual"), default="residual")
    predict.add_argument("--without-temperature", action="store_true")
    predict.add_argument("--cache", type=Path)
    predict.add_argument("--device", choices=("auto", "cpu", "mps", "cuda"))
    predict.add_argument("--allow-runtime-change", action="store_true")
    predict.add_argument("--allow-download", action="store_true")
    return p


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        if args.command == "validate":
            groups, audit = load_splits(args)
            result = {"schema_version": SCHEMA_VERSION, "splits": split_summary(groups, args), **audit}
            if args.output:
                with args.output.open("x", encoding="utf-8") as stream:
                    json.dump(result, stream, ensure_ascii=False, indent=2, allow_nan=False)
                    stream.write("\n")
            print(json.dumps({"valid": True, "splits": result["splits"], "group_policy": audit["policy"]}, indent=2))
        elif args.command == "train":
            train_command(args)
        elif args.command == "evaluate":
            evaluate_command(args)
        else:
            predict_command(args)
    except (ValueError, OSError, KeyError, TypeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
