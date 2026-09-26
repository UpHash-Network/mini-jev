# Related-work comparison for the next manuscript revision

Reviewed 26 September 2026. This note supports the next NAACL-oriented manuscript; it does not change the source archive already submitted to arXiv.

| Work | Mechanism supported by the primary source | Relationship to Mini Jev |
| --- | --- | --- |
| [Zhuang et al., NAACL 2024](https://aclanthology.org/2024.naacl-short.31/) | Sections 3.2–3.3 score fine-grained relevance labels or rating values using label log-likelihoods, normalize these scores, and compute expected relevance. The paper also studies a distinct peak-relevance likelihood rule. | Score's probability-weighted ordinal value is established prior work. Zero-shot use of pretrained models is also established; frozen weights alone are not a novelty claim. Mini Jev exposes related quantities through a shared typed inspection contract and evaluates different system questions. |
| [Wang et al., arXiv:2609.18188v1](https://arxiv.org/abs/2609.18188v1) | Sections 3.2–3.3 use grade tokens 1–5 for job-candidate relevance. They use the expected grade at inference and train with weighted MSE and cross-entropy; the local Qwen3-8B configuration uses LoRA. | This is a close single-token ordinal-readout precedent. Mini Jev does not train a head or adapters, reproduce their hiring task, or establish an advantage over their ranker. Its experiments concern typed outputs, matched native one-token parity/timing, and presentation sensitivity with explicit call accounting. |

The comparison is about mechanisms and research scope, not an empirical ranking of systems. We did not rerun either paper. In particular, Zhuang et al.'s general label log-likelihood formulation should not be described as uniformly single-token scoring. Wang et al. is cited as the inspected arXiv preprint: its abstract page reports workshop acceptance, but this revision does not turn that into a main-conference publication claim.

## Defensible contribution

Mini Jev contributes a runnable local inspection interface with a common Choice/Noul/Score contract, candidate-derived distributions, expected stages, concentration, and request/response JSON. It accompanies that interface with auditable matched runtime and presentation-sensitivity evidence. The new citations make the established expected-value mechanism explicit. They do not require altering the measurements or strengthen them into a new scoring algorithm, a new general discovery about stability and correctness, a usability advantage, or a speed/quality improvement over these papers.

## Source anchors

- [Zhuang et al. primary PDF](https://aclanthology.org/2024.naacl-short.31.pdf), Sections 3.2–3.3, equations (1)–(3), printed pages 359–360; metadata and author ordering checked against the official ACL record.
- [Wang et al. primary HTML](https://arxiv.org/html/2609.18188v1), Sections 3.2–3.3, equations (1)–(5); version and author ordering checked against the arXiv abstract page.

The revised manuscript cites both papers in Section 5. No new baseline experiment or inference run was introduced by this literature-only revision.
