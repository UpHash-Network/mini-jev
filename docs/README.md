# LogitTrail research project page

Static, dependency-free research overview. The intended GitHub Pages source is
`research/naacl2027-demo`, `/docs`; URL: https://uphash-network.github.io/mini-jev/.
LogitTrail was formerly named Mini Jev. The display name changed on 29 September 2026; the repository and Pages URL retain `mini-jev` for existing links. This is the UPHASH project, distinct from the related [r-ms/mini-jev](https://github.com/r-ms/mini-jev) project.

Only this directory is served. No API or inference runs on GitHub Pages.

Preview with `python3 -m http.server 8788 --bind 127.0.0.1 --directory docs`.

## Content provenance

- Scientific content: `paper/naacl2027/main.tex` and `paper/naacl2027/README.md`,
  numerical evidence frozen at commit `bd025e8b1d14352a440d289c73b00ae445290935`.
  The current manuscript was updated on 3 October 2026; the reviewer entry was also updated on 3 October, and the demonstration on 2 October. Later diagnostic studies have separate bundles and are not part of that original evidence commit.
  The separately submitted arXiv preprint is awaiting moderation; the public PDF
  here follows the continuing conference-preparation revision.
- `assets/LogitTrail_Manuscript.pdf`: byte-identical copy of `paper/naacl2027/NAACL2027_LogitTrail.pdf`, the current renamed conference-preparation manuscript. The Mini Jev manuscript and the submitted arXiv package remain historical artifacts; this is not a replacement arXiv upload.
- `assets/LogitTrail_60s.mp4` and `assets/LogitTrail_60s.jpg`: current 60-second
  evidence walkthrough and poster, made from retained study evidence. The video
  is explicitly an explanation of archived results, not a new live inference run. Its archival UI excerpt retains the former Mini Jev name. The earlier `Mini_Jev_60s` assets remain available; new-version provenance is in `publication/rename-20260929/video/`.
- `assets/workbench.png`: unmodified `paper/naacl2027/figures/demo-presentation.png`, recorded under the former Mini Jev name.
- `assets/Mini_Jev_Demonstration.mp4`: unmodified `paper/eacl2027/Mini_Jev_Demonstration.mp4`.
  Its former Mini Jev name, earlier branch caption, and evaluation scope are disclosed on the page.

When a preprint is announced, update the paper link, manuscript citation,
`citation.bib`, publication status, and date together. Do not invent an arXiv ID,
DOI, conference submission, or acceptance. Update the manuscript copy and the
manifest when the source PDF changes. Existing dataset and model licenses still apply.

The overview content works without JavaScript. The optional evidence explorer requires JavaScript and performs SHA-256 checks in the browser. No analytics, remote fonts, or
external embeds. Videos are loaded only on demand. The full interface recording includes embedded captions;
the short evidence walkthrough presents its explanation as visible text.

## Saved evidence explorer (28 September 2026)

`explorer/` adds a comparison screen for the retained presentation-sensitivity and probability-averaging panels. It is included in the October 2 conference-preparation manuscript; the submitted arXiv source remains unchanged. It performs no inference. The original frozen ZIP is the input to the deterministic exporter; see [data scope and derivation](explorer/DATA.md) and [interface verification](explorer/README.md).

## Current demonstration (2 October 2026)

`assets/LogitTrail_Demo_20261002.mp4` contains actual browser interactions with the saved-evidence Explorer and a clearly labeled 16-second excerpt of the earlier local-inference recording. English captions are embedded outside the Explorer viewport; no new inference is claimed. See `publication/revision-20261002/video/` for capture/build scripts, transcript, provenance, and visual verification. The paper figure is a separate unmodified element screenshot of the JCoLA comparison, not a synthetic mockup.

The 3 October strengthening revision adds four primary-source references and a retrospective retained-failure case. `explorer/import/engineering-case.jsonl` is byte-identical to the case projection; it adds no model measurement or human observation. Current source and checks: `paper/naacl2027/revision_20261003_strengthening/`.
