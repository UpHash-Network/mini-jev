# LogitTrail

**29 September 2026: Mini Jev is now LogitTrail.** The new name avoids confusion with the distinct [r-ms/mini-jev](https://github.com/r-ms/mini-jev) project. Existing URLs and API identifiers remain compatible. The submitted arXiv version and historical records retain their original names. [Name and version mapping](NAMING.md).

[Project page](https://uphash-network.github.io/mini-jev/) — current manuscript, demonstration video, evaluation evidence, and installation links.

**Use a local language model as a typed decision function, without generating answer text.**

[日本語](README.ja.md) · [Current paper](paper/naacl2027/README.md) · [Reviewer quick start](paper/naacl2027/reviewer_20261002/README.md) · [Optional live setup](#run-the-native-service) · [Train on your data](TRAINING.md)

LogitTrail turns a state and a question into a choice, a true/false score (`Noul`), or an ordinal score. It reads candidate next-token logits, normalizes them, and constructs the typed response in Python. The released inference configuration uses a **frozen Qwen3.6-35B-A3B Q4_K_M model**, repeated input, and type-specific candidate tokens. It does **not** use a trained decision head.

This independent project is inspired by [TypeSafe's Jev interface](https://docs.typesafe.ai/api). It is not affiliated with TypeSafe and does not reproduce Jev's architecture, RLCD, calibration guarantees, SDK compatibility, or reported speedups. Candidate-logit classification and prompt repetition have prior work; this release contributes an inspectable implementation and empirical record, not a claim of a new algorithm.

## Start here — no model required

**Reviewer entry updated 2 October 2026.** Begin with the saved evidence; installation of a language model is optional. The continuing NAACL 2027 System Demonstrations manuscript has not been submitted, accepted, or peer reviewed. The earlier arXiv submission and historical audits remain separate, unchanged artifacts. The recorded arXiv status on 27 September was awaiting moderation; this guide does not verify a newer moderation status.

1. **Explore saved decisions in your browser:** [open the evidence Explorer](https://uphash-network.github.io/mini-jev/explorer/). Select one item and compare two recorded conditions, semantic probabilities, typed values, shared physical-call counts, and source references. There is no model, API key, inference service, or installation to start this hosted view.
2. **Verify and recompute with Python:** follow the [standalone reviewer guide](paper/naacl2027/reviewer_20261002/README.md). It separates a quick integrity/accounting check from the six frozen analyses and their 56 expected output files. Python 3.10+ and its standard library suffice; no pip packages or weights are required. The frozen analysis archive is **18,060,014 bytes**. Fresh same-Mac isolated-environment commands, timings, and results are included in the guide.
3. **Optionally run live on a Mac:** use [native installation](#run-the-native-service), then [start the browser workbench](demo/README.md#start-the-demo). This separate path builds a native runtime and downloads a **20.4 GB** model; the measured hardware had **64 GB** unified memory. It is not needed for steps 1–2.

[Read the current manuscript PDF](docs/assets/LogitTrail_Manuscript.pdf) · [Watch the current LogitTrail demonstration](docs/assets/LogitTrail_Demo_20261002.mp4) (127.08 seconds; [transcript](publication/revision-20261002/video/TRANSCRIPT.en.md)) · [Reviewer commands and actual verification receipts](paper/naacl2027/reviewer_20261002/README.md).

The current video shows saved-Explorer interaction plus a clearly labeled 16-second archival live-interface excerpt, with silent embedded English captions. It adds no new inference. Earlier recordings remain available: [60-second evidence walkthrough](docs/assets/LogitTrail_60s.mp4), which explains retained results, and [145-second Mini Jev interface recording](docs/assets/Mini_Jev_Demonstration.mp4), captured under the former name. Neither adds new experimental measurements.

## Evidence in the current paper

| Study or check | What it supports |
|---|---|
| 4,050 matched-study requests | Identical direct-readout and native one-token labels/logits in all **1,350 matched pairs**; no established latency advantage |
| 7,600 presentation-sensitivity requests | Changing candidate presentation can change decisions; reduced sensitivity can coexist with incorrect or nearly constant answers |
| 14,400 averaging-study requests | Probability averaging uses multiple model calls and does not consistently improve task quality |
| CPU-only analysis replay | **56 / 56** derived files reproduced byte for byte from retained records |

The three studies total **26,050 measured requests**, not 26,050 independent questions. The latter two span three checkpoints. Model comparisons also differ in runtime and precision; they do not isolate model size. Task-quality evaluations use Japanese public-data subsets on one Apple Silicon Mac, with unknown training-data contamination. There is no human usability study or second-machine replication.

The [paper package](paper/naacl2027/README.md) includes protocols, retained predictions, analyzers, and controlled LMQL/ChainForge integration diagnostics. [Scope and limitations](https://uphash-network.github.io/mini-jev/#evidence) explain what can and cannot be concluded. The original 2,400-item AI-authored regression suite is a separate historical evaluation, documented below.

The September 27 revision adds a comparison appendix and a post-hoc analysis of the same 12 LMQL cases; all three original probability-tolerance failures remain. The public API/UI expose typed values, candidate probabilities, and semantic metadata; candidate token IDs and raw logits are retained internally and in research traces. No new inference or human-study results are added.

The [October 2 matched workflow check](paper/naacl2027/workflow_comparison_20261002/README.md) gives the Explorer, a [complete JSON view](https://uphash-network.github.io/mini-jev/explorer/json/), and unmodified ChainForge 0.3.7.6 the same six hash-selected saved cases. ChainForge's native search, full-text responses and exports retain all supplied evidence: 12 condition records, 52 exact spreadsheet probability values, and six exact full-payload flow exports. The adapter supplies derived alignment and call counts; this establishes information retention, not human efficiency or LogitTrail superiority. [A pilot packet for the actual Explorer](paper/naacl2027/explorer_user_evaluation_20261002/README.md) is prepared; no human observations have been collected.

The [raw-logit follow-up](paper/naacl2027/raw_workflow_20261002/README.md) executes custom diagnostic JavaScript inside ChainForge's native Processor. From 6,000 archived records it reconstructs 2,400 conditions, including semantic probabilities, shared-call counts and panel summaries, within the frozen 1e-12 tolerance. No predicted answers or diagnostic summaries are supplied as input; gold references and member recipes are supplied. This demonstrates competitor feasibility with custom code, not a measured LogitTrail advantage. [A portable replication handoff](paper/naacl2027/external_replication_20261002/README.md) separates CPU evidence checks from actual second-Mac inference; external execution remains pending.

The [local JSONL importer](https://uphash-network.github.io/mini-jev/explorer/import/) accepts your own physical decision records using a [documented v1 format](docs/explorer/import/README.md). It aligns semantic candidates, shows typed values and optional references, and exports exact source records. Files stay in the browser tab; missing references and latency remain unknown. This general-purpose import route is a software addition, not new evidence of usability or diagnostic superiority.

## Explore recorded decisions

Open the [evidence explorer](https://uphash-network.github.io/mini-jev/explorer/) to compare two retained conditions for the same study, model, and source item. The view aligns probabilities by semantic answer key, distinguishes expected stage from most likely stage, counts shared physical calls once, and exports source references with the comparison. It reads the frozen records; it does not run a model or establish human usability gains. [Data scope and derivation](docs/explorer/DATA.md).

The Explorer was introduced on September 28; the October 2 reviewer entry connects it to lightweight checks and the retained analyses. The already submitted arXiv files remain unchanged. Featured examples are deterministic illustrations; the full eligible panels remain browsable.

## Run the native service

The tested native path requires an Apple Silicon Mac with macOS 26.4+, Python 3.10+, Xcode command-line tools, CMake, and Git. The pinned model download is **20.4 GB**. Model weights and prebuilt native binaries are not included in the source repository. Other platforms are not validated for this native path.

Check out the research branch first:

```sh
git clone --branch research/naacl2027-demo --single-branch https://github.com/UpHash-Network/mini-jev.git
cd mini-jev
```

From that repository directory:

```sh
# Build the pinned llama.cpp revision and decision helper.
./build_native.sh --work-dir .build/native --output .build/runtime --jobs 2

# Download and verify the pinned GGUF.
python3 fetch_native_model.py --output models/Qwen3.6-35B-A3B-Q4_K_M.gguf

# A new runtime needs its own calibration. Start at T=1 first.
./run.sh --without-calibration
```

Keep the service running; in another terminal:

```sh
curl -fsS http://127.0.0.1:8765/health
curl -fsS http://127.0.0.1:8765/v1/systemone \
  -H 'Content-Type: application/json' --data-binary @request.json
```

Stop with Control+C. Startup verifies the model file and native artifacts before loading. [NATIVE_BUILD.md](NATIVE_BUILD.md) covers build details. For another location, copy `native_config.json` to `my_config.json`, change `model_file`, `native_binary`, and `native_manifest`, then use `./run.sh --config my_config.json --without-calibration`.

## Python client

Run from the repository directory with the service running. The native service and client need only the Python standard library.

```python
from service import Client, Choice, Noul, Score

with Client() as client:
    result = client.system_one(
        state="HP is 20%. One potion is available. Heal when HP is below 30%.",
        questions={
            "action": Choice("Which action follows the rule?", {
                "heal": "Use the potion", "wait": "Wait"
            }),
            "low_hp": Noul("Is HP below 30%?"),
            "danger": Score("Which HP band applies?", [
                "HP >= 70%", "30% <= HP < 70%", "HP < 30%"
            ]),
        },
    )
    print(result.choices["action"].choice)
    print(result.nouls["low_hp"].noul)
    print(result.scores["danger"].score)
```

The English example demonstrates the interface; the reported quality evaluation is Japanese. Choice returns a semantic key; Noul returns the true candidate's probability; Score returns the expected zero-based stage, with the most likely stage in `label`.

Probabilities are normalized **within the allowed candidate set**, not over all tokens or all real-world outcomes. `confidence` is one minus normalized entropy, not the probability the answer is correct. [API details](service/README.md) · [Architecture](ARCHITECTURE.md)

## Train on your own data

**[TRAINING.md](TRAINING.md)** documents the reusable JSONL workflow: validation, frozen-backbone feature extraction, residual-head or bias-only training, separate temperature fitting, and held-out evaluation. This experimental path is separate from the native 35B configuration. Check that guide for supported models, dependencies, and tested devices.

The earlier Qwen2.5-1.5B experiment is included: a 9,222-parameter residual head decreased held-out top-label accuracy from **73/96 to 67/96**; a bias-only correction scored 74/96. We do not promise that training improves your task. [Original experiment](HEAD_TUNING.md)

## Historical local evaluation — 20 September 2026

| September 20, 2026 local evaluation | Result |
|---|---:|
| Final Japanese suite | **2,238 / 2,400 = 93.25%** |
| Choice / Noul / Score top-label accuracy | 96.00% / 95.25% / 88.50% |
| Individually AI-authored subset | 172 / 180 = 95.56% |
| Warm single-question engine p95, complete input ≤512 tokens | **379.1 ms**; 2,291 questions |
| Complete input >512 tokens | p95 521.8 ms; 109 questions |
| Valid typed outputs | 2,400 / 2,400 |

Measured on **Apple M5 Pro, 64 GB, macOS 26.4, Metal**, with the model resident. Timing includes the complete repeated prompt; it is not cold-start time or an HTTP service SLA. Multi-question requests execute questions sequentially. This historical run did not include a same-model generation baseline. A separate [completed v0.2 matched comparison](paper/matched_study/README.md) measures 4,050 requests: direct and one-token labels/logits match in all 1,350 pairs, with no demonstrated material latency gap in this session. JSON adds about 160 ms to the primary local paired statistic under a serialization-specific prompt; quality varies by task. These research-HTTP timings are separate from the historical measurements above.

The suite is **self-authored**: 2,220 programmatically generated items across 45 template families and 180 individually authored by AI agents, with AI peer review. The legacy field `source: manual` does **not** mean human-expert annotation. New v2 instances were held out from final model selection, but authoring had seen some v1 errors and retained related skill families. This is not an external benchmark or a family-disjoint test. See [DATA_CARD.md](DATA_CARD.md).

Failures remain: delay-from-promised-time 29/49, conditional obligation 31/49, and counts after cancellation 33/49. Temperature scaling slightly improved NLL but worsened ECE and Score expectation MAE. [Full results and limitations](paper/TECHNICAL_REPORT.md#results)


## Reproduce the historical 2,400-item suite

- [2,400 questions as CSV](acceptance-v2/questions_2400.csv) / [JSONL](acceptance-v2/questions_2400.jsonl), with answers and family labels.
- [Final report](results/native-acceptance/REPORT.md), [summary](results/native-acceptance/summary.json), [predictions](results/native-acceptance/predictions.jsonl), and [historical freeze](results/native-acceptance/freeze.json).
- [Numerical/API validation](VALIDATION.md) and [empirical technical report](paper/TECHNICAL_REPORT.md).

```sh
# CPU checks without model loading.
python3 -m unittest service.test_service test_native_engine
python3 -m unittest discover -s acceptance-v2 -p test_runner.py
python3 -m unittest discover -s native -p test_packaging.py

# Fit temperature on the separate 120-item calibration split.
python3 acceptance-v2/run_acceptance.py calibrate --config evaluation_config.json \
  --output-dir .runs/my-calibration

# Run 2,400 items plus 800 reversed Choice-map checks.
python3 acceptance-v2/run_acceptance.py evaluate --config evaluation_config.json \
  --temperature-config .runs/my-calibration/temperature.json \
  --output-dir .runs/my-evaluation
```

Each output directory must be new. To serve with the new calibration, run `./run.sh --temperature-config .runs/my-calibration/temperature.json`. If you change model or runtime paths, update the matching fields in both service and evaluation configurations. Calibration is bound to model, prompt code, native artifacts, configuration, and Python/OS. Published questions support replication and regression; after using them to improve a model, they are not a fresh held-out test. Public historical logs have local paths redacted; historical freeze hashes describe original bytes, not every redacted file. See the publication provenance record for transformations.

## Limits and contributions

The API accepts 2–26 candidates, defaults to eight questions (configurable up to 16), and rejects complete inputs beyond 2,048 tokens. Quality evaluation covers 2–8 candidates; 26-candidate testing is functional coverage only. Choice keys are sorted, so reversed-map agreement demonstrates canonicalization, not learned position invariance. Questions do not share prefill or execute in parallel. The server is loopback-only.

AI coding agents contributed implementation, question authoring, review, experiments, and documentation under the owner's direction. Agent review is not independent human review. The [working-paper package](paper/README.md) contains the completed v0.2 empirical study of one model on one device: direct readout versus one-token and JSON generation, plus [600 external examples](paper/external_expanded/README.md) from JCoLA, JSTS, and JCommonsenseQA. The existing JNLI pilot is separate. These public datasets may have been seen during model training and cannot be pooled into one accuracy. All 4,050 scheduled comparison requests completed without failure. Protocols, traces, analysis, tests, and an independent AI-agent numerical audit are included; this is not human peer review. The older v0.2 working draft is historical; the current preprint and conference-preparation status are stated above.

Useful next contributions include family-disjoint evaluations, substantive repeated training experiments, and measured runs on other models and hardware. See the [current paper and evidence](paper/naacl2027/README.md); the original technical report retains its historical research plan.

Use [CITATION.cff](CITATION.cff) to cite the software. Original project code and local authored data are MIT licensed. External dataset-derived selection, metadata, results, and task protocols/rubrics use CC BY-SA 4.0 with JGLUE/JCoLA attribution; mixed study records retain that data boundary. Third-party code and model artifacts retain their own terms. Original external dataset text, compiled binaries, and model weights are not included. See [NOTICE.md](NOTICE.md).
