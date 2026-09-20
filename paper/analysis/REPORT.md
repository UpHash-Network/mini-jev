# Post-hoc analysis of the frozen v2 run

This analysis makes no new model calls and does not modify prompts, weights, temperature, labels, or acceptance criteria. It recomputes the existing run and describes sensitivity to the composition of its observed task families.

## Reproduction

```sh
python3 paper/analysis/analyze_frozen_run.py
```

Standard library only. Seed `2026092037`; `20,000` replicates. Input and script SHA-256 values are recorded in `analysis.json`. Existing derived outputs in this directory are overwritten; source data remain read-only.

## Verification and estimands

All 2,400 IDs, source/family/type metadata, gold labels, correctness indicators, candidate probabilities, Score expectations, summary losses, and latency quantiles were cross-checked. The original prediction-file hash matches the frozen summary. The reconstructed probabilities and reported losses differ by less than 1e-12.

| Subset | Correct / n | Accuracy |
|---|---:|---:|
| all | 2238 / 2400 | 93.25% |
| generated | 2066 / 2220 | 93.06% |
| manual_ai_authored | 172 / 180 | 95.56% |
| choice | 768 / 800 | 96.00% |
| noul | 762 / 800 | 95.25% |
| score | 708 / 800 | 88.50% |

## Family-aware uncertainty

**These are conditional empirical family-resampling percentile intervals, not guarantees of 95% coverage for an external population.** Families and examples were deliberately authored and were not sampled randomly from a defined deployment population. The bootstrap assumes the observed family clusters are exchangeable within each source; dependencies between different families are not modeled. It measures sensitivity to reweighting these observed families. It does not establish generalization to new families, domains, authors, languages, or machines.

For generated-only estimates, draw 45 family IDs uniformly with replacement and include every member of each drawn family. For macro accuracy, average the 45 drawn family accuracies with equal family weight. For micro accuracy and losses, aggregate the drawn family totals and divide by their applicable item counts. Generated families contain 49 or 50 questions; each family belongs to one type. The family draw is not stratified by type, so its mixture of Choice/Noul/Score can vary.

For combined probability-loss differences, independently draw 45 generated families and 26 individually AI-authored `manual` tags. Preserve each drawn cluster intact, including multiple types within a manual tag. Compute within-source item-weighted means, then keep the original source mixture fixed: 2,220:180 for NLL/Brier/accuracy, and 740:60 for Score-only MAE. The same sampled clusters are used for T=1 and fitted T; the difference is paired at the item level. Manual-only estimates are also provided, but 26 heterogeneous tags, some with one item, give especially fragile uncertainty summaries. `manual` denotes AI-agent construction and review, not human annotation. There is no IID bootstrap over 2,400 individual examples.

| Generated-only estimand | Estimate [conditional 95% percentile interval] |
|---|---:|
| Equal-family macro accuracy | 93.02% [89.91%, 95.74%] |
| Item-weighted micro accuracy | 93.06% [89.97%, 95.76%] |

## Paired temperature comparison

Fitted temperature was frozen from the separate 120-item calibration set: T = 1.348962882591653. It is held fixed in every replicate. These intervals therefore omit uncertainty from calibration-set sampling, temperature fitting, model selection, authoring, and runtime reruns. Positive deltas mean fitted temperature is worse. The intervals below describe the original 2,400-item source mixture using source-standardized family resampling.

| Metric | T=1 | Fitted T | Paired delta [conditional 95% interval] |
|---|---:|---:|---:|
| nll | 0.188423 | 0.187871 | -0.000553 [-0.010705, +0.008315] |
| brier | 0.097261 | 0.096260 | -0.001001 [-0.005021, +0.002176] |
| score_mae | 0.169401 | 0.195121 | +0.025721 [+0.018260, +0.033734] |
| score_normalized_mae | 0.044948 | 0.051964 | +0.007017 [+0.005060, +0.008989] |

Small changes in NLL/Brier should not be presented as established improvements if the family-resampling interval crosses zero. Score MAE measures the continuous expected stage, whose value changes under temperature scaling even though every top label is unchanged. ECE is recomputed descriptively but is not given a paired bootstrap interval here; bin membership changes with temperature.

## Descriptive risk–coverage

Risk is the observed error proportion among accepted top-label decisions; coverage is the accepted fraction. We include two distinct sorting scores: maximum allowed-candidate probability and the API’s `1 − normalized entropy`. Neither is asserted to be a correctness probability. Curves are produced for both temperatures and each source/type subset. All exact-score ties are accepted together, so realized coverage can exceed the requested grid point. The full curves and fixed numerical cutoffs are descriptive post-hoc analysis only. No cutoff is selected to achieve a target risk, no abstention policy is fitted, and no deployment threshold is recommended from these test outcomes.

| Fitted T, maximum probability; requested coverage | Actual coverage | Errors / accepted | Observed risk |
|---:|---:|---:|---:|
| 10.00% | 10.00% | 1 / 240 | 0.42% |
| 20.00% | 20.00% | 2 / 480 | 0.42% |
| 30.00% | 30.00% | 2 / 720 | 0.28% |
| 40.00% | 40.00% | 2 / 960 | 0.21% |
| 50.00% | 50.00% | 2 / 1200 | 0.17% |
| 60.00% | 60.00% | 2 / 1440 | 0.14% |
| 70.00% | 70.00% | 4 / 1680 | 0.24% |
| 80.00% | 80.00% | 17 / 1920 | 0.89% |
| 90.00% | 90.00% | 59 / 2160 | 2.73% |
| 100.00% | 100.00% | 162 / 2400 | 6.75% |

Curves and the fixed-cutoff table expose this run’s ranking behavior; they supply no operational risk guarantee. A deployable cutoff must be selected on separate development/calibration data and evaluated on a fresh external test set.

## Weak families and failure examples

The family table is sorted by observed accuracy. This ordering is post hoc, without multiple-comparison significance claims. No causal failure diagnosis is inferred from a family name. `failures.csv` contains all 162 failed items with their original state, question, candidate criteria, gold, predicted label, and fitted confidence scores.

| Source | Family | Correct / n | Accuracy |
|---|---|---:|---:|
| manual | arithmetic | 10 / 17 | 58.82% |
| generated | 約束時刻からの遅れ | 29 / 49 | 59.18% |
| generated | 条件付き義務 | 31 / 49 | 63.27% |
| generated | 取消しを反映した件数 | 33 / 49 | 67.35% |
| generated | 軽重のある項目 | 38 / 49 | 77.55% |
| generated | 不在時の代理 | 40 / 49 | 81.63% |
| generated | 目標からの差 | 40 / 49 | 81.63% |
| generated | 例外による上限 | 42 / 49 | 85.71% |
| generated | 証拠の最高到達段階 | 43 / 49 | 87.76% |
| generated | 重複を除いた件数 | 43 / 49 | 87.76% |
| generated | 不足の段階 | 44 / 49 | 89.80% |
| generated | 小数量の比較 | 44 / 49 | 89.80% |

The following examples are the highest maximum-candidate-probability errors, sorted post hoc to expose overconfident mistakes. They are illustrative, not a representative subsample or a threshold-development set.

| ID | Type / family | Gold → prediction | Max candidate probability |
|---|---|---|---:|
| v2-gen-score-07-024 | score / 証拠の最高到達段階 | 0 → 1 | 0.998674 |
| v2-gen-score-07-038 | score / 証拠の最高到達段階 | 0 → 1 | 0.997297 |
| v2-gen-choice-12-007 | choice / 条件付き不足書類 | 承認書 → 申込書 | 0.977636 |
| v2-gen-score-13-027 | score / 取消しを反映した件数 | 3 → 4 | 0.971222 |
| v2-gen-score-14-014 | score / 参照表の順序尺度 | 3 → 4 | 0.951763 |
| v2-gen-score-07-036 | score / 証拠の最高到達段階 | 5 → 4 | 0.951046 |
| v2-gen-choice-12-014 | choice / 条件付き不足書類 | 委任状 → 申込書 | 0.947083 |
| v2-gen-score-11-015 | score / 時刻順の評価更新 | 2 → 5 | 0.939928 |
| v2-gen-score-11-044 | score / 時刻順の評価更新 | 4 → 5 | 0.933354 |
| manual_v2_choice_060 | choice / arithmetic | option_3 → option_0 | 0.923017 |
| v2-gen-noul-15-040 | noul / 出来事の前後関係 | false → true | 0.915093 |
| v2-gen-score-06-021 | score / 約束時刻からの遅れ | 2 → 1 | 0.914728 |

## Files

- `analysis.json`: recomputed metrics, cluster-resampling intervals, methods, and input hashes.
- `family_metrics.csv`: all 45 generated families and 26 AI-authored tags, with paired loss differences.
- `paired_metrics.csv`: per-item probability-loss contributions and both confidence scores.
- `risk_coverage.csv`: complete tie-aware descriptive curves.
- `risk_coverage_grid.csv`: fixed requested coverage values from 10% to 100%.
- `risk_fixed_thresholds.csv`: descriptive results for fixed cutoffs, without cutoff selection.
- `failures.csv`: all errors, sorted by fitted maximum candidate probability.
- `test_analysis.py`: numerical fixtures and cluster-unit regression checks.
