# Two-family Japanese/English diagnostic replication

This package extends the separately frozen [Japanese Qwen confirmation](../../diagnostic_value_20261003/publication/README.md). It uses 240 further JCommonsenseQA items and 240 English CommonsenseQA items, each shared by Qwen2.5-1.5B-Instruct and Phi-4-mini-instruct. Each model evaluates five cyclic display orders with fixed token-to-meaning bindings: 4,800 measured forwards, four distinct model/task strata. It is a same-Mac scope extension, not a causal model-family/language comparison or independent operator replication.

The [full report](REPORT.ja.md) retains the primary Phi-English comparisons, all secondary strata and every prespecified budget. [Machine-readable results](bundle_v1/RESULTS.json) contain both error targets, all eight scores, all policies and paired bootstrap intervals. A question is the resampling unit; 960 model-item observations do not become 960 independent questions.

The extension does **not establish added order-TV value**. All four AP contrasts are negative point estimates with intervals crossing zero. At the primary 720-call budget, entropy+TV and entropy have identical itemwise correctness in each stratum. In the primary Phi-English stratum both return 174/240, versus 180/240 for fixed random and 177/240 for first-call entropy; this does not establish a general winning policy or population equivalence.

[Release checks](CHECKS.json) and a [separately implemented numerical review](INDEPENDENT_NUMERICAL_REVIEW.md) record the validation scope.

## Recompute from a fresh checkout

No model weights, access token, network access, third-party Python package or participant data is needed. Python 3.10+:

```sh
python paper/naacl2027/generality_20261003/publication/bundle_v1/replay.py --verify-only
python paper/naacl2027/generality_20261003/publication/bundle_v1/replay.py --out /tmp/logittrail-generality-replay.json
```

Choose a new output filename. The replay verifies every bundled byte, original code bindings, receipt hashes, all 4,800 scheduled rows, the complete five-member pools, the semantic mapping and softmax arithmetic, then recomputes all four strata. Its output must agree with the retained result within 1e-12; the measured replay delta is recorded with the release checks. Reanalysis is not evidence of a second machine executing the model or an independently observed benefit.

`bundle_v1/code/analysis.py` retains the numerical functions and an inherited historical single-panel CLI. **Use `bundle_v1/replay.py` for the public replay, and `code/analyze_all.py` for a newly executed four-stratum study.** The inherited historical CLI is not the entry point for this experiment. Convenience publication/replay/input-restoration code was written after inference began; the numerical functions and protocol were frozen before benchmark inference.

## Design and retained implementation failure

IDs were selected without labels/outcomes using the fixed selection salt. Japanese selection excludes the prior 840 project-used IDs and two further exact-text matches; 277 were eligible, 240 selected and 37 remain. English source IDs/question texts had no matches in the recorded current-file and reachable-Git audit. These are publicly available validation items, not demonstrably absent from model training. Cross-language semantic overlap is not ruled out.

The first attempt stopped at the synthetic numerical gate before any benchmark call. The original 24-call failure receipt is retained, but its detailed gate was not serialized. A separately dated 48-call synthetic diagnosis found two Phi Choice cases exceeding the pre-existing 1e-5 probability tolerance between the last-position-only head and the stock full-position head. These detailed comparisons are subsequent observations, not a recovered log of the original invocation. No threshold was relaxed. A versioned amendment switches both checkpoints to `logits_to_keep=0`, float32 MPS/eager, with all benchmark items, prompts and analyses unchanged. The new gate measures **full-position repeatability**, not parity with the rejected optimization.

A completed v2 has 28 excluded synthetic/check calls per model. Total accounting is 4,800 measured + 24 original failed-gate + 48 diagnostic + 56 v2 checks = 4,928 forwards. No benchmark row is retried or replaced. Selected policy subsets are logical replay costs from the measured five-call pool; their token/latency sums are not measured online speedups.

The hash manifest distinguishes the original freeze from its path-redacted public projection. Included code, raw candidate observations, schedules, receipts and numerical results are byte-identical. Only private path-bearing provenance is projected or omitted as documented. Hashes are integrity witnesses, not signatures or independent preregistration timestamps.

## Optional actual inference reproduction

This route downloads upstream data/model weights and requires a compatible Apple Silicon Mac; it is distinct from the CPU saved-record replay. The observed environment has 64 GiB unified memory. No minimum-memory or cross-machine inference result is claimed. Dependencies used were torch 2.12.1 and Transformers 4.57.6; the recorded implementation manifest lists the other versions and hashes. `trust_remote_code=False`, stock model classes and safetensors are required.

Acquire the exact two dataset files from the URLs in `bundle_v1/code/SELECTION.json`, retaining their source licenses, **outside the repository**. Restore the selected inputs with pyarrow installed:

```sh
python paper/naacl2027/generality_20261003/publication/bundle_v1/restore_questions.py \
  --japanese-source /private-data/jcqa-valid.json \
  --english-source /private-data/commonsenseqa-validation.parquet \
  --out /private-data/logittrail-generality-inputs
```

The restoration uses the frozen IDs and requires exact source, row and input-file hashes. It does not create a new split or a newly unseen test set. Acquire the two Hugging Face revisions and exact file inventory listed in `code/MODEL_PINS.json` and `code/runtime_source/paper/journal_robustness/cross_model/engine.py`; weights remain in the local Hugging Face cache and are not distributed here. Phi is 3.8B/MIT and Qwen is 1.5B/Apache-2.0; unequal size is a confound.

From the repository root, with the inference environment active:

```sh
python paper/naacl2027/generality_20261003/publication/bundle_v1/code/run.py prepare \
  --questions /private-data/logittrail-generality-inputs/questions-ja.jsonl /private-data/logittrail-generality-inputs/questions-en.jsonl \
  --study /private-data/logittrail-generality-new-run
python paper/naacl2027/generality_20261003/publication/bundle_v1/code/run.py run --model phi-4-mini \
  --questions /private-data/logittrail-generality-inputs/questions-ja.jsonl /private-data/logittrail-generality-inputs/questions-en.jsonl \
  --study /private-data/logittrail-generality-new-run
python paper/naacl2027/generality_20261003/publication/bundle_v1/code/run.py run --model qwen2.5-1.5b \
  --questions /private-data/logittrail-generality-inputs/questions-ja.jsonl /private-data/logittrail-generality-inputs/questions-en.jsonl \
  --study /private-data/logittrail-generality-new-run
python paper/naacl2027/generality_20261003/publication/bundle_v1/code/analyze_all.py \
  --study /private-data/logittrail-generality-new-run --out /private-data/logittrail-generality-new-analysis
```

Do not load the two inference models simultaneously. Preparation freezes the new local source/runtime before inference. A failed gate or measured call is retained and stops that attempt. Repeated execution into an existing output is refused. An independent operator must retain their own environment, attempt/failure receipts and model outputs; this documentation alone is not a completed reproduction.

## Sources and rights

- [JGLUE / JCommonsenseQA](https://github.com/yahoojapan/JGLUE): source revision and attribution are in the selection; applicable Japanese-derived material retains CC BY-SA 4.0.
- [CommonsenseQA](https://huggingface.co/datasets/tau/commonsense_qa): MIT; [Talmor et al., NAACL 2019](https://aclanthology.org/N19-1421/).
- [Phi-4-mini-instruct model card](https://huggingface.co/microsoft/Phi-4-mini-instruct): Microsoft, MIT, exact model/tokenizer revision in the pins.
- [Qwen2.5-1.5B-Instruct model card](https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct): Qwen, Apache-2.0, exact revision in the pins.

No model weights, benchmark question text, full tokenized inputs, participant observations, or private machine paths are bundled. Original project code is MIT; upstream terms remain applicable. A separate formative user-study packet exists locally, with zero human observations.

The descriptive [budget figure](CURVES.png) can be regenerated with Matplotlib 3.10.0 using `plot_curves.py --results bundle_v1/RESULTS.json --out NEW-FIGURE.png` from this directory. It contains no additional measured outcomes.
