# Next controlled study: protocol draft

Status: designed after inspecting the published local suite and its retrospective analysis. This is **not** a preregistration of those results. Before new confirmatory inference, freeze a completed configuration and input manifest with hashes and archive the timestamped protocol. The external JNLI pilot has its own earlier, before-inference local manifest; do not retroactively call this document its registration.

## Research question and falsifiable expectations

For a fixed open model and input representation, what changes when the output is read as a candidate distribution, sampled as a single constrained token, or generated as structured JSON? Does lightweight output adaptation improve performance on task families excluded from training, and does calibration transfer?

The matched one-token condition is expected to have the same candidate distribution and greedy accuracy as direct readout. A large discrepancy is a protocol or implementation finding to investigate, not an expected algorithmic advantage. A residual head may help, do nothing, or worsen performance; record all outcomes.

## A. Matched readout and systems experiment

Use the same pinned GGUF, llama.cpp revision, native package, device, threads, context capacity, candidate-token mapping, and complete tokenized prefix for two primary conditions:

1. Direct readout: gather permitted logits, stable softmax, construct the typed return.
2. Single-token masked decoding: mask every disallowed token, apply the same temperature, greedy selection with the same tie rule, and stop immediately after selecting the label. Do not append an unnecessary forward pass to generate EOS.

Instrument the first completed prefill through delivery of the typed response. Verify allowed-token distributions within explicit numeric tolerance and exact semantic labels before measuring speed. Include both engine time and complete loopback request time; report schema validation and serialization separately if instrumented. A sampled label is not the same output as a probability vector or ordinal expectation: return the same vector in a separate parity condition if comparing equal functionality.

A third condition generates grammar-constrained JSON. State the output schema, stopping rule, max output tokens, sampler, and whether probabilities are requested. Use the same state and instructions; any serialization-specific prompt changes and token-budget differences must be disclosed. Compare label accuracy and valid-response fraction; generated self-reported probabilities are not the model's candidate softmax and must not be compared as if they were the same quantity.

Randomize condition order within each input using a fixed seed. Run five measured repetitions per item after seven explicit warm-ups per loaded runtime; retain every timing and failure. Repetitions assess run variability, not new independent semantic data. Use no concurrent GPU workload. Keep prompt caches disabled or explicitly reset for the primary condition. Separate cold process startup from warm inference and disclose OS file-cache state. Report p50/p95 with complete-input length, batch size 1, request question count, concurrency, memory, and all exclusions.

Predeclare primary systems estimand as paired median complete-request latency difference, with request/family-level resampling that keeps each item's repetitions and conditions together. Report p95 and per-token-bin distributions descriptively. Runtime errors are counted and diagnosed rather than silently dropped. No minimum speedup is assumed.

## B. Data and generalization

Keep the existing 2,400 questions and the inspected 300-item JNLI pilot as development/regression material for subsequent design decisions. Do not tune on them and continue calling them untouched final tests.

For a fresh study, define all splits by source family or semantic group before generating variants. Cover Choice, binary decisions, and genuinely ordered labels, using external datasets with verified rights and task semantics. Record training-corpus contamination as unknown where it cannot be ruled out. Use source-group identifiers (for example shared captions or premises) to avoid leakage and preserve clustering in uncertainty analyses.

Commission an independent human audit with a written rubric and adjudication process if a claim depends on newly authored labels. AI-agent review does not satisfy this gate. No claim that this audit has already happened is permitted. Select final sample sizes from a stated minimally relevant paired accuracy difference and development-estimated disagreement rate, or from a desired interval width. The current 300-item pilot is a feasibility sample, not a powered confirmatory design. Freeze exact counts before opening new outcomes.

## C. Prompt and label ablations

Under fixed model and data, compare one versus two copies of the same task, letter versus numeric labels for supported ordinal sets, and displayed-option permutations. Record full input lengths. Canonicalized dictionary reversal is a separate API consistency test, not a displayed-order ablation. Semantic key renaming can change order and must not be silently conflated with semantic equivalence.

Factor effects should not be attributed to readout if the prompt, model size, or precision also changes. Limit the primary ablation to one predeclared contrast. Treat other contrasts as secondary and use a stated multiplicity procedure for confirmatory testing, or report intervals explicitly as exploratory.

## D. Adaptation and probability utility

Compare frozen logits, learned bias, and residual linear head on at least two actually supported backbones. Match split definitions, candidate semantics, training weights, and data budgets. A zero-initialized full-batch deterministic optimizer produces no independent seed replication merely by changing an unused seed. Use at least five substantively different predefined data-group splits, or specify and validate a stochastic procedure before calling repeated training runs independent.

Choose hyperparameters on development data. Fit temperature on a separate calibration split. Evaluate accuracy and per-family accuracy, NLL, Brier, ECE with 5/10/20 bins as a sensitivity analysis, and expected-stage MAE on untouched tests. Hold the learned temperature fixed for transfer. Report attempted and failed runs. Pair conditions at the item level and resample semantic groups, with the assumptions and limits stated.

Select abstention thresholds using only designated development/calibration data for a predeclared error-cost or risk target. On a fresh test report achieved coverage and error rate with group-aware uncertainty. Do not pick the threshold from a test risk-coverage curve and then claim validated operating risk. If the risk target fails under shift, report that failure directly.

## Submission evidence gates

| Claim | Evidence needed before asserting it |
|---|---|
| Faster than a named generator | Matched timing boundaries and output functionality; complete paired measurements |
| Better prediction from a new method | Appropriate baselines, fresh family-disjoint tests, replicated controls |
| Better calibrated decisions | Predefined metrics and held-out domain transfer; no universal claim from NLL alone |
| Practical typed-decision artifact | Runnable source, licenses, model/runtime pins, valid response checks, disclosed failures |
| Generalized empirical finding | More than one dataset type, backbone, and measurement environment as applicable |

The current draft supports the artifact claim and qualified observations. An empirical workshop or systems demonstration is a plausible format once the core missing comparisons are complete; no venue acceptance, deadline, or novelty guarantee is implied. Final venue choice should be based on the resulting contribution and current official call for papers, rather than adapting claims to a desired title.
