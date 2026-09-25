# Mini Jev — NAACL 2027 System Demonstrations manuscript

**Manuscript and reproducibility artifacts completed on 25 September 2026.
Not submitted, accepted, or peer reviewed.**

Author: **Yuki Oshio, UPHASH Inc.** Single author; identified for the single-blind track.

## Read and run

- [Research project page](https://uphash-network.github.io/mini-jev/) — manuscript, video, findings, and installation links in one place.
- [Paper PDF](NAACL2027_Mini_Jev.pdf) — 8 pages: 6 pages including limitations,
  acknowledgements and ethics, followed by 2 reference pages.
- [Download the versioned source and evidence ZIP](https://raw.githubusercontent.com/UpHash-Network/mini-jev/refs/heads/research/naacl2027-demo/paper/naacl2027/reproducibility/naacl-repro-v1-20260925.zip)
  — 18,060,014 bytes; SHA-256
  `a15e0699a54be15d56bd99ed8181429b71fdfc7ace756d6e065a75538786c053`.
- [Reproduction instructions and validation](reproducibility/README.md) —
  CPU-only analysis replay; native installation; exact manifests and limitations.
- [Captioned live demonstration video](https://raw.githubusercontent.com/UpHash-Network/mini-jev/refs/heads/research/eacl2027-demo/paper/eacl2027/Mini_Jev_Demonstration.mp4)
  — 144.96 seconds, 1920 × 1080, MPEG4/H.264. This unchanged earlier recording
  demonstrates the same released interface; its closing caption names the
  earlier source branch. It does not demonstrate the later research-only integrations.
- [LMQL integration diagnostic](comparator_study/README.md) — actual LMQL
  scoring, a disclosed custom native backend, and retained tolerance failures.
- [ChainForge integration diagnostic](chainforge_integration/README.md) —
  actual provider registration/dispatch and the released local API, without a
  browser-interface or human usability claim.
- [Final artifact checks](FINAL_CHECKS.20260925.json).

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
against [their provenance](STYLE_PROVENANCE.json). All eight rendered pages were
visually checked; there are no undefined citations or overfull boxes. Ordinary
underfull-box and the style dependency's existing `lineno` UTF-8 warnings remain
without visible corruption.

The [official call](https://2027.naacl.org/calls/system_demonstration/) opens
submission **1 November 2026**. Deadline: **4 December 2026, 23:59 AoE**
(**5 December, 20:59 JST**). The internal target is 20 November JST. The actual
submission form, account access and current venue requirements must be checked
when the portal opens. There is no submission ID or receipt yet. The earlier
EACL attempt closed without a submission. No overlapping journal submission has
been made; the substantive journal extension remains separate.

Code and original project-authored material: MIT. Dataset-derived material:
applicable CC BY-SA 4.0 terms and upstream attribution in the bundle. Model
weights and third-party libraries retain their upstream terms and are not bundled.
