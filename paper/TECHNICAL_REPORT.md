# Mini Jev: A Reproducible Local Interface for Typed Decisions from Frozen Language-Model Logits

**Yuki Oshio** · September 20, 2026 · Empirical technical note, not peer reviewed

Software and experiments were developed with AI coding agents. No institutional affiliation, external benchmark certification, or independent human review is claimed. This report describes the measured local artifact and a reusable experimental training path; its findings should not be read as general model guarantees.

## Abstract

Mini Jev adapts a causal language model to return categorical choices, binary scores, and ordinal expectations without generating answer text. A frozen model processes a prompt, the runtime reads selected next-token logits, and ordinary software constructs a validated response. The evaluated configuration uses Qwen3.6-35B-A3B in Q4_K_M form with repeated input and type-specific candidate labels. On a self-authored Japanese suite of 2,400 items it obtains 93.25% top-label accuracy. Warm single-question engine latency is 379.1 ms at the 95th percentile for the 2,291 complete inputs of at most 512 tokens, measured on one Apple M5 Pro with 64 GB of memory. The other 109 inputs have a 521.8 ms p95. These are absolute measurements, not demonstrated speedups over a generation baseline. A separate small-model experiment finds that a residual output head reduces held-out accuracy from 73/96 to 67/96. We release implementation, data, predictions, provenance, and an experimental training workflow. The main limitations are self-authored, correlated evaluation data, a single hardware configuration, missing matched generation baselines, and uncertain probability transfer to new domains.

## Motivation and scope

Some software decisions require a choice from a known set rather than a sentence. Routing, checking a stated condition, and assigning an ordered stage can be represented by a small candidate vocabulary. Mini Jev explores a practical implementation: preserve the language model, read candidate logits at a fixed answer position, and expose a typed API.

The public Jev interface motivated the Choice, Noul, and Score terminology. TypeSafe describes its own architecture and training method, including RLCD. Mini Jev does not implement those internals and does not claim equivalent accuracy, calibration, parallel sampling, efficiency, or compatibility. The project has no affiliation with TypeSafe. [TypeSafe API](https://docs.typesafe.ai/api); [TypeSafe introduction](https://typesafe.ai/blog/introducing-system-one-models-and-jev).

The contribution is an engineering artifact and a limited empirical study. It is not a newly invented classification objective. Its inspectable features include fixed token-boundary checks, deterministic type construction, runtime integrity checks, an explicit calibration split, full prediction records, and reporting of an unsuccessful training experiment. The project meets its local acceptance criteria; this does not establish publication-level novelty or broad production readiness.

## Relation to existing methods

Pattern-exploiting training (PET) frames classification using cloze-style patterns and label verbalizers. Mini Jev shares the broader idea of mapping task labels to language-model outputs, but does not reproduce PET's training procedure. [Schick and Schütze, 2021](https://aclanthology.org/2021.eacl-main.20/).

The official Qwen3-Reranker example extracts the final-position logits of `yes` and `no`, stacks them, and normalizes the pair. It directly precedes the basic candidate-logit readout used here. The reranker is specialized for its own task; its results are not results for Mini Jev. [Qwen3-Reranker-8B model card and code](https://huggingface.co/Qwen/Qwen3-Reranker-8B).

Prompt repetition has also been studied for non-reasoning language models. We cite that prior work rather than presenting duplicated input as a novel mechanism. Our local use increases the number of input tokens; we make no claim that it has zero latency cost. [Leviathan, Kalman, and Matias, 2025](https://arxiv.org/abs/2512.14982).

Temperature scaling is an established post-processing method. We fit a single positive temperature on a separate split, following that general approach. It preserves the highest-scoring class while changing probabilities and ordinal expectations. [Guo et al., 2017](https://proceedings.mlr.press/v70/guo17a.html).

## Method and runtime

For state `s`, instructions `q`, and candidates `c[0..K-1]`, a formatter produces an input `x`. The evaluated formatter repeats the task content twice in the same input. Choice candidates are ordered by their semantic keys. Noul has the order false, true. Score retains the user's stage order.

Let `z[i]` be the next-token logit at the final input position for the token assigned to candidate `i`. The returned distribution is

```text
p[i] = exp(z[i] / T) / sum_j exp(z[j] / T)
Choice = semantic_key(argmax_i p[i])
Noul = p[true]
Score = sum_i i * p[i]
confidence = 1 - (-sum_i p[i] * log(p[i])) / log(K)
```

The implementation uses numerically stable softmax. Choice and Noul use letter labels. Score with at most ten stages reads the digits `0` through `9` after the fixed assistant prefix `{"answer":`; larger Score sets fall back to letters. Every label must be one token both in isolation and when appended to the actual prefix. A failed boundary check produces an error instead of silently using a multi-token label.

The native helper computes the full vocabulary output and gathers candidate logits. It does **not** replace the native vocabulary projection with only the selected rows. There is one `llama_decode` API call per question; this is an API accounting statement, not a claim of one GPU kernel or constant work. No output token is sampled, no autoregressive answer loop runs, and no generated JSON is parsed. Input prefill still performs substantial computation. KV and recurrent state are reset between questions.

The service constructs JSON responses from validated values. Its source repository includes a Python client and a loopback HTTP service. Multiple questions are independent and sequential: there is no shared-state prefill, parallel question sampler, or answer cache. Candidate sets contain 2–26 entries, requests default to at most eight questions and can be configured to 16, and complete inputs above 2,048 tokens are rejected rather than truncated. These limits are implementation limits, not a claim about the underlying model's maximum context.

The probabilities are conditional on the allowed tokens. They do not express the fraction of full-vocabulary mass assigned to the permitted response format. In a numerical fixture, the selected Score digits collectively had roughly 0.01% of the full-vocabulary mass, while a space token was more probable. Renormalizing still produces a distribution summing to one. This illustrates why normalized candidate probabilities should not be equated with unrestricted model confidence. The entropy-derived `confidence` is likewise not a correctness probability.

## Model, implementation, and reproducibility

The evaluated model is `ggml-org/Qwen3.6-35B-A3B-GGUF`, revision `baec3ebee244827cda0f4557eafa8b28f7545fa6`, file `Qwen3.6-35B-A3B-Q4_K_M.gguf`. It occupies 20,419,565,568 bytes. Its SHA-256 is `671e47e0ec53c665d048b98c3ecbfd5236b5ca9c3e02ed19fc8f81f7b85140c7`. The upstream model card describes a mixture-of-experts model with 35B total and 3B active parameters. Model weights remain unchanged. [Upstream model card](https://huggingface.co/Qwen/Qwen3.6-35B-A3B); [pinned GGUF](https://huggingface.co/ggml-org/Qwen3.6-35B-A3B-GGUF/tree/baec3ebee244827cda0f4557eafa8b28f7545fa6).

The native runtime uses llama.cpp revision `f072b103714dfa1eee531f80b24512faf38e3dd2`, six threads, Metal and Accelerate, and a 2,048-token context. Measurements used ARM64 Python 3.10.5 on macOS 26.4. Runtime logs recorded all 41 layers offloaded to the Apple M5 Pro GPU.

Startup checks the model's complete SHA-256 and native artifact manifest. The evaluation binds model bytes, prompt code, helper, libraries, aliases, configuration, and Python/OS details to a runtime fingerprint. Each measured question checks for changes. The historical fingerprint is `4d2953166c63f2f1392b661a0331168459ac7cd359638612f37299513a118152`.

The public source release omits model weights and native executables. Local paths in historical logs are redacted, with transformations recorded separately. Historical freeze hashes refer to original files and should not be expected to match every redacted public copy. A fresh build is a reproduction from pinned source, not necessarily a byte-identical executable: compiler, SDK, signatures, and system versions can differ. It needs a new manifest, calibration, and measured validation. The recorded figures below belong to the historical frozen run, not an unmeasured public rebuild.

## Evaluation design and data provenance

The final v2 suite contains 800 Choice, 800 Noul, and 800 Score questions. It consists of 2,220 template-generated examples across 45 task families and 180 individually AI-authored examples, 60 per type. A separate set of 120 items, 40 per type, is used only to select temperature. Quality evaluation uses 2–8 candidates. Examples include conditions, exceptions, state updates, ordering, counts, and bounded arithmetic. Prompts and states are Japanese, with some structured state objects.

The legacy `manual` source label means individually constructed by an AI agent, not annotated by a human expert. Other AI agents reviewed the items. AI review can catch inconsistencies but is not independent human validation. Synthetic examples share generation templates and therefore are correlated. We report family results rather than treating 2,400 examples as 2,400 unrelated task types. We do not present an IID binomial confidence interval as evidence of generalization to new families.

An earlier v1 suite was evaluated, its failures were diagnosed, and it became development data. The final v2 set uses new situations and rubrics and was not consulted for final model selection. However, the v2 author had diagnosed the first 400 frozen v1 predictions, and the intended skill families and candidate-count distributions were retained. The audit reports zero exact input overlap against v1, but lexical deduplication does not prove semantic independence. Thus “held out” refers to final item-level use, not an external, blindly designed, or family-disjoint benchmark.

The model, formatter, temperature, and data were frozen before the final run; no changes were made during evaluation. The run included 2,400 original questions, 800 reversed Choice input maps, and seven warm-up questions, totaling 3,207 actual decode API calls. Public model-development results and the unsuccessful v1 evaluation remain available. Re-running the now-public v2 suite is replication; tuning against it requires a new test set for new generalization claims. [Data card](../DATA_CARD.md); [authoring audit](../acceptance-v2/MANUAL_AUDIT.json).

Top-label accuracy compares the most likely permitted candidate with the gold label. In particular, Score accuracy is stage-label accuracy, not rounded expectation accuracy. We separately measure the absolute error of the continuous expected stage. NLL, multiclass Brier score, and ten equal-width-bin ECE use the candidate probability distribution. Temperature is chosen by calibration-set NLL, not test accuracy.

## Results

### Quality

| Type or subset | Correct / total | Accuracy |
|---|---:|---:|
| Overall | 2,238 / 2,400 | 93.25% |
| Choice | 768 / 800 | 96.00% |
| Noul | 762 / 800 | 95.25% |
| Score | 708 / 800 | 88.50% |
| Individually AI-authored | 172 / 180 | 95.56% |
| Template-generated | 2,066 / 2,220 | 93.06% |

Generated-family macro accuracy is 93.02%. Some families are substantially weaker than the overall figure: delay from a promised time is 29/49 (59.18%), conditional obligation 31/49 (63.27%), counts after cancellation 33/49 (67.35%), and weighted items 38/49 (77.55%). The individually authored arithmetic subset is 10/17. These failures argue against extrapolating the overall score to arbitrary rule execution or arithmetic.

All 2,400 original outputs satisfy checked type, finiteness, normalization, and range constraints. Reversing the input dictionary of each Choice question gives the same semantic label in all 800 cases, but the runtime sorts keys before building the prompt. This verifies the software canonicalization; it is not evidence that the model handles arbitrary displayed option permutations without bias. Semantic key renaming can still change sorted order and model behavior.

### Latency and operations

| Complete input length | Items | Warm p50 | Warm p95 | Maximum |
|---|---:|---:|---:|---:|
| ≤512 tokens | 2,291 | 282.7 ms | 379.1 ms | 423.4 ms |
| >512 tokens | 109 | 441.9 ms | 521.8 ms | 566.6 ms |

Inputs include templates and repeated content. Every timed item executes a real model call; feature-cache retrieval is not timed as inference. These are warm single-question engine measurements on one machine. The 512-token subset must not be silently described as all questions. Startup and HTTP processing are separate measurements.

In an integration check, two fresh process loads reproduced probabilities exactly. Startup, including file verification, took about 9.18 seconds with OS file cache already warm. A three-question HTTP request took approximately 579–582 ms in those checks. We do not divide that request latency by three and present it as user-visible latency. No comparison here establishes superiority over one-token constrained generation, JSON generation, hosted models, or Jev.

### Probability behavior

The separate 120-item calibration split selects `T = 1.3489628825916533`. On final v2 items:

| Metric; lower is better | T=1 | Fitted T |
|---|---:|---:|
| NLL | 0.188423 | 0.187871 |
| Multiclass Brier, sum over classes | 0.097261 | 0.096260 |
| ECE, 10 equal-width bins | 0.014863 | 0.015198 |
| Score expectation MAE, stage units | 0.169401 | 0.195121 |
| Score expectation MAE / (K−1) | 0.044948 | 0.051964 |

The NLL and Brier improvements are small. ECE and ordinal expectation error worsen. A positive temperature preserves class ordering, so accuracy is unchanged. An NLL-optimal temperature is not necessarily optimal for stage MAE, and this synthetic calibration split does not establish calibration for unseen applications. API fields consequently distinguish `temperature_calibration_applied` from unvalidated general calibration and domain generalization.

### Numerical and service checks

A native numerical audit has 434 checks on eight public fixtures, not 434 additional quality questions. It compares 58 selected logits with an independently read full-vocabulary reference and records maximum difference zero. Four public Score boundary fixtures exercise 2, 10, 11, and 26 candidates, with 93 checks covering the digit/letter transition, stage ordering, expected value, and schema.

Service tests cover strict JSON handling, bounds, malformed input, duplicate keys, SDK consistency, restart, and shutdown. These checks reduce implementation errors but do not add independent evidence of semantic accuracy. [Validation record](../VALIDATION.md); [final summary](../results/native-acceptance/summary.json).

## A separate residual-head experiment

The original question was whether a small output-stage update could help turn an existing model into a decision model. An earlier experiment used frozen Qwen2.5-1.5B-Instruct and preserved its original candidate logits. A trainable residual added `ΔW × RMS(h) + Δb` to six candidate positions, with 9,222 trainable parameters. A bias-only comparison trained six parameters. This is distinct from the final 35B model, which has no learned residual head.

The experiment used 768 synthetic training rows plus 256 reversed Choice variants kept within the training split, 192 development rows, 192 calibration rows, and 96 new individually AI-authored test rows. The training loss therefore weighted Choice as half of augmented examples; development and test were balanced by type. Group separation prevented direct scenario reuse, but synthetic splits shared templates. Development NLL selected the head and a separate calibration split selected temperature.

| Qwen2.5-1.5B condition | Held-out top-label accuracy |
|---|---:|
| Frozen baseline | 73 / 96 = 76.04% |
| Residual linear head | 67 / 96 = 69.79% |
| Bias-only correction | 74 / 96 = 77.08% |

The residual head improved some probability losses while lowering accuracy; neither the one-point bias improvement nor this single residual-head failure supports a broad conclusion about fine-tuning. The sample is small, domain-limited, and not a multi-seed study. We retained the negative result and did not deploy that head in the final runtime. [Detailed experiment](../HEAD_TUNING.md); [original metrics](../results/head/REPORT.md).

The public reusable workflow described in [TRAINING.md](../TRAINING.md) allows users to validate their own JSONL splits and run the same class of experiment. It is a tool for measuring whether adaptation helps, not a pretrained improvement or a guarantee for arbitrary causal models. Its supported architectures and tested devices are documented separately. It must not be described as training the released 35B configuration or reproducing RLCD.

## Limitations

The evidence has five main limitations. First, self-authored examples and shared templates can favor the chosen formatter and fail to represent natural user traffic. Second, v1 development informed the kinds of tasks tested in v2; holding out new instances does not hold out abstract skills. Third, changing model size, quantization, runtime, and formatting across historical experiments confounds attribution. A larger model's improvement cannot be assigned solely to the output scheme. Fourth, only one native hardware/software combination and one final run support the reported latency. Fifth, candidate normalization and entropy do not supply calibrated real-world uncertainty or an automatic abstention guarantee.

The method also depends on label tokens and order, rejects long complete inputs, and spends a full prompt computation per question. Repetition consumes context and work. Selecting a valid label prevents a malformed answer string but cannot prevent choosing the wrong label. Question content can contain contradictory or adversarial instructions; the present quality suite is not a comprehensive prompt-injection or deployment-safety evaluation.

## What a research paper still needs

A stronger paper would pre-register an evaluation protocol before examining its test outcomes and make a narrower claim about decision readout and adaptation. Priority experiments are:

1. **Matched baselines:** fix model, quantization, hardware, task definitions, and input budget; compare direct candidate logits, one-token constrained generation, structured JSON generation, and the residual/bias heads. Measure complete user-visible latency and accuracy. Specify differences in prompt budget rather than hiding them.
2. **External and family-disjoint evaluation:** add licensed public datasets and independently reviewed items. Hold out whole task families and domains, not only surface instances. Publish annotations, disagreements, and a family-aware uncertainty analysis.
3. **Training controls:** test several model sizes, data sizes, and random seeds. Compare frozen baseline, bias-only, residual linear head, and appropriate lightweight alternatives. Keep tuning, calibration, and final tests separate and report all selected and unsuccessful runs.
4. **Probability utility:** report NLL, Brier, ECE with binning sensitivity, ordinal error, and selective-prediction risk versus coverage. Choose operating thresholds before the final test and measure their transfer under shift.
5. **System evidence:** report cold and warm paths, memory, throughput, request size, and multi-question latency on multiple devices. Explore selected-row projection or shared prefill only as new measured implementations.

Until those comparisons exist, this release is best read as a reproducible empirical note and a useful implementation, not a state-of-the-art result or a new learning algorithm.

## Data, code, and authorship

The repository provides the source, [2,400-item JSONL](../acceptance-v2/questions_2400.jsonl), [CSV](../acceptance-v2/questions_2400.csv), calibration split, detailed predictions, original experimental results, and publication provenance. Model and third-party licenses remain with their upstream artifacts; authored code and data are provided under the repository license. AI agents contributed coding, research assistance, question generation, peer checking, and drafting. The project owner is responsible for the public artifact; AI-generated review should not be confused with external peer review.

Bibliographic metadata for the cited primary sources is in [references.bib](references.bib). The work has not been submitted to or accepted by a journal or conference as part of this release.
