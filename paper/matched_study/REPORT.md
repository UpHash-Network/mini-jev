# Matched readout study: completed-run analysis

This is an analysis of a locally frozen, single-machine experiment. No model is rerun and no prompt, sample, or temperature is selected by this script.

## Main systems result

The primary comparison keeps the complete direct/one-token model prefix and candidate tokens identical. For each of the 150 published local regression items, average complete loopback HTTP latency over its five repetitions, then compute the within-item condition difference. The primary statistic is the median of those 150 item differences, **not** a difference of marginal medians. Positive values mean the comparator is slower.

| Comparator minus direct | Median item-mean HTTP difference | Conditional 95% family/tag percentile interval |
|---|---:|---:|
| one_token_minus_direct_ms | +0.0898 ms | [-0.7483, +0.8449] ms |
| json_minus_direct_ms | +160.2958 ms | [+138.1189, +177.0587] ms |

The bootstrap draws 55 whole observed family/tag clusters with replacement for 10,000 replicates, seed 2026092061. Every selected item and all its repetitions/paired conditions stay together. Clusters are treated as exchangeable; manual AI-authored tags and generated families differ in size. Intervals describe sensitivity to this observed cluster mix, conditional on this model, machine, software, selected items, schedule, and session. They do not capture independent-session, thermal, between-machine, or unmeasured cross-family dependence, and are not hardware-population coverage guarantees.

JSON uses a serialization-specific prompt and actually emits a grammar-constrained JSON object. Its comparison includes prompt/prefill and multi-token-generation differences, not isolated sampling overhead. All three measured HTTP responses carry the same `type` and semantic `label` schema. Native audit serialization, helper-pipe transfer, and Python parsing occur inside the HTTP interval; only the server-side trace-file write occurs after client timing. This comparison therefore includes audit/runtime overhead and is not a pure sampler-overhead measurement.

## Accounting and parity

All 4,050 scheduled requests and 750 unique items are retained; 21 synthetic warm-up requests are excluded from measured latencies. HTTP failures: 0; invalid/failed records: 0; native trace invariant findings: 0. Measured llama_decode API calls: 11,322; warm-up calls: 49.

There are 1,350 paired direct/one-token observations. Maximum candidate-logit absolute difference is 0.0000000000; tolerance is 1e-5. Prompt-hash matches: 1350; token-hash matches: 1350; candidate-ID matches: 1350; label matches: 1350. Exact maximum-logit ties: 0; mismatches with a tie: 0; mismatches without a tie: 0.

Direct uses candidate-order tie breaking; native one-token greedy sampling uses lowest vocabulary-token ID. Ties and any parity violation remain in the data. Detailed pair checks are in `parity.csv`.

## Complete HTTP latency

All scheduled requests, including failures, contribute to these descriptive request-level summaries. Local counts include five repetitions; external counts include one. These marginal p50/p95 values are not the paired primary estimand. Native phase timings, tokens, output tokens, decode counts, and data coverage are in SUMMARY.json and the CSV tables.

| Dataset | Mode | Requests | Mean ms | p50 ms | p95 ms | Output tokens, total | Decode calls, total |
|---|---|---:|---:|---:|---:|---:|---:|
| local_v2 | direct | 750 | 284.137 | 277.309 | 394.283 | 0 | 750 |
| local_v2 | one_token | 750 | 283.929 | 277.396 | 394.912 | 750 | 750 |
| local_v2 | json | 750 | 447.911 | 437.027 | 594.219 | 4655 | 4655 |
| JCoLA | direct | 200 | 275.426 | 281.289 | 315.114 | 0 | 200 |
| JCoLA | one_token | 200 | 275.931 | 282.024 | 313.877 | 200 | 200 |
| JCoLA | json | 200 | 479.311 | 496.045 | 552.605 | 1462 | 1462 |
| JSTS | direct | 200 | 388.357 | 392.992 | 443.999 | 0 | 200 |
| JSTS | one_token | 200 | 388.740 | 393.130 | 437.763 | 200 | 200 |
| JSTS | json | 200 | 580.192 | 583.390 | 650.147 | 1400 | 1400 |
| JCommonsenseQA | direct | 200 | 263.776 | 268.159 | 305.614 | 0 | 200 |
| JCommonsenseQA | one_token | 200 | 263.924 | 268.391 | 302.195 | 200 | 200 |
| JCommonsenseQA | json | 200 | 424.356 | 414.745 | 509.461 | 1105 | 1105 |

## Local quality and repeatability

The 150 local questions are previously published development/regression material, selected by an outcome-independent ID hash. Quality below uses repetition 0 only. Repeated stability is reported separately and does not create 750 independent quality examples.

| Mode | First-repetition correct / 150 | Choice / 50 | Noul / 50 | Score top-stage / 50 | Stable label across 5 repeats |
|---|---:|---:|---:|---:|---:|
| direct | 139 | 46 | 48 | 45 | 150 / 150 |
| one_token | 139 | 46 | 48 | 45 | 150 / 150 |
| json | 140 | 48 | 47 | 45 | 150 / 150 |

## External task-specific quality

The 600 external public-development questions were fixed before inference. Model pretraining/post-training exposure is unknown. These tasks are not pooled into one accuracy. JCoLA domain names refer to original literature-source splits, not verified unseen model domains. JSTS has six rows sharing text/images with the earlier JNLI pilot, including three identical ordered sentence pairs; this overlap was recorded before inference and no examples were replaced. Semantic/source groups are dependence proxies, not proof of independence.

### JCoLA: binary grammatical acceptability

MCC is primary; a zero denominator is reported as null. An always-true rule gets 158/200 = 79% accuracy on the fixed sample (88/100 in-domain and 70/100 out-of-domain), balanced accuracy 0.5, and undefined MCC. It is a descriptive constant baseline, not a fitted system. Confusion matrices, recall/F1, and split-wise results are retained below/in SUMMARY.json.

| Split | Mode | Accuracy | Balanced accuracy | Macro F1 | MCC |
|---|---|---:|---:|---:|---:|
| all | direct | 0.8600 | 0.7803 | 0.7852 | 0.5708 |
| all | one_token | 0.8600 | 0.7803 | 0.7852 | 0.5708 |
| all | json | 0.8200 | 0.7812 | 0.7533 | 0.5160 |
| in_domain_valid | direct | 0.8600 | 0.6686 | 0.6686 | 0.3371 |
| in_domain_valid | one_token | 0.8600 | 0.6686 | 0.6686 | 0.3371 |
| in_domain_valid | json | 0.7900 | 0.6288 | 0.5992 | 0.2134 |
| out_of_domain_valid | direct | 0.8600 | 0.8238 | 0.8300 | 0.6610 |
| out_of_domain_valid | one_token | 0.8600 | 0.8238 | 0.8300 | 0.6610 |
| out_of_domain_valid | json | 0.8500 | 0.8452 | 0.8291 | 0.6634 |

### JCommonsenseQA: five-way choice

| Mode | Correct / 200 | Accuracy | Macro F1 |
|---|---:|---:|---:|
| direct | 190 | 0.9500 | 0.9506 |
| one_token | 190 | 0.9500 | 0.9506 |
| json | 191 | 0.9550 | 0.9556 |

### JSTS: continuous semantic similarity

Original fractional gold scores remain in [0,5]. Primary MAE compares the probability-weighted expected stage with this continuous gold. Native one-token probability audits support the same calculation without another model call. JSON has no comparable probability vector; its expectation/NLL/Brier are deliberately unavailable. The hard-selected stage is compared with the same continuous gold for **all three modes** as a separate like-for-like secondary measure. No rounded gold stage or classification accuracy is invented.

| Mode / prediction | T | Valid / 200 | MAE | RMSE | Pearson | Spearman | MAE / 5 |
|---|---:|---:|---:|---:|---:|---:|---:|
| direct / hard stage | unavailable | 200 | 0.5480 | 0.7465 | 0.9058 | 0.8754 | 0.1096 |
| direct / t1 | 1.000 | 200 | 0.5065 | 0.6688 | 0.9192 | 0.8892 | 0.1013 |
| direct / historical_temperature | 1.349 | 200 | 0.4984 | 0.6550 | 0.9188 | 0.8894 | 0.0997 |
| one_token / hard stage | unavailable | 200 | 0.5480 | 0.7465 | 0.9058 | 0.8754 | 0.1096 |
| one_token / t1 | 1.000 | 200 | 0.5065 | 0.6688 | 0.9192 | 0.8892 | 0.1013 |
| one_token / historical_temperature | 1.349 | 200 | 0.4984 | 0.6550 | 0.9188 | 0.8894 | 0.0997 |
| json / hard stage | unavailable | 200 | 0.5650 | 0.7656 | 0.8996 | 0.8725 | 0.1130 |

Every metric states its valid-prediction coverage. Invalid outputs remain in accounting; numerical regression metrics are conditional on valid predictions, never silently assigned an arbitrary score. Categorical accuracy counts invalid outputs as errors. No external IID confidence intervals or full-benchmark/leaderboard claims are made.

### Probability transfer

Primary T=1 and the historical T=1.3489628825916533 are applied to the same audit logits. The historical scalar was fitted on the earlier self-authored calibration set, never on this external sample. Positive temperature preserves labels; changes below do not establish calibrated probabilities in new domains. NLL uses stable log-sum-exp. Brier sums squared errors over classes; JCoLA also records the binary true-class form. ECE uses ten equal-width maximum-probability bins.

| Dataset / split | Mode | T | NLL | Brier sum | ECE | Coverage |
|---|---|---:|---:|---:|---:|---:|
| JCoLA / all | direct | 1.000 | 0.3491 | 0.2085 | 0.0725 | 1.000 |
| JCoLA / all | direct | 1.349 | 0.3278 | 0.2042 | 0.0518 | 1.000 |
| JCoLA / all | one_token | 1.000 | 0.3491 | 0.2085 | 0.0725 | 1.000 |
| JCoLA / all | one_token | 1.349 | 0.3278 | 0.2042 | 0.0518 | 1.000 |
| JCoLA / in_domain_valid | direct | 1.000 | 0.4174 | 0.2315 | 0.0895 | 1.000 |
| JCoLA / in_domain_valid | direct | 1.349 | 0.3742 | 0.2259 | 0.0649 | 1.000 |
| JCoLA / in_domain_valid | one_token | 1.000 | 0.4174 | 0.2315 | 0.0895 | 1.000 |
| JCoLA / in_domain_valid | one_token | 1.349 | 0.3742 | 0.2259 | 0.0649 | 1.000 |
| JCoLA / out_of_domain_valid | direct | 1.000 | 0.2808 | 0.1855 | 0.0605 | 1.000 |
| JCoLA / out_of_domain_valid | direct | 1.349 | 0.2815 | 0.1825 | 0.0528 | 1.000 |
| JCoLA / out_of_domain_valid | one_token | 1.000 | 0.2808 | 0.1855 | 0.0605 | 1.000 |
| JCoLA / out_of_domain_valid | one_token | 1.349 | 0.2815 | 0.1825 | 0.0528 | 1.000 |
| JCommonsenseQA / all | direct | 1.000 | 0.1324 | 0.0696 | 0.0326 | 1.000 |
| JCommonsenseQA / all | direct | 1.349 | 0.1318 | 0.0664 | 0.0353 | 1.000 |
| JCommonsenseQA / all | one_token | 1.000 | 0.1324 | 0.0696 | 0.0326 | 1.000 |
| JCommonsenseQA / all | one_token | 1.349 | 0.1318 | 0.0664 | 0.0353 | 1.000 |

Paired external changes and discordant classifications are in SUMMARY.json. They are descriptive comparisons on the same items, not additional independent datasets. Differences for JSON mix readout, completion work, and its serialization-specific prompt.

## Reproduction and files

```bash
python3 paper/matched_study/analyze_study.py
python3 -m unittest discover -s paper/matched_study -p test_matched_analysis.py -v
```

Python standard library only. The script refuses incomplete runs, verifies completion/selection/schedule/frozen-source hashes, and checks request ordering and native counters. `SUMMARY.json` records exact input hashes and this analysis script hash. Derived outputs are overwritten deterministically; protocol, preparation, and results files remain read-only.

- `item_latency.csv`: all 750 item-level paired means/differences, with local repetitions retained.
- `latency.csv` and `native_phases.csv`: request-level descriptive latency/token/phase summaries.
- `parity.csv`: every direct/one-token pair, including ties and violations.
- `external_metrics.csv`: task-specific classification/regression/probability metrics and coverage.
- `SUMMARY.json`: full confusion matrices, probability reliability bins, pairing, repeatability, and provenance.

The study uses one model, one hardware configuration, one session, a research HTTP server, and a limited public sample. It is not a production SLA, a comparison with TypeSafe Jev, evidence that zero generated tokens always yields a material speedup, or proof of new learning-method novelty. Any additional matched model, domain, or independent-session results require separate measurements.
