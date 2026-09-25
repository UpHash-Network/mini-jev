#!/usr/bin/env python3
"""Reproduce frozen analyses in an isolated copy, with Python standard library only."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time

def sha(f):
    return hashlib.sha256(f.read_bytes()).hexdigest()

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", type=Path, required=True, help="New directory outside the bundle")
    a = p.parse_args()
    source = Path(__file__).resolve().parent
    output = a.output.resolve()
    if output == source or source in output.parents:
        raise ValueError("Output must be outside the immutable bundle")
    subprocess.run([sys.executable, str(source / "verify_bundle.py")], check=True)
    output.mkdir(parents=True, exist_ok=False)
    clone = output / "analysis-source"
    shutil.copytree(source, clone, ignore=shutil.ignore_patterns("__pycache__", ".build", "models", ".git", ".venv"))
    steps = []
    def run(name, args, actual, reference, selected_names=None):
        start = time.monotonic()
        log = output / (name + ".log")
        with log.open("w") as f:
            result = subprocess.run([sys.executable, *args], cwd=clone, stdout=f, stderr=subprocess.STDOUT)
        if result.returncode:
            raise RuntimeError(name + " failed; inspect " + str(log))
        comparisons = []
        for original in sorted(reference.iterdir()):
            if original.is_file() and original.suffix in {".json", ".jsonl", ".csv", ".md"} and (selected_names is None or original.name in selected_names):
                if not (actual / original.name).is_file():
                    raise RuntimeError(name + " missing derived output: " + original.name)
                comparisons.append({"file": original.name, "expected_sha256": sha(original), "actual_sha256": sha(actual / original.name), "byte_identical": original.read_bytes() == (actual / original.name).read_bytes()})
        if not comparisons or not all(row["byte_identical"] for row in comparisons):
            raise RuntimeError(name + " differs: " + json.dumps(comparisons))
        steps.append({"step": name, "seconds": time.monotonic()-start, "derived_files": comparisons})
    run("matched", ["paper/matched_study/analyze_study.py"], clone / "paper/matched_study", source / "paper/matched_study", {"SUMMARY.json", "REPORT.md", "item_latency.csv", "native_phases.csv", "parity.csv", "latency.csv", "external_metrics.csv"})
    robust = "paper/journal_robustness"
    run("robustness_native", [robust+"/analyze.py", "--predictions", robust+"/study_v1/results/predictions.jsonl", "--schedule", robust+"/study_v1/SCHEDULE.json", "--output", str(output/"robustness_native")], output/"robustness_native", source/robust/"study_v1/analysis")
    cross = robust + "/cross_model"
    run("robustness_cross", [cross+"/analyze.py", "--predictions", cross+"/study_v1/results", "--schedule", cross+"/study_v1/SCHEDULE.json", "--output", str(output/"robustness_cross")], output/"robustness_cross", source/cross/"study_v1/analysis")
    for model in ("qwen3.6-35b-a3b", "qwen2.5-0.5b", "qwen2.5-1.5b"):
        run("ensemble_"+model, ["-m", "paper.order_ensemble.analyze", "--study", "paper/order_ensemble/study_v1", "--model-key", model, "--output", str(output/model)], output/model, source/"paper/order_ensemble/study_v1/analysis"/model)
    result = {"status": "pass", "mode": "CPU reanalysis of existing observations; no models, network, or new inference", "python": sys.version, "measured_requests_reanalyzed": 26050, "not_independent_experimental_replication": True, "steps": steps}
    (output/"REANALYSIS_CHECKS.json").write_text(json.dumps(result, indent=2)+"\n")
    print(json.dumps({"status": "pass", "steps": len(steps), "byte_identical_derived_files": sum(len(s["derived_files"]) for s in steps)}, indent=2))

if __name__ == "__main__":
    main()
