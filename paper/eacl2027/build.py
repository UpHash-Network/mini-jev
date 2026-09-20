#!/usr/bin/env python3
"""Build the EACL review draft with the unmodified official ACL style."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess


def main() -> None:
    here = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tectonic", default="tectonic", help="Tectonic executable (tested: 0.17.0)")
    parser.add_argument("--build-dir", type=Path, default=here.parents[1] / ".build" / "eacl2027-paper")
    parser.add_argument("--output", type=Path, default=here / "EACL2027_Mini_Jev_Draft.pdf")
    args = parser.parse_args()
    for record in json.loads((here / "STYLE_PROVENANCE.json").read_text())["files"]:
        observed = hashlib.sha256((here / record["file"]).read_bytes()).hexdigest()
        if observed != record["sha256"]:
            raise SystemExit("Official ACL style was changed: " + record["file"])
    executable = shutil.which(args.tectonic)
    if executable is None:
        raise SystemExit("Install Tectonic 0.17.0, or provide --tectonic /path/to/tectonic.")
    build_dir = args.build_dir.resolve()
    build_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [executable, "--untrusted", "--keep-logs", "--keep-intermediates",
         "--outdir", str(build_dir), "main.tex"],
        cwd=here, check=True,
    )
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(build_dir / "main.pdf", output)
    print(json.dumps({
        "file": output.name,
        "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
        "status": "review_draft_not_submitted",
        "note": "Compilation is not a submission-readiness or scientific-quality check.",
    }, indent=2))


if __name__ == "__main__":
    main()
