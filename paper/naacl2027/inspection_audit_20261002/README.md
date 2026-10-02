# Saved-evidence inspection audit — 2 October 2026

This **nonhuman functional audit** checks concrete inspection tasks on the real
LogitTrail saved-evidence Explorer. An information-equivalent formatted-JSON
baseline retains the same complete records and summaries. An independently
written Python reader of the original ZIP checks the resulting answers.
No new model calls, participants, or usage-time measurements are involved.

The result is evidence that the inspection computations and exports preserve
the frozen observations. It **does not establish that people inspect them faster
or more accurately**, or that the Explorer outperforms a competing interface.
The Python implementation is separate code, not an independent research team.

## Complete-population result

The prewritten [protocol](protocol.json) has SHA-256
`da0b8af3a46597e780eba8f3b85b9d61e03ed28a3986e9851d210273a941e8b2`.
It was saved before executing this audit. Earlier integrity checks and featured
examples were already known; this is not a blinded prospective experiment.

| Inspection task | Eligible units checked | Result |
|---|---:|---|
| Semantic label changes, candidate-probability differences, unchanged references | 172,200 unordered condition pairs | No discrepancy |
| Expected Score, most likely stage, continuous reference | 12,600 saved Score conditions | No discrepancy |
| Physical-call intersections/unions, with shared calls counted once | 172,200 pairs, including 46,200 sharing calls | No discrepancy |
| Original ZIP member/one-based line, identity and exact probabilities/value | 31,000 saved conditions; source completeness in all pair exports | No discrepancy |
| All-item label histograms, maximum share and Score value summaries | 155 panel/condition distributions | No discrepancy |

These cover all 18 panels and 3,600 study/item/model combinations, representing
1,200 unique source IDs. The 31,000 saved conditions comprise 22,000 physical
observations plus 9,000 derived answers. **172,200 is an inspection-pair count,
not a question count or number of model executions.** The same observations
appear in many pairs. The audit makes no statistical-independence assumption
and computes no significance tests or performance estimates from that count.

All three in-memory negative controls were rejected: a false change flag, an
overcounted call union, and a false source-line identity. Source files were not
modified. [results.json](results.json) records the exact counts, hashes, runtime,
negative-control outcomes and full-panel distributions.

## Why the JSON baseline is fair

The baseline is deliberately complete. It has selectors for the same panel,
source item and two conditions, the full selected comparison export, every
condition's full-panel summary, the entire selected panel and the shared index.
Computed deltas and shared-call accounting are included in JSON as well, so a
benefit is not manufactured by removing information from the baseline.

Both presentations expose saved semantic labels and typed values. The Explorer
adds aligned visual probability bars and task-specific labels. The baseline
presents all the same information as formatted JSON. No human presentation
effect is estimated by comparing two serializations of these data.

| Task | Explorer location | Equivalent complete-JSON fields |
|---|---|---|
| Detect a semantic answer change | Most likely answer; aligned probability rows | `conditions.a/b.label`, `candidate_comparison` |
| Separate expectation from mode | Expected stage; most likely stage; continuous reference | `conditions.a/b.value`, `.label`, `score_values`, `reference` |
| Avoid counting shared calls twice | Calls per result; shared and distinct calls | `conditions.a/b.calls`, `physical_members`, `shared_physical_calls`, `unique_physical_calls` |
| Trace back to evidence | Expand source details; download exact comparison | condition/member `source`, `sources`, `mappings`, `archive` |
| Distinguish a concentrated output population from item confidence | Full-panel frequencies and expected-value summaries | full panel descriptor `variant_summaries`; complete index and panel |

## Reproduce, without a model

Python 3.10+ standard library and Node.js 18+ are sufficient. From the repository
root, choose a new output path (the runner refuses to overwrite an earlier run):

```sh
python3 paper/naacl2027/inspection_audit_20261002/run_audit.py \
  --output /tmp/logittrail-inspection-recheck.json
```

The Python oracle reads the original ZIP directly and verifies every referenced
member hash. It does not import the Explorer exporter or arithmetic functions.
For derived answers, physical membership comes from archived
`physical_member_indices` and original request indices, independently of the
UI's `member_ids`. A Node child invokes the unchanged published `core.mjs` and
compares every eligible unordered pair; the Python oracle checks the streamed
task answers. Original parsed numeric fields are exact; recomputed arithmetic
uses the protocol's `1e-12` absolute/relative tolerance.

For the actual JSON presentation, serve the **repository root**:

```sh
python3 -m http.server 8878 --bind 127.0.0.1
```

Open
`http://127.0.0.1:8878/paper/naacl2027/inspection_audit_20261002/json_baseline.html`.
The link above the JSON opens the identical selection in the actual Explorer.
HTTPS or localhost is required for SHA-256 checks. The baseline loads existing
files in place; it duplicates neither the corpus nor any original task text.

Browser smoke verification covered initial load, changing panels/conditions,
binary shared-call accounting, Score expectation/mode/reference separation,
fragment restoration after reload, and the link to the identical Explorer.
The observed fields are in [BROWSER_CHECKS.json](BROWSER_CHECKS.json). This is
a small functional smoke check, not exhaustive browser testing or a user study.

## Current competing-tool scope

[CHAINFORGE_SCOPE.md](CHAINFORGE_SCOPE.md) distinguishes the earlier executed
custom-provider parity diagnostic from newly inspected standard ChainForge and
Ollama source/documentation. The new standard decision-model route is a real
overlap that narrows the novelty claim. It was not run locally or through the
ChainForge GUI in this audit. No missing feature is inferred merely from not
testing it.
