# Success criteria and failure interpretation

These criteria apply to the exact pinned source. They do not require another machine to reproduce native binary hashes, exact probabilities or timing from the author's Mac.

| Route/check | Expected observation | Interpretation if it differs |
| --- | --- | --- |
| Pinned source | Commit `3ac8c7b482f93df78e66d3936680bc4bf6194eb2`; selected hashes in `SOURCE_PIN.json` match | Wrong revision, newline conversion or edits; keep the failure and obtain a separate clean checkout |
| Frozen numerical ZIP | 18,060,014 bytes; SHA-256 `a15e0699a54be15d56bd99ed8181429b71fdfc7ace756d6e065a75538786c053` | Do not analyze an unverified bundle |
| CPU integrity | 353 manifest files; exact archive membership/CRCs/hashes; 26,050 measured rows and 300 excluded background rows | Preserve report and specific mismatch; not a successful replay or validation |
| Existing output protection | Integrity checker returns code 2 with `Output exists`; earlier receipt is unchanged | Potential destructive workflow issue; use a new output and report it |
| Metadata-only command | Pinned 20,419,565,568-byte model/revision/hash; no GGUF created or downloaded | Resolve metadata/source identity before using a model |
| Missing model negative check | Downloader `--verify-only` returns 1 with `completed model file is missing` | This is the **expected rejection**, not an installation failure or a model download |
| Wrong-size negative check | Returns 1 with `size mismatch`; test file preserved, no verified receipt | This is the **expected rejection**; a successful return would be a defect |
| Config inspection | T=1; `temperature_config: null`; no native model load | Correct config path or flags; do not silently apply historical calibration |
| Offline scorer | Historical three-type receipt passes; all nine in-memory corruptions rejected | Scorer/software issue; no inference or human response was generated |
| Optional CPU replay on macOS/Linux/WSL | Six completed steps; all 56 derived files byte-identical | Retain per-file differences and logs; no tolerance change or frozen-input patch |
| Native package | Newly built package verifies against its own `BUILD.json` | Build/source/platform issue; preserve full logs and compiler/SDK versions |
| Live health | `ready: true`, pinned model and revision | Not ready means no valid inference should be sent; model load happens before listener startup |
| Live input rejections | Three invalid requests return HTTP 422 with error objects | Stop and preserve responses; expected rejection before inference was not established |
| Live response contract | All three question IDs/types; finite normalized candidate probabilities; label is a probability maximum; Choice equals label; Noul equals P(true); Score equals expectation; zero output tokens; concentration semantics intact | A contract mismatch, separately from whether the model chooses the intended answer |
| Historical example sanity | Choice `heal`, Noul label `true`, Score label `2` | Record as changed behavior; a valid contract can coexist with a different answer. No hidden tuning/retry-until-pass |
| HTTP transport failure evidence | Method/path/status retained before parsing; raw UTF-8/JSON failures retained as bytes, with a 1 MiB cap; connection refusal has null status plus transport error | No absent response may be fabricated; preserve partial/capped evidence and stop |
| Other-machine/operator result | Completed operator log + actual new receipts; machine and operator relationship disclosed | Without this, report only preparation/local validation, not external replication |

## Practical errors

- `venv` unavailable on Linux: install the platform's Python venv component or use an already approved Python 3.10+ installation; record the change. Do not treat installing third-party ML packages as necessary for CPU evidence checks.
- Windows decoding error or hash mismatch: keep files in UTF-8 and disable Git newline conversion. Route A sets UTF-8 explicitly. For strict route-B replay use Linux/WSL and `PYTHONUTF8`; frozen default text writers may emit CRLF on native Windows, so native Windows byte identity is not claimed. Do not normalize or rewrite historical outputs and call that an unmodified replay.
- `ModuleNotFoundError: service` while printing native config: the real entry point imports the pinned repository. Run the documented command or packet runner; adding Python `-I` directly to that application entry point removes its source import path.
- Native platform error: the build targets macOS ARM64, outside Rosetta, with deployment target 26.4. Linux/Windows users should use CPU routes; no claim of validated native inference on those platforms is made.
- Existing native build/output: do not overwrite a previous runtime. Choose new work/output directories and explicitly update config paths; a reused CMake cache is rejected.
- Model size/SHA mismatch: keep the failing file for diagnosis. Downloader never accepts it as the completed pinned model. A `.partial` can resume, but a stale download lock must only be removed after its process has ended.
- Connection refused: `/health` is not available until model verification/load completes. Inspect the native log; do not report a pass based solely on `--print-config`.
- HTTP 503/504: busy/not ready or deadline exceeded. Record the original response and system state before a separately logged retry. Timed-out native work may still be running.
- Memory pressure: model weights alone occupy about 20.4 GB on disk, with extra runtime memory required. Stop other work or use appropriate hardware; lower-memory success is not established by this packet.

Keep failed logs and original outputs. Sharing receipts is optional and must omit credentials and unnecessary identifying paths. No instruction here sends an invitation or uploads data.
