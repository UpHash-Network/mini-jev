#!/usr/bin/env python3
"""Validate the pinned historical ZIP, then extract only into a new directory.

Python standard library only. This utility neither executes bundled code nor
changes the historical ZIP. Paths, duplicate members, links, inventory, CRC,
sizes, and every manifest hash are checked before extraction.
"""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import stat
import zipfile

EXPECTED_SHA256 = "a15e0699a54be15d56bd99ed8181429b71fdfc7ace756d6e065a75538786c053"


def extract(archive, destination):
    archive, destination = Path(archive), Path(destination)
    if destination.exists():
        raise FileExistsError("Destination must be a new directory")
    raw = archive.read_bytes()
    if hashlib.sha256(raw).hexdigest() != EXPECTED_SHA256:
        raise ValueError("Pinned ZIP SHA-256 differs")
    with zipfile.ZipFile(archive) as bundle:
        members = bundle.infolist()
        names = [entry.filename for entry in members]
        if len(names) != len(set(names)):
            raise ValueError("Duplicate ZIP member")
        for entry in members:
            path = PurePosixPath(entry.filename)
            mode = entry.external_attr >> 16
            if (path.is_absolute() or ".." in path.parts or "\\" in entry.filename
                    or not path.parts or path.parts[0] != "mini-jev"
                    or entry.is_dir() or stat.S_ISLNK(mode)
                    or entry.flag_bits & 1):
                raise ValueError("Unsafe or unexpected ZIP member")
        if bundle.testzip() is not None:
            raise ValueError("ZIP CRC failure")
        manifest = json.loads(bundle.read("mini-jev/BUNDLE_MANIFEST.json"))
        expected = {"mini-jev/" + row["path"] for row in manifest["files"]}
        expected.add("mini-jev/BUNDLE_MANIFEST.json")
        if len(expected) != len(manifest["files"]) + 1 or set(names) != expected:
            raise ValueError("ZIP manifest inventory differs")
        for row in manifest["files"]:
            data = bundle.read("mini-jev/" + row["path"])
            if len(data) != row["bytes"] or hashlib.sha256(data).hexdigest() != row["sha256"]:
                raise ValueError("ZIP manifest bytes or hash differ")
        destination.mkdir(parents=True, exist_ok=False)
        for entry in members:
            target = destination.joinpath(*PurePosixPath(entry.filename).parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("xb") as stream:
                stream.write(bundle.read(entry))
        return {"status": "pass", "archive_sha256": EXPECTED_SHA256,
                "archive_bytes": len(raw), "archive_members": len(members),
                "manifest_files_verified": len(manifest["files"]),
                "extracted_logical_bytes": sum(entry.file_size for entry in members),
                "safe_paths": True, "crc": "pass", "exact_inventory": "pass",
                "new_destination_only": True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(extract(args.archive, args.output), indent=2))


if __name__ == "__main__":
    main()
