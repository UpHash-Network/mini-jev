# Mini Jev

**An inspectable local interface for typed decisions from frozen language models.**

[日本語](https://github.com/UpHash-Network/mini-jev/blob/main/README.ja.md) · [Project page](https://uphash-network.github.io/mini-jev/) · [Current research source](https://github.com/UpHash-Network/mini-jev/tree/research/naacl2027-demo)

Mini Jev turns a state and explicit criteria into a categorical **Choice**, the true-candidate probability (**Noul**), or an expected ordinal stage (**Score**). Its browser workbench exposes the candidate distribution, concentration, and request/response JSON. The released native system uses a frozen local language model with no trained decision head.

**Status — 26 September 2026:** a preprint has been submitted to arXiv and is awaiting moderation. There is no public arXiv identifier yet. The current conference manuscript is being prepared for NAACL 2027 System Demonstrations; it is not submitted, accepted, or peer reviewed. The current research source is on **`research/naacl2027-demo`**; use that branch for the instructions below.

## Read, watch, reproduce

| Start here | What you will find |
|---|---|
| [Current paper PDF](https://uphash-network.github.io/mini-jev/assets/Mini_Jev_Manuscript.pdf) | Manuscript, evidence, related work, and limitations |
| [60-second evidence walkthrough](https://uphash-network.github.io/mini-jev/#demo) | Explanation of retained experiment results; not a new live inference run |
| [Full interface recording](https://uphash-network.github.io/mini-jev/assets/Mini_Jev_Demonstration.mp4) | 145-second captioned recording of the local workbench; an earlier branch caption is retained |
| [Reproduction guide and frozen source/evidence ZIP](https://github.com/UpHash-Network/mini-jev/blob/research/naacl2027-demo/paper/naacl2027/reproducibility/README.md) | CPU-only replay of retained analysis, plus native-build verification and exact artifact hashes |
| [Native installation](https://github.com/UpHash-Network/mini-jev/tree/research/naacl2027-demo#run-the-native-service) | Build the pinned runtime, download the model, and start the local API |
| [Browser workbench guide](https://github.com/UpHash-Network/mini-jev/blob/research/naacl2027-demo/demo/README.md) | Run live inference and inspect typed outputs and JSON |

## What the current paper shows

- **1,350 / 1,350 matched pairs** have identical direct-readout and native one-token labels/logits. No latency advantage was established.
- **26,050 measured requests** cover the matched study and two studies of presentation sensitivity and probability averaging. This is not a count of independent questions.
- Reduced sensitivity can coexist with incorrect or nearly constant predictions. Averaging needs multiple model calls and does not consistently improve task quality.
- **56 / 56 analysis outputs** were reproduced byte for byte from retained records. This is analysis replay, not an independent experiment or second-machine replication.

Task-quality evidence uses Japanese public-data subsets on one Apple Silicon Mac. Training-data contamination is unknown; no human usability study has been performed. A separate 2,400-item AI-authored regression suite is historical background. See the [paper guide](https://github.com/UpHash-Network/mini-jev/blob/research/naacl2027-demo/paper/naacl2027/README.md) for the full scope.

## Run the current version

```sh
git clone --branch research/naacl2027-demo --single-branch https://github.com/UpHash-Network/mini-jev.git
cd mini-jev
```

Then follow the [native installation steps](https://github.com/UpHash-Network/mini-jev/tree/research/naacl2027-demo#run-the-native-service). The tested system is an Apple M5 Pro with 64 GB memory and macOS 26.4. It requires Python 3.10+, Xcode command-line tools, CMake, Git, and a roughly 20.4 GB model download. Weights and native binaries are not bundled; lower-memory hardware is not validated. The [CPU-only analysis replay](https://github.com/UpHash-Network/mini-jev/blob/research/naacl2027-demo/paper/naacl2027/reproducibility/README.md) does not require the model.

Candidate probabilities are conditional on the supplied candidates. Concentration is not the probability that the answer is correct. Mini Jev is independently inspired by TypeSafe's Jev, with no affiliation or claim to reproduce its architecture, training, calibration, or speed. Candidate scoring and expected-value scoring have prior work; the contribution here is an inspectable implementation and auditable system evaluation.

[Report an issue or reproduction result](https://github.com/UpHash-Network/mini-jev/issues) · [Manuscript BibTeX](https://uphash-network.github.io/mini-jev/citation.bib) · [Software citation](https://github.com/UpHash-Network/mini-jev/blob/research/naacl2027-demo/CITATION.cff)

Original code and authored data: [MIT](https://github.com/UpHash-Network/mini-jev/blob/research/naacl2027-demo/LICENSE). Dataset-derived records and third-party artifacts retain their applicable licenses and attribution: [NOTICE](https://github.com/UpHash-Network/mini-jev/blob/research/naacl2027-demo/NOTICE.md).
