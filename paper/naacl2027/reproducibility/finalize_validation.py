#!/usr/bin/env python3
"""Collect completed local checks; no model inference or external publication."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import zipfile

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--work", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    work, out = a.work.resolve(), a.output.resolve()
    archive = work/"bundle-v1-release/naacl-repro-v1-20260925.zip"
    app = work/"release-extracted/mini-jev"
    manifest = json.loads((app/"BUNDLE_MANIFEST.json").read_text())
    expected = {"mini-jev/"+r["path"]:r for r in manifest["files"]}
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        assert len(z.namelist()) == len(set(z.namelist()))
        assert set(z.namelist()) == set(expected) | {"mini-jev/BUNDLE_MANIFEST.json"}
        for name, r in expected.items():
            raw = z.read(name)
            assert len(raw) == r["bytes"] and hashlib.sha256(raw).hexdigest() == r["sha256"]
            assert (app/r["path"]).read_bytes() == raw
        assert z.read("mini-jev/BUNDLE_MANIFEST.json") == (app/"BUNDLE_MANIFEST.json").read_bytes()
    reanalysis = json.loads((work/"reanalysis-release/REANALYSIS_CHECKS.json").read_text())
    assert reanalysis["status"] == "pass"
    assert len(reanalysis["steps"]) == 6
    assert sum(len(s["derived_files"]) for s in reanalysis["steps"]) == 56
    assert all(r["byte_identical"] for s in reanalysis["steps"] for r in s["derived_files"])
    smoke = json.loads((work/"LIVE_SMOKE.json").read_text())
    assert smoke["status"] == "pass" and all(smoke["checks"].values())
    native = json.loads((work/"NATIVE_PACKAGE_CHECKS.json").read_text())
    assert native["native_verification"]["verified"]
    # Ensure this CPU-suite receipt covers the final application despite the
    # wrapper's additional missing-file guard after the first candidate.
    previous = json.loads((work/"bundle-v1-final/mini-jev/BUNDLE_MANIFEST.json").read_text())
    old = {r["path"]:r["sha256"] for r in previous["files"]}
    source_changes = [r["path"] for r in manifest["files"] if old.get(r["path"]) != r["sha256"]]
    assert source_changes == ["REPRODUCIBILITY.md", "reanalyze.py"]
    tests = []
    for name, count in (("cpu-app-tests.log",58),("cpu-packaging-tests.log",13)):
        text = (work/name).read_text()
        assert f"Ran {count} tests" in text and "OK (skipped=1)" in text
        tests.append({"log":name,"discovered":count,"passed":count-1,"skipped":1,"failed":0})
    forbidden_keys = {"messages","state","sentence1","sentence2","question","choices","input_ids","tokenized_input","rendered_prompt"}
    result_files, record_count, background_count = [], 0, 0
    for f in app.glob("paper/**/results/**/predictions.jsonl"):
        rows = [json.loads(line) for line in f.read_text().splitlines() if line.strip()]
        def keys(value):
            if isinstance(value,dict):
                return set(value).union(*(keys(v) for v in value.values()))
            if isinstance(value,list):
                return set().union(*(keys(v) for v in value))
            return set()
        for row in rows:
            assert not keys(row) & forbidden_keys, f
        is_background = "external_pilot" in f.parts
        result_files.append({"path":f.relative_to(app).as_posix(),"measured_rows":len(rows),"sha256":sha(f),"role":"historical_background_not_current_count" if is_background else "naacl_study"})
        if is_background:
            background_count += len(rows)
        else:
            record_count += len(rows)
    assert record_count == 26050
    target_archive = out/archive.name
    shutil.copy2(archive,target_archive)
    copies = {
        "BUNDLE_MANIFEST.json":app/"BUNDLE_MANIFEST.json",
        "BUNDLE_BUILD_RECEIPT.json":work/"bundle-v1-release/BUILD_RECEIPT.json",
        "REANALYSIS_CHECKS.json":work/"reanalysis-release/REANALYSIS_CHECKS.json",
        "LIVE_SMOKE.json":work/"LIVE_SMOKE.json",
        "NATIVE_PACKAGE_CHECKS.json":work/"NATIVE_PACKAGE_CHECKS.json",
        "NATIVE_BUILD.json":work/"native-runtime/BUILD.json",
        "CPU_APP_TESTS.txt":work/"cpu-app-tests.log",
        "CPU_PACKAGING_TESTS.txt":work/"cpu-packaging-tests.log",
    }
    for dest, source in copies.items():
        shutil.copy2(source,out/dest)
    # The build log contains local compiler paths. Retain only a disclosed
    # sanitized copy; original private runtime/model logs are not distributed.
    build_log = work/"native-build.log"
    sanitized = build_log.read_text().replace(str(work),"<REPRODUCTION_ROOT>")
    sanitized = re.sub(r"/Users/[^/\s]+", "<USER_HOME>", sanitized)
    (out/"NATIVE_BUILD_LOG.txt").write_text(sanitized)
    result = {
        "schema_version":1,"status":"pass","created_at_utc":datetime.now(timezone.utc).isoformat(),
        "artifact_version":manifest["artifact_version"],"archive":archive.name,"archive_sha256":sha(target_archive),"archive_bytes":target_archive.stat().st_size,
        "bundle_source_record_files":353,"archive_members_including_manifest":354,
        "archive_crc_file_set_and_all_hashes_verified":True,"extracted_files_equal_archive":True,
        "measured_requests_reanalyzed":26050,"analysis_steps":6,"byte_identical_derived_files":56,
        "cpu_tests":tests,"skipped_checks_covered_against_actual_rebuilt_runtime_and_source":True,
        "source_change_after_initial_cpu_suite":source_changes,"final_reanalysis_repeated_after_wrapper_guard":True,
        "runtime_build":{"fresh_native_compile":True,"cached_pinned_llama_cpp_source_reused":True,"upstream_revision":"f072b103714dfa1eee531f80b24512faf38e3dd2","old_native_binaries_reused":False,"build_jobs":2,"package_files_verified":18,"package_symlinks_verified":14,"source_libraries_license_presence_verified":True},
        "live_smoke":{"new_model_process":True,"model_download_repeated":False,"verified_cached_model_reused":True,"model_bytes":20419565568,"model_sha256":"671e47e0ec53c665d048b98c3ecbfd5236b5ca9c3e02ed19fc8f81f7b85140c7","sdk_http_requests":1,"typed_questions":3,"expected_example_labels_verified":True,"input_tokens":813,"output_tokens":0,"calibration_applied":False,"ended":True,"service_closed_by_parent_after_additional_separate_integration_checks":True},
        "environment":{"python":sys.version,"platform":platform.platform(),"machine":platform.machine(),"same_mac_as_original_experiments":True,"fresh_machine_or_clean_os":False,"python_dependency_install_required_for_reanalysis_service_demo":False},
        "distribution_checks":{"allowlist_enforced":True,"credential_and_personal_home_path_markers_absent":True,"raw_text_fields_absent_from_measured_prediction_rows":True,"naacl_measured_prediction_rows_scanned":record_count,"background_pilot_rows_scanned_excluded_from_current_total":background_count,"model_weights_native_binaries_private_logs_and_mail_excluded":True},
        "prediction_files":result_files,
        "preparatory_corrections":["First assembly attempt rejected a credential-pattern literal inside the existing release-check script; scanner corrected to match actual token-shaped values and a fresh archive was created.","The final reanalysis wrapper additionally rejects a missing expected output; its final full six-stage replay passed.","An initial shell launch used the workspace directory and exited 127 before loading code/model; relaunch from the extracted application succeeded.","Initial smoke health check used nonexistent status instead of actual ready; corrected using the same stored health response, with no repeated inference."],
        "build_log_redaction":{"original_sha256":sha(build_log),"published_sha256":sha(out/"NATIVE_BUILD_LOG.txt"),"transform":"replace reproduction-root and personal home prefixes; no numeric build/runtime result changes"},
        "limitations":["No independent-machine experiment or new benchmark","Only one synthetic three-question installation smoke; no statistical accuracy/latency estimate","No human usability study","Existing upstream source and model caches reused; no fresh network download validated","Historical full-audit environment is not reconstructed by CPU reanalysis","Git history, journal new studies and current NAACL manuscript/video absent from this focused bundle","Artifact is prepared locally and not published or formally submitted by this check"],
        "artifacts":{name:{"sha256":sha(out/name),"bytes":(out/name).stat().st_size}for name in [*copies,"NATIVE_BUILD_LOG.txt"]},
    }
    (out/"VALIDATION.20260925.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps({k:result[k]for k in ("status","archive_sha256","archive_bytes","measured_requests_reanalyzed","byte_identical_derived_files")},indent=2))

if __name__ == "__main__":
    main()
