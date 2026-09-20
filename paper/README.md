# Working-paper package

Version **v0.2**, September 20, 2026. The matched experiment and its independent numerical audit are complete. This is an empirical working draft, not a submitted, accepted, peer-reviewed, or formally deposited paper. It extends the original [technical report](TECHNICAL_REPORT.md), which remains a record of the initial release. The completed run retains all 4,050 scheduled measured requests and 21 warm-ups, with zero failures.

- [Manuscript, editable Markdown](MANUSCRIPT.md)
- [Review PDF](Mini_Jev_Working_Paper.pdf)
- [Japanese research brief and remaining work](RESEARCH_STATUS.ja.md)
- [Retrospective analysis and reproduction](analysis/REPORT.md)
- [Earlier external JNLI pilot](external_pilot/README.md)
- [Expanded external data: JCoLA, JSTS, and JCommonsenseQA](external_expanded/README.md)
- [Matched comparison: protocol, scope, and fresh-run instructions](matched_study/README.md)
- [Source-checked related work](related_work_review.md)
- [Earlier next-study plan](NEXT_STUDY_PROTOCOL.md); the current experiment uses the [matched-study protocol](matched_study/PROTOCOL.json)
- [Claim-to-evidence map](CLAIM_EVIDENCE.md)
- [Official-source venue, deadline, and location list](SUBMISSION_OPTIONS.ja.md)

The draft's contribution is a reproducible artifact and qualified empirical observations. Candidate-token readout, prompt repetition, and temperature scaling are prior techniques. The v0.2 design is a **single-model, single-device empirical study**, not a novel training algorithm or a reproduction of Jev/RLCD. All 1,350 direct/one-token pairs have identical logits and labels; the primary latency difference is +0.090 ms with conditional interval [-0.748, +0.845]. JSON adds +160.296 ms [138.119, 177.059] under a serialization-specific prompt, with mixed task-quality changes. These are observations in the recorded session, not general speed guarantees.

## Existing evidence retained from v0.1

The historical 2,400-item local run is unchanged. A retrospective 20,000-replicate whole-family analysis reproduces its reported values and distinguishes small, uncertain NLL/Brier changes from increased expected-stage MAE. The newly executed, fixed 300-item JNLI public-dev pilot scores 243/300 (81.0%); contradiction recall is 61%. The historical temperature transfers favorably on the pilot's probability-loss point estimates, without fitting on JNLI. These are different task distributions and must not be pooled into one accuracy or interpreted as a controlled distribution-shift experiment.

JNLI preparation and inference use an immutable source revision, source hash, fixed sampling, and before-inference local receipts. There is no external registration claim. Metadata in the pilot identifies an overlap-counter issue and supplies an independently recomputed definition; the original run and predictions are retained.

## Completed v0.2 experiment

The frozen design compares direct candidate readout, matched one-token constrained decoding, and grammar-constrained JSON generation through a common loopback HTTP harness. It selects 150 existing local regression items and 600 additional public-development examples: 200 JCoLA, 200 JSTS, and 200 JCommonsenseQA. Five repetitions per local item and one per external item across three modes specify **4,050 measured requests plus 21 excluded warm-up requests**. Requests and generated-token decode calls are different counts; JSON may need several decode calls per request. All scheduled requests completed. See the [analysis](matched_study/REPORT.md), [full metrics](matched_study/SUMMARY.json), and [independent audit](matched_study/INDEPENDENT_AUDIT.json).

Direct and one-token modes share the complete prompt and candidate tokens. JSON uses a format-specific prompt and emits the complete object, so its comparison includes that prompt difference. The measured HTTP response has the same type/semantic-label schema in all modes; numerical distributions and native traces are retained separately. These timings describe the research harness, not a production-service SLA. Follow the [matched-study guide](matched_study/README.md) to build its separate helper and create a fresh local freeze.

The earlier JNLI pilot and the three new tasks represent four named public datasets, with unknown pretraining/post-training contamination and measured source overlap. They are not four independent deployment domains. JCoLA classification, JCommonsenseQA classification, and JSTS continuous-score regression require distinct metrics. Expected-score MAE and hard-selected-stage MAE are reported separately; there is no common accuracy across these tasks. Original dataset text stays outside the repository.

## Reproduce the analysis and figures

From the repository root, no model or extra package is needed for these checks:

```sh
python3 -m unittest discover -s paper/analysis -p test_analysis.py -v
python3 -m unittest discover -s paper/external_pilot -p test_pilot.py -v
python3 -m unittest discover -s paper/external_expanded -p test_prepare.py -v
python3 -m unittest discover -s paper/matched_study -p 'test_*.py' -v
python3 paper/analysis/analyze_frozen_run.py
python3 paper/matched_study/analyze_study.py
```

The fixture commands exercise statistics, sampling, formatting, and the research HTTP contract, not semantic model quality or GPU performance. Re-running the historical analysis overwrites only derived files in `paper/analysis/`. It does not analyze a partial matched run. For fresh native inference, follow the separate pilot or matched-study instructions; they require local model weights, the pinned native runtime, and new output directories. Preserve published preparation, protocol, and result files.

To build review figures and PDF in a separate environment:

```sh
python3 -m venv .cache/paper-render
.cache/paper-render/bin/python -m pip install -r paper/requirements-render.txt
.cache/paper-render/bin/python paper/make_figures.py
.cache/paper-render/bin/python paper/make_matched_figures.py
.cache/paper-render/bin/python paper/build_paper.py
```

The renderer refuses to build with unfilled manuscript sections. Markdown is the canonical editable source. PNG and SVG charts are rebuilt from the historical CSVs and completed matched-study traces. The PDF is a readable review layout, not a particular conference template. Figure rendering and PDF metadata may vary by platform; the recorded inference and statistical output hashes have distinct provenance.

Bibliographic entries are split between `references.bib` and `additional_references.bib`; the manuscript's numbered reference list corresponds to primary sources checked during drafting. Upstream project documentation is identified as product evidence.

## Data and code licensing

Project-authored paper code, tests, build/analysis tools, generic methods, and original explanatory documentation use the repository **MIT** license. External dataset-derived metadata, selections, audits, predictions, results, and task protocols/rubrics retain **CC BY-SA 4.0** with their original JGLUE or JCoLA attribution. This includes adapted JSTS annotation guidance and external records inside mixed matched-study files; the underlying local authored data remain MIT.

See the [JNLI data notice](external_pilot/README.md), [expanded-data notice and license copies](external_expanded/README.md), [matched-record boundary](matched_study/README.md), and [root attribution notice](../NOTICE.md). Original external source texts, model weights, and compiled native executables/libraries are not distributed in this paper package. Download source data to a separate local cache and build executable artifacts separately.
