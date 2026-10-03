# Retained numerical-gate failure and prospective amendment

This is a retrospective author/AI-assisted engineering case, reconstructed from
already published records. It adds no inference, participant, or benchmark
outcome. The original failure was detected by a command-line synthetic gate;
there is no evidence that the LogitTrail GUI discovered it. The JSONL projection
allows the existing importer to inspect the observations afterwards.

## Evidence chain

1. The first Phi attempt stopped after 24 synthetic forwards and before any
   benchmark forward. Its failure receipt survives, but its detailed gate was
   not serialized. The receipt's `excluded_calls: 28` denotes planned checks;
   the executed counter is 24. Do not describe later logs as the original gate.
2. A subsequent 24-forward comparison retained all 12 fixed synthetic fixtures
   (four each of Choice, Noul, and Score). Two Choice fixtures exceeded the
   pre-existing absolute probability tolerance of `1e-5`: `1.0880903907e-5` and
   `1.2785692608e-5`. All 12 argmax labels agreed. The magnitude is small; no
   consequential semantic error was demonstrated. The contrast is the stock
   **last-input-position-only** versus **all-input-position** vocabulary head,
   not selected-vocabulary-row projection.
3. A separate 24-forward stock full-position repetition had zero candidate-logit
   difference on all 12 fixtures. Shape-dependent floating-point rounding is a
   plausible explanation for the failed comparison, not a causally isolated fact.
4. An amendment recorded at `2026-10-02T18:24:09Z`, followed by a source freeze at
   `18:24:23Z`, changed both checkpoints to `logits_to_keep=0` before any benchmark
   result was available. Questions, candidate mappings, dtype, device, attention,
   tolerance and numerical analyses remained fixed. This was a local timestamped
   amendment, not independent preregistration. The replacement gate establishes
   full-position repeatability; it does not establish equivalence with the
   rejected optimization.
5. Both models completed 2,400 benchmark forwards with zero recorded errors.
   Actual accounting is 4,800 measured + 24 initial-failure + 48 subsequent
   diagnostic/repeat + 56 final synthetic checks = **4,928 forwards**. No failed
   benchmark item was retried or replaced. These are existing measurements.
6. The resulting study retained its negative evidence: all four AP differences
   for entropy+TV versus entropy were negative with intervals crossing zero.
   Primary Phi-English was `−0.0512 [−0.1190, +0.0134]`. At 720 logical calls,
   entropy+TV and entropy each returned 174/240, fixed random 180/240, and
   first-call entropy 177/240. Completing the run did not establish added TV
   value or demonstrate an accuracy repair.

## Retrospective importer walkthrough and fair baseline

Load [diagnostic_import.jsonl](diagnostic_import.jsonl) into the released
[local importer](https://uphash-network.github.io/mini-jev/explorer/import/). It contains **all
48 subsequent diagnostic/repeat observations**, across 12 groups and four
conditions. `synthetic-choice-0` is the first fixture in the retained source
order; inspect `synthetic-choice-1` as the second failed comparison, and the
other ten fixtures as retained nonfailures. Switch A/B from
`diagnostic_last_position_only` / `diagnostic_stock_full_position` to
`repeat_stock_full_position_a` / `repeat_stock_full_position_b`.

The maximum first-pair differences are approximately **0.0011 and 0.0013
percentage points** in the UI; the decision labels do not change. The comparison
download preserves exact candidate values. The repeat pairs have zero
differences. The declared source location points to the first line of the
original logit array, and each note supplies its exact JSON pointer. Source IDs
bind the original file hash and pointer, rather than inventing extra calls.
References and latency are unknown and remain omitted.

A fair same-data baseline is the complete original
[diagnostic JSON](../generality_20261003/publication/bundle_v1/provenance/earlier_synthetic_only/PHI_SYNTHETIC_FAILURE_DIAGNOSIS.json)
and [repeat JSON](../generality_20261003/publication/bundle_v1/provenance/earlier_synthetic_only/PHI_FULL_POSITION_REPEAT.json).
Both include every fixture and full recorded candidate logits; the diagnostic
JSON also includes the corresponding probabilities. An ordinary JSON reader
or script can recover every discrepancy. The adapter adds organization and
provenance links, not privileged information. No comparison of human completion
time, errors, discoverability, or UI-driven decisions has been measured.

## Verification and rights

From the repository root:

```sh
python3 paper/naacl2027/case_study_20261003/build_case.py
node paper/naacl2027/case_study_20261003/check_import.mjs
```

The Python check verifies the existing public manifest, retained logits and
probabilities, timestamps, all four 1,200-row benchmark files, counts and final
negative results. It recreates the two generated case files byte for byte;
`--write` rebuilds only those new projections. The JavaScript check exercises
the actual released importer core against all 48 records. Neither executes a
model. [CASE_EVIDENCE.json](CASE_EVIDENCE.json) contains full source-relative
paths, SHA-256s, JSON pointers, and derived values. The new package redistributes
only already public synthetic output vectors and project code (MIT); it adds no
benchmark question text, model weights, private paths, or participant data.

## Suggested manuscript paragraph (118 words)

An author/AI-assisted engineering case illustrates retained numerical failures,
not measured usability. A Phi optimization gate stopped before benchmark
inference. Subsequent checks found that two of twelve synthetic fixtures exceeded
the fixed `1e-5` candidate-probability tolerance between stock last-position-only
and full-position projection (maximum `1.28e-5`); all argmax labels agreed. A
versioned pre-benchmark amendment switched both checkpoints to stock full-position
projection without relaxing tolerance. All retained repeatability checks passed,
and 4,800 benchmark forwards completed without recorded errors, preserving the
study's negative diagnostic-value results. We provide a retrospective importer
projection of all 48 diagnostic/repeat observations, with exact source links and
the same complete JSON as baseline. This demonstrates traceable inspection, not
GUI-driven discovery, an accuracy improvement, or a measured advantage over
reading JSON.

## Strongest defensible takeaway

The failure, amendment and subsequent completed measurements form an auditable
chain without discarding inconvenient records or claiming the original
optimization passed. The importer can present its exact distribution-level
evidence afterwards. Establishing a usability advantage or a practically
consequential repair still requires independently observed comparison work.

## Browser verification

`check_browser.cjs` uses Playwright Chromium and Firefox with local static files. Install Playwright and its browsers, then run `node paper/naacl2027/case_study_20261003/check_browser.cjs`. The checker imports the same 48 rows, visits all 12 groups, and exports the diagnostic and repeat pair for each group. It compares exact export values and source records, and checks that no requests occur after initial page loading. Export actions are deliberately spaced; elapsed time is not a human-performance measurement. See `BROWSER_CHECKS.json` for the recorded outcome and `BROWSER_ATTEMPTS.json` for test-environment failures.
