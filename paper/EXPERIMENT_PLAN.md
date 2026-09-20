# Follow-up study protocol (planned, not completed)

Research question: when an open causal language model is used as a typed decision function, how do readout, lightweight training, and output generation affect task accuracy, latency, and probability quality?

This protocol describes future work. The current release does not claim these comparisons have been run.

## Matched comparisons

Hold model revision, quantization/precision, input content, candidate semantics, device, and warm/cold policy fixed. Compare candidate-logit readout, one-token constrained generation, and constrained JSON generation. Report total input tokens and complete request latency, including JSON generation/parsing; measure unconstrained generation only as a separately named baseline.

Run ablations for single versus repeated input, letter versus numeric ordinal labels, and temperature scaling. Do not attribute effects of changing model size to changing the readout. A constrained one-token generator may have little additional cost over reading its logits; this is an empirical question.

## Data and separation

Use an external public benchmark appropriate to the three decision types and a new task-family holdout with human label audit. Document provenance, rights, language, candidate counts, and annotation disagreements. Split by semantic group/family before generating variants. Treat the released 2,400 items as a public regression set once anyone uses them to tune a model.

Select hyperparameters on development data, fit temperature on a distinct calibration split, and freeze both before opening the new final test results. Record a manifest before evaluation. A failed test that guides another iteration becomes development evidence; it cannot remain the same untouched final test.

## Lightweight training

Use frozen readout, label bias, and residual linear head as controls. Vary training data quantity on the same split definitions. Add adapter training only as a separately specified extension. The current full-batch, zero-initialized head optimizer is deterministic under its recorded conditions; changing an unused random seed alone does not create independent trials. For replication uncertainty, vary actual data splits or introduce and document a stochastic training procedure.

Test at least two supported backbone sizes, and add a second model family only after validating its actual logit transformation and tokenizer boundary behavior. Report all attempted conditions and failed runs, not only the selected model.

## Measurements and claims

Report per-type and per-family accuracy, ordinal expected-value MAE, NLL, multiclass Brier score, reliability diagrams, ECE with its binning definition, and risk versus coverage when abstaining. Include candidate-set probability mass where available; entropy-derived confidence is not correctness probability.

Report paired differences with uncertainty. Because generated questions share families, include family-level resampling in addition to item-level resampling and disclose the clustering assumption. For latency, report complete input length, batch size, concurrent load, p50/p95, cold start, memory, and the exact device/backend. Never divide a batched request latency by its item count and call it single-request latency.

## Submission decision

Use the resulting evidence to decide whether a methods paper, empirical workshop paper, or systems demonstration is supported. An engineering release and technical note remain useful even if no proposed training method beats the frozen baseline. Do not describe the work as peer reviewed or as a reproduction of Jev/RLCD without corresponding evidence.
