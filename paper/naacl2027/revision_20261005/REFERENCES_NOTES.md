# Citation notes — 5 October 2026

All three records are verified against primary arXiv metadata and selected methods sections. They remain preprints in the checked records. Exact authors, versions, submission times, source URLs and inspection limits are in [REFERENCES_REVIEW.json](REFERENCES_REVIEW.json).

Suggested concise related-work prose:

```tex
LLM2Jev scores complete bracketed numeric suffixes on frozen backbones and also studies fine-tuning \citep{li2026llm2jev}. AnyJev studies label-prior correction and log-space cyclic aggregation with position-bound labels \citep{zhang2026anyjev}; our frozen records use arithmetic probability means with fixed token--meaning bindings. AudioJev trains an audio classifier with supervised, meaning-aligned order consistency \citep{lv2026audiojev}. These methods address readout and order sensitivity; we have not compared their predictive quality or inspection utility.
```

Source distinctions to preserve:

- [LLM2Jev §3.3](https://arxiv.org/html/2610.02076v1#S3.SS3): full-suffix scoring includes the closing bracket and uses cached-prefix branch evaluation. Do not label it a one-token baseline or count only prompt prefill. Its separate training recipe is not the frozen comparator.
- [AnyJev §§4–5](https://arxiv.org/html/2610.00831v1#S4): Eq. 3 aggregates the **pre-prior** restricted distributions in log space. Avoid saying its L0 applies per-layout prior correction before aggregation. Its stopping criterion concerns agreement with its own full-cycle answer; this is separate from correctness. Label-prior estimation uses unlabelled inputs, but prior strength selection and temperature fitting use labels.
- [AudioJev §§3–4](https://arxiv.org/html/2610.01293v1#S3): order consistency is learned with meaning-aligned paired supervision; it differs from inference-time averaging and confidence calibration. Full accuracy includes position-relative alternatives, whereas its order-bias metrics exclude them.

Keep the separate AnyJev source discrepancy in engineering notes. It is not needed to motivate this manuscript or to describe the paper fairly. Do not claim method novelty, comparative superiority, or new human evidence from these citations.
