# External JNLI pilot

This is a zero-shot **Choice-only** natural-language-inference pilot on a balanced subset of the **public JNLI v1.3 development split**. It is not a hidden test, a full JGLUE benchmark run, a Noul/Score validation, or evidence that the base model never saw the examples during training. Pretraining and post-training contamination are unknown.

The completed run scored **243/300 = 81.0% accuracy**, with **0.8101 macro F1**. Contradiction recall was 61%, entailment 87%, and neutral 95%. This is a different task and distribution from the self-authored suite; the two accuracy figures are not a controlled domain-shift comparison.

JNLI is part of [JGLUE](https://github.com/yahoojapan/JGLUE), created by Kentaro Kurihara, Daisuke Kawahara, and Tomohide Shibata through Yahoo Japan Corporation and Kawahara Lab, Waseda University. The task classifies Japanese premise–hypothesis pairs into contradiction, entailment, or neutral. See the [JGLUE paper](https://aclanthology.org/2022.lrec-1.317/) and [official task description at the pinned commit](https://github.com/yahoojapan/JGLUE/tree/6f071c09316baae89c3d083a90985b4b1cb9968c#jnli).

## Fixed procedure

[PROTOCOL.json](PROTOCOL.json) specifies the source SHA-256, sampling rule, complete task instructions and label descriptions, temperatures, metrics, warm-up examples, and failure policy. [PREPARATION.json](PREPARATION.json) captures these and the runner/native-engine hashes **before source rows were parsed or inference began**. This is a locally timestamped freeze record, not a claim of independent preregistration or a public registration made before results existed.

The runner selected 100 examples per class, ordered within class by SHA-256 of a fixed salt and the official sentence-pair ID. It then interleaved all 300 selected examples by that same hash order. There was no source-text, difficulty, result-based, or length filtering, no replacement, and no prompt/temperature tuning on JNLI. The source has 2,434 rows: 735 contradiction, 349 entailment, and 1,350 neutral. The balanced subset therefore **does not preserve the original class prevalence**.

The source sentences are inserted without rewriting or truncation into a fixed Japanese premise/hypothesis state. The unchanged `NativeEngine` uses `repeat_typed_score`, frozen Qwen3.6-35B-A3B Q4_K_M, six threads, Metal, and a 2,048-token input limit. Semantic Choice keys are sorted: **A=contradiction, B=entailment, C=neutral**. Label order was not varied. The runtime repeats the task text and reads candidate logits without generating answer text.

Primary probabilities use **T=1.0**, the uncalibrated runtime default. A prespecified secondary analysis applies the earlier self-authored calibration temperature **T=1.3489628825916533** to exactly the same logits. It does not fit anything on JNLI. Positive temperature scaling preserves the class argmax; accuracy is identical in both analyses. Probabilities are conditional on the three permitted candidate tokens, not guaranteed correctness probabilities.

Three synthetic, non-JNLI warm-up inputs precede the evaluation. Latency covers each serial single-question engine call, including its Python checks, after model startup. Startup is reported separately. These observations do not establish a speedup over generation, HTTP request latency, or an SLA. The run manifest identifies the current source/native artifacts rather than claiming they are byte-identical to the earlier acceptance run.

## Measured results

All 300 selected inputs completed without substitution or truncation. The run used 303 actual decode API calls including the three warm-ups. Raw [prediction records](results/predictions.jsonl), [metrics](results/METRICS.json), and [runtime manifest](results/RUN_MANIFEST.json) are included.

| Metric | T=1.0, primary | Historical T=1.3489628826, no fitting on JNLI |
|---|---:|---:|
| Correct / total | 243 / 300 | 243 / 300 |
| Accuracy | 81.00% | 81.00% |
| Macro F1 | 0.810075 | 0.810075 |
| NLL | 0.548088 | 0.461370 |
| Multiclass Brier, sum over classes | 0.291734 | 0.271941 |
| ECE, 10 equal-width bins | 0.129978 | 0.098614 |

The historical temperature improved all three probability metrics on this sample. It was not selected or refitted using these outcomes, and this single pilot does not establish reliable calibration across applications.

The confusion matrix below has gold labels as rows and predictions as columns. **38 of 100 contradiction examples were predicted neutral**, the largest error category. No follow-up prompt adjustment was made to remove those errors.

| Gold / prediction | contradiction | entailment | neutral |
|---|---:|---:|---:|
| contradiction | 61 | 1 | 38 |
| entailment | 1 | 87 | 12 |
| neutral | 1 | 4 | 95 |

On the same Apple M5 Pro / 64 GB / macOS 26.4 host, the warm single-question latency was **297.0 ms p50, 379.7 ms p95, and 393.6 ms maximum**. All complete inputs were 406–476 tokens. Startup, including artifact verification and loading, was 9,968.9 ms; OS file-cache state was not controlled, so this is not a cold-start benchmark. The actual runtime fingerprint is `4a18dfa35c8935d8582fdae1eb39455c1533d388e75ff58b14b33b46ee4de875`.

## Correlation and scope

The selected sample has 300 distinct pair IDs, 300 distinct exact sentence pairs, and 300 distinct full caption-pair IDs. However, its 600 sentence occurrences contain only 536 distinct sentence strings: 57 strings repeat, producing 64 occurrences beyond the first. **77 of the 300 examples share at least one exact sentence with another selected example.** There are 292 distinct premises and 292 distinct hypotheses. Shared image origins or near-duplicate content can create further dependence; unique pair IDs do not establish independence. We therefore do not attach an IID binomial confidence interval or call these 300 independent tasks.

The frozen runner's `rows_with_any_shared_sentence` field is 84: its occurrence-based definition also includes seven rows whose premise and hypothesis are identical within that row. The later [audit](AUDIT.json) distinguishes this from the 77 rows sharing text **across different examples**. It preserves the original run artifacts and changes no selection, prompt, prediction, or accuracy value. The [audit script](audit_pilot.py) verifies source hashes, selected row references, gold labels, prediction accounting, and absence of source sentences in public artifacts.

This pilot adds an externally authored data source to the self-authored Japanese evaluation. It does not establish broad domain generalization, novelty, leaderboard standing, or equivalence to TypeSafe Jev. The stratified sample and fixed local prompting setup are not directly comparable with published full-dev results from task-fine-tuned systems.

## Reproduction

Use the Python environment and pinned native build described in the [main README](../../README.md). No dataset/model download or GPU call is required for the four fixture tests:

```bash
python3 -m unittest discover -s paper/external_pilot -p test_pilot.py -v
```

From the repository root, choose a raw-data cache **outside the repository**. `curl` uses normal HTTPS certificate verification. The source download must match the pinned SHA-256. Use a new preparation directory for a fresh local freeze receipt; preparation never overwrites existing receipts.

```bash
python3 paper/external_pilot/run_pilot.py prepare \
  --cache-dir /absolute/path/outside-repository/jnli-cache \
  --preparation-dir .runs/jnli-preparation

python3 paper/external_pilot/run_pilot.py run \
  --cache-dir /absolute/path/outside-repository/jnli-cache \
  --preparation-dir .runs/jnli-preparation \
  --output-dir .runs/jnli-results \
  --model-file models/Qwen3.6-35B-A3B-Q4_K_M.gguf \
  --native-binary .build/runtime/bin/llama-decision-helper \
  --native-manifest .build/runtime/BUILD.json
```

The output directory must not already exist. Any changed protocol, runner, engine, source hash, or selected index causes verification to fail. Changes to the native build or host produce a new runtime fingerprint and can affect numerical results and timing; their measured outputs are a new run. A failure preserves partial predictions and must be reported as incomplete, without silently dropping or replacing the affected example.

The published [selection index](SELECTION.json) contains IDs, gold labels, and hashes, **not source sentences**. The row hash covers the original parsed JSON object reserialized with UTF-8, sorted keys, compact separators, and no ASCII escaping. The sentence-pair hash covers the ordered two-sentence array using that same serialization. Individual sentence hashes use their unchanged UTF-8 bytes.

To verify the saved published run after downloading the source, use a fresh output filename:

```bash
python3 paper/external_pilot/audit_pilot.py \
  --cache-dir /absolute/path/outside-repository/jnli-cache \
  --output-file .runs/jnli-audit.json
```

## Data attribution and licensing

The [pinned upstream dataset license](https://github.com/yahoojapan/JGLUE/blob/6f071c09316baae89c3d083a90985b4b1cb9968c/LICENSE) is **CC BY-SA 4.0**. A copy is included as [LICENSE-DATA.txt](LICENSE-DATA.txt). JGLUE/Yahoo Japan Corporation and Kawahara Lab, Waseda University are the original data source; no endorsement is implied.

The original sentence text is downloaded only to the external cache and is not redistributed here. `SELECTION.json`, `AUDIT.json`, prediction records, and dataset-derived metrics in `results/` are shared under **CC BY-SA 4.0**, preserving attribution and indicating the transformations: deterministic subsampling, omission of source text, hashing, fixed prompt formatting, model predictions, and aggregate evaluation. The Python runner and tests are authored project code under the repository's MIT license. The upstream dataset is not relicensed as MIT.

AI agents implemented the harness, checked the fixtures, executed this pilot, and prepared the report under the project owner's direction. These checks are not independent human peer review.
