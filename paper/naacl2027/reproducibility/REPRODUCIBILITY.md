# Mini Jev NAACL reproducibility bundle v1

This locally prepared artifact contains the application source and the recorded
**26,050 measured requests** used by the NAACL working paper: matched readout
(4,050), presentation sensitivity (7,600), and cyclic averaging (14,400).
Requests are not independent questions. The journal's later 16,300 requests are
outside this bundle. No submission or public release is implied.

## Start with the CPU-only path

Unzip to a new directory. From its `mini-jev` directory, use Python 3.10 or newer:

```sh
python3 verify_bundle.py
python3 reanalyze.py --output /absolute/new-directory/mini-jev-reanalysis
```

This path needs **no pip packages, network, model weights or accelerator**.
It preserves the bundle and runs the original frozen analyzers in an isolated
copy. The matched analyzer normally overwrites derived files, so the wrapper
only runs it in that copy. It compares recomputed files with the packaged
historical files and writes `REANALYSIS_CHECKS.json` and individual logs.
Reanalysis verifies the calculations over the recorded observations; it is
not new inference, a second machine experiment, or independent human review.

## Install and run the actual application

The Python service, SDK and demo require only the standard library. The tested
native path is Apple Silicon/macOS 26.4+, with Python 3.10+, CMake, Git and Xcode
command-line tools. The measured machine has 64 GB RAM. From `mini-jev`:

```sh
./build_native.sh --work-dir .build/native --output .build/runtime --jobs 2
python3 fetch_native_model.py --output models/Qwen3.6-35B-A3B-Q4_K_M.gguf
./run.sh --without-calibration
```

In a second terminal, from the same directory:

```sh
python3 -m demo.server
```

Open `http://127.0.0.1:8766/`. The model is downloaded separately: **20,419,565,568
bytes**, pinned by revision and SHA-256 in `native_model.json`. The runtime build
pins llama.cpp `f072b103714dfa1eee531f80b24512faf38e3dd2`. Build/download are not
part of inference latency. No model, native executable or shared library is
included. The old `native/BUILD.json` is historical metadata, not an installed
runtime. `build_native.sh` writes fresh `.build/runtime/BUILD.json`.

For a verified existing GGUF, copy `native_config.json` to
`native_config.local.json` **in the same `mini-jev` directory**, set its
`model_file` to that absolute GGUF file, and run
`./run.sh --config native_config.local.json --without-calibration`.
Other relative paths resolve from the configuration file's directory; keeping
the copy beside the original preserves their meaning.
Leave TLS/hash verification enabled; a cache reuse is
not a fresh download. See `demo/README.md`, `NATIVE_BUILD.md` and
`service/README.md` for the full operation and API boundaries.

Useful targeted CPU checks (test fake engines are not empirical evidence):

```sh
python3 -m unittest service.test_service test_native_engine demo.test_demo
python3 -m unittest discover -s native -p test_packaging.py
```

## Evidence navigation

| Evidence | Location |
|---|---|
| Every shipped file's exact hash | `BUNDLE_MANIFEST.json` |
| Matched 4,050 requests and original analysis | `paper/matched_study/` |
| Presentation sensitivity, 4,000 native + 3,600 small-model requests | `paper/journal_robustness/` and `cross_model/` |
| Averaging, 14,400 requests | `paper/order_ensemble/study_v1/` |
| Fixed native formatter and two-checkpoint adapter | `native_engine.py`, `paper/journal_robustness/cross_model/engine.py` |
| Source retrieval, hashes and dataset licenses | `paper/external_expanded/`, `paper/external_pilot/` |
| Exact 600-item averaging selection reconstruction | `paper/order_ensemble/materialize.py`, `README-data.md` |

The older `external_pilot/results/` contains 300 historical predictions retained
as background documentation. They are not counted in the 26,050 NAACL-study
requests or in the six analysis replays above.

The bundled application comes from the NAACL preparation checkout; the two
additional historical studies come from its frozen research checkout. The
manifest records both base commits and every actual file hash. This is an
explicit composition, not a claim that all content belongs to one public commit.
Legacy application documentation can refer to historical reports or manuscript
files outside this focused bundle; use the table above as its entry point.

## Full-inference replication boundaries

The study READMEs preserve the exact commands and frozen protocols. Raw external
texts must be reconstructed from the pinned upstream sources into a separate
cache. The small-model experiments also require pinned Transformers checkpoints
and runtime packages, described in `cross_model/README.md`. The frozen full
auditors require actual runtime/checkpoint files and can reject a new environment
even when CPU reanalysis succeeds. Do not edit historical freezes to force a
pass. Fresh runs use new output directories and new receipts.

The averaging preparer requires a Git checkout. This ZIP omits Git history and
does **not** claim that a ZIP alone can rerun the prospective history-based
selection procedure. Its exact-selection materializer and CPU reanalysis are
history-free. For fresh inference of the same selection, initialize a local
checkout of the supplied source and record the resulting local commit in the
new freeze; historical source-history exclusion evidence remains the shipped
`DATA_FREEZE.json`. New selections require a new documented exclusion inventory.

No humans were recruited or evaluated here. Same-Mac installation validation
and recorded numerical replay do not establish usability, cross-platform
portability, model generalization or a latency advantage over a competitor.

## Distribution boundaries

Original source code and project-authored local regression data use MIT;
dataset-derived selections, rubrics and numeric records retain **CC BY-SA 4.0**
with JGLUE/JCoLA attribution in the bundled notices/license files. Model and
third-party code retain their own licenses. Raw source questions, source token
sequences, credentials, account/mail records, model logs, weights and binaries
are excluded. `acceptance/private/` is the historical name of already-public
project-authored regression files, not user personal records.

Historical files are copied byte-for-byte. The file manifest and archive hash
identify this artifact; modifications create a different version. The compiler
and model cache reuse, actual smoke test, and analysis outcomes are recorded in
the companion validation receipt rather than asserted in advance.
