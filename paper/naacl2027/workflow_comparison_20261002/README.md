# Six-case frozen-evidence workflow comparison

**Observed result:** LogitTrail, complete formatted JSON and a pinned, unmodified ChainForge GUI all retain the supplied evidence in the tested paths. The checked ChainForge import supports real native table filtering, condition metadata and named candidate scores; it is not limited to an unstructured JSON blob. The differences documented here concern presentation and preparation, not evidence availability or demonstrated user benefit.

This is a finite, AI-operated functional inspection of **six frozen cases**, with **32 question instances in the task inventory**. There were **zero human participants and zero new model calls**. Neither count is an independent empirical sample size or a human success-rate denominator. No elapsed human timings, usability superiority, preference or decision-quality improvement were measured.

## Design and source provenance

[protocol.json](protocol.json) and [tasks.json](tasks.json) were frozen before these case-level GUI runs. [TASK_DESIGN.md](TASK_DESIGN.md) records sampling, task definitions, prior knowledge and scope. Two studies × Choice/Noul/Score are covered, and each of three checkpoints occurs twice. Each item is the minimum hash among 200 eligible IDs, without looking at outcomes. Fixed condition pairs reflect presentation reversal or overlapping averaging pools. There was no re-selection of trivial or unchanged results; none of the selected IDs coincides with the previously published featured examples.

- Protocol SHA-256: `237ce0e6dc1dea51a0928d43a5167441e4b1dbf21d2438e806f80622d8d8bad0`
- Task package SHA-256: `d629475e55bdc8c5d35cfb813a982925e65485a6a21b27d0a34e0c4fefc829a7`
- Source ZIP SHA-256: `a15e0699a54be15d56bd99ed8181429b71fdfc7ace756d6e065a75538786c053`

Expected answers come from an independently implemented Python reader of the original ZIP, with original source rows, physical request identities and full-panel distributions. The unchanged Explorer core constructs the comparison export and is checked against that reader. Independent code is not independent human review. The source data and previous full-record audit were already known; this is not a blinded study or external preregistration.

The same complete information is supplied to every presenter: exact comparison export, every condition for the selected item, the entire 200-item panel, its descriptor/full-panel summaries, and the complete shared index including models, sources, mappings, hashes and limitations. ChainForge receives the exact per-case evidence string plus a useful deterministic extraction into condition rows and numeric score columns. The adapter does not read the assessor's answer key.

## Observed paths

See [RESULT_MATRIX.md](RESULT_MATRIX.md) for the compact task-family matrix. Machine-readable reports are [LogitTrail/JSON browser checks](evidence/logittrail/BROWSER_RESULTS.json), [ChainForge GUI checks](evidence/chainforge/CHAINFORGE_RESULTS.json), and [spreadsheet checks](evidence/chainforge/SPREADSHEET_CHECK.json). [REVIEW.json](REVIEW.json) records their original report hashes and the limits of this separate review. Screenshots and the compact spreadsheet accompany the reports. The original full exported flow is retained locally with a digest rather than duplicating its multi-megabyte contents in the public evidence directory.

- **LogitTrail:** six selected browser comparisons, probability display rounding, labels and shared/union-call counts, all 200-item label counts, provenance member/line/hash access and exact key export fields checked. Detailed values remain available in JSON. The absolute expectation–mode gap requires subtraction; some distribution summaries require metadata access or arithmetic.
- **Complete JSON:** the original audit viewer and the new public route were both exercised. All six selected exports, entire panels, entire indices and every-condition summaries match the common input after parsing. This is evidence access, not measured ease of finding an answer.
- **ChainForge 0.3.7.6:** all six cases were selected through the actual Inspector's search; each exposes the matching item and two conditions. All twelve actual response lightboxes were opened and their compact condition/source JSON checked exactly. Top-level flow export recovers all six complete evidence strings byte-for-byte. The native Inspector spreadsheet contains twelve exact compact condition/source records and 52 candidate-probability numeric cells equal to the saved binary floating-point values (maximum observed difference zero). A separate standard-library XLSX/XML reader independently reproduced those checks. This does not assert byte identity of the XLSX file across runs or preservation of multi-megabyte inputs in spreadsheet cells.
- The completed browser reports contain no page errors. Zero reported errors does not establish support for other browsers, configurations or workloads.

**Computation boundary:** ChainForge's named candidate scores, labels, typed values, semantic alignment, comparison deltas and physical-call membership/union values were supplied by the adapter from existing saved exports. ChainForge genuinely presents, filters and exports these values; this run does not show it recomputing those semantics from raw inference runs. LogitTrail's own comparison code computes its alignment/differences/call accounting from saved records. The formatted-JSON viewer calls the same core and displays the resulting fields. All three conditions receive the same underlying information.

## Version and setup

The served ChainForge application is the unmodified published **0.3.7.6 wheel**, SHA-256 `ffd4cc4519974e56be42f7b8d7e0f48f661d6a5a543f2122ff5ecb71ab35133f`. Its main bundle's source map matched 139 project files at official commit `641fd577442daf43b45064e7aae86c983f03f85d`. See [version provenance](competitor/VERSION_PROVENANCE.json), [import manifest](competitor/IMPORT_MANIFEST.json) and [setup/import instructions](competitor/README.md). The wheel and pinned source were checked separately; matching source-map files is not a reproducible-build certificate for every dependency.

The existing isolated Python dependency environment was reused. Cache-holder processor nodes and two native Inspect nodes were constructed by the supplied format adapter. The processors were not executed. This is a customized frozen-record import workflow, not a zero-configuration integration, a clean installation study or a test of the Ollama decision provider. No API/model credentials were used for inference.

LogitTrail/JSON used Playwright Chromium **151.0.7922.34**, headless; ChainForge used installed Google Chrome **154.0.8037.93**, headed with a fresh profile. Browser and operating modes differ, which further precludes a performance comparison. A preliminary ChainForge attempt stopped on an ambiguous automation locator; the completed run targets the visible search field. The task/protocol hashes remained fixed. Harness failures are not treated as missing product capabilities. [Execution notes](RUN_NOTES.md) document the exploratory attempts and corrections.

## Reproduce

From the repository root, first verify deterministic task regeneration:

```sh
python3 paper/naacl2027/workflow_comparison_20261002/generate_tasks.py --check
```

Serve that root on localhost, with the browser tooling and pinned competitor installed separately:

```sh
python3 -m http.server 18880 --bind 127.0.0.1
```

In another terminal, with Playwright resolvable by Node and Chromium available:

```sh
node paper/naacl2027/workflow_comparison_20261002/check_browser.cjs \
  --base-url http://127.0.0.1:18880 --out /tmp/logittrail-workflow-new
node paper/naacl2027/workflow_comparison_20261002/check_chainforge.cjs \
  --url http://127.0.0.1:18881 --out /tmp/chainforge-workflow-new
```

Verify the downloaded compact spreadsheet with `python3 paper/naacl2027/workflow_comparison_20261002/check_spreadsheet.py /tmp/chainforge-workflow-new/conditions.xlsx --out /tmp/chainforge-workflow-new/SPREADSHEET_CHECK.json` (requires openpyxl).

Output directories must be new. Start the pinned ChainForge server and use the included `.cfzip` as described in its setup guide. These commands test application paths and saved-data fidelity; they do not generate human observations or new predictions. Actual browser versions and installation differences must be recorded on rerun.

## Interpretation limits

This closes the narrow gap between a source-only competitor description and an executed, information-equivalent GUI import check. It supports describing the tested workflow and its preparation. It does **not** establish an advantage in task completion, discovery of errors, time, workload or preference, nor general absence of a ChainForge capability. Full-payload preservation and task-specific native presentation must remain separate in the paper. The two-person human pilot is planned separately and has no collected results.
