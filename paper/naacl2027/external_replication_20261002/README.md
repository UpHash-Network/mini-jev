# External replication handoff — 2 October 2026

This packet lets another operator check LogitTrail without author-specific paths. **It is preparation for external replication, not a completed third-party result.** A fresh local source/venv check passed on the existing Mac; no other operator or computer has run this packet. The CPU preflight is designed for macOS/Linux/native Windows, while strict numerical replay uses macOS/Linux or Linux under WSL; those other operating systems have not been executed here.

Choose one route:

| Route | Requirements | Successful result establishes |
| --- | --- | --- |
| **A. CPU evidence check** | Git, Python 3.10+ and its standard library; macOS/Linux/Windows; no model, accelerator or pip packages | Integrity and accounting of the retained evidence, plus validation of the independent smoke-response scorer |
| **B. Optional six-analysis replay** | Python 3.10+ on macOS/Linux, or Linux in WSL on Windows; new output directory | Six original analyses reproduce 56 saved files byte-for-byte; still no new inference |
| **C. Actual native inference on another Mac** | Apple Silicon/macOS 26.4+, Python 3.10+, Git, CMake, Xcode command-line tools; fixed **20,419,565,568-byte** GGUF and a locally built native runtime | A newly built service handles one three-question Choice/Noul/Score request and rejects three invalid requests |

A successful A or B does **not** establish C. Running the scorer against an old receipt is not a new model execution. Even C is one synthetic interface smoke, not an accuracy study, a latency comparison or validation of scientific generalization.

## Obtain the pinned source

Keep this packet in a separate folder from the pinned source, because it was prepared after the source revision. From a directory containing this packet as `external_replication_20261002`, obtain a sibling `mini-jev-source`:

```sh
git -c core.autocrlf=false clone --no-checkout --single-branch --branch research/naacl2027-demo https://github.com/UpHash-Network/mini-jev.git mini-jev-source
git -C mini-jev-source -c core.autocrlf=false checkout --detach 3ac8c7b482f93df78e66d3936680bc4bf6194eb2
git -C mini-jev-source rev-parse HEAD
```

The last output must be `3ac8c7b482f93df78e66d3936680bc4bf6194eb2`. Disabling newline conversion matters for byte hashes, especially on Windows. A full checkout includes recordings and research artifacts and is larger than the 18.06 MB frozen numerical ZIP. `SOURCE_PIN.json` identifies the selected files exercised by this packet; all 353 files inside the numerical ZIP are separately checked.

## A. Offline CPU preflight

Run the following from the common parent directory. On Windows PowerShell use `py -3` in place of `python3`; no shell activation, `env`, `mktemp`, Unix tools or pip are required.

```sh
python3 external_replication_20261002/portable_check.py --source mini-jev-source --output replication-cpu-01
```

The output directory must not exist. The script creates a fresh `--without-pip` virtual environment, verifies selected source hashes, then checks the original archive's exact members/hashes and request counts. It reads model metadata without downloading anything; exercises missing/wrong-size model rejection; checks configuration without loading a model; and scores the historical three-type response with nine deliberately corrupted in-memory controls.

Expected final output: `status: pass`. Inspect `replication-cpu-01/PREFLIGHT_RECEIPT.json`, `EVIDENCE_CHECKS.json`, `SCORER_CHECK.json` and the individual command logs. Success criteria are in [SUCCESS_CRITERIA.md](SUCCESS_CRITERIA.md).

Python launch commands use isolated mode except the native configuration-print command, which intentionally imports the verified source tree. Every subprocess uses the fresh no-pip interpreter with `PYTHONPATH`/`PYTHONHOME` removed and user-site imports disabled. Explicit UTF-8 mode and UTF-8 file I/O avoid relying on a Windows locale for Japanese records. This is not an OS security or network sandbox. No checked command requests a network operation.

**Actually performed here:** exact revision copied through local `git archive`, 663 tracked files, fresh no-pip Python 3.10.5 environment, zero GGUF files, zero third-party distributions, all nine preflight commands completed as expected. Integrity: 353 files / 26,050 measured rows / 300 excluded background rows. Scorer: three historical answers accepted and nine corruptions rejected. An initial passing preflight was repeated once after adding explicit UTF-8 handling for portability; the earlier receipt remains under `verification/initial_pre_utf8/`. The prior six-analysis/56-file replay was not repeated because no new analyzer issue was found. Receipts are in [verification/](verification/), with source/output/packet paths replaced by placeholders. No new model was built, downloaded or run. An initial local extraction guard stopped before extraction due to macOS `/var` symlink normalization; canonicalizing the scratch root resolved that preparation issue without changing source.

## B. Optional CPU replay on the operator's machine

Use this when the operator intends to establish numerical reanalysis on their own environment. It is **planned for that operator**, not part of this packet's new local execution.

For byte-identical replay, use macOS/Linux or a Linux environment under WSL on Windows. Native Windows is not a validated byte-identical replay target: frozen scripts use default text newline handling, which can produce CRLF instead of the frozen LF bytes. This is a source-inspection finding, not an observed Windows execution. Keep the frozen scripts unchanged. In the POSIX shell set UTF-8 for the wrapper and its child analyzers with `export PYTHONUTF8=1`, then:

```sh
python3 -X utf8 mini-jev-source/paper/naacl2027/reviewer_20261002/verification/safe_extract.py --archive mini-jev-source/paper/naacl2027/reproducibility/naacl-repro-v1-20260925.zip --output replication-bundle-01
python3 -X utf8 replication-bundle-01/mini-jev/verify_bundle.py
python3 -X utf8 replication-bundle-01/mini-jev/reanalyze.py --output replication-analysis-01
```

On Windows run this block in the Linux/WSL shell using its `python3`; native PowerShell remains supported for route A only. All extraction/replay output directories must be new. Expect six successful steps and 56 byte-identical outputs in `REANALYSIS_CHECKS.json`. A mismatch remains a mismatch: retain the files and logs; do not change a frozen input, expected hash or tolerance to force a pass. The original [reviewer guide](../reviewer_20261002/README.md) describes the previous same-Mac replay and isolated-environment option.

## C. Actual native inference on an Apple Silicon Mac

Run these commands **inside `mini-jev-source`**. Model and binaries are not included in the repository. A historical sentence in `service/README.md` describing a bundled native package should be read with the authoritative source-build instructions in `NATIVE_BUILD.md`.

```sh
./build_native.sh --work-dir .build/native --output .build/runtime --jobs 2
python3 native/package_runtime.py --verify .build/runtime
python3 fetch_native_model.py --output models/Qwen3.6-35B-A3B-Q4_K_M.gguf
python3 fetch_native_model.py --verify-only --output models/Qwen3.6-35B-A3B-Q4_K_M.gguf
./run.sh --without-calibration
```

Use new native work/output directories. The default config already points to the shown paths. If reusing a verified model elsewhere, `./run.sh --model-file /absolute/path/to/model.gguf --without-calibration` is supported; record that cache reuse rather than calling it a fresh download. Config-relative paths resolve relative to the config file, not the shell directory. Keep a copied config alongside the original or use absolute paths for all relocated artifacts.

Leave the service running. From a second terminal in the common parent directory:

```sh
python3 external_replication_20261002/smoke_contract.py --live http://127.0.0.1:8765 --output replication-native-01.json
```

This command explicitly makes one real inference HTTP request containing three sequential questions, plus three invalid requests expected to return 422 before inference. It uses no remote API and ignores proxy configuration. It requires `health.ready: true` and the pinned model revision. The independent scorer checks probabilities, typed values, Score expectation, concentration semantics, zero generated tokens and metadata. Failed/mismatched HTTP exchanges are recorded before JSON decoding: method, path, status, and up to 1 MiB of raw body bytes (base64, SHA-256 and a readable UTF-8 view). Invalid JSON/UTF-8 retains the bytes and decode error. Oversized bodies retain a marked prefix and are rejected without parsing; a connection failure records the transport error with null status because no response arrived. Do not overwrite an earlier receipt.

Historical labels on this one Japanese rule example were Choice `heal`, Noul `true`, Score modal stage `2`; these are sanity checks, not an accuracy rate. Historical input tokens were 813. Exact probabilities, binary hashes and latency need not equal the old Mac's results across compiler/runtime differences. A valid contract with changed labels is reported separately as `contract_pass_historical_labels_differ` and returns nonzero for review; do not silently tune away the difference. Detailed current runtime/OS/model information belongs in the operator log.

Stop the native service with Control+C after saving results. The optional browser workbench (`python3 -m demo.server`, port 8766) is unnecessary for this HTTP smoke.

## Resources and handoff records

- CPU: frozen ZIP 18,060,014 bytes; previous extraction 101.84 MB and replay plus isolated copy 119.44 MB. Full tracked source contains media and is larger. The current local source tar was 219,791,360 bytes. Allocate additional room for Git history, virtual environment and logs. Previously observed memory use is not a validated minimum; no GPU is required.
- Native: model alone **20.4 GB decimal**; additional disk for source, build, runtime and logs, and additional runtime memory. The tested machine had **64 GB unified memory**. This is an observed configuration, not proof that lower memory is sufficient or insufficient. No installation-time promise is made. Linux/Windows native inference is outside the validated path.
- Pin: GGUF SHA-256 `671e47e0ec53c665d048b98c3ecbfd5236b5ca9c3e02ed19fc8f81f7b85140c7`; model revision `baec3ebee244827cda0f4557eafa8b28f7545fa6`; llama.cpp commit `f072b103714dfa1eee531f80b24512faf38e3dd2`.

Copy and fill [OPERATOR_LOG.blank.json](OPERATOR_LOG.blank.json). Use an operator code and pseudonymous machine ID; do not add credentials or unnecessary personal paths. Record failed commands, workarounds, cache reuse and whether the machine/operator differs from the author. The preflight receipt itself leaves machine/operator relationships unverified; fill the manual log rather than inferring independence from automated checks. Historical local receipts keep their original, correctly labeled same-Mac scope. Only an actual externally completed log and receipts can support an external-replication statement. There have been no invitations or external responses.

A targeted October 3 correction verifies malformed JSON, HTTP 500, invalid UTF-8, oversized bodies and connection refusal with ephemeral standard-library HTTP fixtures. All five checks retained the expected failure evidence; no model or native service was involved, and no full preflight or numerical analysis was repeated. See [transport checks](verification/transport_20261003/TRANSPORT_CHECK.json). Reproduce only these checks with `python3 external_replication_20261002/check_transport.py --output transport-check-new` from the packet parent.

This packet adds code and documentation; earlier frozen artifacts and receipts remain unchanged. Model, dataset and runtime terms remain as documented in the source repository's `NOTICE.md` and licenses.
