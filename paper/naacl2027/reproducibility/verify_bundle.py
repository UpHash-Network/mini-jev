#!/usr/bin/env python3
"""Verify the shipped file set and bytes before running any bundled code."""
import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parent
manifest = json.loads((root / "BUNDLE_MANIFEST.json").read_text())
errors = []
for record in manifest["files"]:
    f = root / record["path"]
    if not f.is_file() or f.is_symlink():
        errors.append("Missing file or unexpected symlink: " + record["path"])
    elif f.stat().st_size != record["bytes"] or hashlib.sha256(f.read_bytes()).hexdigest() != record["sha256"]:
        errors.append("File changed: " + record["path"])
print(json.dumps({"status": "pass" if not errors else "fail", "verified_files": len(manifest["files"]), "errors": errors}, indent=2))
raise SystemExit(bool(errors))
