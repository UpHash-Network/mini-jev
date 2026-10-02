# LogitTrail demonstration — 2 October 2026

[Watch the 127.08-second video](https://uphash-network.github.io/mini-jev/assets/LogitTrail_Demo_20261002.mp4) · [English transcript](TRANSCRIPT.en.md) · [Provenance](PROVENANCE.json)

1920 × 1080 H.264, 25 fps, silent with embedded English captions. The main portion records actual browser interactions with saved evidence at real-time speed. A separate 16-second archival excerpt shows the local inference interface under its former Mini Jev name. Intro/outro cards and caption strips explain the scope. No new model inference or human evaluation is depicted.

The viewport is uniformly scaled from 1280 × 640 to 1920 × 960; the 120-pixel caption area is added below it. No Explorer pixels are cropped. The archival excerpt replaces only its earlier caption strip. Original task/option text is not reconstructed. Four pre-existing outcome-selected examples illustrate behavior, not prevalence.

## Rebuild

Install Playwright/Chromium, Pillow, and ffmpeg/ffprobe. From the repository root, serve `docs/` at `http://127.0.0.1:18879`, then:

```sh
node publication/revision-20261002/video/capture.cjs .runs/demo-capture
python3 publication/revision-20261002/video/build_video.py --capture-dir .runs/demo-capture
```

Actual browser timings vary, so raw frames and final hashes are not expected to rebuild bit-for-bit. `capture.json` records this run's event timings. `capture_figure.cjs` independently captures the paper's binary JCoLA comparison; it is not a frame substituted into the screencast. The frozen data index is recorded by hash. See `docs/explorer/DATA.md` and `NOTICE.md` for derivation and attribution. Composed video and dataset-derived visuals: CC BY-SA 4.0; software: MIT.
