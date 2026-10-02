# Local physical-record import v1

Open [the import page](./) from the served project website. A file or pasted JSONL is processed entirely in the browser. The route makes no data uploads, inference calls, analytics requests, or browser-storage writes; its content-security policy disables connections. Static HTML, JavaScript, and CSS load from the same site. A comparison download is a local JSON file. Refresh or **Clear data** removes the app's current data; the app does not control the browser's own memory management or downloaded files.

This route is separate from the published saved-evidence explorer. It computes candidate comparisons from supplied physical records. It neither verifies the data's authenticity nor evaluates a new model. Source identities, semantic mappings, completeness, references, and declared probability origins are assertions made by the file author.

## Format

UTF-8 JSONL: one JSON object per nonblank line, maximum 25 MiB and 20,000 records. A BOM and blank lines are accepted. Unknown fields, malformed rows, duplicate physical IDs or declared source locations, duplicate conditions, or incompatible conditions reject the **whole file**. No partial dataset is shown as a complete import. Successful imports collapse the warning list; errors expand it. Missing reference and latency also remain explicit in the comparison. UI percentages/deltas use at most four decimal places and typed values six significant digits; original records and downloaded JSON retain unrounded values.

Every record requires:

| Field | Meaning |
|---|---|
| `schema_version` | Integer `1`. |
| `kind` | Literal `physical`; one individual saved observation. |
| `model` | Stable model/runtime identity. Include a revision/precision in this identifier when needed to distinguish runs. |
| `item_id` | Item identity including dataset/split when needed. Same model/item is one comparison group. |
| `type` | `choice`, `noul`, or `score`. |
| `condition` | Unique condition within a model/item group. |
| `source_id` | Globally unique physical identity in this file; 1–256 ASCII characters from letters, numbers, `. _ : / # -`, starting with a letter or number. It must not be a newly invented alias for the same observation. |
| `key_schema` | Identifier for the shared semantic interpretation of candidate keys. |
| `candidate_keys` | 2–256 unique semantic strings; positions align with the numeric arrays below. Displayed tokens are not a substitute for semantic keys unless they have the same meaning in both conditions. |
| `candidate_count` | Integer exactly equal to the full `candidate_keys` length. |
| `distribution_scope` | Literal `full_candidate_set`. |

`model`, `item_id`, `condition`, `key_schema`, and candidate keys have 1–256 characters, no control characters, and no leading/trailing whitespace. Same-model/item conditions must have the same type, key schema, candidate set, and semantic Score mapping. Candidate order may differ: alignment uses keys, never array positions across conditions.

Provide **exactly one** numeric representation:

| Input | Required fields and interpretation |
|---|---|
| Logits | `logits`: finite numeric array; `temperature`: finite positive number. The importer computes stable softmax of the supplied candidate logits divided by temperature. Origin is `softmax_of_supplied_logits`. Do not include probability-only fields. |
| Probabilities | `probabilities`: numeric array in `[0,1]`, summing to 1 within `1e-8`; `probability_semantics`: `conditional_on_candidate_set`; `probability_origin`: `reported_probabilities` or `renormalized_candidate_scores`. Do not include temperature. Values are retained without renormalization. The declared origin remains visible and does not imply independent verification. |

“Full” refers to the intended declared candidate set, **not the model's full vocabulary**. A declared `top_k` scope, a length/count mismatch, or missing probability mass is rejected. A producer could falsely declare a truncated, renormalized vector complete; without the original candidate inventory the importer cannot discover such omitted candidates. Do not use this format to conceal that truncation. Candidate probabilities are not calibrated correctness probabilities.

Type-specific rules:

- **Choice:** label = highest candidate probability.
- **Noul:** keys must be the literal strings `false` and `true`; typed value = probability assigned to `true`.
- **Score:** required `score_values` finite numeric array aligned with candidate keys; typed value = probability-weighted expectation on the supplied numeric scale. The app does not assume equal spacing or replace a continuous reference with a rounded label.
- Exact argmax ties are disclosed and use the lexically first semantic key, independent of input order. This is a display convention, not evidence favoring that label.

Optional fields:

| Field | Meaning |
|---|---|
| `reference` | Exactly `{"kind":"label","value":"semantic-key"}`, or for Score `{"kind":"score","value":6.25}`. Supplied references must agree within a group. Missing reference stays unknown. A/B reference diagnostics require references on both records. |
| `recorded_latency_ms` | Finite nonnegative recorded measurement. Missing latency remains unknown, never zero. There is no financial-cost field or cost estimate in v1. |
| `provenance` | `file_id` string (up to 1,024 characters), positive integer `line_1based`, optional 64-character lowercase `file_sha256`. Declared duplicate file/line or hash/line locations are rejected even if assigned different source IDs. The app does not fetch the file or verify its hash against external bytes. |
| `note` | Plain text, up to 4,096 characters without control characters. Displayed as text, never HTML. |

No derived averages, ensemble recipes, repeated-member expansions, or inferred physical call counts are accepted in v1. The UI reports the number of **declared physical identities** among the selected individual records. This should not be interpreted as an independently audited inference-call count. If A and B select the same record, the union counts it once.

Minimal record:

```json
{"schema_version":1,"kind":"physical","model":"model@revision/runtime","item_id":"dataset:split:42","type":"choice","condition":"baseline","source_id":"run-1:42","key_schema":"answer-meaning-v1","candidate_keys":["accept","reject"],"candidate_count":2,"distribution_scope":"full_candidate_set","logits":[2,0],"temperature":1}
```

For a second condition, use the same model/item/semantic schema, a distinct condition and genuine source identity, and its actual numeric values. The app allows an individual record to be inspected when no second condition is present and explicitly marks that limitation.

## Demonstration and verification

[synthetic.mjs](synthetic.mjs) contains six hand-written physical records across Choice, Noul, and Score. The UI labels them synthetic; they are not model observations. The hand-computed test oracle checks probabilities `4/7, 2/7, 1/7`, Noul values `0.25/0.75`, and Score expectations `6.5/5.5`.

[archived-projection.jsonl](archived-projection.jsonl) is a separate compatibility fixture made from **three previously published physical conditions of one existing item**, not a new experiment. [Its manifest](archived-projection.manifest.json) records the source hashes and expected values. Selection takes the minimum SHA256 of compact ASCII JSON `[panel_id,item_id]` across all 3,600 eligible published model/item groups, before considering observed values. All physical conditions of the selected item are retained. Source question text is not redistributed. Original task licenses and attribution remain in the project's [NOTICE](https://github.com/UpHash-Network/mini-jev/blob/research/naacl2027-demo/NOTICE.md).

Rebuild and check from the repository root:

```bash
python3 docs/explorer/import/build_archived_projection.py
node --test tests/test_import_core.mjs
```

Tests check independent hand-computed examples, tuple-order invariance, invalid and duplicate inputs, unknown-reference behavior, safe data representation, and exact agreement of the archived projection with the unchanged published source. This is software validation; it does not establish human usability or empirical model gains. A separate browser review is required before site integration.
