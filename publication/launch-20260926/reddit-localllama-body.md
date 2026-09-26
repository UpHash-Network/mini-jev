# Mini Jev: a local UI for inspecting typed LLM decisions, including stable-but-wrong outputs

I'm Yuki Oshio at UPHASH Inc., the author of Mini Jev and its manuscript. This English draft was prepared with an AI assistant. The manuscript has not been peer reviewed. AI agents also assisted implementation, experiments, and documentation under my direction; that is not independent human review.

Mini Jev exposes a frozen local model's next-token candidate scores through three typed outputs: a choice, the probability assigned to a true candidate, and an expected ordinal stage. There is no trained decision head in the released native configuration. The browser UI shows the input criteria, candidate distributions, and request/response JSON so you can inspect what a small decision actually means.

The interesting result is a failure case. On a 200-item Japanese grammatical-acceptability panel, Qwen2.5-1.5B-Instruct always selected “acceptable,” before and after reversing the displayed candidate order. It had zero label flips, yet was wrong on 42 items. Stability hid a constant prediction.

Across three studies, we recorded 26,050 requests, including repeats and transformations; this is not 26,050 independent questions. In a matched comparison, direct readout and native one-token selection agreed on all 1,350 pairs, and we did not establish a material latency advantage for direct readout. Averaging across display rotations sometimes reduced disagreement, but cost multiple calls and did not consistently improve accuracy.

The implementation uses established candidate scoring rather than a new decoding algorithm. The displayed probabilities are conditional on the candidate set; concentration is not calibrated correctness. The task-quality evaluations use Japanese public-development data, with possible training-data exposure. There is no independent second-machine replication or human usability study.

The released native path was tested on an Apple Silicon Mac with 64 GB unified memory. Its pinned Qwen3.6-35B-A3B Q4_K_M model file is about 20.4 GB; this is not a claim that it runs on every laptop. The model weights and native binaries are not bundled. GitHub Pages hosts the overview and recording; inference runs locally after setup.

- [Project page, manuscript, and recording](https://uphash-network.github.io/mini-jev/)
- [Source and setup instructions](https://github.com/UpHash-Network/mini-jev/tree/research/naacl2027-demo)
- [Reproduction package and evaluation accounting](https://github.com/UpHash-Network/mini-jev/tree/research/naacl2027-demo/paper/naacl2027)

For people building local routing or rubric-based decisions: which failure cases or baselines would make this useful to you? Concrete installation reports and examples where a concentrated distribution is wrong would be particularly helpful.
