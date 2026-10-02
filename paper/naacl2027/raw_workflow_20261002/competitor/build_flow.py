#!/usr/bin/env python3
"""Import raw input fields and executable code, with no cached result answers."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile


def sha(data):
    return hashlib.sha256(data).hexdigest()


def build(cases_path, processor_path, fixture_path, intermediate_path):
    cases = json.loads(cases_path.read_text())
    fields = []
    provenance = []
    for case in cases:
        # Expected status/oracle answers are intentionally not imported.
        raw = case["input"]
        text = json.dumps(raw, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
        fields.append({"text": text, "uid": "raw-" + case["id"],
                       "prompt": "Saved raw records; no new inference",
                       "fill_history": {"case_id": case["id"]},
                       "metavars": {}, "llm": "Recorded raw input"})
        provenance.append({"case_id": case["id"], "raw_text_sha256": sha(text.encode()),
                           "raw_text_bytes": len(text.encode())})
    code = processor_path.read_text()
    nodes = [
        {"id": "raw_input", "type": "processor", "position": {"x": 0, "y": 0},
         "data": {"title": "Imported raw inputs; no computed outputs", "language": "javascript",
                  "sandbox": True, "code": "function process(response) { return response.text; }",
                  "fields": fields, "refresh": False}},
        {"id": "compute_raw", "type": "processor", "position": {"x": 460, "y": 0},
         "data": {"title": "Compute diagnostics from raw records", "language": "javascript",
                  "sandbox": True, "code": code, "refresh": False}},
        {"id": "result_inspect", "type": "inspect", "position": {"x": 930, "y": 0},
         "data": {"title": "New native Processor results", "viewFormat": "table", "refresh": False}},
    ]
    edges = [
        {"id": "raw-to-compute", "source": "raw_input", "sourceHandle": "output",
         "target": "compute_raw", "targetHandle": "responseBatch"},
        {"id": "compute-to-inspect", "source": "compute_raw", "sourceHandle": "output",
         "target": "result_inspect", "targetHandle": "input"},
    ]
    fixture = {"flow": {"nodes": nodes, "edges": edges,
                         "viewport": {"x": 50, "y": 150, "zoom": 0.8}},
               "cache": {"__s": []}}
    encoded = (json.dumps(fixture, ensure_ascii=False, indent=2) + "\n").encode()
    intermediate_path.parent.mkdir(parents=True, exist_ok=True)
    intermediate_path.write_bytes(encoded)
    fixture_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(fixture_path, "w") as z:
        entry = zipfile.ZipInfo("flow.json", (2026, 10, 2, 0, 0, 0))
        entry.compress_type = zipfile.ZIP_DEFLATED
        z.writestr(entry, encoded)
    # Source fields must parse to the supplied inputs exactly; no expected keys included.
    assert [json.loads(f["text"]) for f in fields] == [c["input"] for c in cases]
    assert fixture["cache"] == {"__s": []}
    assert "fields" not in nodes[1]["data"]
    record = {"schema_version": 1, "case_count": len(cases),
              "cases_sha256": sha(cases_path.read_bytes()),
              "processor_sha256": sha(processor_path.read_bytes()),
              "fixture_sha256": sha(fixture_path.read_bytes()),
              "flow_json_sha256": sha(encoded), "fixture_bytes": fixture_path.stat().st_size,
              "flow_json_bytes": len(encoded), "input_fields": provenance,
              "preseeded_output_cache": False, "preseeded_output_fields": False,
              "cache_keys": ["__s"], "raw_inputs_roundtrip_exact": True,
              "transformation": "JSON serialization of case.input only; case identifier metadata. No oracle answers, expected_status, derived diagnostics or output cache are imported.",
              "execution_path": "Native JavaScript Processor Run; process(response) receives raw text through data.fields via responseBatch, then writes compute_raw.json. Code is supplied by the experiment, not a built-in domain-specific diagnostic."}
    fixture_path.with_suffix(".manifest.json").write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps({k: v for k, v in record.items() if k != "input_fields"}, indent=2))


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--cases", type=Path, required=True)
    p.add_argument("--processor", type=Path, required=True)
    p.add_argument("--fixture", type=Path, required=True)
    p.add_argument("--intermediate", type=Path, required=True)
    a = p.parse_args()
    build(a.cases, a.processor, a.fixture, a.intermediate)
