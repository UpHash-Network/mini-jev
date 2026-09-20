# Model and decision-adapter card

## Artifact identity

Mini Jev is an inference adapter and experimental training toolkit, not a newly pretrained language model. The measured native configuration uses an unchanged pretrained model plus prompt formatting and temperature scaling.

| Field | Evaluated native configuration |
|---|---|
| Upstream model | `Qwen/Qwen3.6-35B-A3B` |
| Source revision | `995ad96eacd98c81ed38be0c5b274b04031597b0` |
| GGUF repository | `ggml-org/Qwen3.6-35B-A3B-GGUF` |
| GGUF revision | `baec3ebee244827cda0f4557eafa8b28f7545fa6` |
| File | `Qwen3.6-35B-A3B-Q4_K_M.gguf` |
| Size | 20,419,565,568 bytes |
| Model SHA-256 | `671e47e0ec53c665d048b98c3ecbfd5236b5ca9c3e02ed19fc8f81f7b85140c7` |
| Model license | Apache-2.0; retained upstream terms apply |
| Runtime | Pinned llama.cpp, Metal/Accelerate, six threads |
| Prompt style | `repeat_typed_score` |
| Temperature | 1.3489628825916533, fit on 120 separate authored items |
| Additional model training | **None for this final configuration** |

The upstream card describes 35B total and 3B active parameters. Model capabilities, pretraining data, and original model limitations should be assessed from the [upstream card](https://huggingface.co/Qwen/Qwen3.6-35B-A3B). Mini Jev did not audit the upstream training corpus. Weights are downloaded from the pinned upstream artifact rather than redistributed in this repository.

## Inputs, outputs, and intended use

Inputs are a JSON-compatible state, instructions, and a finite candidate schema. Outputs are Choice, Noul, or Score values built by deterministic Python code from permitted token logits. Useful development applications include routing among known categories and checking explicit rules in bounded inputs.

The native helper performs one decode API call per question and no autoregressive answer generation. It computes full-vocabulary logits, then gathers candidates. Multiple questions run sequentially without shared prefill. Inputs above the configured 2,048-token complete prompt limit are rejected. Candidate sets have 2–26 entries; measured semantic quality covers only 2–8 entries.

Choice keys are canonicalized by sorting; Score order is preserved. Score up to ten stages uses digit labels; larger sets use letter labels. All candidate tokens must pass prefix-boundary validation. Different semantic keys, prompts, or candidate descriptions can change results.

## Evaluation and probabilities

On the 2,400-item Japanese project-authored v2 suite, overall top-label accuracy was 93.25%, with Choice 96.00%, Noul 95.25%, and Score 88.50%. The 180 individually AI-authored questions scored 95.56%. The other 2,220 questions share 45 generation templates. There was no independent human annotation study, external benchmark, or family-disjoint evaluation. V2 authoring had access to some earlier v1 failures. See [DATA_CARD.md](DATA_CARD.md).

Warm engine p95 was 379.1 ms for 2,291 complete inputs of at most 512 tokens and 521.8 ms for the remaining 109 inputs. The single measured machine was an Apple M5 Pro, 64 GB, macOS 26.4. These figures are not cold-start or HTTP SLA measurements, and no matched generation baseline establishes a speedup.

Candidate probabilities sum to one because they are normalized over the allowed set. They are not unrestricted vocabulary probabilities or verified probabilities of being correct. `confidence` is an entropy-derived concentration score. Calibration minimized NLL on a separate small split. In final evaluation NLL slightly improved (0.188423 to 0.187871), while ECE worsened (0.014863 to 0.015198) and Score expectation MAE worsened (0.169401 to 0.195121). General calibration under distribution shift is unproven.

Known weaknesses include time-difference calculations, conditional obligations, counts with cancellations, and arithmetic. A type-correct output can still be semantically wrong. The model is not validated for automatic high-stakes decisions, arbitrary languages or domains, or adversarial instructions. There is no claim that the model cannot hallucinate or make errors.

## Separate experimental heads

The historical optional residual head uses frozen `Qwen/Qwen2.5-1.5B-Instruct`, adds 9,222 learned parameters to six candidate positions, and does not alter the backbone. Its held-out 96-item top-label accuracy was 67/96 versus a frozen baseline of 73/96. A six-parameter bias-only variant obtained 74/96. This result is included as a limited negative experiment, not adopted in the final native runtime.

The reusable pipeline in [TRAINING.md](TRAINING.md) lets users test the same kind of small correction on their own splits. Its output is an experimental adapter with its own model/tokenizer/configuration provenance. It is not compatible by assumption with the native 35B path and is not a replication of Jev's RLCD. Training may reduce accuracy; measure against the frozen baseline on new held-out data.

## Reproduction and release boundaries

The evaluated runtime fingerprint is `4d2953166c63f2f1392b661a0331168459ac7cd359638612f37299513a118152`. Public code builds the pinned runtime from source, but compiler and environment differences can produce different files and outputs. Refit temperature and rerun evaluation on a new environment. Do not bypass fingerprint errors to reuse historical calibration.

Public historical logs have local paths redacted. Historical freeze hashes therefore refer to the original artifacts, while publication provenance records transformed public files. Neither the source-only release nor a newly built runtime is represented as a byte-identical distribution of every artifact from the measured run.

Project code and authored data are MIT licensed; upstream code, libraries, and model artifacts retain their own terms. AI coding agents participated in implementation, test authoring, and review under Yuki Oshio's direction. This is an independent project, unaffiliated with TypeSafe or Qwen.
