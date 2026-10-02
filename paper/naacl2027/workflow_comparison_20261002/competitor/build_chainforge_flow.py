#!/usr/bin/env python3
"""Lossless frozen-evidence import into unmodified ChainForge 0.3.7.6.

This is a format adapter, not a model provider. It never executes an LLM,
modifies ChainForge, or reads task answer keys. Complete input strings are
retained verbatim; the compact view exposes fields already present in them.
"""
import argparse
import hashlib
import json
import zipfile
from pathlib import Path


def digest(data):
    return hashlib.sha256(data).hexdigest()


def response(uid, text, variables, label, scores=None):
    row = {"uid": uid, "prompt": "Frozen saved evidence; no new inference",
           "vars": variables, "metavars": {}, "llm": label,
           "responses": [text]}
    if scores is not None:
        row["eval_res"] = {"items": [scores], "dtype": "KeyValue_Numeric"}
    return row


def processor(node_id, title, x, y):
    return {"id": node_id, "type": "processor", "position": {"x": x, "y": y},
            "data": {"title": title, "language": "javascript", "sandbox": True,
                     "code": "// Imported cache: no model execution.\nfunction process(response) { return response.text; }",
                     "refresh": False}}


def inspector(node_id, title, x, y):
    return {"id": node_id, "type": "inspect", "position": {"x": x, "y": y},
            "data": {"title": title, "viewFormat": "table", "input": "frozen-import-v1", "refresh": True}}


def build(tasks_file, output_dir):
    task_bytes = tasks_file.read_bytes()
    tasks = json.loads(task_bytes)
    complete, compact, hashes = [], [], []
    for task in tasks["tasks"]:
        task_id, text = task["id"], task["evidence_json"]
        text_hash = digest(text.encode("utf-8"))
        assert text_hash == task["evidence_sha256"], task_id
        evidence = json.loads(text)
        comparison = evidence["comparison_export"]
        selection = task["selection"]
        variables = {"task_id": task_id, "item_id": selection["item"],
                     "dataset": selection["dataset"], "study": selection["study"],
                     "model": selection["model"]}
        complete.append(response(task_id + ":complete", text, variables,
                                 "Complete frozen evidence (imported)"))
        for side in ("a", "b"):
            condition = comparison["conditions"][side]
            summary = {
                "import_notice": "These values were supplied by the frozen-evidence format adapter, not generated or independently computed by ChainForge.",
                "task_id": task_id, "side": side, "selection": selection,
                "canonical_keys": comparison["canonical_keys"],
                "score_values": comparison["score_values"],
                "condition": condition,
                "candidate_comparison": comparison["candidate_comparison"],
                "reference": comparison["reference"],
                "physical_members": comparison["physical_members"],
                "shared_physical_calls": comparison["shared_physical_calls"],
                "unique_physical_calls": comparison["unique_physical_calls"],
                "sources": comparison["sources"], "mappings": comparison["mappings"],
                "archive": comparison["archive"], "model": comparison["model"],
                "complete_evidence_sha256": text_hash,
            }
            scores = {"P(" + key + ")": value for key, value in
                      zip(comparison["canonical_keys"], condition["probabilities"])}
            scores.update({"recorded_calls": condition["calls"],
                           "recorded_input_tokens": condition["input_tokens"],
                           "recorded_latency_ms": condition["latency_ms"]})
            compact.append(response(task_id + ":" + side,
                                    json.dumps(summary, ensure_ascii=False, indent=2),
                                    {**variables, "side": side, "condition": condition["id"],
                                     "selected_label": condition["label"],
                                     "typed_value": str(condition["value"])},
                                    side.upper() + " (frozen condition)", scores))
        hashes.append({"task_id": task_id, "evidence_sha256": text_hash,
                       "bytes_utf8": len(text.encode("utf-8"))})
    nodes = [processor("frozen_conditions", "Imported condition rows; no inference", -450, 0),
             inspector("condition_inspector", "Conditions: probabilities, metadata, export", 0, 0),
             processor("frozen_complete", "Complete evidence strings; no inference", -450, 700),
             inspector("complete_inspector", "Complete evidence: all panel and source context", 0, 700)]
    edges = [{"id": source + "-" + dest, "source": source, "target": dest,
              "sourceHandle": "output", "targetHandle": "input"}
             for source, dest in [("frozen_conditions", "condition_inspector"),
                                  ("frozen_complete", "complete_inspector")]]
    flow = {"flow": {"nodes": nodes, "edges": edges,
                     "viewport": {"x": 200, "y": 110, "zoom": 0.8}},
            "cache": {"frozen_conditions.json": compact,
                      "frozen_complete.json": complete, "__s": []}}
    output_dir.mkdir(parents=True, exist_ok=True)
    output = output_dir / "logittrail-frozen-evidence.cforge"
    output.write_text(json.dumps(flow, ensure_ascii=False, indent=2) + "\n")
    bundle = output.with_suffix(".cfzip")
    with zipfile.ZipFile(bundle, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        entry = zipfile.ZipInfo("flow.json", (2026, 10, 2, 0, 0, 0))
        entry.compress_type = zipfile.ZIP_DEFLATED
        archive.writestr(entry, output.read_bytes())
    # JSON serialization roundtrip must preserve all complete input strings.
    reloaded = json.loads(output.read_text())
    assert [row["responses"][0] for row in reloaded["cache"]["frozen_complete.json"]] == [t["evidence_json"] for t in tasks["tasks"]]
    manifest = {"schema_version": 1, "tasks_sha256": digest(task_bytes),
                "protocol_sha256": tasks["protocol_sha256"],
                "flow_sha256": digest(output.read_bytes()),
                "cfzip_sha256": digest(bundle.read_bytes()),
                "flow_bytes": output.stat().st_size,
                "cfzip_bytes": bundle.stat().st_size,
                "full_evidence_rows": len(complete), "condition_rows": len(compact),
                "new_inference_calls": 0, "complete_strings_roundtrip_equal": True,
                "evidence": hashes,
                "adapter_boundary": "Complete evidence strings preserved verbatim. Compact fields and named numeric scores are deterministic extraction from supplied comparison_export, not ChainForge-computed task answers. No expected_answers read.",
                "native_features_to_check": ["Inspect Table", "Inspect List", "Inspect Grid", "group by", "column pivot", "search", "Export data (xlsx)"]}
    (output_dir / "IMPORT_MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tasks", type=Path)
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).parent)
    args = parser.parse_args()
    build(args.tasks, args.output_dir)
