#!/usr/bin/env python3
"""Fetch one pinned GGUF artifact; publish only after full size/SHA verification."""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import time
from urllib.request import Request, urlopen

PIN = {
    "repo_id": "ggml-org/Qwen3.6-35B-A3B-GGUF",
    "revision": "baec3ebee244827cda0f4557eafa8b28f7545fa6",
    "filename": "Qwen3.6-35B-A3B-Q4_K_M.gguf",
    "bytes": 20419565568,
    "sha256": "671e47e0ec53c665d048b98c3ecbfd5236b5ca9c3e02ed19fc8f81f7b85140c7",
}
CHUNK = 4 * 1024 * 1024


def metadata():
    value = json.loads(Path(__file__).with_name("native_model.json").read_text())
    if any(value.get(k) != v for k, v in PIN.items()):
        raise ValueError("native_model.json does not match this downloader's pinned artifact")
    return value


def verify(path: Path, pin=PIN):
    if not path.is_file() or path.is_symlink():
        raise ValueError(f"expected a regular nonsymlink file: {path}")
    before = path.stat()
    if before.st_size != pin["bytes"]:
        raise ValueError(f"size mismatch: {before.st_size} bytes, expected {pin['bytes']}")
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(CHUNK), b""):
            digest.update(chunk)
    after = path.stat()
    if (before.st_ino, before.st_size, before.st_mtime_ns) != (after.st_ino, after.st_size, after.st_mtime_ns):
        raise ValueError("file changed during verification")
    if digest.hexdigest() != pin["sha256"]:
        raise ValueError("SHA-256 mismatch; file was not accepted")
    return digest.hexdigest()


@contextlib.contextmanager
def lock_for(output: Path):
    lock = output.with_name(output.name + ".download.lock")
    try:
        fd = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        raise ValueError(f"download lock exists: {lock}; if its process has ended, remove that lock and retry") from None
    try:
        with os.fdopen(fd, "w") as stream:
            stream.write(f"pid={os.getpid()}\n")
        yield
    finally:
        lock.unlink(missing_ok=True)


def download_partial(partial: Path, pin=PIN, opener=urlopen):
    if partial.is_symlink():
        raise ValueError("partial download must not be a symlink")
    offset = partial.stat().st_size if partial.exists() else 0
    if offset > pin["bytes"]:
        raise ValueError("partial file exceeds expected size; remove it and retry")
    if offset == pin["bytes"]:
        return
    url = f"https://huggingface.co/{pin['repo_id']}/resolve/{pin['revision']}/{pin['filename']}"
    headers = {"User-Agent": "MiniJev-model-fetch/1", "Accept-Encoding": "identity"}
    if offset:
        headers["Range"] = f"bytes={offset}-"
    with opener(Request(url, headers=headers), timeout=60) as response:
        status = response.status
        if status == 206:
            match = re.fullmatch(r"bytes (\d+)-(\d+)/(\d+)", response.headers.get("Content-Range", ""))
            if not match or tuple(map(int, match.groups())) != (offset, pin["bytes"] - 1, pin["bytes"]):
                raise ValueError("server returned an inconsistent resume range")
        elif status == 200:
            offset = 0  # Range ignored: restart the partial artifact, never append.
        else:
            raise ValueError(f"unexpected download status: {status}")
        length = response.headers.get("Content-Length")
        if length is not None and int(length) != pin["bytes"] - offset:
            raise ValueError("server returned an inconsistent content length")
        written = offset
        last_report = time.monotonic()
        with partial.open("ab" if offset else "wb") as stream:
            while True:
                chunk = response.read(CHUNK)
                if not chunk:
                    break
                if written + len(chunk) > pin["bytes"]:
                    raise ValueError("download exceeds expected artifact size")
                stream.write(chunk)
                written += len(chunk)
                if time.monotonic() - last_report >= 5:
                    print(f"Downloaded {written:,}/{pin['bytes']:,} bytes ({written / pin['bytes']:.1%})", file=sys.stderr)
                    last_report = time.monotonic()
            stream.flush()
            os.fsync(stream.fileno())
        if written != pin["bytes"]:
            raise ValueError(f"incomplete download ({written:,} bytes); rerun to resume")


def fetch(output: Path, *, verify_only=False, pin=PIN, opener=urlopen):
    # Resolve the parent, not the filename: a symlink at the target is rejected.
    output = output.expanduser().absolute()
    if verify_only and not output.exists():
        raise ValueError("completed model file is missing")
    output.parent.mkdir(parents=True, exist_ok=True)
    with lock_for(output):
        if output.exists() or output.is_symlink():
            verify(output, pin)
        else:
            partial = output.with_name(output.name + ".partial")
            download_partial(partial, pin, opener)
            verify(partial, pin)
            # A final filename never represents an incomplete/unverified download.
            if output.exists() or output.is_symlink():
                raise ValueError("target appeared during download; refusing to replace it")
            os.replace(partial, output)
        receipt = {**pin, "path": str(output), "verified": True,
                   "verification": "complete_file_size_and_sha256",
                   "note": "Receipt is informational; runtime must perform its own startup verification."}
        receipt_path = output.with_name(output.name + ".verified.json")
        temporary = output.with_name(output.name + f".verified.{os.getpid()}.tmp")
        try:
            with temporary.open("x", encoding="utf-8") as stream:
                stream.write(json.dumps(receipt, indent=2) + "\n")
            os.replace(temporary, receipt_path)
        finally:
            temporary.unlink(missing_ok=True)
        return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="exact destination GGUF path; no model copy is made automatically")
    parser.add_argument("--verify-only", action="store_true", help="hash an existing file without accessing the network")
    parser.add_argument("--info", action="store_true", help="print pinned artifact metadata without downloading")
    args = parser.parse_args()
    try:
        info = metadata()
        if args.info:
            print(json.dumps(info, ensure_ascii=False, indent=2))
            return 0
        if args.output is None:
            parser.error("--output is required unless --info is used")
        print(json.dumps(fetch(args.output, verify_only=args.verify_only), indent=2))
        return 0
    except (OSError, ValueError) as error:
        print(f"Model fetch failed: {error}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("Interrupted; the .partial file is retained for resuming.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
