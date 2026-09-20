# Attribution and artifact boundaries

Original Mini Jev code, documentation, and project-authored example/evaluation data are distributed under the root MIT license. Copyright (c) 2026 MiniJev contributors. The project was developed by Yuki Oshio with substantial AI assistance, including code, individual question writing, synthetic question generators, and agent review.

Third-party code, datasets, and model weights retain their own licenses. The root MIT license does not relicense model weights, external datasets, or third-party components.

External research data are explicit exceptions to the root MIT license:

- JNLI, JSTS, and JCommonsenseQA originate from JGLUE, by Kentaro Kurihara, Daisuke Kawahara, and Tomohide Shibata through Yahoo Japan Corporation and Kawahara Lab, Waseda University. The pinned dataset license is **CC BY-SA 4.0**; copies are in `paper/external_pilot/LICENSE-DATA.txt` and `paper/external_expanded/LICENSE-JGLUE.txt`.
- JCoLA originates from Taiga Someya, Yushi Sugimoto, and Yohei Oseki and is distributed separately by osekilab. Its pinned **CC BY-SA 4.0** license is preserved in `paper/external_expanded/LICENSE-JCoLA.txt`.
- Dataset-derived selection, gold labels, hashes, dependence groups, audits, prediction records, and aggregate results in `paper/external_pilot/` and `paper/external_expanded/` retain **CC BY-SA 4.0**. The external task protocols and their dataset-derived prompt/rubric material also use that license; in particular, the JSTS rubric paraphrases the attributed official annotation guidelines. See the [JNLI description](paper/external_pilot/README.md) and [expanded-data description](paper/external_expanded/README.md) for pinned sources and modifications.
- `paper/matched_study/preparation/SELECTION.json` and external dataset-derived records in `paper/matched_study/results/` have the same **CC BY-SA 4.0** data boundary. Redistribute mixed local/external selection or prediction files under CC BY-SA 4.0 with both source attributions. This does not remove the MIT license from the original project-authored local questions. Copies or extracts of external task protocols/rubrics retain their CC BY-SA 4.0 attribution wherever included.

Python and C++ source, tests, build tools, generic experimental-method protocols, and original explanatory documentation remain project-authored **MIT** material, except for clearly attributed embedded external data or rubric adaptations. The standalone `paper/matched_study/PROTOCOL.json` describes the project-authored comparison method; referencing an external dataset does not relicense that dataset as MIT. Purely synthetic warm-up data remain project-authored material. Machine-readable records combining multiple sources must preserve the respective underlying notices.

Modifications to external material include deterministic subsampling, omission of source text, hashing, grouping, fixed question formatting, rubric paraphrasing, model predictions, and aggregate evaluation. No dataset-creator endorsement is implied. Original external sentences, questions, and answer-option text are downloaded to a separate local cache and are not redistributed in this source package. The license copies and applicable attributions accompany the derived records.

- llama.cpp: MIT, fixed revision `f072b103714dfa1eee531f80b24512faf38e3dd2`; see `native/LICENSE-llama-cpp.txt`.
- Native helper: MIT; see `native/LICENSE-helper.txt`.
- Native dependencies: original notices in `native/licenses/` include nlohmann/json, cpp-httplib, SHA-256, xxHash, and rotate-bits.
- Qwen3.6-35B-A3B model: upstream Apache-2.0 notice is retained in `native/licenses/LICENSE-Qwen3.6-Apache-2.0.txt`. Weights are downloaded separately and are not in this repository.
- Other Qwen models used in historical experiments and optional training: obtain the models from their upstream model repositories and consult their model cards and license files.

Mini Jev is an independent experiment inspired by TypeSafe's typed decision interface. It is not affiliated with TypeSafe and does not reproduce Jev's internal architecture, training procedure, calibration guarantees, or reported performance.

Historical result files describe specific past experiments. The public source checkout excludes compiled native binaries, model weights, temporary environments, and machine logs not needed to interpret results. Local paths in retained historical records may be redacted; see `publication/SANITIZATION.json` for the transformation inventory. Historical freeze hashes refer to the original measured artifacts, not rebuilt binaries or revised public documentation.
