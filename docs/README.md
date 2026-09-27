# Mini Jev research project page

Static, dependency-free research overview. The intended GitHub Pages source is
`research/naacl2027-demo`, `/docs`; URL: https://uphash-network.github.io/mini-jev/.
Only this directory is served. No API or inference runs on GitHub Pages.

Preview with `python3 -m http.server 8788 --bind 127.0.0.1 --directory docs`.

## Content provenance

- Scientific content: `paper/naacl2027/main.tex` and `paper/naacl2027/README.md`,
  numerical evidence frozen at commit `bd025e8b1d14352a440d289c73b00ae445290935`.
  Entry copy and related-work discussion were updated on 26 September 2026.
  The separately submitted arXiv preprint is awaiting moderation; the public PDF
  here follows the continuing conference-preparation revision.
- `assets/Mini_Jev_Manuscript.pdf`: byte-identical copy of
  `paper/naacl2027/NAACL2027_Mini_Jev.pdf` (not a replacement upload of the submitted arXiv package).
- `assets/Mini_Jev_60s.mp4` and `assets/Mini_Jev_60s.jpg`: 60-second
  evidence walkthrough and poster, made from retained study evidence. The video
  is explicitly an explanation of archived results, not a new live inference run.
- `assets/workbench.png`: unmodified `paper/naacl2027/figures/demo-presentation.png`.
- `assets/Mini_Jev_Demonstration.mp4`: unmodified `paper/eacl2027/Mini_Jev_Demonstration.mp4`.
  Its earlier branch caption and evaluation scope are disclosed on the page.

When a preprint is announced, update the paper link, manuscript citation,
`citation.bib`, publication status, and date together. Do not invent an arXiv ID,
DOI, conference submission, or acceptance. Update the manuscript copy and the
manifest when the source PDF changes. Existing dataset and model licenses still apply.

The overview content works without JavaScript. The optional evidence explorer requires JavaScript and performs SHA-256 checks in the browser. No analytics, remote fonts, or
external embeds. Videos are loaded only on demand. The full interface recording includes embedded captions;
the short evidence walkthrough presents its explanation as visible text.

## Saved evidence explorer (28 September 2026)

`explorer/` adds a comparison screen for the retained presentation-sensitivity and probability-averaging panels. It is a later interface supplement, separate from the September 27 manuscript and submitted arXiv source. It performs no inference. The original frozen ZIP is the input to the deterministic exporter; see [data scope and derivation](explorer/DATA.md) and [interface verification](explorer/README.md).
