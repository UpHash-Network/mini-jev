"""An experimental decision interface over a local causal language model.

No training, no generated text in decide(), no claim of calibrated confidence.
Candidate probabilities are conditional on the allowed single-token labels.
"""
from __future__ import annotations

import argparse
import json
import math
import string
import time
from pathlib import Path
from typing import Any

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

DEFAULT_MODEL = "Qwen/Qwen2.5-0.5B-Instruct"


def options_for(question: dict[str, Any]) -> list[tuple[str, str]]:
    """Validate a typed question; evaluation labels are deliberately ignored."""
    if not isinstance(question, dict):
        raise ValueError("question must be an object")
    if "state" not in question:
        raise ValueError("state is required")
    if not isinstance(question.get("instructions"), str) or not question["instructions"].strip():
        raise ValueError("instructions must be a non-empty string")
    kind, criteria = question.get("type"), question.get("criteria")
    if kind == "noul":
        criteria = criteria if criteria is not None else {"false": "いいえ", "true": "はい"}
        if not isinstance(criteria, dict) or set(criteria) != {"false", "true"}:
            raise ValueError("noul criteria must have exactly false and true keys")
        options = [(k, criteria[k]) for k in ("false", "true")]
    elif kind == "choice":
        if not isinstance(criteria, dict):
            raise ValueError("choice criteria must be an object")
        options = list(criteria.items())
    elif kind == "score":
        if not isinstance(criteria, list):
            raise ValueError("score criteria must be an ordered array")
        options = [(str(i), description) for i, description in enumerate(criteria)]
    else:
        raise ValueError("type must be choice, noul, or score")
    if not 2 <= len(options) <= 26:
        raise ValueError("this prototype supports 2 to 26 options")
    if any(not isinstance(k, str) or not k or not isinstance(v, str) or not v.strip()
           for k, v in options):
        raise ValueError("option keys and descriptions must be non-empty strings")
    return options


def typed_answer(kind: str, keys: list[str], probabilities: list[float]) -> dict[str, Any]:
    if len(keys) != len(probabilities) or not probabilities:
        raise ValueError("keys and probabilities must have the same non-zero length")
    if any(not math.isfinite(p) or p < 0 for p in probabilities):
        raise ValueError("probabilities must be finite and non-negative")
    if abs(sum(probabilities) - 1.0) > 1e-5:
        raise ValueError("probabilities must sum to one")
    best = max(range(len(keys)), key=lambda i: probabilities[i])
    result = {"type": kind, "label": keys[best],
              "probabilities": dict(zip(keys, probabilities)), "calibrated": False,
              "probability_semantics": "conditional_on_allowed_label_tokens"}
    if kind == "choice":
        result["choice"] = keys[best]
    elif kind == "noul":
        result["noul"] = result["probabilities"]["true"]
    elif kind == "score":
        result["score"] = sum(int(k) * p for k, p in zip(keys, probabilities))
    else:
        raise ValueError("unknown question type")
    return result


class MiniJev:
    def __init__(self, model: str = DEFAULT_MODEL, device: str = "auto",
                 local_files_only: bool = True, max_input_tokens: int = 2048,
                 revision: str | None = None, dtype: str = "float32"):
        if device == "auto":
            device = "cuda" if torch.cuda.is_available() else (
                "mps" if torch.backends.mps.is_available() else "cpu")
        self.device = torch.device(device)
        if dtype not in ("float32", "float16", "bfloat16"):
            raise ValueError("dtype must be float32, float16, or bfloat16")
        self.dtype = getattr(torch, dtype)
        self.model_id = model
        if max_input_tokens < 1:
            raise ValueError("max_input_tokens must be positive")
        self.max_input_tokens = max_input_tokens
        self.tokenizer = AutoTokenizer.from_pretrained(
            model, revision=revision, local_files_only=local_files_only, trust_remote_code=False)
        self.tokenizer.padding_side = "left"
        if self.tokenizer.pad_token_id is None:
            self.tokenizer.pad_token_id = self.tokenizer.eos_token_id
        self.model = AutoModelForCausalLM.from_pretrained(
            model, revision=revision, local_files_only=local_files_only, trust_remote_code=False,
            use_safetensors=True, torch_dtype=self.dtype).to(self.device).eval()
        if self.model.config.model_type != "qwen2":
            raise ValueError("only Qwen2/Qwen2.5 architecture is validated; other models may transform logits after the LM head")
        self.model_limit = getattr(self.model.config, "max_position_embeddings", max_input_tokens)
        self.max_input_tokens = min(max_input_tokens, self.model_limit)
        self.symbol_ids = []
        for symbol in string.ascii_uppercase:
            ids = self.tokenizer.encode(symbol, add_special_tokens=False)
            if len(ids) != 1:
                raise ValueError(f"{symbol!r} is not one token in this tokenizer")
            self.symbol_ids.append(ids[0])
        if len(set(self.symbol_ids)) != len(self.symbol_ids):
            raise ValueError("label token ids must be unique")
        self._head_cache: dict[int, tuple[Any, Any, Any]] = {}

    def synchronize(self) -> None:
        if self.device.type == "mps":
            torch.mps.synchronize()
        elif self.device.type == "cuda":
            torch.cuda.synchronize(self.device)

    def _prepare(self, question: dict[str, Any], format: str = "token"):
        options = options_for(question)
        state = question["state"]
        if not isinstance(state, str):
            state = json.dumps(state, ensure_ascii=False, allow_nan=False)
        choices = "\n".join(f"{string.ascii_uppercase[i]}. {key}: {description}"
                            for i, (key, description) in enumerate(options))
        answer_rule = ("答えは選択肢の英大文字1文字だけを出力してください。説明は不要です。"
                       if format == "token" else
                       '答えはキーがlabelだけのJSONオブジェクトで出力してください。'
                       'labelの値には選んだ選択肢の英大文字1文字を文字列で入れてください。説明は不要です。')
        messages = [
            {"role": "system", "content": "あなたは状態と質問を読み、最も適切な選択肢を選ぶ判定器です。"},
            {"role": "user", "content": f"状態:\n{state}\n\n質問:\n{question['instructions']}"
             f"\n\n選択肢:\n{choices}\n\n{answer_rule}"},
        ]
        prompt = self.tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True)
        ids = self.tokenizer.encode(prompt, add_special_tokens=False)
        if not ids or len(ids) > self.max_input_tokens:
            raise ValueError(f"input has {len(ids)} tokens; limit is {self.max_input_tokens}; no truncation applied")
        # Check the actual prompt boundary, not just the isolated label strings.
        for symbol, token_id in zip(string.ascii_uppercase[:len(options)], self.symbol_ids):
            if self.tokenizer.encode(prompt + symbol, add_special_tokens=False) != ids + [token_id]:
                raise ValueError(f"label {symbol!r} is not one appended token at this prompt boundary")
        return options, ids

    def _batch(self, token_lists: list[list[int]]):
        inputs = self.tokenizer.pad({"input_ids": token_lists}, padding=True, return_tensors="pt")
        inputs = {k: v.to(self.device) for k, v in inputs.items()}
        positions = inputs["attention_mask"].long().cumsum(-1) - 1
        inputs["position_ids"] = positions.masked_fill(inputs["attention_mask"] == 0, 0)
        return inputs

    def _head(self, count: int):
        if count not in self._head_cache:
            ids = torch.tensor(self.symbol_ids[:count], device=self.device)
            head = self.model.get_output_embeddings()
            weight = head.weight.index_select(0, ids)
            bias = getattr(head, "bias", None)
            bias = None if bias is None else bias.index_select(0, ids)
            self._head_cache[count] = (ids, weight, bias)
        return self._head_cache[count]

    @torch.inference_mode()
    def decide_many(self, questions: list[dict[str, Any]], projection: str = "selected"):
        """Ordinary padded batching; each question includes its own state tokens.

        This does NOT implement Jev's shared-state parallel inference.
        Per-result latency_ms is the entire batch latency, never divided by N.
        """
        if projection not in ("selected", "full"):
            raise ValueError("projection must be selected or full")
        if not questions:
            return []
        started = time.perf_counter()
        prepared = [self._prepare(q) for q in questions]
        inputs = self._batch([ids for _, ids in prepared])
        self.synchronize()
        model_started = time.perf_counter()
        # Run the backbone once and project ONLY the final hidden state.
        hidden = self.model.base_model(**inputs, use_cache=False, return_dict=True).last_hidden_state[:, -1, :]
        all_logits = self.model.get_output_embeddings()(hidden) if projection == "full" else None
        results = []
        for i, (question, (options, token_ids)) in enumerate(zip(questions, prepared)):
            selected_ids, weight, bias = self._head(len(options))
            if all_logits is None:
                logits = torch.nn.functional.linear(hidden[i], weight, bias).float()
                mass = None
            else:
                row = all_logits[i].float()
                logits = row.index_select(0, selected_ids)
                mass = float(torch.exp(torch.logsumexp(logits, 0) - torch.logsumexp(row, 0)).cpu())
            probabilities = torch.softmax(logits, dim=-1).cpu().tolist()
            keys = [key for key, _ in options]
            answer = typed_answer(question["type"], keys, probabilities)
            answer.update(candidate_keys=keys, candidate_logits=logits.cpu().tolist(),
                          candidate_mass=mass, input_tokens=len(token_ids),
                          output_tokens=0, projection=projection, batch_size=len(questions))
            results.append(answer)
        self.synchronize()
        model_ms = (time.perf_counter() - model_started) * 1000
        latency_ms = (time.perf_counter() - started) * 1000
        for answer in results:
            answer.update(model_ms=model_ms, latency_ms=latency_ms)
        return results

    def decide(self, question: dict[str, Any], projection: str = "selected"):
        return self.decide_many([question], projection=projection)[0]

    @torch.inference_mode()
    def generate(self, question: dict[str, Any], format: str = "token"):
        if format not in ("token", "json"):
            raise ValueError("format must be token or json")
        started = time.perf_counter()
        options, ids = self._prepare(question, format=format)
        inputs = self._batch([ids])
        # generate() manages the changing positions itself.
        inputs.pop("position_ids")
        max_new_tokens = 1 if format == "token" else 32
        if len(ids) + max_new_tokens > self.model_limit:
            raise ValueError("input plus generation allowance exceeds model context")
        self.synchronize()
        model_started = time.perf_counter()
        generated = self.model.generate(
            **inputs, max_new_tokens=max_new_tokens, do_sample=False,
            temperature=None, top_p=None, top_k=None, use_cache=True,
            repetition_penalty=1.0,
            pad_token_id=self.tokenizer.pad_token_id)
        output_ids = generated[0, len(ids):].cpu().tolist()
        self.synchronize()
        model_ms = (time.perf_counter() - model_started) * 1000
        output = self.tokenizer.decode(output_ids, skip_special_tokens=True)
        symbol = output.strip()
        if format == "json":
            try:
                parsed = json.loads(output)
                symbol = parsed.get("label") if isinstance(parsed, dict) else None
            except (ValueError, TypeError):
                symbol = None
        valid = isinstance(symbol, str) and len(symbol) == 1 and symbol in string.ascii_uppercase[:len(options)]
        label = options[string.ascii_uppercase.index(symbol)][0] if valid else None
        return {"label": label, "text": output, "valid": valid,
                "input_tokens": len(ids), "output_tokens": len(output_ids),
                "model_ms": model_ms, "latency_ms": (time.perf_counter() - started) * 1000}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True, help="question object or array of questions as JSON")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--device", default="auto", choices=["auto", "cpu", "mps", "cuda"])
    parser.add_argument("--projection", default="selected", choices=["selected", "full"])
    parser.add_argument("--allow-download", action="store_true", help="explicitly allow downloading model weights")
    args = parser.parse_args()
    data = json.loads(args.input.read_text(encoding="utf-8"))
    engine = MiniJev(model=args.model, device=args.device, local_files_only=not args.allow_download)
    results = engine.decide_many(data if isinstance(data, list) else [data], projection=args.projection)
    print(json.dumps(results if isinstance(data, list) else results[0], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
