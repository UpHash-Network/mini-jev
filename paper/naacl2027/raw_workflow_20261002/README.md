# Diagnostic reconstruction from archived logits

**Executed:** unmodified ChainForge 0.3.7.6 runs the supplied JavaScript through its native Processor in Firefox 153.0, starting with no computed output. The export passes a separately implemented Python arithmetic check. This is evidence that the competing framework can implement the diagnostic computation with custom code. It does not show a LogitTrail advantage, a built-in ChainForge domain feature, or human task performance.

This follows the [saved-evidence GUI check](../workflow_comparison_20261002/README.md), which supplied precomputed diagnostic fields. Here those output fields are deliberately absent from the input. The previous check and its frozen receipts are unchanged.

## Input and frozen scope

The same six previously selected cases cover Choice, Noul and Score across presentation and averaging studies and three checkpoints. Each case includes its full 200-item panel, two conditions per item. The six panels contain **6,000 archived physical records and 2,400 condition instances**. They are dependent observations from existing studies, not new model requests or independent scientific samples.

`protocol.json` was frozen before fixture generation and native execution. Prior results and selected cases were already known; this is neither blinded evaluation nor registry preregistration. `build_inputs.py` checks the original archive, source-member and panel hashes before extracting an explicit allowlist:

- Candidate logits, semantic keys, token IDs, temperature, recorded cost and physical source identity.
- Gold labels/scores and the Score rubric, which are reference inputs rather than model predictions.
- Original physical-member recipes and source-line addresses for each condition.

The input excludes saved probabilities, model-selected labels, typed predictions, alignment differences, reference-error results, call unions and panel summaries. It contains no original benchmark text. `tie_order` records original candidate-vector order, not a predicted answer. The offline builder authenticates archived bytes; the browser processor checks structure and context but does not fetch or authenticate whole archive members.

| Frozen file | SHA-256 |
| --- | --- |
| `protocol.json` | `367691c071d2e353f8968bac5a031ed0a239a435667752480508fd1501f56f53` |
| `raw_inputs.json` | `9c2d01cecf4c5ce06d8d0497db03a17f55a164cec3ae5ee4ef2815c02e4fd5a1` |
| Executed `process.js` | `7de19273b487cf45ae2da3b6fb12392758f7904f40acb82ed9b1d6e354533055` |

## What was computed and checked

The processor recomputes restricted softmax at the recorded temperature; averages member probabilities after semantic alignment; constructs typed values and concentration; compares references; counts physical-call intersection/union; and summarizes all 200 items. Physical argmax ties use original vector order; derived ties use canonical order. There are no actual maximum-logit ties in these 6,000 records, so passing this fixture alone does not establish behavior at ties.

The Python oracle uses independent arithmetic code and `math.fsum`, with no import from the processor or Explorer comparison code. It shares the input specification and recipes; it is AI-assisted author-side verification, not independent human or scientific replication. The frozen tolerance is `rel_tol=abs_tol=1e-12`; labels, source identities and integer accounting require exact equality.

| Check | Observed result |
| --- | --- |
| Original conditions vs unchanged published data | 2,400 checked; probabilities and typed values match exactly in the Python recomputation; labels, call counts and recipe addresses agree |
| Actual native Processor export vs Python | No discrepancies; maximum numeric difference `1.7763568394002505e-15` |
| Candidate tuple reversal controls | All six preserve diagnostics, including physical identity and call accounting |
| Deliberately invalid input controls | All eight rejected with their frozen error codes |
| New model calls / human participants | 0 / 0 |

The invalid controls cover a missing member, duplicated physical source, member from another problem, duplicate candidate, nonfinite logit, nonpositive temperature, invalid source line and empty recipe. They are finite regression checks, not a complete input-validation guarantee. Numeric comparison totals contain repeated derived values and invariance checks and must not be presented as independent sample counts.

An additional AI review found that Python equality in the first checker revision would accept Boolean/float substitutes for integer fields. Its separate type audit found no such mismatch in the current output. The checker was then made type-strict, explicit type probes rejected those substitutes, and both unchanged Node and native GUI exports passed again. Initial receipts are retained under `verification/initial_checker/`; final receipts record the revised checker hash. The frozen protocol, inputs, processor, exports and tolerance were unchanged. Supplemental post-hoc tie probes are recorded separately in the AI review and are not added to the frozen 20-case inventory.

## Reproduce the arithmetic without a browser

From the repository root, with Python 3.10+ and Node.js available, use new output paths:

```sh
python3 paper/naacl2027/raw_workflow_20261002/build_inputs.py --check
python3 paper/naacl2027/raw_workflow_20261002/make_cases.py --output /tmp/logittrail-raw-cases.json
node paper/naacl2027/raw_workflow_20261002/run_node.cjs --cases /tmp/logittrail-raw-cases.json --out /tmp/logittrail-raw-results.json
python3 paper/naacl2027/raw_workflow_20261002/check_results.py /tmp/logittrail-raw-results.json --report /tmp/logittrail-raw-check.json --execution node
```

No model, network request or third-party Python package is needed. These Node checks are also included in the Linux source-test workflow. A Node pass is not a native GUI execution. The scripts refuse to overwrite prior generated inputs or receipts.

For the native flow and exact retained browser outputs, see [competitor/](competitor/). After extracting the retained export, the same oracle accepts its `after.cforge` path with `--execution chainforge`. The pre-run export contains an empty native output-cache placeholder; the post-run export contains the computed responses. `verification/CHAINFORGE_CHECK.json` records the exact export hash checked. Browser execution uses normal application import, Run and export handlers, with no patched application or injected answer cache.

## Interpretation and remaining work

The competitor succeeds with disclosed custom code. LogitTrail's released Explorer remains a preprocessed-data interface and does not natively ingest this raw fixture. This is not a symmetric user-task or setup-effort experiment. Agent execution time and browser automation failures are not estimates of human effort or application performance. Candidate token IDs, provenance and references still rely on the validity of the original recorded studies.

The existing [actual-Explorer pilot](../explorer_user_evaluation_20261002/README.md) has zero participants and observations. An [external replication handoff](../external_replication_20261002/README.md) is available, but no external operator or second-machine inference is established by this work. Those remain the principal evidence gaps for practical value and portability.

Source code is original project material; dataset-derived selections, rubrics and records retain the upstream attribution and applicable terms documented in the repository's `NOTICE.md` and the frozen evidence archive. Original artifacts and arXiv submission files were not changed.
