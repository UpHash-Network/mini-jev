# LogitTrail: reviewer quick start — 2 October 2026

Start with saved evidence, then verify or recompute it. A local model is **optional**. This guide accompanies the manuscript submitted to EACL 2027 System Demonstrations on 6 October 2026; the decision is pending, and it does not modify the frozen experiments, earlier audit receipts, or submitted arXiv files. The original `mini-jev` repository/archive identifiers remain valid after the LogitTrail rename.

[Current manuscript PDF](../../../docs/assets/LogitTrail_Manuscript.pdf) · [Current demonstration](../../../docs/assets/LogitTrail_Demo_20261002.mp4) · [Hosted Explorer](https://uphash-network.github.io/mini-jev/explorer/)

The current 127.08-second video records saved-Explorer interaction and a clearly labeled 16-second archival live-interface excerpt. It has embedded English captions and no audio, adds no new inference, and has a [complete transcript](../../../publication/revision-20261002/video/TRANSCRIPT.en.md).

| Route | Requirements and download | What you can establish |
|---|---|---|
| **1. Inspect saved decisions** | Browser with Web Crypto support; hosted HTTPS or localhost. No install, key, model, or inference API. The complete static data export is about 13 MB; panels load individually. | Inspect retained conditions, semantic probabilities, typed values, physical-call membership, and source references. |
| **2. Check and recompute** | Python 3.10+ standard library; no pip packages. The frozen numerical bundle is 18,060,014 bytes (18.06 MB). A new extraction and replay directory need additional disk space. | Verify file integrity/accounting; rerun the original six analyses and compare their 56 derived files. |
| **3. Optional live inference** | Apple Silicon/macOS native toolchain; a separate 20,419,565,568-byte model download. The measured Mac had 64 GB unified memory. | Exercise the local API with new inputs. This is a separate setup, not required to review saved evidence. |

The fresh checks documented below were performed on the **same existing Mac**, with a new source extraction and Python virtual environment. They are not a second-machine replication, a clean operating-system install, a new inference experiment, or a human usability study.

## 1. Inspect a recorded comparison

Open the [hosted Explorer](https://uphash-network.github.io/mini-jev/explorer/). Alternatively, from the repository root:

```sh
python3 -m http.server 8777 --bind 127.0.0.1 --directory docs
```

Open `http://127.0.0.1:8777/explorer/`; stop this static server with Control+C. Do not open the HTML with `file://`: panel SHA-256 checks require a secure context, supplied by HTTPS or localhost. This server only serves static files; it does not start or call the model service.

1. Choose an illustrated observation, or select a study, model/runtime, task, and source item.
2. Select two retained conditions for that same item and model. The probability bars use semantic answer keys and a common scale.
3. Compare the selected label, the typed value, the reference, and concentration. For Score, the most likely stage and the expected stage are different quantities. Concentration is not a probability of correctness.
4. Inspect the **union of physical calls**, not the sum of two displayed call counts: derived answers can share source calls.
5. Expand source details and download the comparison JSON. It includes ZIP member paths, one-based JSONL lines, hashes, exact saved values, and derivation membership. Original benchmark question/option text is not reconstructed.

The Explorer includes 22,000 physical records from presentation sensitivity and averaging, plus 9,000 saved derived answers. Those derived answers are not extra model executions. Its 3,600 study/item/model combinations contain 1,200 distinct source item IDs; repeated models and conditions do not create independent questions. The separate 4,050-request matched study is included in the numerical bundle, not these Explorer panels. Featured examples use disclosed selection rules, sometimes conditioned on outcomes; use full panels to inspect frequencies. [Data definitions and selection rules](../../../docs/explorer/DATA.md).

## 2. Verify integrity, then recompute

### Obtain the source and create a minimal environment

These are POSIX/macOS shell commands, run from a checkout of this revision. A browser-only Explorer review does not require this checkout. If needed:

```sh
git clone --branch research/naacl2027-demo --single-branch https://github.com/UpHash-Network/mini-jev.git
cd mini-jev
```

The complete checkout also contains recordings and other research artifacts; its download is larger than the 18.06 MB numerical ZIP. To review only the six numerical analyses, the separate [frozen ZIP instructions](../reproducibility/REPRODUCIBILITY.md) avoid that full checkout.

Create a new environment without installing pip or third-party packages:

```sh
LOGITTRAIL_REVIEW_OUT="$(mktemp -d "${TMPDIR:-/tmp}/logittrail-review.XXXXXX")"
python3 -I -B -m venv --without-pip "$LOGITTRAIL_REVIEW_OUT/venv"
LOGITTRAIL_REVIEW_PY="$LOGITTRAIL_REVIEW_OUT/venv/bin/python"
```

`mktemp` creates a new scratch directory for both the virtual environment and results, outside the checkout and immutable bundle. Retain its reports if needed; each replay destination must be new.

### Quick integrity and accounting check

From the checkout root:

```sh
env -u PYTHONPATH -u PYTHONHOME PYTHONNOUSERSITE=1 \
  "$LOGITTRAIL_REVIEW_PY" -I -B \
  paper/naacl2027/nonhuman_revision_20260927/check_evidence.py \
  --output "$LOGITTRAIL_REVIEW_OUT/evidence-checks.json"
```

A passing report confirms the pinned ZIP, its exact member set and 353 source/record file hashes, and the request counts: **4,050 + 7,600 + 14,400 = 26,050**. The 300 earlier pilot rows remain excluded. It also retains the original LMQL **3/12 probability-tolerance failures** despite all 12 label matches, and checks the recorded ChainForge **4 request pairs / 8 typed-answer pairs**. It does not rerun either framework or replace the numerical analyses below.

To verify that the Explorer's static data match a deterministic export of the frozen evidence:

```sh
env -u PYTHONPATH -u PYTHONHOME PYTHONNOUSERSITE=1 \
  "$LOGITTRAIL_REVIEW_PY" -I -B scripts/build_evidence_explorer.py --check
```

`--check` compares inventory and bytes without replacing `docs/explorer/data/`. It performs more work than opening a single browser panel. It is an integrity check, not an independent scientific validation of the original measurements.

### Recompute the six numerical analyses

The archive must have SHA-256:

```text
a15e0699a54be15d56bd99ed8181429b71fdfc7ace756d6e065a75538786c053
```

The extraction utility verifies that hash, the file manifest, CRCs, and member paths before writing to a new destination. It uses only the standard library and does not execute or alter frozen scripts. Keep the shell variables from the setup step:

```sh
env -u PYTHONPATH -u PYTHONHOME PYTHONNOUSERSITE=1 \
  "$LOGITTRAIL_REVIEW_PY" -I -B \
  paper/naacl2027/reviewer_20261002/verification/safe_extract.py \
  --archive paper/naacl2027/reproducibility/naacl-repro-v1-20260925.zip \
  --output "$LOGITTRAIL_REVIEW_OUT/bundle"

env -u PYTHONPATH -u PYTHONHOME PYTHONNOUSERSITE=1 \
  "$LOGITTRAIL_REVIEW_PY" -I -B \
  "$LOGITTRAIL_REVIEW_OUT/bundle/mini-jev/verify_bundle.py"

env -u PYTHONPATH -u PYTHONHOME PYTHONNOUSERSITE=1 \
  "$LOGITTRAIL_REVIEW_PY" -I -B \
  "$LOGITTRAIL_REVIEW_OUT/bundle/mini-jev/reanalyze.py" \
  --output "$LOGITTRAIL_REVIEW_OUT/reanalysis"
```

The frozen wrapper copies the verified bundle into the new replay directory before executing analyzers. It writes `REANALYSIS_CHECKS.json` and one log per analysis there. A successful run reports **6 steps / 56 byte-identical derived files**. Inspect the per-file hashes in that receipt rather than treating a successful import as a replay. No analysis writes to the checkout's retained results or to the original bundle.

The virtual environment excludes system-site packages and contains no installed third-party packages. Top-level Python commands use `-I`; the frozen wrapper's child processes do not inherit that flag and intentionally import from their verified analysis-source working directory. They use the same fresh virtual-environment interpreter with `PYTHONPATH`/`PYTHONHOME` removed and user-site loading disabled. No frozen script is patched to make this work.

### Optional Explorer software tests

These exercise integrity and comparison/export arithmetic; they do not operate a real model or measure a person using the interface:

```sh
env -u PYTHONPATH -u PYTHONHOME PYTHONNOUSERSITE=1 \
  "$LOGITTRAIL_REVIEW_PY" -I -B -m unittest discover \
  -s tests -p test_evidence_explorer.py -v

node tests/test_evidence_core.mjs
```

Node is only needed for the last command, not for opening the Explorer, Python integrity checks, or six-analysis replay. No npm installation is required. The actual tested versions, timing, results, and resource measurements are recorded with this revision below; they are observations on one machine, not performance guarantees.

## Fresh verification receipt

The October 2 run passed on macOS 26.4/arm64, using Python 3.10.5 in a fresh `--without-pip` environment with **zero installed third-party distributions**. Node **v23.0.0** was used only for the optional JavaScript test. The tracked source was copied locally with `git archive`; source download time is not included. The original source and extracted bundle were verified unchanged after execution.

| Actual command/check | Result | Observed wall time |
|---|---|---:|
| Integrity/accounting | 353 manifest files; 26,050 measured request rows; 300 background rows excluded | 0.48 s |
| Frozen numerical replay | 6 analyses; 56/56 output files byte-identical | 6.11 s |
| Explorer deterministic rebuild check | 19 files / 12,985,578 bytes identical | 6.45 s |
| Explorer Python tests | 21 passed; 0 skipped | 14.26 s |
| Optional Node tests | 31,000 comparisons; 3,600 item export round trips; invalid cases rejected | 0.58 s |
| Full recorded verification, including snapshot/environment setup and verification | All checks passed | 29.88 s |

These timings are one observed run, not a deadline or performance guarantee. The extracted numerical bundle occupied 101.84 MB of logical file data; replay outputs including its isolated source copy occupied another 119.44 MB. This audit's full scratch area, including the tracked snapshot and tar copy, contained 593.43 MB. The largest reported command resident-set watermark was about 670 MB (Explorer Python tests); replay reported about 194 MB. These are observed resource measurements, not validated minimum-memory requirements. No weight download, accelerator, paid API, model service, or native compilation was involved.

- [Reviewer-entry link and static HTTP checks](ENTRY_CHECKS.json); this is separate from browser interaction testing.
- [Execution provenance and command results](verification/RUN.json): fresh source identity, virtual-environment setup, actual commands, elapsed time, platform, and scope.
- [Fresh integrity/accounting result](verification/EVIDENCE_CHECKS.json).
- [Fresh six-analysis result and per-file hashes](verification/REANALYSIS_CHECKS.json).
- Command output logs under [`verification/`](verification/); path placeholders identify source, work, virtual environment, bundle, and replay roots without publishing a personal home path.

The historical receipts in `reproducibility/`, `nonhuman_revision_20260927/`, and other study directories are preserved byte for byte. This new receipt records a separate execution; it does not redate or replace those audits. The source snapshot predates this guide's documentation and media edits; its executed checker, exporter, tests, and frozen bundle are identified by hashes in the receipt.

## 3. Optional: run new inputs through the local model

This route is independent of the static Explorer. Stop the static server if no longer needed, then follow the [native setup](../../../README.md#run-the-native-service), [native build details](../../../NATIVE_BUILD.md), and [live workbench guide](../../../demo/README.md#start-the-demo). From a repository checkout, the main commands are:

```sh
./build_native.sh --work-dir .build/native --output .build/runtime --jobs 2
python3 fetch_native_model.py --output models/Qwen3.6-35B-A3B-Q4_K_M.gguf
./run.sh --without-calibration
```

In another terminal at the same checkout:

```sh
python3 -m demo.server
```

Open `http://127.0.0.1:8766/`. This live service requires Apple Silicon/macOS, Python 3.10+, CMake, Git, and Xcode command-line tools. The historical tested runtime used macOS 26.4 and 64 GB unified memory. That memory size is the tested machine, not an established minimum. The model alone is approximately 20.4 GB; compilation, runtime memory, downloads, and startup are additional costs. Other native platforms and lower-memory configurations are not validated here.

The October 2 reviewer verification does **not** rebuild this runtime, download weights, call the model API, or add predictions. The earlier [same-Mac native build and smoke receipt](../reproducibility/README.md) is separate and reused pre-existing source/model caches. It is not a fresh-machine installation claim. A full new inference reproduction also requires upstream data retrieval and new output directories; follow the frozen study protocols and never edit a historical freeze to force success.

## What these checks do not show

Byte-identical analysis confirms calculations on retained observations. It does not establish training-data independence, new model generalization, a latency advantage, calibration of candidate probabilities, or a human usability gain. The model/runtime comparisons differ in precision and backend as well as checkpoint; they do not isolate model size. The request counts are not counts of independent questions.

Original code uses MIT terms. Dataset-derived records, selections, and rubrics retain the documented CC BY-SA 4.0 attribution and share-alike terms; third-party models and runtime components retain their own terms. Weights, compiled native binaries, and original external benchmark text are not bundled. See [NOTICE.md](../../../NOTICE.md) and the [frozen bundle's distribution boundary](../reproducibility/REPRODUCIBILITY.md#distribution-boundaries).
