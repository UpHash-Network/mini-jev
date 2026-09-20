# Empirical draft v0.2: claim-to-evidence map

This map distinguishes completed observations from unsupported extensions. It is an editorial control, not an independent replication or peer review.

| Claim in the draft | Evidence | Permitted interpretation / limitation |
|---|---|---|
| All 4,050 requests complete, zero invalid outputs | `matched_study/results/COMPLETION.json`, `SUMMARY.json`, `INDEPENDENT_AUDIT.json` | 750 unique items; repeated calls are not new semantic examples |
| Direct/one-token logits and labels agree in all 1,350 pairs | `matched_study/parity.csv`, full native traces and independent audit | Same prefix and candidates, greedy selection, no observed ties; not a new algorithm |
| One-token minus direct +0.090 ms [-0.748, +0.845] | Five repetitions/item; 10,000 whole-group bootstrap over 55 groups | Median of 150 paired item means; conditional single-session interval, no formal equivalence claim |
| JSON minus direct +160.296 ms [138.119, 177.059] | Same measured response schema and timing boundary | JSON prompt differs; instrumented system comparison, not pure sampling overhead or universal speed claim |
| JCoLA MCC 0.5708 and accuracy 86% | External 200-item fixed public-dev sample | Always-true accuracy 79%; in-domain direct accuracy is below its 88% constant baseline; no full-dev result |
| JCommonsenseQA direct 190/200, JSON 191/200 | Fixed five-choice external sample | One-item descriptive difference, not proven general JSON advantage |
| JSTS expected MAE 0.5065; hard MAE 0.548 direct versus 0.565 JSON | Continuous gold, stored logits and independent regression calculation | Expected output and hard stage differ; JSON has no comparable probability vector |
| External calibration effects vary by metric and split | `matched_study/external_metrics.csv` | JCQA ECE and JCoLA out-of-domain NLL increase even though other point estimates improve |
| 93.25% local top-label accuracy | `../results/native-acceptance/predictions.jsonl`, `summary.json`; recomputed in `analysis/analysis.json` | Self-authored local-suite performance, not broad domain accuracy |
| All 2,400 outputs passed checked structure/range conditions | Historical summary and test records | Structural correctness, not semantic correctness |
| 45-family macro accuracy 93.02%, interval 89.91-95.74% | `analysis/analyze_frozen_run.py`, seed and 20,000 replicates in `analysis.json` | Conditional family-reweighting interval; no external-population coverage claim |
| NLL/Brier point estimates improve slightly with temperature | Paired logit reanalysis and `paired_metrics.csv` | Both family-resampling delta intervals span zero |
| Expected-stage MAE increases under fitted temperature | Same-item score analysis, delta +0.025721 [0.018260, 0.033734] | Holds fitted T fixed; does not include temperature-fit or selection uncertainty |
| Retrospective risk decreases when accepting high-scoring items | `analysis/risk_coverage.csv` and fixed grid | Descriptive ranking; no threshold selected or risk guarantee |
| 81.0% on a balanced external JNLI pilot | `external_pilot/results/predictions.jsonl`, `METRICS.json` | Public-dev Choice-only sample, not full JGLUE or unseen-data claim |
| Weak contradiction recall (61%) | Pilot confusion matrix: 38 contradiction items predicted neutral | Failure concentration, without a causal diagnosis |
| Historical temperature improves pilot probability losses | Both probability conditions from identical recorded logits | No JNLI fitting; one pilot's descriptive transfer result |
| 77 pilot rows share a sentence with a different row | `external_pilot/AUDIT.json` | Additional dependencies remain; old frozen 84 counter includes within-row repeats |
| Candidate softmax equals matched masked one-token distribution | Algebra in Section 3; established restricted softmax | Exact in real arithmetic under stated assumptions, not a new algorithm |
| Warm p95 379.1 ms for 2,291 local inputs <=512 tokens | Historical native summary, token counts and timings | One machine and run; not all inputs, HTTP latency, or a relative speed claim |
| Earlier residual head underperforms its frozen control | `../results/head/REPORT.md`, 67/96 versus 73/96 | Separate small model and data; no universal anti-fine-tuning conclusion |
| Artifact is reproducible from pinned source | Model/runtime manifests, source, build and training instructions | Public rebuild is not necessarily historical byte identity |

The completed study supports a measured comparison against the specified native one-token and JSON implementations and external binary/continuous-score observations. It does not establish a speed advantage over all generators, unseen-pretraining generalization, a human-audited new local test set, or a repeatable improvement from output-head learning. Broader model/device replication and learning studies remain extensions in `NEXT_STUDY_PROTOCOL.md`.
