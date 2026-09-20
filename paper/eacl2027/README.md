# EACL 2027 System Demonstrations: review-draft package

**Status: revised local materials for author review; not submitted, accepted, or peer reviewed.**

The video and presentation view were revised for readability. [VALIDATION.json](VALIDATION.json) records this revision’s artifact hashes and completed video checks; its earlier public-download checks remain explicitly historical. Publication and matching-ZIP verification performed after that record are tracked separately, so the versioned record does not make a self-referential claim about its own commit.

Author: **Yuki Oshio, UPHASH Inc.** Contact: **oshio@uphash.net**.

## Materials

- [Paper PDF](EACL2027_Mini_Jev_Draft.pdf): official ACL format, identified author, review line numbers. Main content including limitations ends within page 6; references extend to page 7.
- [Live demonstration video](Mini_Jev_Demonstration.mp4): 144.96 seconds (about 145), 1920×1080 H.264 MP4, 9,105,242 bytes, English captions, no audio. It records actual browser interaction and native-model responses, with no replayed or substituted predictions. The recording uses the optional presentation view with all three typed results visible together; caption panels appear beneath the captured screen. Its SHA-256 is `094c759f7b6d10af1bdac427bd121a5671cc7e2122857863cd1aa9526b378123`.
- [Install and run the demonstration](../../demo/README.md).
- [LaTeX source](main.tex), [bibliography](references.bib), [style provenance](STYLE_PROVENANCE.json).
- [Validation record](VALIDATION.json): artifact hashes, PDF/video checks, public download checks, and the limits of installation testing.
- [Video provenance](VIDEO_PROVENANCE.json), [caption script](VIDEO_SCRIPT.md), and the two recorded [responses](recording/).
- [Submission checklist](SUBMISSION_CHECKLIST.md), [form draft](FORM_DRAFT.md), [author review guide in Japanese](AUTHOR_REVIEW.ja.md).

The publication branch is `research/eacl2027-demo`. For a source checkout:

```sh
git clone --branch research/eacl2027-demo https://github.com/UpHash-Network/mini-jev.git
cd mini-jev
./build_native.sh --work-dir .build/native --output .build/runtime --jobs 2
python3 fetch_native_model.py --output models/Qwen3.6-35B-A3B-Q4_K_M.gguf
./run.sh --without-calibration
```

Keep that terminal running. In another terminal in the same repository:

```sh
python3 -m demo.server
```

Open `http://127.0.0.1:8766/` for the standard workbench, or `http://127.0.0.1:8766/#presentation` for the recording layout. The tested native path requires Apple Silicon, macOS 26.4+, Python 3.10+, Xcode command-line tools, CMake, and Git. The model download is 20.4 GB. Recorded runs used 64 GB unified memory; a lower-memory minimum has not been established. Model weights and prebuilt executables are not in this source package.

## Build the paper

Install [Tectonic](https://tectonic-typesetting.github.io/) (tested with 0.17.0), then run from the repository root:

```sh
python3 paper/eacl2027/build.py
```

Alternatively pass `--tectonic /path/to/tectonic`. The first build may download TeX resources. Build logs and intermediates are kept under `.build/eacl2027-paper/`. The builder verifies that the official ACL style files still match their recorded hashes. It does not alter margins, text size, or the official style source.

## Validation and scope

The browser bridge passed eight CPU HTTP integration tests, rerun successfully after the presentation-view revision. An independent AI-agent code review of the earlier workbench found no critical or high issues; that earlier review does not cover the later presentation-view changes. The earlier workbench was also exercised against the real resident model at desktop and mobile viewport sizes. The revised recording contains two new live requests, viewport checks, and a successful clipboard read-back. Independent AI inspection of 24 frames around caption boundaries found no material screen/caption mismatch; the validation record distinguishes these final-artifact checks from 17 representative scenes inspected in an earlier encode of the same recording. These checks validate the software demonstration, not a new benchmark or independent human usability study.

The existing [matched empirical study](../matched_study/README.md) remains unchanged: 4,050 requests, 1,350 direct/one-token pairs, one model and one machine. Its latency measurements use a different controlled wrapper from the live browser interface. The two English support examples are illustrative; reported quality benchmarks are Japanese.

Project-authored source, captions, and local examples follow the repository MIT license. Existing external-data materials retain their documented attribution and CC BY-SA terms. See [NOTICE.md](../../NOTICE.md).

## Remaining author and submission steps

The author must review and approve the exact paper and recording, confirm the required reviewer nomination and submission declarations, and sign in with an active OpenReview profile. The user reports that OpenReview registration has been submitted and activation is pending; active login has not been verified. The submission form and any attachment-size limits must be checked in the authenticated page. The browser-verification screen prevented form inspection during preparation. No venue submission or declaration has been made on the author's behalf; the assistant has not created an account or sent registration email.

The deadline is **September 23, 2026, 20:59 Japan time** (September 22, 23:59 AoE). See the [official Demo call](https://2027.eacl.org/calls/demos/).
