# Independent numerical replay review — PASS

The separate standard-library reviewer imported no primary analysis, metric, or
runner code. It reconstructed all results directly from the 4,800 candidate-logit
records. The review script was hashed before any benchmark observations or
primary results were inspected; that hash remained unchanged during comparison.

- All 32 frozen input/source hashes, 480 selected question-row hashes, source
  gold labels, scheduled request identities and completion receipts matched.
- All four model–dataset strata were analyzed separately: 960 model-item
  records, representing 480 distinct questions shared across two models.
- Raw logits, candidate softmax, first/pair/five-member labels and eight scores
  matched, as did 128 AP/AUROC point values and nominal-top-20 tie handling.
- All 80 policy–budget points matched, including selected item IDs, paid member
  indices, call counts, input tokens, recorded latency sums and correctness.
- Primary Phi-English AP/AUROC contrast intervals, both component-score
  intervals and the primary three-call accuracy contrast interval matched an
  independent 2,000-draw weighted-bootstrap implementation.
- Maximum absolute numerical difference: **5.551115123125783e-16**.

The primary Phi-English AP contrast was **−0.05119**, with descriptive 95%
interval **[−0.11900, +0.01340]**. Both primary routing policies answered
**174/240** correctly at 720 calls and had identical per-item correctness.
The resulting conditional accuracy-difference interval [0, 0] describes these
fixed cohort predictions; it does not establish population equivalence.
The fixed-random and first-entropy references scored 180/240 and 177/240,
respectively, and must remain visible. These observations do not establish
added value of the order-variation composite.

This is AI-assisted numerical replay verification, not independent human
validation, independent model inference, or replication on another machine.
Only the primary Phi-English bootstrap was independently recomputed; all four
strata's point metrics and allocation curves were verified.

Artifacts: [review record](INDEPENDENT_NUMERICAL_REVIEW.json) and [exact reviewer source](independent_numeric_review.py). This source retains its original-study CLI, which expects the original path-bearing private freeze and restored input files; it is published for implementation inspection. The portable public entry point is `bundle_v1/replay.py`. Only artifact links and this portability note have been added to the original review prose.
Synthetic validation of the reviewer covered 3,888 score/target/weight
configurations against direct positive-threshold AP and pairwise AUROC.
