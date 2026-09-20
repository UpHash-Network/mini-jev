# Working-paper package

Version 0.1, September 20, 2026. This is an empirical working draft, not a submitted, accepted, peer-reviewed, or formally deposited paper. It extends the original [technical report](TECHNICAL_REPORT.md), which remains a record of the initial release.

- [Manuscript, editable Markdown](MANUSCRIPT.md)
- [Review PDF](Mini_Jev_Working_Paper.pdf)
- [Japanese research brief and remaining work](RESEARCH_STATUS.ja.md)
- [Retrospective analysis and reproduction](analysis/REPORT.md)
- [New external JNLI pilot](external_pilot/README.md)
- [Source-checked related work](related_work_review.md)
- [Next controlled-study protocol](NEXT_STUDY_PROTOCOL.md)
- [Claim-to-evidence map](CLAIM_EVIDENCE.md)

The draft's contribution is a reproducible artifact and qualified empirical observations. Candidate-token readout, prompt repetition, and temperature scaling are prior techniques. No speed advantage over matched one-token generation, novel training algorithm, or reproduction of Jev/RLCD is claimed.

## Evidence added in this version

The historical 2,400-item local run is unchanged. A retrospective 20,000-replicate whole-family analysis reproduces its reported values and distinguishes small, uncertain NLL/Brier changes from increased expected-stage MAE. The newly executed, fixed 300-item JNLI public-dev pilot scores 243/300 (81.0%); contradiction recall is 61%. The historical temperature transfers favorably on the pilot's probability-loss point estimates, without fitting on JNLI. These are different task distributions and must not be pooled into one accuracy or interpreted as a controlled distribution-shift experiment.

JNLI preparation and inference use an immutable source revision, source hash, fixed sampling, and before-inference local receipts. There is no external registration claim. Metadata in the pilot identifies an overlap-counter issue and supplies an independently recomputed definition; the original run and predictions are retained.

## Reproduce the analysis and figures

From the repository root, no model or extra package is needed for these checks:

```sh
python3 -m unittest discover -s paper/analysis -p test_analysis.py -v
python3 -m unittest discover -s paper/external_pilot -p test_pilot.py -v
python3 paper/analysis/analyze_frozen_run.py
```

The first command set exercises statistical and sampling fixtures, not semantic model quality. Re-running the historical analysis overwrites only derived files in `paper/analysis/`. For fresh native inference, follow the separate pilot instructions; it requires local model weights, the pinned native runtime, and a new output directory.

To build review figures and PDF in a separate environment:

```sh
python3 -m venv .cache/paper-render
.cache/paper-render/bin/python -m pip install -r paper/requirements-render.txt
.cache/paper-render/bin/python paper/make_figures.py
.cache/paper-render/bin/python paper/build_paper.py
```

The renderer refuses to build with unfilled manuscript sections. Markdown is the canonical editable source. PNG and SVG charts are rebuilt from released CSVs. The PDF is a readable review layout, not a particular conference template. Figure rendering and PDF metadata may vary by platform; the recorded inference and statistical output hashes have distinct provenance.

Bibliographic entries are split between `references.bib` and `additional_references.bib`; the manuscript's numbered reference list corresponds to primary sources checked during drafting. Upstream project documentation is identified as product evidence.

## Data-license exception

Project-authored paper code and documentation use the repository MIT license. JNLI-derived selection and result records use **CC BY-SA 4.0**, as specified in [the pilot README](external_pilot/README.md) and [root notice](../NOTICE.md). No original JNLI sentences, model weights, or new native binaries are included in this package.
