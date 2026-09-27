# Saved evidence explorer

Open [the published explorer](https://uphash-network.github.io/mini-jev/explorer/), or serve `docs/` locally:

```sh
python3 -m http.server 8777 --bind 127.0.0.1 --directory docs
```

Open `http://127.0.0.1:8777/explorer/`. HTTPS or localhost is required for the panel SHA-256 checks. No build step, model download, API key, external JavaScript, or live inference is required.

## Inspect a comparison

1. Choose an illustrated observation, or select a study, model/runtime, task, and source item.
2. Pick two recorded conditions. Candidate probabilities share a semantic key and a 0–100% scale.
3. Compare the selected label, typed value, concentration, reference, and number of distinct physical calls. Score mode, expectation, and continuous reference are separate.
4. Expand the source details for ZIP member paths, one-based JSONL lines, mappings, hashes, and exact values. Original task/option text is not reconstructed.
5. Download the comparison JSON. It retains exact values and source definitions for selected derived results, physical members, and model metadata. The URL fragment retains the selected comparison for sharing.

The full panel frequencies remain independent of the item search. Featured examples follow documented deterministic selection rules; they are illustrations, not a representative performance sample. See [DATA.md](DATA.md).

## Check the static artifact

```sh
python3 -m unittest discover -s tests -p test_evidence_explorer.py -v
node tests/test_evidence_core.mjs
```

The Python tests compare exported records and aggregates with the frozen archive. The JavaScript checks validate every retained condition, semantic comparison arithmetic, shared-call accounting, export round trips, and rejection of corrupt or cross-item comparisons. These are software and evidence-integrity checks, not human usability results.

This interface was added on September 28, 2026, after the current manuscript snapshot. No source experiment, submitted arXiv package, or manuscript PDF was changed to add it.
