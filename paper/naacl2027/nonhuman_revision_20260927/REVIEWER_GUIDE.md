# Review the recorded evidence without running a model

This is a companion to the continuing NAACL manuscript revision, prepared on
27 September 2026. It does not replace the frozen source/evidence ZIP or the
submitted arXiv files. The guide and diagnostic are distributed with this revision; the
[publication manifest](PUBLICATION_MANIFEST.json) identifies their exact bytes.

## Quick integrity and accounting check

From a checkout containing this revision, with Python 3.10 or newer:

```sh
python3 paper/naacl2027/nonhuman_revision_20260927/check_evidence.py
```

This uses only the standard library and does not download files, extract the
archive, load weights, contact a service, or rerun inference. It verifies all
353 archived source/record files, checks the actual prediction row counts,
retains the LMQL tolerance failures, and compares the stored ChainForge typed
answers. It prints JSON and exits nonzero on a detected mismatch. Use
`--output /absolute/new-path/checks.json` to retain a new report; an existing
report is not overwritten. The historical `EVIDENCE_CHECKS.json` is the recorded
execution for this revision, not the output of a future reviewer's run.

## Recompute the published analysis

The immutable [source/evidence ZIP](../reproducibility/naacl-repro-v1-20260925.zip)
has SHA-256
`a15e0699a54be15d56bd99ed8181429b71fdfc7ace756d6e065a75538786c053`.
Extract it into a new directory. Inside its `mini-jev` directory:

```sh
python3 verify_bundle.py
python3 reanalyze.py --output /absolute/new-directory/mini-jev-reanalysis
```

This separate path executes the six original CPU analyses and compares their
56 derived files to the retained outputs. No pip packages, network, weights,
accelerator, or model execution are required. The new destination must not
already contain a prior replay. The instructions in the ZIP describe this path
in full. The quick check above verifies integrity/accounting; it does not stand
in for these numerical calculations.

## Follow each claim to its evidence

| Claim or boundary | Evidence entry point | What it does not establish |
|---|---|---|
| 4,050 matched requests; direct/one-token parity and timing | ZIP: `paper/matched_study/`; its frozen protocol, predictions and analysis | Other machines/sessions, human speed, stock LMQL speed |
| 7,600 presentation-sensitivity requests | ZIP: `paper/journal_robustness/` and `cross_model/` | Model-size causality; identical precision/backend across checkpoints |
| 14,400 averaging requests | ZIP: `paper/order_ensemble/study_v1/` | Equal-compute improvement; new averaging algorithm |
| 26,050 total requests | 4,050 + 7,600 + 14,400 actual rows | 26,050 independent examples; the separate 300 background rows are excluded |
| LMQL custom-backend integration | `../comparator_study/run_v1/results.jsonl`; [new diagnostic](lmql_diagnostic/README.md) | Exact probability parity or near-boundary label robustness |
| ChainForge registration/dispatch | `../chainforge_integration/results.json` | Browser flow editor usability or competitor accuracy |
| Installation | `../reproducibility/VALIDATION.20260925.json` | Fresh-machine replication; this reused source/model caches on the same Mac |
| Live interface | `demo/static/app.js` and `service/schema.py` at repository root | Raw candidate token/logit exposure: those are internal research traces, outside the public response |

The primary-source feature comparison in the manuscript describes architecture
and available evidence. Langfuse/Phoenix interfaces were not experimentally
compared with Mini Jev. “Not verified” must not be read as “not supported.”

## Recompute the new LMQL diagnostic

The separate diagnostic explains the preserved 3/12 probability-tolerance
failures, candidate margins, and typed-value differences from the same 12 logs.
It is post hoc and adds no model calls or independent examples. Follow its
README for the exact invocation and input hashes. Do not increase the original
`1e-5` threshold to turn the original failures into passes.

## Optional live execution

Use [the native installation instructions](../reproducibility/REPRODUCIBILITY.md)
to build and run the actual API/browser demonstration. That path separately
requires the roughly 20.4 GB model, a native toolchain, and appropriate hardware;
the tested machine had 64 GB unified memory. The software does not provide
canned live predictions when inference is unavailable.

Human usability is not an outcome of these checks. The separate AI fixture
rehearsal is tooling QA, not a human study, model-quality evaluation, or evidence
that the released interface improves a person's work. Data/license notices and
AI-assistance disclosures remain part of the source/evidence artifact and paper.
