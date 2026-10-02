# Portable diagnostic A/B replay

This package supports CPU-only reanalysis of saved candidate logits/probabilities using Python 3.10 or newer and its standard library. It does not load a model, install Torch, run inference, contact a server or reconstruct benchmark text.

## Recompute the published result

The completed study and its negative/null findings are in [the Japanese report](REPORT.ja.md). From a fresh repository checkout:

```sh
python paper/naacl2027/diagnostic_value_20261003/publication/bundle_v1/replay.py --verify-only
python paper/naacl2027/diagnostic_value_20261003/publication/bundle_v1/replay.py --out /tmp/logittrail-diagnostic-replay.json
```

Use a new output filename. This recomputes all eight error-detection scores and all four policies at five budgets for both checkpoints, comparing them with the retained numerical result. It requires no private source files. The original analysis and an independent raw-logit reconstruction agree: neither primary comparison establishes additional value from order-TV information.

## Author-side bundle construction

The commands below require the original local study and are provided to document packaging. They are not prerequisites for the public replay above.

From the repository root, after both model receipts and the original analysis are complete:

```sh
python paper/naacl2027/diagnostic_value_20261003/publication/build_bundle.py \
  --study paper/naacl2027/diagnostic_value_20261003/confirmation/study_v1 \
  --analysis PATH_TO_ORIGINAL_ANALYSIS_DIRECTORY \
  --out PATH_TO_NEW_PUBLIC_BUNDLE
python PATH_TO_NEW_PUBLIC_BUNDLE/replay.py --verify-only
python PATH_TO_NEW_PUBLIC_BUNDLE/replay.py --out PATH_TO_NEW_REPLAY_RESULT.json
```

The output directory and replay result must not already exist. An optional `--allow-pending` build without `--analysis` produces a clearly marked preparation snapshot. Its numerical replay is refused. A missing or incomplete model is never replaced, silently retried, or represented as completed; no results are invented. Build a new directory when the study completes.

## Frozen source and derivative provenance

`frozen/confirmation/analyze.py` and `frozen/exploratory/analyze.py` retain their exact pre-inference bytes. The original protocol and exploratory metric specification are copied unchanged. Their hashes must match the original local freeze; the protocol, analysis and helper also match the independent source audit.

The portable entry point calls `verify_schedule`, `records_from_rows`, `analyze_a` and `analyze_b` from that copied module. It does **not** call the original `main`, whose original-path checks cannot run after relocation. This builder and wrapper were written after inference started and are explicitly **not** pre-inference-frozen code. They do not alter the frozen analysis functions.

Original absolute paths in JSON keys and values are replaced by `{REPOSITORY}`, `{WORKSPACE}`, `{HOME}`, or an opaque `{ABSOLUTE_PATH_SHA256}` identifier. Original byte SHA256 values are retained alongside published derivative SHA256 values. Original receipts still reference the original private prediction-file bytes; the manifest separately identifies the allowlisted public prediction bytes. Removed prediction fields are enumerated. These two sets of hashes must not be confused.

The replay checks published byte hashes, source/freeze/audit links, schedule identity, selection identity, complete model receipts, model closure, measured and excluded call counts, original prediction witnesses, per-row physical call counters, and identical model panels. It compares the reanalysis with the original `RESULTS.json` numerical models object. Identities, structure and integers must match exactly; finite floats must differ by at most 1e-12. Exact equality and the largest difference are also reported. Original result bytes and the sanitized reference each have separate hashes.

Hashes are integrity witnesses, not signatures, third-party timestamps or independent proof that private original bytes were collected as claimed. An independent reviewer can reproduce the saved-record arithmetic, but cannot reconstruct omitted original bytes from their hashes.

## Data and cost interpretation

The intended completed experiment has **240 shared questions**, evaluated by two Qwen checkpoints, with five fixed cyclic display-order members per question: **1,200 measured calls per model and 2,400 total**, not 480 independent questions. This is project-unused JCommonsenseQA validation material selected by a frozen hash rule from 517 eligible questions. Source pin and IDs are included. Raw text is omitted; the upstream JGLUE dataset and its CC BY-SA 4.0 license remain the source of benchmark content. Option-index gold labels are retained solely for metric calculation.

A uses the first one or two logical members to diagnose error; the primary target is the error of the two-call mean prediction. Its primary AP contrast compares the entropy+TV rank score with the pair-mean entropy score, both using two calls. B is a retrospective batch-policy replay: first-only policies pay one initial member, pair policies pay two, and selected items complete all five. The reported policy budget pays the union of selected physical members; collecting the experiment nevertheless paid the full five-member pool. Synthetic parity and warmup calls are separately recorded in completion receipts and are not measured benchmark calls.

The physical schedule was shuffled; logical policy members remain replicas 0, then 1, then 2–4. No gold labels or later-member output enter the gate. Scores use outcome-free cohort midranks. A's percentile intervals condition on those cohort ranks; B's paired bootstrap conditions on the realized fixed allocation and does not reallocate in resamples. They are descriptive, unadjusted 95% intervals, not a significance-based winner declaration. All scores, budgets, models, null results and negative results are retained.

This is neither an online scheduler timing experiment nor an independent replication, human study or publicly preregistered trial. Recorded serial latency sums are bookkeeping, not causal wall-time speedups. Old exploratory outcomes informed the locally timestamped design. Project-unused exact IDs/question hashes do not establish absence from model pretraining or semantic independence. Scope is one Japanese five-choice task, two related Qwen checkpoints and one Mac. An incomplete secondary checkpoint must remain explicitly incomplete.

Raw benchmark text, original token IDs (including candidate IDs), model weights, binaries, native logs, credentials and private path mappings are not part of the bundle. Fixed candidate letters, semantic option IDs, hash witnesses, option-index gold labels, logits, probabilities and necessary scoring metadata remain.
