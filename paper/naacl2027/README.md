# LogitTrail — NAACL 2027 System Demonstrations manuscript

**29 September 2026: renamed from Mini Jev to LogitTrail.** The submitted arXiv version retains its original Mini Jev title; this is a later conference-preparation revision. [Name and version mapping](../../NAMING.md).

**Conference submission preparation, updated 3 October 2026 (JST).**
The related preprint was submitted to arXiv on 26 September and is awaiting
moderation; a public arXiv ID is not yet available. This NAACL manuscript is
**not submitted, accepted, or peer reviewed**. The arXiv submission and this
continuing conference revision are distinct versions.

Author: **Yuki Oshio, UPHASH Inc.** Single author; identified for the single-blind track.

The October 2 revision integrates the saved-evidence Explorer, complete-record functional audit, current related work, and a new 127-second demonstration. The frozen experiment archive and arXiv submission are unchanged. [Revision evidence](revision_20261002/README.md).

A subsequent [matched saved-evidence workflow check](workflow_comparison_20261002/README.md) runs six hash-selected cases in the Explorer, complete JSON, and the published ChainForge 0.3.7.6 GUI. All retain the supplied information; the comparison does not establish a human-performance advantage. [Current revision checks](revision_20261002_workflows/README.md) and [unrun Explorer pilot materials](explorer_user_evaluation_20261002/README.md) are separate from the frozen research experiments.

The [raw-record follow-up](raw_workflow_20261002/README.md) executes custom JavaScript in the unmodified ChainForge Processor, reconstructing 2,400 conditions from 6,000 archived logit records. The actual GUI export matches independent Python arithmetic within the frozen 1e-12 tolerance. This establishes competitor feasibility with custom code; neither human advantage nor new model performance is claimed. [Latest revision checks](revision_20261003_raw/README.md) cover this addition.

## Read and run

- [Research project page](https://uphash-network.github.io/mini-jev/) — manuscript, video, findings, and installation links in one place.
- [Paper PDF](NAACL2027_LogitTrail.pdf) — 10 pages: main text, limitations, and acknowledgements end on page 6; ethics begins on page 6 and references end on page 8; Appendix A occupies pages 9–10.
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
- [External replication handoff](external_replication_20261002/README.md) — pinned source, CPU preflight, separate second-Mac native smoke and blank operator log; no external result yet.
- [Original source/evidence artifact checks](FINAL_CHECKS.20260925.json) — historical 25 September snapshot.

The September 29 name revision preserves the numerical results and adds the distinct r-ms/mini-jev implementation to related work. [Rename revision and checks](rename_20260929/README.md). The September 27 manuscript remains available as [a historical PDF](NAACL2027_Mini_Jev.pdf). Its reviewer guide and post-hoc diagnostic remain applicable. Their [publication manifest](nonhuman_revision_20260927/PUBLICATION_MANIFEST.json) records exact file hashes. The published source/evidence ZIP remains unchanged.

The source/evidence ZIP is a frozen composition of the application and the three
paper studies (26,050 measured research requests). It excludes the current
manuscript, video, later journal experiments, and the separately linked framework
diagnostics. Its exact manifest distinguishes historical background records.
The ZIP preserves historical documentation; this page is the current entry point.

## What the evidence supports

The system exposes Choice/Noul/Score, candidate probabilities, concentration,
and request/response JSON from frozen local models. Candidate normalization and
these inspection ideas have precedents, identified in the paper. There is no
claim of a new scoring algorithm, trained-head gain, one-token latency advantage,
or human usability advantage.

The three main experiments use 4,050, 7,600 and 14,400 measured requests;
requests are not independent questions. The separate local regression suite has
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
against [their provenance](STYLE_PROVENANCE.json). All ten rendered pages were
visually checked; there are no undefined citations or overfull boxes. Ordinary
underfull-box and the style dependency's existing `lineno` UTF-8 warnings remain
without visible corruption.

The [official call](https://2027.naacl.org/calls/system_demonstration/) opens
submission **1 November 2026**. Deadline: **4 December 2026, 23:59 AoE**
(**5 December, 20:59 JST**). The internal target is 20 November JST. The actual
submission form, account access and current venue requirements must be checked
when the portal opens. There is no NAACL submission ID or receipt yet. The separate arXiv preprint is awaiting moderation. The earlier
EACL attempt closed without a submission. No overlapping journal submission has
been made; the substantive journal extension remains separate.

Code and original project-authored material: MIT. Dataset-derived material:
applicable CC BY-SA 4.0 terms and upstream attribution in the bundle. Model
weights and third-party libraries retain their upstream terms and are not bundled.
