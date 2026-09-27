# Additional diagnosis of the saved LMQL comparison

2026-09-27. Post-hoc arithmetic reanalysis, with zero new inference calls and zero human participants. The frozen run, its tolerances, and its historical audit remain unchanged.

**All 12 argmax decisions agree, but three probability-tolerance failures remain.** This is neither exact framework equivalence nor evidence about decisions near a boundary.

|Failed case|Probability L-infinity error|Native top-two probability margin|LMQL top-two probability margin|Shared argmax|Score expectation error|
|---|---:|---:|---:|---:|---:|
|score-01|2.43458463e-5|0.97991772|0.97988456|4|5.61503454e-5|
|score-03|2.00471710e-5|0.98971216|0.98968674|3|1.32391280e-5|
|score-04|2.63258882e-5|0.99067197|0.99063545|5|7.18139334e-5|

The prespecified probability tolerance of 1e-5 passes in 9/12 cases; the Noul/Score value tolerance of 1e-4 passes in 8/8 applicable cases. Agreement within tolerance does not mean identical numeric values.

## What the saved evidence establishes

All native top probabilities exceed 0.9845 and all top-two probability margins exceed 0.9799. Each margin exceeds twice the observed maximum coordinate-wise probability difference, so the unchanged argmax follows from the observed perturbation bound. These inputs provide no near-boundary test.

Applying double-precision candidate softmax to the saved LMTP raw logits reproduces LMQL probabilities within 3.63670e-9. Within each case, the vocabulary logsumexp is exactly the same across candidate continuations and cancels under candidate normalization. The observed probability discrepancies can therefore be reproduced almost entirely from the saved native-logit path differences. Saved LMQL scores also exactly equal float32-rounded LMTP log probabilities. That rounding and subsequent normalization alone do not explain the discrepancies exceeding 1e-5. This is an arithmetic decomposition of recorded values, not a new execution of the library internals.

The maximum saved raw-logit difference is 0.0106124878, with nonconstant shifts across candidates. The direct native path decodes a prefix once and reads final-position logits. The custom LMTP path requests logits at every predictive position for each candidate continuation, returns full-vocabulary sequence log probabilities, and passes through unmodified LMQL 0.7.3 scoring. The original run used 12 direct and 52 LMTP decodes. Different native execution paths are confirmed; a specific kernel, precision, or batching cause is not established. These data do not identify a defect in LMQL's normalization formula.

All 12 frozen prompts repeat the entire user task body twice. Choice/Noul/Score use 5/2/6 candidates respectively, and only Score uses the assistant prefix `{"answer":`. Thus task type, candidate count, and prefix are confounded. Failures occurring only in Score do not isolate a Score-specific cause. Exact prefix equality preserves the internal comparison, but the result should not be generalized to ordinary single-body prompts, boundary cases, multiple-token candidates, stock LMQL backends, speed, or human usability.

Any future causal investigation should preserve this failed run and prespecify a separate study that controls final-position versus all-position extraction, repeats the same prefixes, holds candidate count and prefix constant, and includes close decisions. No such new study was run here.

## Reproduction and source evidence

From the repository root:

```sh
python3 paper/naacl2027/nonhuman_revision_20260927/lmql_diagnostic/analyze.py
```

[DIAGNOSTIC.json](DIAGNOSTIC.json) contains all 12 cases and 52 candidate-level deltas, typed values, margins, and source hashes. The standard-library script imports neither LMQL nor a model, verifies the saved receipt and relevant frozen source hashes, and checks that its evidence files remain unchanged. It does not rehash the original model weights or runtime environment.

Sources: [saved trace](../../comparator_study/run_v1/results.jsonl), [freeze](../../comparator_study/FREEZE.json), [protocol](../../comparator_study/PROTOCOL.ja.md), [native helper](../../comparator_study/llama_lmql_helper.cpp) lines 223–260 and 309–335, [runner](../../comparator_study/run.py) lines 32–45 and 68–98, and [case generator](../../comparator_study/make_cases.py).
