# Saved-evidence data

This explorer reads saved measurements. It does not run a model, expose benchmark
source text, or add observations to a study. All records come from
`paper/naacl2027/reproducibility/naacl-repro-v1-20260925.zip`, SHA-256
`a15e0699a54be15d56bd99ed8181429b71fdfc7ace756d6e065a75538786c053`.

The export contains all eligible records from two completed studies: 7,600
presentation-sensitivity calls and 14,400 averaging-study calls, plus 9,000
derived answers from the latter. The 18 panels each contain 200 items. The 3,600
study/item/model combinations represent 1,200 distinct source item IDs, not
3,600 independent questions. The same items recur across checkpoints.

## Reproduce and verify

From the repository root, using Python 3.10 or later and only the standard library:

```sh
python scripts/build_evidence_explorer.py --check
python -m unittest discover -s tests -p test_evidence_explorer.py -v
```

To generate a separate copy, pass a new destination:

```sh
python scripts/build_evidence_explorer.py --out /tmp/mini-jev-evidence-copy
```

A normal build refuses an existing directory. `--check` rebuilds in memory and
requires an identical file inventory and identical bytes. The exporter checks
the pinned ZIP, internal member hashes, existing successful audit receipts,
completion inventories, schedules, physical softmax mappings, and saved derived
answers. This is a bounded data-integrity check, not a new peer review or a new
independent assessment of the scientific conclusions.

Archived probability vectors, typed values, physical concentration, and saved
latencies retain their exact parsed JSON values after independent validation.
Diagnostics newly created for this explorer (derived concentration and panel
MAE/variance) use exact binary-float-to-Decimal conversion and a fixed 50-digit
`ROUND_HALF_EVEN` context. `Decimal.ln` is correctly rounded; these diagnostics
are serialized at 15 decimal places. This avoids platform `libm` differences
without rounding original saved measurements. Integer counts/ratios and saved
extrema use their existing representation. The contract is also recorded in
`index.numeric_representation`. Tests perturb `math.log` and require identical
export bytes, in addition to checking every source record and ensemble recipe.

## Layout and definitions

`data/index.json` is the shared index. Its `panels` array provides each panel's
relative path, SHA-256, count, canonical semantic key order, variant IDs, complete
panel summaries, and model metadata. `data/panels/*.json` loads one selected
study/model/dataset at a time. The uncompressed export is about 13 MB in total;
individual panels avoid loading the full corpus into the browser.

Every item provides a source item ID and `source_question_sha256`, split, group,
and either a semantic `gold_label` or the continuous `gold_score`. No question,
answer text, model input, or private field is exported. `gold_score` is not
rounded. The score scale is 0–5.

Every variant has a `source: [source_id, line]`, where `line` is the one-based
JSONL line in the ZIP member identified by `index.sources[source_id]`. That
shared entry includes the member path and file SHA-256. Physical variants also
reference `index.mappings`: candidate keys and tokens retain the original raw
vector order. A null `display_order` means the source record omitted that field;
it is not a reconstructed order.

Probabilities always follow the panel's `canonical_keys`, even when an answer
label was rebound or candidate rows were reordered. `label` is the semantic
argmax. `value` is the semantic label for Choice, p(true) for Noul, and the
expected score for Score. The most probable score stage is not the expected
score. Exact physical ties follow the source's candidate vector order; exact
derived ties follow canonical semantic order. `top_tie_keys` contains every
maximum, including the usual single maximum.

`concentration = 1 − H(p)/log(K)` describes the candidate distribution. It is
neither correctness probability nor calibrated confidence. Zero probabilities
contribute zero entropy; JSON zero and null remain distinct.

Derived `baseline`, `reverse_single`, `cyclic_forward`, `cyclic_reverse`, and
`dihedral` variants use the frozen analyzer's membership recipes and arithmetic
means of semantic probabilities, never mean logits. Their `member_ids` refer to
physical variants within the same item and model. `member_sources` gives the
corresponding original physical rows. `source` separately points to the saved
derived-answer row. Derived records do not represent additional executions.

`calls` counts physical members needed for one answer. To compare two answers,
count the union of their physical members, not the sum of displayed call counts.
For binary items, forward and reverse cyclic pools contain the same two calls:
their equality is structural. Nonbinary orientation comparisons have distinct
pools. `latency_ms` is saved sequential time, summed over members for derived
answers; it is not live service performance.

Runtime metadata is available per panel and in `index.models[study_id][model_key]`.
It preserves the saved backend, precision and pinned revision. The native model's
revision identifies the GGUF distribution. Checkpoint, architecture,
quantization, and backend differences prevent a causal model-size comparison.

## Featured examples

Four examples have deterministic, explicit selection rules in `index.featured`:
the first item ID with an order flip; the first correct-single/wrong-average
case; the first 0.5B JSTS item, with full-panel collapse context; and the first
native JSTS item whose expected score differs from its modal stage by at least
0.4. These are explanatory selections, some conditioned on outcomes. They do not
estimate prevalence or represent random samples. The full panels and eligible
counts remain available regardless of the featured examples.

Reworded conditions are hypotheses of semantic equivalence, without independent
human verification. The exporter and UI should restrict comparisons to the same
study, item and model. Saved artifacts and this integrity test do not establish
new novelty, calibration, independence from pretraining, or inferential validity.
