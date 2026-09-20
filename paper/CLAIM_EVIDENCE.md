# Working draft: claim-to-evidence map

This map distinguishes completed observations from unsupported extensions. It is an editorial control, not an independent replication or peer review.

| Claim in the draft | Evidence | Permitted interpretation / limitation |
|---|---|---|
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

The paper does not currently have evidence for a speedup against a fair generation baseline, an externally validated Noul/Score result, a human-audited new test set, or a repeatable improvement from output-head learning. These are explicit future experiments in `NEXT_STUDY_PROTOCOL.md`.
