# Frozen six-case workflow comparison — 2026-10-02

This package supports a finite, nonhuman GUI capability and evidence-access check. It does not measure usability, preference, human task success, speed, or model quality. The same already-frozen observations are shown in LogitTrail, complete formatted JSON, and an actual pinned ChainForge GUI.

## Freeze and reproducibility

The protocol was written and its hash fixed before generating task answers. The task package was then frozen and its hash sent to the root and competitor-setup agents **before their six-case GUI execution**. This is an internal timestamped freeze, not external preregistration or a blinded study. No inference was performed.

- `protocol.json` SHA-256: `237ce0e6dc1dea51a0928d43a5167441e4b1dbf21d2438e806f80622d8d8bad0`
- `tasks.json` SHA-256: `d629475e55bdc8c5d35cfb813a982925e65485a6a21b27d0a34e0c4fefc829a7`
- Original archive SHA-256: `a15e0699a54be15d56bd99ed8181429b71fdfc7ace756d6e065a75538786c053`
- Frozen question instances: **32** = five common questions × six cases + Score expectation/mode questions × two cases. These are inspection instances, not independent scientific samples.

From the repository root:

```sh
python3 paper/naacl2027/workflow_comparison_20261002/generate_tasks.py --check
```

This regenerates the package in memory, validates input hashes, compares unchanged Explorer exports to an independent reader of original ZIP rows, and demands byte-identical `tasks.json`. It never overwrites the frozen file. Python standard library and Node are sufficient; no model, API, package installation or network is required.

## Structural sampling, before consulting outcomes

Each of two studies contributes Choice, Noul and Score. A fixed Latin-cycle assignment uses each of the three models twice. For each panel, all 200 retained item IDs are eligible; the chosen ID has minimum SHA-256 of `seed + "\n" + panel_id + "\n" + item_id`, with item-ID tie-break. Seed is `logittrail-workflow-comparison-v1-20261002`. The generator stores the selected hash and a digest of the entire eligible ID/hash list.

Presentation comparisons use `baseline` and `display_reverse`. Order comparisons use `cyclic_forward` and `dihedral`, making overlapping call pools structurally relevant. No outcome, label change, accuracy, gap or variance controls selection. In particular, the Noul order pools may match exactly; that valid result must remain. The selected cases have no overlap with the published featured item IDs. Featured examples were already known and were not excluded by the selection algorithm.

| Case | Study | Type | Model | Item | Conditions A / B |
| --- | --- | --- | --- | --- | --- |
| W01 | presentation_robustness | choice | qwen2.5-0.5b | `jcommonsenseqa:valid:9925` | `baseline` / `display_reverse` |
| W02 | presentation_robustness | noul | qwen2.5-1.5b | `jcola:out_of_domain_valid:8744` | `baseline` / `display_reverse` |
| W03 | presentation_robustness | score | qwen3.6-35b-a3b | `jsts:valid:969` | `baseline` / `display_reverse` |
| W04 | order_ensemble | choice | qwen2.5-1.5b | `jcommonsenseqa:valid:8952` | `cyclic_forward` / `dihedral` |
| W05 | order_ensemble | noul | qwen3.6-35b-a3b | `jcola:out_of_domain_valid:8653` | `cyclic_forward` / `dihedral` |
| W06 | order_ensemble | score | qwen2.5-0.5b | `jsts:valid:1437` | `cyclic_forward` / `dihedral` |

## Package schema and identical inputs

`tasks.json.tasks[]` has:

- `id`, `selection`, `explorer_fragment`: stable case identity and deep-link selection.
- `prompts`: all applicable questions.
- `expected_answers`: assessor-only answers from original archived rows, never extra input for one presenter.
- `evidence_json`: **the exact complete pretty-printed JSON string** supplied to all presenters.
- `evidence_sha256`, `evidence_bytes_utf8`: digest and byte count of that string. Preserve this string during ChainForge import instead of parsing/stringifying it through a different numeric serializer.

Each evidence string includes the unchanged `comparisonExport`, the complete selected item, the complete 200-item panel with **all conditions**, its complete descriptor and summaries, and the complete original Explorer index including provenance, sources, mappings, model revisions, archive information, other panel summaries and limitations. The large inputs are intentional: no comparator loses full-panel or provenance fields. All have the same frozen ZIP available for optional source retrieval. Source question text remains outside this artifact, just as it does in the original saved Explorer.

The root operator must make this exact canonical payload accessible to **each** presenter in addition to its normal UI. The old complete JSON baseline is `paper/naacl2027/inspection_audit_20261002/json_baseline.html`; an additive published route is not a reason to alter the frozen baseline during observation. Loading the full JSON in a generic cell is valid information access. It is not evidence of specialized semantic visualization. Conversely, a dedicated visual field can be present while detailed source values require JSON export. These are separate observations.

ChainForge's setup/import is part of the comparator condition: record the actual pinned version, fixture digest and transformation. Cached frozen evidence is not a natural ChainForge inference run. Any custom adapter, parsing or code must be described, and no required field may be dropped merely because it is inconvenient to render.

## Questions and reference answers

1. Semantic label, typed value, full conditional candidate distribution; Noul probability of true.
2. Score only: expectation, modal stage, absolute gap, and unchanged continuous reference.
3. Canonical semantic alignment, each B-minus-A probability difference, label-change flag, per-physical-member token mapping and display order.
4. Individual, shared and union physical-call counts and exact member identities.
5. ZIP member, one-based line and SHA-256 for each condition and underlying physical call, plus model provenance and exact source-row identity/value recovery.
6. Full-panel counts, maximum label share, used labels, and Score min/max/population variance.

The independent reader uses archived `physical_member_indices` resolved against archived request indices, rather than trusting GUI membership fields. It recalculates distributions over all 200 original rows. Copied labels, identities and values compare exactly; recomputed arithmetic uses 1e-12 absolute/relative tolerance. Report display rounding explicitly instead of alleging data corruption. Presentation-study 35B rows do not carry `model_key`; their model is resolved from the known archive member/panel model metadata, and the answer key retains `model_key_in_row: null` rather than inventing an original-row value. Null compact `display_order` is an absent recorded field, not proof that the prompt was not reversed.

## How to report observations fairly

For each presenter/case/question record:

- Actual route/version and evidence location (screenshot, visible field, expansion, export or source retrieval).
- Whether the answer is natively presented with semantic labels.
- Whether the complete evidence remains reachable in the generic payload.
- Whether answering requires manual arithmetic, custom code or an external source reader.
- Correctness if actually verified; otherwise `not_verified_due_to_blocker` with the attempted route and concrete blocker.

These descriptors can co-occur and are **not ranked scores**. Do not report “32 tasks passed in the GUI” from an automated payload equality check or a few screenshots. A preserved payload hash verifies preservation, not that every GUI path was inspected. Equal functionality, absent advantages, and failed paths all remain in the report. No timing, action-count, human-success or overall winner metric is planned.

The run order is W01–W06 and the same questions for every presenter. Record deviations without changing the task selection, expected answers or frozen hashes. Keep later GUI observations in separate root-owned result files.

## Prior knowledge and limits

Authors/agents knew the implementation, outcome-selected featured examples, the prior source-only ChainForge review, and the earlier all-record functional audit (172,200 condition pairs, 31,000 saved conditions, 18 panels, zero reported discrepancies). This package reuses those data. The six cases add bounded actual-GUI observations; they are neither independent human validation nor new model tests. A custom-import limitation does not establish that every possible ChainForge setup lacks a capability. Supported conclusions are about this version, fixture, task set and observed paths only.
