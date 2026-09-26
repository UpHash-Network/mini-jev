**Mini Jev update: the matched one-token comparison is complete, and stable outputs can still be wrong**

I'm Yuki Oshio at UPHASH Inc., the author. This updates my earlier Mini Jev comment in this thread, where the same-model comparison was still future work. This English text was prepared with an AI assistant. AI agents also assisted development, experiments, and documentation under my direction; this is not independent human review. The manuscript has not been peer reviewed.

Mini Jev is a local browser workbench for inspecting typed decisions from frozen language models: a choice, a true-candidate probability, or an expected ordinal stage. It exposes candidate distributions and request/response JSON. The released native configuration has no trained decision head, and the candidate-scoring mechanism is established rather than a new algorithm.

The source remains free, with no paid service or subscription. Original project code is MIT licensed; external dataset-derived artifacts retain their documented terms. You supply the hardware, build the runtime, and download the model separately. The tested native setup is an Apple Silicon Mac with 64 GB memory and a roughly 20.4 GB model file.

What changed since the earlier comment:

- The matched study now measures 4,050 requests across direct readout, native one-token selection, and constrained JSON generation. Direct readout and one-token selection match in all 1,350 pairs. This session did **not** establish a material latency advantage for direct readout.
- Two presentation/averaging studies add 7,600 and 14,400 requests across three checkpoints. The combined 26,050 is a request count, including repeats and transformations, not a count of independent questions.
- One concrete failure: Qwen2.5-1.5B-Instruct predicted “acceptable” for all 200 JCoLA items, before and after reversing the displayed options. Zero label flips, but 42 errors. Candidate-probability averaging sometimes reduced disagreement while costing more model calls and did not consistently improve accuracy.
- There is now a browser demonstration, a manuscript, and a reproducibility package with frozen selections, traces, and analyzers.

Candidate probabilities are normalized within the supplied options; they are not calibrated probabilities of correctness. Task-quality evaluations use Japanese public-development data, with possible exposure during model training. We have not established second-machine reproducibility or a human usability advantage.

[Project page, manuscript, and recording](https://uphash-network.github.io/mini-jev/) · [Source and reproducibility package](https://github.com/UpHash-Network/mini-jev/tree/research/naacl2027-demo)

I'd especially value feedback on the evaluation: which additional equal-compute control would best distinguish useful reduction in presentation sensitivity from collapse to a constant label?
