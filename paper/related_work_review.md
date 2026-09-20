# Related-work review for a Mini Jev research manuscript

Verified September 20, 2026. This is a source-checked drafting aid, not a systematic literature review or a claim that the selected papers exhaust prior work. Seven directly relevant research papers are prioritized. Product documentation is identified separately from research evidence. Citation keys in the draft resolve across `references.bib` and `additional_references.bib`; the latter contains only new entries.

## Proposed positioning

The defensible research question is how a reproducible, local typed-decision interface behaves under controlled changes to prompt format, readout, calibration, and lightweight adaptation. Candidate-logit normalization, label verbalizers, prompt repetition, and temperature scaling are established techniques. A stronger paper would contribute matched measurements, failure analysis, and an inspectable experimental protocol. The present artifact supports an empirical case study; broad efficiency, generalization, and adaptation claims require the additional experiments in the technical report.

## English Related Work draft

**Classification through language-model outputs.** Pattern-exploiting training (PET) maps class labels to vocabulary words through verbalizers and normalizes their scores at a masked position (Schick and Schütze, 2021; `schick2021pet`). Mini Jev uses the same broad label-to-token idea at the next-token position of a frozen causal model, without reproducing PET's semi-supervised training procedure. More directly, Qwen3 reranking treats relevance as a binary decision using the next-token scores of yes and no (Zhang et al., 2025; `zhang2025qwen3embedding`). Its official inference code gathers those two logits and normalizes the pair (`qwen3reranker`). These precedents make candidate-logit readout an established component rather than an algorithmic novelty of this work. [PET](https://aclanthology.org/2021.eacl-main.20/); [Qwen3 Embedding, Section 2](https://arxiv.org/html/2506.05176v3); [official implementation](https://huggingface.co/Qwen/Qwen3-Reranker-8B).

**Constrained output and the one-token case.** Grammar-constrained decoding restricts generation to valid continuations and supports structured tasks with input-dependent output spaces (Geng et al., 2023; `geng2023grammar`). For the special case of distinct single-token labels, direct candidate softmax and a decoder that masks every other token have the same next-token distribution when their prefix, logits, temperature, and permitted tokens match. This equality follows directly from normalization; it is not an empirical novelty claim. Mini Jev returns probabilities and constructs typed values in software, avoiding an answer-generation loop. It still computes the prompt and full vocabulary projection. Any latency difference against one-token constrained decoding is therefore a systems measurement requiring a matched implementation. The equality does not extend without qualification to different prompts, multi-token labels, or complete JSON sequences. [Geng et al., Section 2.2](https://aclanthology.org/2023.emnlp-main.674/).

**Prompt repetition.** Leviathan et al. (2025; `leviathan2025repetition`) study repeated prompts in non-reasoning settings and report improvements across their tested models and tasks. Their latency observations include qualifications for long inputs and provider-side measurements. Mini Jev adopts repetition as an existing prompting technique, but a local prefill measurement is needed to determine its cost and utility in this runtime. Repetition increases complete input length and should be evaluated against an unrepeated prompt under a fixed model and documented token budgets. [Leviathan et al., Sections 1–2](https://arxiv.org/html/2512.14982v1).

**Probability adjustment and option sensitivity.** Temperature scaling rescales all class logits with a positive scalar fitted on held-out data; it preserves the predicted class while changing probabilities (Guo et al., 2017; `guo2017calibration`). Contextual calibration instead estimates answer bias from content-free inputs (Zhao et al., 2021; `zhao2021calibrate`). These are distinct interventions. Zheng et al. (2024; `zheng2024selectors`) further show that multiple-choice selection can depend on option identifiers and ordering. Mini Jev's canonical key sorting ensures deterministic serialization, but does not remove these model biases. Its calibration and key-order checks should consequently be interpreted as limited implementation and empirical results, not as general guarantees of calibrated probabilities or permutation robustness. [Guo et al.](https://proceedings.mlr.press/v70/guo17a.html); [Zhao et al.](https://proceedings.mlr.press/v139/zhao21c.html); [Zheng et al.](https://arxiv.org/abs/2309.03882).

**Relation to Jev.** TypeSafe's public API motivated the Choice, Noul, and Score interface terminology. Its launch announcement describes a distinct architecture, parallel sampler, and training method called Reinforcement Learning for Calibrated Decisions (RLCD) (`typesafe2026jev`; `typesafeapi`). Those are vendor descriptions, not independently reproduced results in this study. Mini Jev uses a frozen general-purpose model with sequential per-question inference and does not reproduce Jev's architecture or RLCD. We make no equivalence claim regarding accuracy, calibration, throughput, or speed. [TypeSafe announcement](https://typesafe.ai/blog/introducing-system-one-models-and-jev); [API reference](https://docs.typesafe.ai/api).

## Exact one-token equivalence to state in the method section

This is an elementary derivation from the manuscript's own definition, rather than a theorem attributed to another paper.

Let the shared tokenized prefix be `x`, vocabulary logits be `z_v(x)`, positive temperature be `T`, and `C` be a set of distinct allowed token IDs. Define a masked logit by `m_v = z_v` when `v` is in `C`, and `m_v = -infinity` otherwise. For a candidate `c`:

```text
softmax(m / T)[c]
  = exp(z_c / T) / sum_{v in vocabulary} exp(m_v / T)
  = exp(z_c / T) / sum_{j in C} exp(z_j / T).
```

Thus, absent additional score processors, this is exactly Mini Jev's candidate distribution in real arithmetic. Floating-point implementations can differ within numerical tolerance. Greedy selection also agrees if tie-breaking is identical. Sampling from this distribution has the same categorical law, but a single sampled label is not the same object as the complete distribution or its ordinal expectation.

Conditions to record in a matched baseline are identical weights and quantization; identical tokenized prefix and label IDs; identical logits, temperature, and ordering; no differing top-k/top-p filters, penalties, bias terms, or hidden processing; and immediate stopping after the label. A one-token sampler does not need a second model evaluation just to choose that first token: its distribution is already produced by prefill. Do not manufacture a speed advantage by forcing an unnecessary second decode into the baseline. If an implementation requests EOS or serializes additional tokens, report that separately.

At `T = 1`, candidate normalization can also be written as the unrestricted next-token distribution conditional on the event `token in C`. At other temperatures it conditions the temperature-adjusted distribution. Neither identity turns token probability into an empirical probability of semantic correctness. A full-vocabulary candidate-mass diagnostic is useful because the conditional distribution discards how much original mass lay outside `C`.

## Claim–source mapping and verified locations

| Citation key | Primary source and verified location | Claim supported | Boundary for this manuscript |
|---|---|---|---|
| `schick2021pet` | [EACL paper PDF](https://aclanthology.org/2021.eacl-main.20.pdf), Section 3, especially 3.1 | Verbalizers map classes to vocabulary words; class scores are normalized. | PET's training procedure and results were not reproduced. |
| `zhang2025qwen3embedding` | [Author paper](https://arxiv.org/html/2506.05176v3), Section 2, Reranking Models; Section 3.1 | Binary reranking based on yes/no next-token scores; task-specific training. | The reranker's performance is not evidence about a frozen Mini Jev model. |
| `qwen3reranker` | [Official model card](https://huggingface.co/Qwen/Qwen3-Reranker-8B), `compute_logits` example | Explicit final-position yes/no logit selection, pair normalization, return of the positive score. | Code establishes the numerical readout precisely; it is not an efficiency comparison. |
| `geng2023grammar` | [EMNLP paper PDF](https://aclanthology.org/2023.emnlp-main.674.pdf), Section 2.2 | Pruning the next-token distribution to grammar-permitted continuations. | The single-token equality above is our algebraic specialization, not an attributed theorem. |
| `leviathan2025repetition` | [Author paper](https://arxiv.org/html/2512.14982v1), Sections 1–2, Efficiency, and conclusion footnotes | Prompt duplication is prior work; long-input latency qualifications are explicit. | No universal zero-cost claim; measure local prefill costs. |
| `guo2017calibration` | [ICML paper PDF](https://proceedings.mlr.press/v70/guo17a/guo17a.pdf), Section 4, Equation 9 | Positive scalar temperature, validation-set fitting, unchanged class ordering. | Does not guarantee every metric or distribution improves. |
| `zhao2021calibrate` | [ICML paper](https://proceedings.mlr.press/v139/zhao21c.html) and [PDF](https://proceedings.mlr.press/v139/zhao21c/zhao21c.pdf), Sections 3–4 | Prompt-induced answer bias and content-free-input contextual calibration. | Distinguish this from held-out supervised temperature fitting and trained bias parameters. |
| `zheng2024selectors` | [Author paper v4](https://arxiv.org/html/2309.03882v4), Sections 2.4 and 3; [arXiv record](https://arxiv.org/abs/2309.03882) identifies ICLR 2024 Spotlight | Option token and position effects; permutation analysis and prior-bias correction. | Sorted dictionary input is not a permutation test of the displayed options. |
| `typesafe2026jev`, `typesafeapi` | [Vendor announcement](https://typesafe.ai/blog/introducing-system-one-models-and-jev), September 15, 2026; [API](https://docs.typesafe.ai/api), Question types and Answer types | Public interface terminology and the vendor's stated RLCD/architecture/sampling distinction. | Cite as product sources; do not endorse or borrow performance and calibration claims. |

OpenReview served a browser-verification challenge during this review. The Zheng paper's author-hosted arXiv record and v4 full text were available, including conference-status metadata. No secondary summary was used to support its technical claims. The Japanese note article is the project's historical motivation, not evidence for an algorithm or measured result, and is not needed in the scholarly Related Work section.

## Direct consequences for the next experiment

1. Use candidate logits versus one-token masked decoding as a numerical consistency and systems comparison. Identical classification performance is the expected null result, not a research failure.
2. Treat prompt repetition, output-token alphabet, and displayed option order as separate experimental factors. Preserve semantic labels while changing their presentation; keep those tests distinct from dictionary canonicalization.
3. Compare the frozen distribution, supervised temperature, learned bias, and residual head without conflating them with contextual calibration or RLCD. Fit every supervised transform on designated training or calibration splits.
4. Report accuracy, probability loss, calibration diagnostics, ordinal utility, and latency separately. A better NLL with worse stage error is a substantive trade-off rather than a universal improvement.
5. Base an eventual contribution claim on new controlled observations and released evidence. The present related-work review does not establish novelty by itself.
