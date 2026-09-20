# Reddit release draft

Status: not posted. Recommended first venue: r/MachineLearning, with the `[P]` title tag and Project flair if available. This is a technical project discussion, not a research-paper announcement. Check the current posting rules and available flair at submission time. See [POSTING_PLAN.md](POSTING_PLAN.md) for the community-specific reasoning and official rule links. The repository transfer to UpHash-Network is complete and public access to the URL below has been verified. Organization ownership does not imply an institutional research affiliation.

## Title

[P] Mini Jev: typed decisions from frozen Qwen logits, with 2,400 Japanese eval items and a failed head-tuning experiment

## Body

I wanted to see how far an existing local LLM could go as a decision function: give it a state and explicit options, then receive a choice, a true/false score, or an ordinal score without generating answer text.

The result is **Mini Jev**. It is an independent implementation inspired by TypeSafe's public Jev interface, not a reproduction of their model, RLCD, or performance claims. The core technique—reading candidate token logits—is established; I am sharing the implementation, data, and measurements rather than claiming a new algorithm.

The current native configuration uses frozen **Qwen3.6-35B-A3B Q4_K_M**, repeated input, and type-specific label tokens. A small llama.cpp helper reads the final-position logits; Python constructs the response. It computes the full vocabulary head before selecting candidate logits. Each question performs its own model call; a request with multiple questions runs them sequentially. It is not shared-prefill or parallel decision inference.

Measured on an **M5 Pro, 64 GB, macOS 26.4**:

- 2,238/2,400 correct on the project's Japanese evaluation suite: Choice 96.0%, binary 95.25%, ordinal top-label accuracy 88.5%.
- Warm single-question engine p95 of 379.1 ms for the 2,291 inputs with at most 512 complete input tokens, including repeated prompt content. The other 109 inputs had a 521.8 ms p95.
- This is an absolute latency measurement, not a speedup claim. I have not yet run a matched comparison with one-token constrained generation or JSON generation.

**Evaluation caveat:** this is a self-authored suite, not an established external benchmark. It contains 2,220 generated items across 45 template families and 180 individually AI-authored items reviewed by other AI agents. The authoring process had seen some earlier evaluation failures, and v2 retains related skill families. It is not human-expert annotation or family-disjoint generalization. All questions, answers, and prediction records are included.

There is also a negative training result. On an earlier frozen Qwen2.5-1.5B model, a 9,222-parameter residual head reduced held-out accuracy from 73/96 to 67/96; bias-only got 74/96. I kept that experiment and added a reusable JSONL training/calibration/evaluation workflow so others can test their own data. **The final 35B inference configuration does not use this trained head.**

The probabilities are conditional on the allowed candidate tokens. They are not guaranteed correctness probabilities. Fitting temperature slightly improved final NLL while making ECE and ordinal expectation error worse; the report includes those numbers too. Canonicalizing Choice keys explains perfect reversed-map consistency—it is not evidence of learned order invariance.

The source release requires building the pinned native runtime; it does not include model weights or prebuilt native binaries. The current native path is tested on Apple Silicon/macOS, and the training guide separately lists its dependencies and tested devices. Coding, question authoring, checking, and documentation were developed with AI agents under my direction.

Repository: https://github.com/UpHash-Network/mini-jev

The README links the technical note, raw results, data/model cards, and training guide. I would particularly appreciate suggestions for **external decision benchmarks** and a fair **same-model constrained-generation comparison**. Those are the next experiments needed before making a stronger research claim.
