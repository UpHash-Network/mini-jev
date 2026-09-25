# LMQL native adapter diagnostic

This folder records **one prespecified diagnostic run**, not a task benchmark or an out-of-box comparison of frameworks. It exercises installed, unmodified **LMQL 0.7.3** using a custom LMTP backend to the same pinned native model runtime as Mini Jev's direct readout.

**Result:** all 12 argmax decisions matched; probability differences reached **2.63e-5**, so **3 cases failed** the prespecified **1e-5** tolerance. The gate remains failed. Noul/Score value differences were below 1e-4 in all 8 applicable cases. No additional model run was used to seek a passing result.

- [Japanese report](REPORT.ja.md) and [per-case CSV](RESULTS.csv).
- [Prespecified protocol](PROTOCOL.ja.md), [12 exact prompts](CASES.json), [pre-inference freeze](FREEZE.json).
- [Measured result trace](run_v1/results.jsonl), [run receipt](run_v1/SUMMARY.json), [independent arithmetic audit](run_v1/AUDIT.json).
- [CPU-only plumbing check](CPU_PREFLIGHT.json) uses a labelled fixture, **not model evidence**.
- [Pinned dependencies](requirements.lock.txt), [runner](run.py), [native source](llama_lmql_helper.cpp), [native build script](build_native_bridge.py), [audit script](audit.py).

There were **64 llama_decode calls**, comprising 12 direct calls and 52 LMQL continuation scoring calls. These are separate from the paper's existing research-request counts. We make no speed, task-accuracy, usability, standard-backend compatibility, or multi-token equivalence claim. Inputs are simple synthetic cases with highly concentrated probabilities; the diagnostic does not assess behavior near decision boundaries.

## What was actually executed

`lmql.model(...).score(prompt, labels)` invokes the installed LMQL tokenizer, DcModel, LMTP transport/scheduler, custom `LMTPModel.score`, and installed `ScoringResult.probs`. The native adapter returns true full-sequence log probabilities computed from vocabulary-wide logits; it does not receive Mini Jev candidate probabilities as answers. The original native direct path is unchanged, with source equality outside the one added scoring branch verified before freezing. The two native scoring paths produced slightly different raw logits. The root cause has not been established.

The actual LMQL package and native runtime file hashes are in `FREEZE.json`. Its paths are relative to the original experiment workspace, rather than to this directory. Package source names such as `openai_secret.py` identify installed LMQL code files only; no credential contents are included.

## Publication and original evidence

The original runtime log `run_v1/native.log` is preserved locally and excluded by this directory's `.gitignore`, because it includes one absolute workstation path. [native.public.log](run_v1/native.public.log) replaces only that workspace prefix with `${WORKSPACE_ROOT}`. [NATIVE_LOG_PUBLICATION.json](run_v1/NATIVE_LOG_PUBLICATION.json) records both hashes, sizes, and the exact single replacement. This derivative **does not change the pre-run freeze or measured JSON traces**. Synthetic prompts, full token IDs, numeric results, code, dependency versions, and relative frozen artifact identifiers are included. No model weights, compiled binaries, API keys, or emails are bundled.

## Reproduction scope

This is a research artifact in the documented local experiment layout, not a standalone installer. The source expects the repository at `WORKSPACE/outputs/mini-jev-naacl2027/` and isolated prerequisites at `WORKSPACE/work/naacl-finalization/comparator/`. Acquire the pinned GGUF and tokenizer revisions specified in the protocol, install the dependency lock into `venv/`, and build against the pinned clean llama.cpp checkout and verified shared libraries. Those large/model-specific prerequisites are deliberately not committed.

The original freeze is immutable: do not overwrite it merely to accept a newly built runtime. A replication should use a separate study directory at the same nesting depth, preserve the published originals, build and verify its own pinned prerequisites, generate its own new freeze **before inference**, and give its run a new output directory. `run.py` refuses an existing output directory and verifies frozen files before and after inference. A failed numeric gate causes a nonzero exit while retaining its complete trace and summary, as occurred in this original run.

For the original documented local workspace:

```sh
work/naacl-finalization/comparator/venv/bin/python \
  outputs/mini-jev-naacl2027/paper/naacl2027/comparator_study/audit.py
```

The audit also refuses to overwrite its existing receipt. Use a copied results directory for a repeated audit. `audit.py` recomputes normalization and readouts without importing the runner; it verifies 494 integrity checks and reports the separate 32 numeric/label gates, of which 3 failed. This is an audit of the saved result, not an independent model replication.

Primary documentation: [LMQL generation/scoring API](https://lmql.ai/docs/lib/generations.html), [llama.cpp integration](https://lmql.ai/docs/models/llama.cpp.html), [LMTPModel extension interface](https://github.com/eth-sri/lmql/blob/main/src/lmql/models/lmtp/backends/lmtp_model.py).
