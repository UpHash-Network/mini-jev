"""Optional residual decision head over the unchanged, frozen MiniJev backbone."""
from __future__ import annotations

import argparse
import hashlib
import inspect
import json
import math
import time
from pathlib import Path

import torch
from safetensors.torch import load_file
from mini_jev import MiniJev, typed_answer


def prompt_fingerprint():
    return hashlib.sha256(inspect.getsource(MiniJev._prepare).encode()).hexdigest()


def normalize_hidden(hidden):
    return hidden.float() / hidden.float().square().mean(dim=-1, keepdim=True).sqrt().clamp_min(1e-6)


def feature_fingerprint():
    functions = (MiniJev._prepare, MiniJev._batch, MiniJev._head, normalize_hidden)
    return hashlib.sha256("\n".join(inspect.getsource(f) for f in functions).encode()).hexdigest()


class HeadMiniJev(MiniJev):
    def __init__(self, head: str | Path, device="auto", use_temperature=True):
        path = Path(head)
        config_path = path / "config.json" if path.is_dir() else path
        self.head_config = json.loads(config_path.read_text())
        c = self.head_config
        if c["prompt_fingerprint"] != prompt_fingerprint():
            raise ValueError("prompt code differs from the head training configuration")
        if c["feature_fingerprint"] != feature_fingerprint():
            raise ValueError("feature processing differs from the head training configuration")
        super().__init__(model=c["model"], device=device, local_files_only=True,
                         max_input_tokens=c["max_input_tokens"])
        if getattr(self.model.config, "_commit_hash", None) != c["model_revision"]:
            raise ValueError("backbone revision differs from the head training configuration")
        self.max_choices = c["max_choices"]
        if self.symbol_ids[:self.max_choices] != c["symbol_ids"]:
            raise ValueError("label token ids differ from training")
        weights = load_file(str(config_path.parent / "head.safetensors"))
        self.delta_weight = weights["delta_weight"].to(self.device)
        self.delta_bias = weights["delta_bias"].to(self.device)
        expected = (self.max_choices, self.model.config.hidden_size)
        if tuple(self.delta_weight.shape) != expected or tuple(self.delta_bias.shape) != (self.max_choices,):
            raise ValueError("invalid residual head dimensions")
        self.temperature = float(c["temperature"]) if use_temperature else 1.0
        if not math.isfinite(self.temperature) or self.temperature <= 0:
            raise ValueError("temperature must be finite and positive")
        self.temperature_applied = use_temperature
        self.model.requires_grad_(False)

    def generate(self, question, format="token"):
        raise NotImplementedError("the residual head returns decisions only; use MiniJev for baseline text generation")

    @torch.inference_mode()
    def decide_many(self, questions, projection="selected"):
        if projection != "selected":
            raise ValueError("the residual head supports selected projection only")
        if not questions:
            return []
        started = time.perf_counter()
        prepared = [self._prepare(q) for q in questions]
        if any(len(options) > self.max_choices for options, _ in prepared):
            raise ValueError(f"this trained head supports at most {self.max_choices} choices")
        inputs = self._batch([ids for _, ids in prepared])
        self.synchronize()
        model_started = time.perf_counter()
        hidden = self.model.base_model(**inputs, use_cache=False, return_dict=True).last_hidden_state[:, -1, :]
        _, weight, bias = self._head(self.max_choices)
        baseline = torch.nn.functional.linear(hidden, weight, bias).float()
        correction = torch.nn.functional.linear(normalize_hidden(hidden), self.delta_weight, self.delta_bias)
        logits = (baseline + correction) / self.temperature
        results = []
        for i, (q, (options, ids)) in enumerate(zip(questions, prepared)):
            count = len(options)
            probabilities = logits[i, :count].softmax(-1).cpu().tolist()
            keys = [k for k, _ in options]
            answer = typed_answer(q["type"], keys, probabilities)
            answer.update(candidate_keys=keys, candidate_logits=logits[i, :count].cpu().tolist(),
                          candidate_mass=None, input_tokens=len(ids), output_tokens=0,
                          projection="residual_head", batch_size=len(questions),
                          temperature=self.temperature,
                          temperature_calibration_applied=self.temperature_applied,
                          calibration_method="temperature_scaling_synthetic_holdout" if self.temperature_applied else None,
                          calibration_generalization_validated=False)
            results.append(answer)
        self.synchronize()
        for answer in results:
            answer.update(model_ms=(time.perf_counter()-model_started)*1000,
                          latency_ms=(time.perf_counter()-started)*1000)
        return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--head", type=Path, required=True)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--device", default="auto")
    parser.add_argument("--without-temperature", action="store_true")
    args = parser.parse_args()
    engine = HeadMiniJev(args.head, device=args.device, use_temperature=not args.without_temperature)
    data = json.loads(args.input.read_text())
    out = engine.decide_many(data if isinstance(data, list) else [data])
    print(json.dumps(out if isinstance(data, list) else out[0], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
