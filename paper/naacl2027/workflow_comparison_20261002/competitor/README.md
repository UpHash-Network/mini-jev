# ChainForge comparison fixture (2 October 2026)

This is a **format adapter for frozen data into the unmodified ChainForge UI**,
not an implementation of LogitTrail inside ChainForge and not a comparison of
new model predictions. The same complete evidence strings supplied to the
other presenters are included here without truncation.

## Version actually served

- Official repository HEAD inspected: `641fd577442daf43b45064e7aae86c983f03f85d`.
- Published PyPI wheel verified: **0.3.7.6**, uploaded
  **2026-10-01T00:47:55.674312Z**. Earlier source-only reviews did not establish
  package publication; this check does.
- Served application: the unmodified **published wheel**, including its compiled
  React UI and Flask backend. The wheel SHA-256 matches PyPI's digest.
- The main compiled bundle's source map contains **139 project source files**
  matching the pinned checkout exactly, including `App.tsx`, `InspectorNode.tsx`,
  and backend conversion/provider code. This is source-map comparison, not an
  independent reproducible-build certificate for all dependencies.
- The existing isolated Python 3.12 dependency environment was reused while
  the 0.3.7.6 wheel was selected through `PYTHONPATH`. This is **not** a clean
  installation study. Optional RAG dependencies are disabled. No model is loaded.

Machine-readable wheel URL, digests, source checks and limitations are in
[`VERSION_PROVENANCE.json`](VERSION_PROVENANCE.json).

Primary sources:
[official source](https://github.com/ianarawjo/ChainForge/tree/641fd577442daf43b45064e7aae86c983f03f85d),
[PyPI release](https://pypi.org/project/chainforge/0.3.7.6/),
[PyPI metadata](https://pypi.org/pypi/chainforge/0.3.7.6/json).

## Reproduce the import

From the repository root:

```sh
python3 paper/naacl2027/workflow_comparison_20261002/competitor/build_chainforge_flow.py \
  paper/naacl2027/workflow_comparison_20261002/tasks.json
```

For a separate local installation of the pinned package:

```sh
python3 -m venv .venv-chainforge-comparison
.venv-chainforge-comparison/bin/python -m pip install chainforge==0.3.7.6
.venv-chainforge-comparison/bin/chainforge serve --host 127.0.0.1 --port 18881
```

The current study server uses a separate custom flow directory under the
project's ignored `work/chainforge-gui-20261002/flows` directory. Its reusable
launcher is `work/chainforge-gui-20261002/start_gui.py`; it passes no provider API
credentials. Launch only one server on that port at a time.

Open `http://127.0.0.1:18881` in a supported desktop browser. Choose the native
**Import** action and select `logittrail-frozen-evidence.cfzip` (or its equivalent
`.cforge`). No Run, Generate, provider or model action is required. The fixture
contains:

1. **Conditions: probabilities, metadata, export** — 12 response rows, one A and
   one B per task. Native named numerical scores expose every candidate
   probability plus recorded call count, input-token count and latency. Native
   variables expose task, source item, dataset, study, model, condition, selected
   label and typed value. Compact response text preserves the complete selected
   condition, candidate comparison, reference, physical members, shared-call
   counts, archive provenance and source mappings.
2. **Complete evidence: all panel and source context** — six response rows whose
   text is the exact original `evidence_json` string, including the full
   200-item panel and index. Their UTF-8 SHA-256 hashes are checked by the builder.

The imported cache belongs to standard JavaScript processor nodes containing
an identity function. They explicitly say **no inference**. These nodes are
only cache holders; the study does not execute them. Genuine Inspect nodes
read their cached responses through ChainForge's supported flow-import path.

The Table, List and Grid tabs, grouping, column selection, search and export
are native ChainForge UI features. The browser execution report records which
were actually exercised; source support alone is not a completed GUI result.

## Information and interpretation boundaries

The adapter uses `task.evidence_json`, identifiers and selection metadata. It
does **not** read `expected_answers`. It preserves the complete original input
and also extracts compact fields for a useful competing interface, rather
than restricting the baseline to a large unstructured blob.

The supplied `comparison_export` already contains semantic candidate alignment,
comparison deltas, physical members and shared/unique-call counts. Exposing
these fields in ChainForge does **not** show that ChainForge computed them from
raw runs. All other presenters receive those same precomputed fields. Named
numeric scores here are imported candidate probabilities and recorded metadata,
not new judge scores or confidence of correctness.

Compact response text is 3,951–15,702 characters per cell, below Excel's 32,767
character limit. Complete input strings are approximately 0.57–3.33 MB each:
**use the top-level flow Export (`.cforge`) for their lossless round trip**.
The per-Inspector **Export data** action exports a spreadsheet; it cannot be
assumed to preserve multi-megabyte values in individual cells. Preserve and
verify the top-level flow export separately from the compact spreadsheet.

Supported import shape, confirmed from the pinned source:

```json
{
  "flow": {"nodes": [], "edges": [], "viewport": {}},
  "cache": {
    "source_node_id.json": [{
      "uid": "stable-row-id",
      "prompt": "Frozen saved evidence; no new inference",
      "vars": {"task_id": "W01"},
      "metavars": {},
      "llm": "Imported evidence",
      "responses": ["exact evidence string"]
    }],
    "__s": []
  }
}
```

A `.cfzip` contains this JSON as `flow.json`. No media are needed. On export,
ChainForge may intern response strings in `cache.__s`; comparisons must resolve
those documented string references before checking the six text hashes.

Relevant pinned implementation:
[flow importer](https://github.com/ianarawjo/ChainForge/blob/641fd577442daf43b45064e7aae86c983f03f85d/chainforge/react-server/src/App.tsx#L1178-L1320),
[Inspect node](https://github.com/ianarawjo/ChainForge/blob/641fd577442daf43b45064e7aae86c983f03f85d/chainforge/react-server/src/InspectorNode.tsx),
[cache import and response retrieval](https://github.com/ianarawjo/ChainForge/blob/641fd577442daf43b45064e7aae86c983f03f85d/chainforge/react-server/src/backend/backend.ts#L1952-L2078).

No task timings from an AI operator establish human efficiency, and no inspected
configuration establishes a general absence of a feature from ChainForge.
