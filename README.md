# Mini Jev

**Use a local language model as a typed decision function, without generating answer text.**

[日本語](README.ja.md) · [Technical report](paper/TECHNICAL_REPORT.md) · [Working paper and v0.2 study](paper/README.md) · [Train on your data](TRAINING.md) · [Data card](DATA_CARD.md) · [Model card](MODEL_CARD.md)

Mini Jev turns a state and a question into a choice, a true/false score (`Noul`), or an ordinal score. It reads candidate next-token logits, normalizes them, and constructs the typed response in Python. The released inference configuration uses a **frozen Qwen3.6-35B-A3B Q4_K_M model**, repeated input, and type-specific candidate tokens. It does **not** use a trained decision head.

This independent project is inspired by [TypeSafe's Jev interface](https://docs.typesafe.ai/api). It is not affiliated with TypeSafe and does not reproduce Jev's architecture, RLCD, calibration guarantees, SDK compatibility, or reported speedups. Candidate-logit classification and prompt repetition have prior work; this release contributes an inspectable implementation and empirical record, not a claim of a new algorithm.

## What was measured

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

## EACL demonstration preparation

The [local decision workbench](demo/README.md) adds an editable browser interface for Choice, Noul, and Score. The [EACL review-draft package](paper/eacl2027/README.md) includes a six-page-body paper, a 135-second captioned live demonstration, and reproducibility material. These materials are **not submitted, accepted, or peer reviewed**.

## Run the native service

The tested native path requires an Apple Silicon Mac with macOS 26.4+, Python 3.10+, Xcode command-line tools, CMake, and Git. The pinned model download is **20.4 GB**. Model weights and prebuilt native binaries are not included in the source repository. Other platforms are not validated for this native path.

From the repository directory:

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

## Reproduce and inspect

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

AI coding agents contributed implementation, question authoring, review, experiments, and documentation under the owner's direction. Agent review is not independent human review. The [working-paper package](paper/README.md) contains the completed v0.2 empirical study of one model on one device: direct readout versus one-token and JSON generation, plus [600 external examples](paper/external_expanded/README.md) from JCoLA, JSTS, and JCommonsenseQA. The existing JNLI pilot is separate. These public datasets may have been seen during model training and cannot be pooled into one accuracy. All 4,050 scheduled comparison requests completed without failure. Protocols, traces, analysis, tests, and an independent AI-agent numerical audit are included; this is not human peer review or a submitted paper.

Useful next contributions include family-disjoint evaluations, substantive repeated training experiments, and measured runs on other models and hardware. See the [research plan](paper/TECHNICAL_REPORT.md#what-a-research-paper-still-needs).

Use [CITATION.cff](CITATION.cff) to cite the software. Original project code and local authored data are MIT licensed. External dataset-derived selection, metadata, results, and task protocols/rubrics use CC BY-SA 4.0 with JGLUE/JCoLA attribution; mixed study records retain that data boundary. Third-party code and model artifacts retain their own terms. Original external dataset text, compiled binaries, and model weights are not included. See [NOTICE.md](NOTICE.md).
