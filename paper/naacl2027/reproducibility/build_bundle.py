#!/usr/bin/env python3
"""Build a deterministic, allowlisted source/record bundle; never run inference."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import zipfile

VERSION = "naacl-repro-v1-20260925"
SOURCE_DIRS = {"service", "demo", "native", "acceptance", "acceptance-v2", "data", "tests", "examples", "test_fixtures", "scripts"}
PAPER_DIRS = {"matched_study", "matched_native", "external_expanded", "external_pilot"}
ALLOWED_SUFFIXES = {".py", ".sh", ".cpp", ".hpp", ".h", ".md", ".txt", ".json", ".jsonl", ".csv", ".yaml", ".yml", ".cff", ".html", ".css", ".js", ".svg", ".png", ".pdf"}

def digest(raw):
    return hashlib.sha256(raw).hexdigest()

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--application", type=Path, required=True)
    p.add_argument("--research", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    application, research, output = a.application.resolve(), a.research.resolve(), a.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    stage = output / "mini-jev"
    stage.mkdir()
    selected = {}
    tracked = subprocess.check_output(["git", "ls-files", "-z"], cwd=application).decode().split("\0")
    for rel in filter(None, tracked):
        parts = Path(rel).parts
        if len(parts) == 1 or parts[0] in SOURCE_DIRS or (parts[0] == "paper" and len(parts) > 1 and parts[1] in PAPER_DIRS):
            selected[rel] = (application / rel, "application_checkout")
    for study in ("journal_robustness", "order_ensemble"):
        for f in sorted((research / "paper" / study).rglob("*")):
            if f.is_file() and "__pycache__" not in f.parts and f.suffix in ALLOWED_SUFFIXES:
                selected[f.relative_to(research).as_posix()] = (f, "frozen_research_checkout")
    here = Path(__file__).resolve().parent
    for name in ("REPRODUCIBILITY.md", "reanalyze.py", "verify_bundle.py"):
        selected[name] = (here / name, "reproduction_wrapper")
    records = []
    for rel, (source, origin) in sorted(selected.items()):
        if source.is_symlink():
            raise ValueError("No source symlinks allowed: " + rel)
        raw = source.read_bytes()
        if source.suffix not in {".pdf", ".png"}:
            text = raw.decode("utf-8")
            for marker in ("/Users/", "BEGIN PRIVATE KEY", "BEGIN OPENSSH PRIVATE KEY", "profile/activate?token="):
                if marker in text:
                    raise ValueError("Disallowed personal-path/credential marker in " + rel + ": " + marker)
            if re.search(r"(?:github_pat_|ghp_|ya29\.)[A-Za-z0-9_-]{25,}", text):
                raise ValueError("Credential-like value in " + rel)
        dest = stage / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(raw)
        executable = source.stat().st_mode & 0o111 != 0
        dest.chmod(0o755 if executable else 0o644)
        records.append({"path": rel, "sha256": digest(raw), "bytes": len(raw), "executable": executable, "origin": origin})
    manifest = {
        "schema_version": 1, "artifact_version": VERSION,
        "purpose": "Source/demo installation and CPU reanalysis of the 26050 recorded NAACL study requests",
        "not_submitted_or_published": True,
        "application_base_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=application, text=True).strip(),
        "research_base_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=research, text=True).strip(),
        "file_hashes_are_authoritative": True,
        "measured_requests": {"matched": 4050, "presentation_robustness": 7600, "order_ensemble": 14400, "total": 26050},
        "excluded": ["journal equal_call_v1 and score_controls_v1 new studies", "raw external source text and token sequences", "model weights", "native binaries and shared libraries", "private model execution logs", "emails and account data", "Git history", "PDF manuscripts and video for the current NAACL submission"],
        "historical_paths_note": "The word private in acceptance/private denotes already-public project-authored regression data; it does not denote user records.",
        "historical_freezes": "Preserved verbatim. Rebuilt binaries and new environments require new receipts; this archive does not rebind old freezes to new code or claim independent replication.",
        "files": records,
    }
    manifest_raw = (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode()
    (stage / "BUNDLE_MANIFEST.json").write_bytes(manifest_raw)
    archive_path = output / (VERSION + ".zip")
    with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for f in sorted(stage.rglob("*")):
            if f.is_file():
                entry = zipfile.ZipInfo("mini-jev/" + f.relative_to(stage).as_posix(), (2026, 9, 25, 0, 0, 0))
                entry.compress_type = zipfile.ZIP_DEFLATED
                entry.create_system = 3
                entry.external_attr = (0o100755 if f.stat().st_mode & 0o111 else 0o100644) << 16
                z.writestr(entry, f.read_bytes())
    receipt = {"artifact_version": VERSION, "archive": archive_path.name, "archive_sha256": digest(archive_path.read_bytes()), "archive_bytes": archive_path.stat().st_size, "manifest_sha256": digest(manifest_raw), "source_and_record_files": len(records), "uncompressed_bytes": sum(r["bytes"] for r in records), "status": "assembled_verification_pending"}
    (output / "BUILD_RECEIPT.json").write_text(json.dumps(receipt, indent=2)+"\n")
    print(json.dumps(receipt, indent=2))

if __name__ == "__main__":
    main()
