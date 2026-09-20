# Matched readout and generation study

This v0.2 experiment is **complete**, with all 4,050 scheduled measured requests, 21 warm-up requests, and zero failures. See the [analysis report](REPORT.md), [full metrics](SUMMARY.json), and [independent numerical audit](INDEPENDENT_AUDIT.json). The [protocol](PROTOCOL.json), [local freeze](preparation/FREEZE.json), [selection](preparation/SELECTION.json), and [request schedule](preparation/SCHEDULE.json) describe the design before measured inference. They are locally timestamped records, not independent preregistration. The [completion receipt](results/COMPLETION.json) binds the full prediction file.

The experiment uses one pinned Qwen3.6-35B-A3B Q4_K_M model on one Apple M5 Pro with 64 GB. It compares three modes in a separate research helper and common loopback HTTP harness. It does not modify the released native service or train a model.

## Conditions and measurement

| Mode | Input and output behavior |
|---|---|
| `direct` | Original `repeat_typed_score` input; gather candidate logits, normalize them, and select a label without generating tokens. |
| `one_token` | Identical complete prompt and candidate tokens; mask other vocabulary entries and greedily select one token. Stop immediately, with no EOS request or unnecessary additional forward pass. |
| `json` | Preserve task content and repetition, use the specified JSON-format instruction, and generate a grammar-constrained complete answer object. Stop when the object is complete. |

The JSON prompt differs from the other two modes, including removal of the prefilled Score assistant prefix. That condition is a structured-answer system comparison, not an isolated estimate of sampler overhead. The helper computes the full vocabulary projection. Numeric candidate distributions are audit outputs for direct and one-token modes; JSON generation does not supply the same distribution vector.

Every mode returns the same `type` and semantic `label` schema over HTTP. The client times request JSON serialization through response body read and parsing, using one persistent loopback connection and one request at a time. Native phases are recorded separately. Audit-file writes happen after the timed request; native audit JSON construction and serialization, subprocess-pipe transfer, and Python parsing remain inside the measured interval. These are research-harness measurements with a resident model, not the production service, a remote-network benchmark, or an SLA. A fresh build, host, or runtime creates a new measurement.

Direct/one-token prompt hashes, input-token hashes, candidate IDs, logits, and label agreement are checked as paired conditions. Native tie behavior is recorded. Failures must remain visible with the intended denominator; no difficult, long, or failed example is replaced or silently excluded.

## Selected data and request counts

The local subset has 150 already-public regression questions: three per each of 45 generated families plus five individually AI-authored questions per decision type. The external subset contains 600 public-development examples: JCoLA 200, JSTS 200, and JCommonsenseQA 200. Their [preparation and dependence audit](../external_expanded/README.md) fix IDs, prompts, gold handling, and overlap before inference.

Five repetitions per local question and one per external question, each in three modes, specify `(150 × 5 + 600) × 3 = 4,050` measured **requests**. Another 21 synthetic warm-up requests are excluded. All these requests were retained; repetitions are not additional semantic examples or independent hardware runs. A JSON request can contain several `llama_decode` calls, so native decode counts are reported separately from HTTP requests.

Mode order is randomized within each item/repetition using the fixed recorded seed. The primary systems estimand is the median across local items of their five-repetition mean latency difference, one-token minus direct. Local family/tag resampling describes sensitivity to the observed groups; it does not provide a deployment-population or hardware-population guarantee.

Semantic quality is kept separate by task. JCoLA uses MCC and related classification summaries; JCommonsenseQA uses classification accuracy. JSTS keeps its original continuous reference: direct expected-score MAE is distinct from the all-mode hard-selected-stage MAE. No JSTS categorical gold distribution is invented. The earlier JNLI pilot is separate and has known caption/image connections to JSTS. Four named public datasets do not justify a common accuracy, independence claim, or guarantee that the pretrained model has not seen them.

## Recompute the completed analysis

```sh
python3 paper/matched_study/analyze_study.py
python3 -m unittest discover -s paper/matched_study -p test_matched_analysis.py -v
```

This reads completed traces, makes no model calls, and overwrites only derived summary/report/CSV files. Thirteen statistical fixtures pass, and all seven derived files regenerate byte-identically in the recorded environment.

## Reproduce a fresh run

Run commands from the repository root. Native inference requires the Apple Silicon environment described in the [main README](../../README.md) and [native build guide](../../NATIVE_BUILD.md), including local compiler/CMake tools and the separately downloaded pinned model. The Python study runner uses the standard library. CPU fixture tests do not run the model:

```sh
python3 -m unittest discover -s paper/matched_study -p test_study.py -v
python3 -m unittest discover -s paper/external_expanded -p test_prepare.py -v
```

Choose a new absolute work directory **outside the repository** for raw external data, compiled research artifacts, preparation receipts, and outputs. Replace the example path before running it. Preserve the published protocol, preparation, and results directories.

```sh
jev_repro_work=/absolute/path/outside-repository/mini-jev-study
mkdir -p "$jev_repro_work"

# Build the pinned production runtime and obtain the separate model artifact.
./build_native.sh --work-dir .build/native --output .build/runtime --jobs 2
python3 fetch_native_model.py --output models/Qwen3.6-35B-A3B-Q4_K_M.gguf

# Materialize the frozen external selection without changing public records.
python3 paper/external_expanded/materialize.py \
  --cache-dir "$jev_repro_work/datasets"
python3 paper/external_expanded/prepare.py verify \
  --cache-dir "$jev_repro_work/datasets"

# Compile the separate helper against the verified pinned runtime.
python3 paper/matched_native/build.py \
  --llama-source .build/native/llama.cpp \
  --runtime .build/runtime \
  --output "$jev_repro_work/native"

# Freeze this new build, source, data, selection, and schedule before inference.
python3 paper/matched_study/run_study.py prepare \
  --expanded-questions "$jev_repro_work/datasets/questions.jsonl" \
  --native-binary "$jev_repro_work/native/bin/llama-matched-helper" \
  --output "$jev_repro_work/preparation"

python3 paper/matched_study/run_study.py run \
  --expanded-questions "$jev_repro_work/datasets/questions.jsonl" \
  --native-binary "$jev_repro_work/native/bin/llama-matched-helper" \
  --preparation "$jev_repro_work/preparation" \
  --model-file models/Qwen3.6-35B-A3B-Q4_K_M.gguf \
  --log-file "$jev_repro_work/native.log" \
  --output "$jev_repro_work/results"
```

The native build, preparation, and run output directories must be new. The runner verifies helper build/source/library hashes and the external question-file hash, then refuses changes after preparation. It records the model hash and actual runtime separately. Rebuilt binary bytes need not match the published historical build; use fresh receipts rather than replacing hashes in the old freeze. Keep other inference workloads off the measured device.

Retain incomplete attempts and their diagnostics. An implementation failure requires an explicitly recorded invalidated attempt and a new complete freeze. A result-guided prompt or sampling change becomes development and cannot be presented as the original fixed comparison. Completion requires the complete scheduled records and their audits, not merely the existence of a results directory.

## Record and license boundaries

Original external sentences, questions, and answer options are materialized only in the external cache. Public study records contain IDs, hashes, labels or continuous gold, groups, predictions, numeric traces, and timing; no source question text is intended for redistribution. Model weights, native binaries/libraries, and private machine logs are not included in the source package. The helper's third-party attribution is in [its notice](../matched_native/NOTICE.md).

JGLUE-derived JSTS/JCommonsenseQA records and JCoLA-derived records retain **CC BY-SA 4.0**, with the attribution and license copies in the [expanded-data README](../external_expanded/README.md). Mixed local/external selection and prediction files are distributed with this data license and both dataset attributions. Transformations include fixed subsampling, field selection, hashing, grouping, question formatting, added model predictions, and aggregate metrics. The original project-authored local questions retain MIT.

External task protocols and adapted rubric material retain their CC BY-SA 4.0 attribution when copied or embedded in another record; the JSTS rubric is adapted from official annotation guidance. Project-authored Python/C++ code, fixtures, build/analysis tools, this generic comparison-method protocol, original explanatory prose, and purely synthetic warm-ups remain **MIT** material. Source-dataset terms are not replaced by the repository license. See the [root notice](../../NOTICE.md) for the full attribution boundary. No dataset creator, model publisher, or TypeSafe endorsement is claimed.
