# LogitTrail — EACL 2027 System Demonstrations submission

**29 September 2026: renamed from Mini Jev to LogitTrail.** The submitted arXiv version retains its original Mini Jev title; this is a later conference revision. [Name and version mapping](../../NAMING.md).

**Submitted to EACL 2027 System Demonstrations on 6 October 2026.**
A decision is pending; no acceptance is claimed. The related preprint was
submitted to arXiv on 26 September, under its original Mini Jev title. No public
arXiv identifier has been verified as of 6 October. The arXiv submission and
this conference revision are distinct versions. Existing `paper/naacl2027/`
paths, PDF filenames and the `research/naacl2027-demo` branch remain for link
compatibility; they do not indicate a concurrent NAACL submission.

Author: **Yuki Oshio, UPHASH Inc.** Single author; identified for the single-blind track.

The October 2 revision integrates the saved-evidence Explorer, complete-record functional audit, current related work, and a new 127-second demonstration. The frozen experiment archive and arXiv submission are unchanged. [Revision evidence](revision_20261002/README.md).

A subsequent [matched saved-evidence workflow check](workflow_comparison_20261002/README.md) runs six hash-selected cases in the Explorer, complete JSON, and the published ChainForge 0.3.7.6 GUI. All retain the supplied information; the comparison does not establish a human-performance advantage. [Current revision checks](revision_20261002_workflows/README.md) and [unrun Explorer pilot materials](explorer_user_evaluation_20261002/README.md) are separate from the frozen research experiments.

The [raw-record follow-up](raw_workflow_20261002/README.md) executes custom JavaScript in the unmodified ChainForge Processor, reconstructing 2,400 conditions from 6,000 archived logit records. The actual GUI export matches independent Python arithmetic within the frozen 1e-12 tolerance. This establishes competitor feasibility with custom code; neither human advantage nor new model performance is claimed. [Raw-record revision checks](revision_20261003_raw/README.md) cover that addition.

The separate [Japanese diagnostic confirmation](diagnostic_value_20261003/publication/README.md) adds 2,400 measured calls on 240 further questions shared by two Qwen checkpoints. A subsequent [two-family Japanese/English follow-up](generality_20261003/publication/README.md) adds 4,800 measured calls on 240 JCommonsenseQA and 240 CommonsenseQA questions shared by Qwen2.5-1.5B and Phi-4-mini. Its primary Phi-English comparison finds identical per-item correctness for entropy+order-TV and entropy alone: **174/240 at 720 calls**. Fixed-random and first-entropy references score 180/240 and 177/240. Added order-TV benefit remains unestablished; [the full report](generality_20261003/publication/REPORT.ja.md) retains all scores, error targets, strata and budgets, plus the synthetic implementation failure and versioned correction. An additional formative user-study packet is local and unpublished, with zero human participants or observations.

[October 3 manuscript revision checks](revision_20261003_strengthening/README.md) record that PDF, four added primary-source citations, and a [retrospective engineering case](case_study_20261003/CASE_STUDY.md). The case preserves 48 diagnostic/repeat records, two probability-tolerance failures with unchanged labels, the pre-benchmark amendment, and unchanged final study results. It is not a human study or new model experiment.

The [October 5 revision](revision_20261005/README.md) adds verified LLM2Jev, AnyJev and AudioJev references and a [post-hoc aggregation-only control](aggregation_control_20261005/README.md). The same 4,800 saved responses produce all four arithmetic-versus-geometric comparisons; 4–8 labels change per 240-item stratum, without a consistent accuracy gain. Full first-order references, paired intervals, source hashes and replay code are retained. There is no new inference, unseen confirmation, human evaluation or complete AnyJev benchmark.

## Read and run

- [Research project page](https://uphash-network.github.io/mini-jev/) — manuscript, video, findings, and installation links in one place.
- [Paper PDF](NAACL2027_LogitTrail.pdf) — 11 pages: main text, limitations, and acknowledgements end on page 6; ethics and references occupy pages 7–9; Appendix A occupies pages 10–11.
- [Download the versioned source and evidence ZIP](https://raw.githubusercontent.com/UpHash-Network/mini-jev/refs/heads/research/naacl2027-demo/paper/naacl2027/reproducibility/naacl-repro-v1-20260925.zip)
  — 18,060,014 bytes; SHA-256
  `a15e0699a54be15d56bd99ed8181429b71fdfc7ace756d6e065a75538786c053`.
- [Reproduction instructions and validation](reproducibility/README.md) —
  CPU-only analysis replay; native installation; exact manifests and limitations.
- [Current 127-second captioned demonstration](https://uphash-network.github.io/mini-jev/assets/LogitTrail_Demo_20261002.mp4) — real saved-evidence browser interaction plus a labeled archival live-inference excerpt.
- [Complete-record inspection audit](inspection_audit_20261002/README.md) — 172,200 within-item condition pairs, not independent questions or human task results.
- [60-second evidence walkthrough](https://uphash-network.github.io/mini-jev/#demo)
  — an explanation of retained experiment results, not a new live run.
- [Captioned recorded interface demonstration](https://uphash-network.github.io/mini-jev/assets/Mini_Jev_Demonstration.mp4)
  — 144.96 seconds, 1920 × 1080, MPEG4/H.264. This unchanged earlier recording
  demonstrates the same released interface; its closing caption names the
  earlier source branch. It does not demonstrate the later research-only integrations.
- [LMQL integration diagnostic](comparator_study/README.md) — actual LMQL
  scoring, a disclosed custom native backend, and retained tolerance failures.
- [ChainForge integration diagnostic](chainforge_integration/README.md) —
  actual provider registration/dispatch and the released local API, without a
  browser-interface or human usability claim.
- [September 27 revision and checks](nonhuman_revision_20260927/README.md) — evidence-led evaluation without a required human study; comparison scopes and post-hoc LMQL diagnosis.
- [Reviewer guide](reviewer_20261002/README.md) — standard-library integrity/accounting checks and the separate model-free numerical replay.
- [Japanese diagnostic package](diagnostic_value_20261003/publication/README.md) — 2,400 additional calls; source witnesses and model-free replay.
- [Japanese/English, two-family package](generality_20261003/publication/README.md) — 4,800 additional calls; all four strata, retained implementation failure, model-free replay and separate inference reproduction instructions.
- [External replication handoff](external_replication_20261002/README.md) — pinned source, CPU preflight, separate second-Mac native smoke and blank operator log; no external result yet.
- [Original source/evidence artifact checks](FINAL_CHECKS.20260925.json) — historical 25 September snapshot.

The September 29 name revision preserves the numerical results and adds the distinct r-ms/mini-jev implementation to related work. [Rename revision and checks](rename_20260929/README.md). The September 27 manuscript remains available as [a historical PDF](NAACL2027_Mini_Jev.pdf). Its reviewer guide and post-hoc diagnostic remain applicable. Their [publication manifest](nonhuman_revision_20260927/PUBLICATION_MANIFEST.json) records exact file hashes. The published source/evidence ZIP remains unchanged.

The source/evidence ZIP is a frozen composition of the application and the original
three paper studies (26,050 measured research requests). It excludes the current
manuscript, video, later journal experiments, the separate 2,400-call and 4,800-call
follow-up packages, and the separately linked framework diagnostics.
Its exact manifest distinguishes historical background records.
The ZIP preserves historical documentation; this page is the current entry point.

## What the evidence supports

The system exposes Choice/Noul/Score, candidate probabilities, concentration,
and request/response JSON from frozen local models. Candidate normalization and
these inspection ideas have precedents, identified in the paper. There is no
claim of a new scoring algorithm, trained-head gain, one-token latency advantage,
or human usability advantage.

The original three experiments use Japanese public-data subsets and 4,050, 7,600
and 14,400 measured requests; requests are not independent questions. The newer
Japanese/English follow-up extends five-choice evidence to two model families
and two distinct datasets on the same Mac; language, dataset, size and family
differences are not isolated causal effects. Model pretraining overlap remains
unknown. The separate local regression suite has
2,400 AI-authored items. Reanalysis reproduced all 56 derived outputs byte for
byte. A fresh native compile and a real three-type smoke succeeded on the same
Mac, reusing verified upstream source and model caches. No second-machine or
fresh-download reproduction is claimed.

LMQL's 12 synthetic argmax decisions matched; maximum probability difference
was 2.63e-5, with 3 cases failing the frozen 1e-5 tolerance. ChainForge's four
request pairs/eight typed-answer pairs matched exactly, and three invalid inputs
were rejected. These are diagnostic integrations, not general framework benchmarks.

## Build and submission state

From the repository root:

```sh
python3 paper/naacl2027/build.py --tectonic /path/to/tectonic
```

Tested with Tectonic 0.17.0. Official ACL style files are unmodified and checked
against [their provenance](STYLE_PROVENANCE.json). All eleven rendered pages were
visually checked; there are no undefined citations or overfull boxes. Ordinary
underfull-box and the style dependency's existing `lineno` UTF-8 warnings remain
without visible corruption.

The current PDF was submitted through the reopened EACL portal on
**6 October 2026**; the receipt and submitted record were verified. The
[official EACL call](https://2027.eacl.org/calls/demos/) lists author notification
on **18 December 2026**. The decision is pending. The PDF and frozen evidence
were not changed for this submission-status update. No concurrent NAACL or
overlapping journal submission has been made; the substantive journal extension
remains separate.

Code and original project-authored material: MIT. Japanese dataset-derived material:
applicable CC BY-SA 4.0 terms and upstream attribution in the bundle; English
CommonsenseQA retains MIT terms. Model
weights and third-party libraries retain their upstream terms and are not bundled.
