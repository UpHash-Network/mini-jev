# Train a small decision head on your own data

This workflow trains a **candidate-position bias or linear residual head on a frozen Qwen2/Qwen2.5 causal language model**. It compares both with the unchanged model, fits one temperature per condition, and evaluates a held-out test split. The training pathway is experimental: it does not reproduce the 35B GGUF native release, and better accuracy is not guaranteed. The earlier head experiment decreased accuracy on its independent test.

The supported architecture guard is `model_type == "qwen2"`. Other architectures, LoRA, full-model fine-tuning, GGUF adapter export, and deployment of these heads through the native HTTP service are not implemented. All three answer types use the original Japanese decision prompt and A–Z labels. This is a separate experiment from the native release's repeated-input/numeric-Score prompt.

## Install

Use Python 3.10 or newer and a virtual environment. The repository's PyTorch requirements are separate from the standard-library-only native service:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
```

`validate` requires only the Python standard library. Training and inference require PyTorch, Transformers, and safetensors. See `requirements.lock.txt` for the original tested environment; a different environment is recorded in new checkpoints. Do not run multiple large model experiments concurrently on a memory-limited machine.

## Data format

Provide **four explicit, nonempty JSONL files**: `train`, `dev`, `calibration`, and `test`. One labeled object per line:

```json
{"id":"ticket-001","type":"choice","state":{"text":"Please cancel my subscription"},"instructions":"Which action is requested?","criteria":{"cancel":"Cancel subscription","keep":"Keep subscription"},"label":"cancel","group":"conversation-001","family":"subscription-action"}
```

Required fields are `id`, `type`, `state`, `instructions`, `criteria`, and `label`. Optional fields are `group` and `family`; unknown fields are rejected. `state` may be any finite JSON value. Candidate descriptions and instructions must be nonempty strings. A record is limited to 1 MiB and state nesting to 32 levels.

| Type | Criteria | Label |
|---|---|---|
| `choice` | Object of 2–26 semantic keys and descriptions | One string key from that object |
| `noul` | Object with exactly `false` and `true` keys | JSON boolean or the string `false`/`true` |
| `score` | Ordered array of 2–26 stage descriptions | Integer, zero-based stage index |

Set `--max-candidates` to the largest candidate count you want the head to handle (default 6; allowed 2–26). Score labels are discrete ordinal stages; the output score is their probability-weighted mean. Arbitrary continuous regression labels are not supported.

The split audit rejects:

- Duplicate IDs, including within one file.
- Duplicate normalized inputs, ignoring labels/IDs, Choice map order, object key order, Unicode compatibility differences, and repeated whitespace. Score stage order remains significant.
- Cross-split `group` or `family` reuse when requested with `--disjoint-groups group`, `family`, or `both`. Every record must contain each requested field. Reuse within a split is allowed.
- Duplicate JSON keys, non-finite numbers, invalid labels, unknown fields, invalid Unicode, and excessive candidate counts.

**The input audit does not recognize arbitrary paraphrases or verify the truth of group tags.** Keep all examples from the same conversation/source/entity together. For research, also reserve whole task families and audit semantic overlap independently. The bundled toy fixture intentionally shares templates and is only an execution smoke test; `--disjoint-groups family` correctly rejects it.

## Validate before loading a model

```sh
python training_cli.py validate \
  --train examples/training/train.jsonl \
  --dev examples/training/dev.jsonl \
  --calibration examples/training/calibration.jsonl \
  --test examples/training/test.jsonl \
  --max-candidates 3 --disjoint-groups group
```

The same validation runs at the start of training, before any model loading or download. Token-length and label-token boundary checks require a tokenizer and run during extraction. Inputs exceeding `--max-input-tokens` fail; they are not truncated.

## Train and evaluate once

This small example uses a pinned Qwen2.5-0.5B-Instruct revision. Omit `--allow-download` if the exact revision is already in your Hugging Face cache.

```sh
python training_cli.py train \
  --model Qwen/Qwen2.5-0.5B-Instruct \
  --revision 7ae557604adf67be50417f59c2c2f167def9a775 \
  --device auto --dtype float32 --seed 42 \
  --train examples/training/train.jsonl \
  --dev examples/training/dev.jsonl \
  --calibration examples/training/calibration.jsonl \
  --test examples/training/test.jsonl \
  --max-candidates 3 --disjoint-groups group \
  --epochs 10 --learning-rates 0.001 --penalties 0.01 \
  --batch-size 2 --max-input-tokens 512 \
  --output .runs/toy-001 --allow-download
```

Replace the four paths with your data, select a compatible Qwen2/Qwen2.5 model ID and its full 40-character commit SHA, and choose `cpu`, `mps`, `cuda`, or `auto`. Precision choices are `float32`, `float16`, and `bfloat16`; hardware/backend support is required. The smoke verification uses float32. Other model sizes and precisions need their own quality/numerical validation.

The default hyperparameter grid is learning rates `0.001,0.003` and correction penalties `0.01,0.1`, with 120 epochs. Change them before reading test results. Epoch zero is included as an identity fallback. The three controls always run:

1. `baseline`: no trainable parameters.
2. `bias`: one trainable bias per candidate position.
3. `residual`: a linear correction from RMS-normalized final hidden state, plus bias.

The backbone and original language-model head stay frozen. The correction is `base_logits + W × normalized_hidden + b`, masked to the number of candidates in each question. Only the residual/bias is optimized, on CPU cached features, using full-batch AdamW and a squared-correction penalty. A–Z are positions, so the learned head can acquire position biases. Include order-robustness evaluation before deployment; this workflow does not canonicalize Choice keys or automatically augment permutations.

**Selection boundaries:** train fits parameters; dev NLL selects the epoch and hyperparameters; calibration NLL selects temperature in `[0.1, 10]`; test reports final metrics only. All files, including test labels, are read initially for schema/leak checks. Test features and metrics are computed only after the weights and temperatures have been saved and reloaded. Keep the test unchanged and do not choose a winning control or alter training based on repeated test results; use a new independent final test if you do.

A seed is mandatory and recorded. The current head optimizer uses zero initialization and full batches, with no random sample order, dropout, or random projection. **Changing the seed alone is not an independent stochastic training trial.** Floating-point results can still differ across backends and environments.

## Artifacts and reproducibility

A run writes:

- `data_audit.json`: file/content hashes, record counts, IDs, normalized-input hashes, split policy.
- `checkpoint/config.json`: pinned model/revision, actual device/dtype, runtime/package/build details, tokenizer/prompt/source hashes, candidate mapping, selected settings, scalar temperatures, data audit, weight checksums.
- `checkpoint/{baseline,bias,residual}.safetensors`: CPU float32 correction tensors. Reload requires exact source-code fingerprints and valid weight checksums/shapes.
- `report.json`: dev/calibration/test metrics and per-case predictions for all three controls with and without temperature, selection histories, cache provenance, exact checkpoint-reload check, and post-test immutability check.
- `feature-cache/`: hidden-state and baseline-logit tensors. Features include labels/targets and must be treated as private data if your source data are private.

Run and evaluation destinations **must not already exist**. Failed runs remain for inspection; choose a fresh directory to retry. `--cache PATH` can reuse a cache in the same environment. Cache identity includes order-sensitive input records, model commit, device, dtype, Python/OS, package/build details, attention implementation, tokenizer, batch size, token limit, and source hashes; checksums and tensor validation guard against stale/corrupt files. Use one writer per cache directory. A runtime change creates different feature keys.

The script records seed and numerical provenance; it does not promise bit-for-bit reproducibility across operating systems or accelerators. Source/config checksums provide audit linkage, not a cryptographic signature against an attacker who can rewrite all artifacts. Model weights are loaded from the pinned Hugging Face revision and not redistributed in checkpoints.

## Reload on labeled held-out data

```sh
python training_cli.py evaluate \
  --checkpoint .runs/toy-001/checkpoint \
  --test examples/training/test.jsonl \
  --output .runs/toy-001-reloaded
```

The original test can be replayed. Additional test data must not overlap train/dev/calibration under the saved audit policy. Evaluation cannot update weights or temperatures. It loads the recorded model/dtype/device and requires identical runtime provenance by default. To explicitly test a different device, use, for example, `--device cpu --allow-runtime-change`; the result records the mismatch and does not claim temperature portability or equivalent probabilities. Changing source code requires keeping/reusing the original source revision for that checkpoint.

## Use a checkpoint without gold labels

```sh
python training_cli.py predict \
  --checkpoint .runs/toy-001/checkpoint \
  --input examples/training/predict.json \
  --control residual --output .runs/toy-001-predictions
```

Prediction input is one JSON question object or an array, with exactly `type`, `state`, `instructions`, and `criteria`. No label is required or accepted. It writes `predictions.json` containing typed answers and provenance. Choose `--control baseline` or `bias` to inspect those controls, or `--without-temperature` to disable temperature scaling. This CLI can use cached features; it is not a latency benchmark or HTTP server.

Probabilities are **conditional on the allowed candidate-label tokens**, not calibrated correctness probabilities. Temperature calibration can improve NLL and worsen ECE or Score MAE; the report includes those metrics and does not hide that tradeoff. No external/generalization calibration claim is made.

## Tests

```sh
python -m unittest discover -s tests -p 'test_training*.py' -v
```

CPU tests use artificial features for optimization and verify schema failures before ML imports, leakage detection, cache identities/tamper detection, controls, checkpoint save/reload, and the test-selection boundary. The bundled 30-record toy run is a separate real-model smoke test, not an accuracy benchmark.

## Release verification

The pinned 0.5B example completed real feature extraction/training/calibration on Apple M5 Pro (MPS, float32). A separate process reloaded the checkpoint and reproduced all six-control test predictions/metrics exactly. Unlabeled prediction completed for three questions. CPU reload/evaluation also completed with the runtime-change flag and was correctly recorded as a different environment; numerical equivalence is not claimed. CUDA was not tested. The 12/6/6/6 toy split is only an execution check. See [verification receipt](publication/VALIDATION.json).
