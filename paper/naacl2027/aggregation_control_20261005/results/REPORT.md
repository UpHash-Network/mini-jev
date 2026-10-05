# Post-hoc fixed-binding aggregation control

**Exploratory, already-seen saved panel; no new inference.** This is an aggregation-only control, not an AnyJev reproduction. The same five physical responses, fixed token-to-option binding, candidate sets, temperature and prompts are used by both five-member methods. Geometric averaging adds no token reassignment or prior correction.

The specification in `../PROTOCOL.json` was locally recorded before calculating these new contrasts. The underlying data and original arithmetic results were already seen, so this is not preregistered or unseen confirmation. All four strata are retained separately; the models share 480 distinct questions.

Arithmetic: a(k) = mean_r p_r(k). Normalized geometric: g(k) = exp(mean_r log p_r(k)) / sum_j exp(mean_r log p_r(j)). Stable log-softmax uses saved logits at T=1; the calculation is checked against softmax of mean logits. Labels use the first canonical option in exact ties. First order means frozen replicate 0, independent of the physical execution order.

| Model / dataset | First order | Arithmetic mean, 5 | Geometric mean, 5 | Geometric − arithmetic, pp [95% CI] | G fixes / breaks A | Label disagreements |
|---|---:|---:|---:|---:|---:|---:|
| qwen2.5-1.5b/JCommonsenseQA | 194/240 | 200/240 | 198/240 | -0.83 [-2.50, +0.83] | 1 / 3 | 7 |
| qwen2.5-1.5b/CommonsenseQA | 166/240 | 170/240 | 170/240 | +0.00 [-1.67, +1.67] | 2 / 2 | 5 |
| phi-4-mini/JCommonsenseQA | 204/240 | 205/240 | 202/240 | -1.25 [-2.92, +0.00] | 0 / 3 | 4 |
| phi-4-mini/CommonsenseQA | 180/240 | 174/240 | 178/240 | +1.67 [-0.42, +4.17] | 6 / 2 | 8 |

Both five-member methods reuse 1,200 physical responses per stratum (4,800 total); these shared calls are counted once. First order reuses 240 per stratum. This analysis adds **0 model forwards and 0 model downloads**. Saved token and serial-latency sums in `RESULTS.json` are historical bookkeeping, not newly measured performance or online speedups.

| Model / dataset | Contrast | Accuracy difference, pp [95% CI] | Reference wrong → correct | Reference correct → wrong | Both wrong | Label disagreements |
|---|---|---:|---:|---:|---:|---:|
| qwen2.5-1.5b/JCommonsenseQA | geometric_mean5 − arithmetic_mean5 | -0.83 [-2.50, +0.83] | 1 | 3 | 39 | 7 |
| qwen2.5-1.5b/JCommonsenseQA | arithmetic_mean5 − first_order | +2.50 [-0.42, +5.42] | 10 | 4 | 36 | 18 |
| qwen2.5-1.5b/JCommonsenseQA | geometric_mean5 − first_order | +1.67 [-1.25, +4.58] | 8 | 4 | 38 | 20 |
| qwen2.5-1.5b/CommonsenseQA | geometric_mean5 − arithmetic_mean5 | +0.00 [-1.67, +1.67] | 2 | 2 | 68 | 5 |
| qwen2.5-1.5b/CommonsenseQA | arithmetic_mean5 − first_order | +1.67 [-2.92, +6.25] | 17 | 13 | 57 | 34 |
| qwen2.5-1.5b/CommonsenseQA | geometric_mean5 − first_order | +1.67 [-2.50, +6.25] | 17 | 13 | 57 | 33 |
| phi-4-mini/JCommonsenseQA | geometric_mean5 − arithmetic_mean5 | -1.25 [-2.92, +0.00] | 0 | 3 | 35 | 4 |
| phi-4-mini/JCommonsenseQA | arithmetic_mean5 − first_order | +0.42 [-2.08, +2.92] | 6 | 5 | 30 | 16 |
| phi-4-mini/JCommonsenseQA | geometric_mean5 − first_order | -0.83 [-3.75, +2.08] | 5 | 7 | 31 | 18 |
| phi-4-mini/CommonsenseQA | geometric_mean5 − arithmetic_mean5 | +1.67 [-0.42, +4.17] | 6 | 2 | 60 | 8 |
| phi-4-mini/CommonsenseQA | arithmetic_mean5 − first_order | -2.50 [-5.83, +0.83] | 6 | 12 | 54 | 24 |
| phi-4-mini/CommonsenseQA | geometric_mean5 − first_order | -0.83 [-4.17, +2.50] | 8 | 10 | 52 | 24 |

Intervals are 10,000 paired whole-question percentile bootstrap draws within each stratum, with fixed predictions and common question indices across methods. They are exploratory and unadjusted across contrasts and strata. They do not support a multiplicity-adjusted winner declaration or a population equivalence claim. No questions, methods or strata were selected using these results.

This control isolates the aggregation operation only. It does not test permutation-dependent token bindings, content-free priors or complete external systems. The two tasks are different public validation datasets, the model sizes differ, and collection used one machine. It supplies no independent participant evidence, causal language comparison, calibration validation or universal utility claim.

Input hashes and relative source paths: `../INPUTS.json`. Locally recorded analysis and code hashes: `../FREEZE.json`. Full method accuracies, all three paired contrasts, probability-change diagnostics, saved costs and numerical identity checks: `RESULTS.json`. Every item prediction, distribution and physical-member reference: `records.jsonl`.
