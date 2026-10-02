"""Offline, pinned Transformers readout for a two-checkpoint replication.

Verification and token preparation do not load model weights. Only constructing
TransformersResearchEngine loads a model; at most one instance may be resident
in this process. Full prompt text / input IDs must stay outside public records.
"""
from __future__ import annotations

from dataclasses import dataclass
import gc
import hashlib
from importlib import metadata
import json
import math
from pathlib import Path
import platform
import sys
import threading
import time

DEFAULT_CACHE_ROOT = Path.home() / ".cache/huggingface/hub"
MAX_INPUT_TOKENS = 2048
LOGIT_ATOL = 1e-3
LOGIT_RTOL = 1e-5
PROBABILITY_ATOL = 1e-5
COMMON_FILES = {
    "generation_config.json": (242, "e558847a8b4402616f1273797b015104dc266fe4b520056fca88823ba8f8ebe6"),
    "tokenizer_config.json": (7305, "5b5d4f65d0acd3b2d56a35b56d374a36cbc1c8fa5cf3b3febbbfabf22f359583"),
    "tokenizer.json": (7031645, "c0382117ea329cdf097041132f6d735924b697924d6f6fc3945713e96ce87539"),
    "merges.txt": (1671839, "599bab54075088774b1733fde865d5bd747cbcc7a547c5bc12610e874e26f5e3"),
    "vocab.json": (2776833, "ca10d7e9fb3ed18575dd1e277a2579c16d108e32f27439684afa0e10b1440910"),
}
MODEL_SPECS = {
    "qwen2.5-0.5b": {
        "repo_id": "Qwen/Qwen2.5-0.5B-Instruct",
        "revision": "7ae557604adf67be50417f59c2c2f167def9a775",
        "files": {**COMMON_FILES,
                  "config.json": (659, "18e18afcaccafade98daf13a54092927904649e1dd4eba8299ab717d5d94ff45"),
                  "model.safetensors": (988097824, "fdf756fa7fcbe7404d5c60e26bff1a0c8b8aa1f72ced49e7dd0210fe288fb7fe")},
    },
    "qwen2.5-1.5b": {
        "repo_id": "Qwen/Qwen2.5-1.5B-Instruct",
        "revision": "989aa7980e4cf806f80c7fef2b1adb7bc71aa306",
        "files": {**COMMON_FILES,
                  "config.json": (660, "98d2ff8cc47488d08a2b0b3acf4eb99ef210779b42bd48605f6b8e36acdbf670"),
                  "model.safetensors": (3087467144, "dd924a11b4c220f385b51ffa522daea7c9f3d850e31b162bb5661df483c6d3ee")},
    },
}


MODEL_SPECS["phi-4-mini"] = {'repo_id': 'microsoft/Phi-4-mini-instruct', 'revision': 'cfbefacb99257ffa30c83adab238a50856ac3083', 'model_type': 'phi3', 'architecture': 'Phi3ForCausalLM', 'files': {'LICENSE': [1084, 'fa8235e5b48faca34e3ca98cf4f694ef08bd216d28b58071a1f85b1d50cb814d'], 'NOTICE.md': [1809, 'a3386cc7125ec75ed34d4f0a340c47782982095e251d322e01d8ecab22d87ba4'], 'README.md': [29246, 'c4f34916182a3ee87d95d00c92847cfa687ab21dc338a577275f0c34cf0e1dfd'], 'added_tokens.json': [249, 'd4f2aceb0f20b71dd1f4bcc7e052e4412946bf281840b8f83d39f259571af486'], 'config.json': [2504, 'ac65d86061d3d0d704ee2511fd0eb8713ef19eb6eedba17c3080a4165d5b933b'], 'data_summary_card.md': [4320, '470514f8d8408e1254c9487401dc4d7d2edb4e08f0453f7bbfb5e01dbb976456'], 'generation_config.json': [168, '3e3f48753753f92d2b958679151861d4fd7bf26e4dfc41fd47056116c4914dcd'], 'merges.txt': [2418348, '856ce61180bb689282eed6b3a6838bb1f438399be23aefe9d20eb379791fb4ad'], 'model-00001-of-00002.safetensors': [4903637712, 'bc703090b63eda16f639fa4de7ac54635c23105ab1da2f6ec4d3403151d38ee6'], 'model-00002-of-00002.safetensors': [2768428504, '7ff79b9d2d31076bac2663393451f6530f4fc8ca49b09002116c92c373dba983'], 'model.safetensors.index.json': [16273, '613a98d5e5716ca96fa75931abedc9c5a5d95f488ce4d62df71e639fe3ac6c59'], 'special_tokens_map.json': [587, 'aff38493227d813e29fcf8406e8e90062f1f031aa47d589325e9c31d89ac7cc3'], 'tokenizer.json': [15524095, '382cc235b56c725945e149cc25f191da667c836655efd0857b004320e90e91ea'], 'tokenizer_config.json': [2932, '9c9b6bc0c94d95f69f826c41069a3e8b387ac3ced89601d201886e99240ac9db'], 'vocab.json': [3910310, '6cb65a857824fa6615bb1782d95d882617a8bbce1da0317118586b36f39e98bd']}}

def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _identity(path):
    st = path.stat()
    return (str(path.resolve()), st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns, st.st_ctime_ns)


def _verify_file(path, size, expected):
    before = _identity(path)
    if before[3] != size:
        raise ValueError("pinned artifact size mismatch: " + path.name)
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(block)
    if _identity(path) != before or digest.hexdigest() != expected:
        raise ValueError("pinned artifact hash mismatch or concurrent change: " + path.name)
    return before


def implementation_manifest():
    """Hash actual installed implementation artifacts without importing/loading a model.

    Includes the relevant Transformers/PyTorch Python modules and every shipped
    torch dylib plus its extension and the tokenizers extension. Package versions
    supplement those actual hashes; they do not stand in for file verification.
    """
    module_files = {
        "torch": ["torch/__init__.py", "torch/nn/modules/module.py", "torch/nn/modules/linear.py",
                  "torch/utils/_contextlib.py", "torch/autograd/grad_mode.py"],
        "transformers": ["transformers/__init__.py", "transformers/modeling_utils.py",
            "transformers/tokenization_utils_base.py", "transformers/tokenization_utils_fast.py",
            "transformers/utils/chat_template_utils.py", "transformers/models/qwen2/modeling_qwen2.py",
            "transformers/models/phi3/modeling_phi3.py", "transformers/models/phi3/configuration_phi3.py", "transformers/models/gpt2/tokenization_gpt2_fast.py", "transformers/models/qwen2/configuration_qwen2.py", "transformers/models/qwen2/tokenization_qwen2_fast.py"],
        "tokenizers": ["tokenizers/__init__.py"],
        "safetensors": ["safetensors/__init__.py", "safetensors/torch.py"],
        "jinja2": ["jinja2/environment.py", "jinja2/compiler.py", "jinja2/lexer.py", "jinja2/parser.py"],
    }
    files, versions = {}, {}
    for package, relative_paths in module_files.items():
        distribution = metadata.distribution(package)
        versions[package] = distribution.version
        paths = [Path(distribution.locate_file(rel)) for rel in relative_paths]
        if package == "torch":
            folder = Path(distribution.locate_file("torch"))
            paths += list(folder.glob("_C*.so"))+list((folder/"lib").glob("*.dylib"))
        elif package in {"tokenizers", "safetensors"}:
            paths += list(Path(distribution.locate_file(package)).glob("*.so"))
        for path in sorted(paths):
            before = _identity(path)
            digest = hashlib.sha256()
            with path.open("rb") as stream:
                for block in iter(lambda: stream.read(4*1024*1024), b""):
                    digest.update(block)
            if _identity(path) != before:
                raise ValueError("installed implementation changed while hashing")
            relative = str(path.relative_to(distribution.locate_file("")))
            files[relative] = {"sha256": digest.hexdigest(), "bytes": before[3]}
    return {"python": platform.python_version(), "executable": str(Path(sys.executable).resolve()),
            "platform": platform.platform(), "machine": platform.machine(), "versions": versions,
            "implementation_files": files, "model_loads": 0}


@dataclass
class VerifiedSnapshot:
    model_key: str
    path: Path
    file_identities: dict

    @property
    def spec(self):
        return MODEL_SPECS[self.model_key]

    def assert_unchanged(self):
        # Also reject newly added source files that from_pretrained might inspect.
        if {p.name for p in self.path.iterdir() if p.is_file()} != set(self.file_identities):
            raise ValueError("snapshot file inventory changed after verification")
        for name, identity in self.file_identities.items():
            if _identity(self.path / name) != identity:
                raise ValueError("verified checkpoint changed: " + name)

    def manifest(self):
        return {"model_key": self.model_key, "repo_id": self.spec["repo_id"],
                "revision": self.spec["revision"], "model_type": self.spec.get("model_type", "qwen2"),
                "file_sha256": {name: digest for name, (_, digest) in self.spec["files"].items()},
                "file_bytes": {name: size for name, (size, _) in self.spec["files"].items()},
                "verification": "All required artifacts fully SHA-256 verified, then stat/target identities checked."}


def verify_snapshot(model_key, cache_root=DEFAULT_CACHE_ROOT):
    """Read and hash local artifacts only; never download, import a model or load weights."""
    if model_key not in MODEL_SPECS:
        raise ValueError("unsupported checkpoint")
    spec = MODEL_SPECS[model_key]
    repo_folder = "models--" + spec["repo_id"].replace("/", "--")
    path = (Path(cache_root) / repo_folder / "snapshots" / spec["revision"]).resolve()
    if not path.is_dir():
        raise ValueError("pinned local checkpoint is absent")
    # README/LICENSE files are inert, but record their identities so additions or
    # replacements cannot alter what the loader sees after this initial audit.
    names = {p.name for p in path.iterdir() if p.is_file()}
    unexpected = names - set(spec["files"]) - {"README.md", "LICENSE", ".gitattributes"}
    if unexpected or not set(spec["files"]) <= names:
        raise ValueError("unexpected or missing checkpoint artifact files")
    identities = {name: _verify_file(path/name, size, digest)
                  for name, (size, digest) in spec["files"].items()}
    identities.update({name: _identity(path/name) for name in names - set(identities)})
    config = json.loads((path/"config.json").read_text())
    if (config["model_type"] != spec.get("model_type", "qwen2") or config["architectures"] != [spec.get("architecture", "Qwen2ForCausalLM")]
            or config["max_position_embeddings"] < MAX_INPUT_TOKENS):
        raise ValueError("unexpected pinned architecture or context limit")
    result = VerifiedSnapshot(model_key, path, identities)
    result.assert_unchanged()
    return result


def _request_fields(request):
    if not isinstance(request, dict) or not {"messages", "candidates", "max_input_tokens"} <= set(request):
        raise ValueError("incomplete inference request")
    if set(request) - {"messages", "candidates", "max_input_tokens", "assistant_prefix"}:
        raise ValueError("unexpected inference request field")
    if request["max_input_tokens"] != MAX_INPUT_TOKENS:
        raise ValueError("cross-model context limit must equal the frozen 2048-token limit")
    messages, candidates = request["messages"], request["candidates"]
    if (not isinstance(messages, list) or len(messages) != 2
            or [m.get("role") for m in messages if isinstance(m, dict)] != ["system", "user"]
            or any(set(m) != {"role", "content"} or not isinstance(m["content"], str) for m in messages)):
        raise ValueError("expected exact system and user messages")
    if (not isinstance(candidates, list) or not 2 <= len(candidates) <= 26
            or any(not isinstance(x, str) or not x for x in candidates)
            or len(set(candidates)) != len(candidates)):
        raise ValueError("invalid candidate tokens")
    if not isinstance(request.get("assistant_prefix", ""), str):
        raise ValueError("assistant prefix must be text")


def _prepare_with_tokenizer(tokenizer, request, model_key, revision):
    _request_fields(request)
    # Preserve exact v1 message text; no tool schema, reasoning template, forced
    # whitespace, EOS or extra special tokens are appended by this adapter.
    rendered = tokenizer.apply_chat_template(request["messages"], tokenize=False,
                                            add_generation_prompt=True)
    prompt = rendered + request.get("assistant_prefix", "")
    ids = tokenizer.encode(prompt, add_special_tokens=False)
    if not 1 <= len(ids) <= MAX_INPUT_TOKENS:
        raise ValueError(f"input has {len(ids)} tokens; limit is {MAX_INPUT_TOKENS}; no truncation applied")
    candidate_ids = []
    for token in request["candidates"]:
        isolated = tokenizer.encode(token, add_special_tokens=False)
        if len(isolated) != 1:
            raise ValueError("candidate is not one isolated token")
        if tokenizer.encode(prompt+token, add_special_tokens=False) != ids+isolated:
            raise ValueError("candidate is not one appended token at the actual assistant boundary")
        candidate_ids.append(isolated[0])
    if len(set(candidate_ids)) != len(candidate_ids):
        raise ValueError("candidate token IDs are not distinct")
    result = {"model_key": model_key, "revision": revision, "input_ids": ids,
            "candidate_ids": candidate_ids, "candidate_tokens": list(request["candidates"]),
            "input_tokens": len(ids), "request_sha256": sha(canonical(request).encode()),
            "rendered_sha256": sha(prompt.encode()),
            "tokenized_input_sha256": sha(canonical(ids).encode()),
            "candidate_boundary_verified": True}
    result["prepared_integrity_sha256"] = sha(canonical(result).encode())
    return result


class TokenizerPreparer:
    def __init__(self, verified):
        from transformers import AutoTokenizer
        verified.assert_unchanged()
        self.verified = verified
        self.tokenizer = AutoTokenizer.from_pretrained(str(verified.path), local_files_only=True,
                                                       trust_remote_code=False, use_fast=True)
        verified.assert_unchanged()

    def prepare(self, request):
        self.verified.assert_unchanged()
        return _prepare_with_tokenizer(self.tokenizer, request, self.verified.model_key,
                                       self.verified.spec["revision"])

    @staticmethod
    def public_metadata(prepared):
        return {key: value for key, value in prepared.items() if key != "input_ids"}


def prepare_requests(model_key, requests, cache_root=DEFAULT_CACHE_ROOT):
    """Tokenize the whole proposed schedule before loading any model."""
    preparer = TokenizerPreparer(verify_snapshot(model_key, cache_root))
    return preparer, [preparer.prepare(request) for request in requests]


def candidate_answer(logits, keys, kind):
    if (len(logits) != len(keys) or not 2 <= len(keys) <= 26
            or any(not isinstance(k, str) for k in keys) or len(set(keys)) != len(keys)
            or any(type(v) not in (int, float) or not math.isfinite(v) for v in logits)):
        raise ValueError("invalid candidate vector")
    if kind == "noul" and set(keys) != {"false", "true"}:
        raise ValueError("invalid Noul semantic keys")
    if kind == "score" and set(keys) != {str(i) for i in range(len(keys))}:
        raise ValueError("invalid ordinal semantic keys")
    if kind not in {"choice", "noul", "score"}:
        raise ValueError("unsupported decision type")
    peak = max(logits)
    weights = [math.exp(v-peak) for v in logits]
    total = math.fsum(weights)
    p = [v/total for v in weights]
    probabilities = dict(zip(keys, p))
    # Match the actual candidate vector's first maximum; never silently move a tie.
    index = max(range(len(logits)), key=logits.__getitem__)
    label = keys[index]
    value = label if kind == "choice" else probabilities["true"] if kind == "noul" else math.fsum(float(k)*v for k, v in probabilities.items())
    return {"logits": list(logits), "probabilities": probabilities, "label": label,
            "typed_value": value, "temperature": 1.0,
            "concentration": max(0.0, min(1.0, 1+math.fsum(v*math.log(v) for v in p if v)/math.log(len(p)))),
            "top_logit_tie_count": sum(v == peak for v in logits),
            "tie_break": "first_candidate_vector_index"}


class TransformersResearchEngine:
    _resident_lock = threading.Lock()
    _resident = False

    def __init__(self, preparer, device="mps"):
        if device not in {"mps", "cpu"}:
            raise ValueError("device must be explicit mps or cpu")
        self.closed, self._owns_resident = True, False
        with self._resident_lock:
            if TransformersResearchEngine._resident:
                raise RuntimeError("close the resident research model before loading another")
            TransformersResearchEngine._resident = True
            self._owns_resident = True
        try:
            import torch
            import transformers
            from transformers import AutoModelForCausalLM
            self.torch, self.preparer = torch, preparer
            preparer.verified.assert_unchanged()
            if device == "mps" and not torch.backends.mps.is_available():
                raise RuntimeError("MPS unavailable; no automatic device fallback")
            self.device = torch.device(device)
            self.model = AutoModelForCausalLM.from_pretrained(
                str(preparer.verified.path), local_files_only=True, trust_remote_code=False,
                use_safetensors=True, dtype=torch.float32, attn_implementation="eager"
            ).to(self.device).eval().requires_grad_(False)
            if self.model.config.model_type != preparer.verified.spec.get("model_type", "qwen2") or any(p.requires_grad for p in self.model.parameters()):
                raise RuntimeError("unexpected or unfrozen model")
            if any(p.is_floating_point() and p.dtype != torch.float32 for p in self.model.parameters()):
                raise RuntimeError("model parameters do not use fixed float32")
            self.runtime_metadata = {**preparer.verified.manifest(), "backend": "transformers",
                "device": str(self.device), "dtype": "float32", "attention": "eager",
                "torch_version": torch.__version__, "transformers_version": transformers.__version__,
                "use_cache": False, "batch_size": 1, "logits_to_keep": 0,
                "projection": "stock_causal_lm_all_positions_full_vocab_then_last_candidate_gather",
                "engine_source_sha256": sha(Path(__file__).read_bytes())}
            preparer.verified.assert_unchanged()
            self.closed = False
            self.forward_calls = 0
            self._gate_passed = False
        except BaseException:
            self.close()
            raise

    def _synchronize(self):
        if self.device.type == "mps":
            self.torch.mps.synchronize()

    def _forward(self, prepared, logits_to_keep):
        if self.closed:
            raise RuntimeError("research model is closed")
        self.preparer.verified.assert_unchanged()
        ids = prepared["input_ids"]
        integrity = {k: v for k, v in prepared.items() if k != "prepared_integrity_sha256"}
        if (logits_to_keep not in {0, 1}
                or prepared.get("prepared_integrity_sha256") != sha(canonical(integrity).encode())
                or prepared["model_key"] != self.preparer.verified.model_key
                or prepared["revision"] != self.preparer.verified.spec["revision"]
                or prepared["tokenized_input_sha256"] != sha(canonical(ids).encode())
                or prepared["input_tokens"] != len(ids)
                or not 1 <= len(ids) <= MAX_INPUT_TOKENS
                or prepared.get("candidate_boundary_verified") is not True):
            raise ValueError("prepared input does not match its verified model/hash")
        t = self.torch
        tensor = t.tensor([ids], dtype=t.long, device=self.device)
        self._synchronize()
        started = time.perf_counter()
        with t.inference_mode():
            context = {"model_training": bool(self.model.training),
                       "parameters_require_grad": any(p.requires_grad for p in self.model.parameters()),
                       "grad_enabled": bool(t.is_grad_enabled()),
                       "inference_mode_enabled": bool(t.is_inference_mode_enabled())}
            if context["model_training"] or context["parameters_require_grad"] or context["grad_enabled"] or not context["inference_mode_enabled"]:
                raise RuntimeError("actual forward context does not satisfy frozen inference contract")
            self.forward_calls += 1
            answer = self.model(input_ids=tensor, attention_mask=t.ones_like(tensor),
                                use_cache=False, return_dict=True, logits_to_keep=logits_to_keep)
            context["past_key_values_returned"] = answer.past_key_values is not None
            if context["past_key_values_returned"]:
                raise RuntimeError("no-cache forward unexpectedly returned cached state")
            last = answer.logits[0, -1].float()
            logits = last[prepared["candidate_ids"]].cpu().tolist()
        self._synchronize()
        model_ms = (time.perf_counter()-started)*1000
        self._last_forward_context = context
        if any(not math.isfinite(v) for v in logits):
            raise RuntimeError("nonfinite candidate logits")
        self.preparer.verified.assert_unchanged()
        return logits, model_ms

    def evaluate_request(self, prepared, canonical_keys, kind):
        if not self._gate_passed:
            raise RuntimeError("fixed synthetic full-position repeatability gate has not passed")
        candidate_answer([0.0]*len(prepared["candidate_ids"]), canonical_keys, kind)
        started = time.perf_counter()
        logits, model_ms = self._forward(prepared, 0)
        result = candidate_answer(logits, canonical_keys, kind)
        result.update(backend="transformers", forward_calls=1,
                      forward_calls_total=self.forward_calls, use_cache=False, batch_size=1,
                      candidate_ids=list(prepared["candidate_ids"]), input_tokens=prepared["input_tokens"],
                      output_tokens=0, model_ms=model_ms, latency_ms=(time.perf_counter()-started)*1000,
                      logits_to_keep=0, candidate_boundary_verified=True,
                      projection="stock_causal_lm_all_positions_full_vocab_then_last_candidate_gather", error=None)
        result.update(self._last_forward_context)
        return result

    def close(self):
        self.closed = True
        if hasattr(self, "model"):
            del self.model
            gc.collect()
            if hasattr(self, "device") and self.device.type == "mps":
                self.torch.mps.empty_cache()
        if self._owns_resident:
            with self._resident_lock:
                TransformersResearchEngine._resident = False
            self._owns_resident = False


def synthetic_gate_requests():
    """Exactly 12 fixed, non-benchmark requests: four contexts for each type."""
    from native_engine import NativeEngine, options_for
    formatter = object.__new__(NativeEngine)
    formatter.prompt_style = "repeat_typed_score"
    result = []
    for kind in ("choice", "noul", "score"):
        for variant in range(4):
            q = {"type": kind, "state": ("合成動作検証。番号は2。鉛筆と定規を並べました。\n" * (variant+1)),
                 "instructions": "記載された情報に最も合う候補を選んでください。",
                 "criteria": ({"pencil": "鉛筆", "ruler": "定規", "other": "それ以外"} if kind == "choice"
                              else {"false": "いいえ", "true": "はい"} if kind == "noul"
                              else [f"番号{i}" for i in range(6)])}
            options = options_for(q)
            candidates, prefix, _ = formatter._candidate_spec(q, options)
            request = {"messages": formatter._messages(q, options), "candidates": candidates,
                       "max_input_tokens": MAX_INPUT_TOKENS}
            if prefix:
                request["assistant_prefix"] = prefix
            result.append({"fixture": f"synthetic-{kind}-{variant}", "type": kind,
                           "keys": [k for k, _ in options], "request": request})
    return result


def validate_full_position_repeatability(engine):
    """24 model calls on fixed synthetic inputs; no benchmark/outcome filtering.

    Thresholds are fixed in source before all cross-model benchmark inference.
    Any failure blocks evaluate_request rather than changing thresholds or dtype.
    """
    engine._gate_passed = False
    checks = []
    forwards_before = engine.forward_calls
    for case in synthetic_gate_requests():
        prepared = engine.preparer.prepare(case["request"])
        optimized, _ = engine._forward(prepared, 0)
        full, _ = engine._forward(prepared, 0)
        a, b = candidate_answer(optimized, case["keys"], case["type"]), candidate_answer(full, case["keys"], case["type"])
        delta = max(abs(x-y) for x, y in zip(optimized, full))
        pdelta = max(abs(a["probabilities"][k]-b["probabilities"][k]) for k in case["keys"])
        passed = (all(abs(x-y) <= LOGIT_ATOL+LOGIT_RTOL*abs(y) for x, y in zip(optimized, full))
                  and pdelta <= PROBABILITY_ATOL and a["label"] == b["label"])
        checks.append({"fixture": case["fixture"], "input_tokens": prepared["input_tokens"],
                       "request_sha256": prepared["request_sha256"], "candidate_ids": prepared["candidate_ids"],
                       "candidate_keys": case["keys"], "repeat_a_logits": optimized, "repeat_b_logits": full,
                       "repeat_a_probabilities": a["probabilities"], "repeat_b_probabilities": b["probabilities"],
                       "repeat_a_top_logit_tie_count": a["top_logit_tie_count"],
                       "repeat_b_top_logit_tie_count": b["top_logit_tie_count"],
                       "repeat_a_label": a["label"], "repeat_b_label": b["label"],
                       "max_absolute_logit_difference": delta, "max_absolute_probability_difference": pdelta,
                       "labels_equal": a["label"] == b["label"], "passed": passed})
    observed_forwards = engine.forward_calls-forwards_before
    engine._gate_passed = all(c["passed"] for c in checks) and observed_forwards == 24
    return {"passed": engine._gate_passed, "fixture_count": len(checks), "forward_calls": observed_forwards,
            "expected_forward_calls": 24, "forward_count_semantics": "Stock model forward invocation attempts, incremented immediately before the call.",
            "fixtures_sha256": sha(canonical(synthetic_gate_requests()).encode()),
            "logit_atol": LOGIT_ATOL, "logit_rtol": LOGIT_RTOL, "probability_atol": PROBABILITY_ATOL,
            "exact_label_agreement_required": True, "checks": checks,
            "scope": "Stock full-position repeatability only, not optimized/full parity; no semantic-accuracy threshold or benchmark data."}
