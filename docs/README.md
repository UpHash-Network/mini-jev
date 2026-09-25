# Mini Jev research project page

Static, dependency-free research overview. The intended GitHub Pages source is
`research/naacl2027-demo`, `/docs`; URL: https://uphash-network.github.io/mini-jev/.
Only this directory is served. No API or inference runs on GitHub Pages.

Preview with `python3 -m http.server 8788 --bind 127.0.0.1 --directory docs`.

## Content provenance

- Scientific content: `paper/naacl2027/main.tex` and `paper/naacl2027/README.md`,
  research snapshot at commit `bd025e8b1d14352a440d289c73b00ae445290935`.
- `assets/Mini_Jev_Manuscript.pdf`: byte-identical copy of
  `paper/naacl2027/NAACL2027_Mini_Jev.pdf` (not the unsubmitted arXiv package).
- `assets/workbench.png`: unmodified `paper/naacl2027/figures/demo-presentation.png`.
- `assets/Mini_Jev_Demonstration.mp4`: unmodified `paper/eacl2027/Mini_Jev_Demonstration.mp4`.
  Its earlier branch caption and evaluation scope are disclosed on the page.

When a preprint is announced, update the paper link, manuscript citation,
`citation.bib`, publication status, and date together. Do not invent an arXiv ID,
DOI, conference submission, or acceptance. Update the manuscript copy and the
manifest when the source PDF changes. Existing dataset and model licenses still apply.

All primary content works without JavaScript. No analytics, remote fonts, or
external embeds. The video is loaded only on demand and includes embedded captions.
