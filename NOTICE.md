# Attribution and artifact boundaries

Original Mini Jev code, documentation, and project-authored example/evaluation data are distributed under the root MIT license. Copyright (c) 2026 MiniJev contributors. The project was developed by Yuki Oshio with substantial AI assistance, including code, individual question writing, synthetic question generators, and agent review.

Third-party code, datasets, and model weights retain their own licenses. The root MIT license does not relicense model weights, external datasets, or third-party components.

The external JNLI pilot is an explicit data-license exception: `paper/external_pilot/SELECTION.json`, `paper/external_pilot/AUDIT.json`, and dataset-derived records in `paper/external_pilot/results/` use **CC BY-SA 4.0**, with attribution to JGLUE/Yahoo Japan Corporation and Kawahara Lab, Waseda University. See `paper/external_pilot/README.md` and `LICENSE-DATA.txt` for source attribution, modifications, and exact scope. Original JNLI sentence text is not included. The runner and tests remain project-authored MIT code.

- llama.cpp: MIT, fixed revision `f072b103714dfa1eee531f80b24512faf38e3dd2`; see `native/LICENSE-llama-cpp.txt`.
- Native helper: MIT; see `native/LICENSE-helper.txt`.
- Native dependencies: original notices in `native/licenses/` include nlohmann/json, cpp-httplib, SHA-256, xxHash, and rotate-bits.
- Qwen3.6-35B-A3B model: upstream Apache-2.0 notice is retained in `native/licenses/LICENSE-Qwen3.6-Apache-2.0.txt`. Weights are downloaded separately and are not in this repository.
- Other Qwen models used in historical experiments and optional training: obtain the models from their upstream model repositories and consult their model cards and license files.

Mini Jev is an independent experiment inspired by TypeSafe's typed decision interface. It is not affiliated with TypeSafe and does not reproduce Jev's internal architecture, training procedure, calibration guarantees, or reported performance.

Historical result files describe specific past experiments. The public source checkout excludes compiled native binaries, model weights, temporary environments, and machine logs not needed to interpret results. Local paths in retained historical records may be redacted; see `publication/SANITIZATION.json` for the transformation inventory. Historical freeze hashes refer to the original measured artifacts, not rebuilt binaries or revised public documentation.
