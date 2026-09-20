#!/usr/bin/env python3
"""Assemble or verify a relocatable macOS ARM64 helper package; no model loads."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

COMMIT = "f072b103714dfa1eee531f80b24512faf38e3dd2"
LICENSES = {
    "licenses/LICENSE-jsonhpp": "LICENSE-jsonhpp",
    "vendor/cpp-httplib/LICENSE": "cpp-httplib-LICENSE",
    "vendor/hash/sha256/LICENSE": "sha256-LICENSE",
    "vendor/hash/xxhash/LICENSE": "xxhash-LICENSE",
    "vendor/hash/rotate-bits/LICENSE.md": "rotate-bits-LICENSE.md",
}


def run(args):
    return subprocess.check_output(list(map(str, args)), text=True).strip()


def inventory(folder):
    files, links = {}, {}
    for path in sorted(folder.rglob("*")):
        relative = str(path.relative_to(folder))
        if path.is_symlink():
            target = os.readlink(path)
            if Path(target).is_absolute() or not path.resolve().is_relative_to(folder.resolve()) or not path.exists():
                raise ValueError(f"nonlocal or broken package symlink: {relative}")
            links[relative] = target
        elif path.is_file() and relative != "BUILD.json" and "__pycache__" not in path.parts:
            files[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    return files, links


def write_manifest(folder, *, provenance):
    files, links = inventory(folder)
    document = {
        "schema_version": 1, "llama_cpp_commit": COMMIT, "platform": "macOS arm64",
        "minimum_macos": "26.4", "provenance": provenance,
        "sha256": {Path(k).name: v for k, v in files.items() if k.startswith("bin/")},
        "files_sha256": files, "symlinks": links,
        "integrity_note": "Hashes identify this package; recompilation with a different SDK/compiler can produce different bytes.",
    }
    (folder / "BUILD.json").write_text(json.dumps(document, indent=2) + "\n")


def verify_package(folder):
    manifest = json.loads((folder / "BUILD.json").read_text())
    if manifest["llama_cpp_commit"] != COMMIT:
        raise ValueError("unexpected llama.cpp revision")
    files, links = inventory(folder)
    if files != manifest["files_sha256"] or links != manifest["symlinks"]:
        raise ValueError("package file hashes or symlinks do not match BUILD.json")
    return {"verified": True, "files": len(files), "symlinks": len(links), "llama_cpp_commit": COMMIT}


def relocate(folder):
    binaries = [p for p in sorted((folder / "bin").iterdir()) if p.is_file() and not p.is_symlink()]
    for binary in binaries:
        architecture = run(["lipo", "-archs", binary])
        if architecture != "arm64":
            raise ValueError(f"unexpected architecture: {binary.name}: {architecture}")
        for line in run(["otool", "-L", binary]).splitlines()[1:]:
            dependency = line.strip().split(" (", 1)[0]
            basename = Path(dependency).name
            if (folder / "bin" / basename).exists():
                replacement = "@loader_path/" + basename
                if dependency != replacement:
                    subprocess.run(["install_name_tool", "-change", dependency, replacement, str(binary)], check=True)
            elif not dependency.startswith(("/usr/lib/", "/System/Library/")):
                raise ValueError(f"unpackaged dependency: {dependency}")
        commands = run(["otool", "-l", binary]).splitlines()
        paths = [commands[i+2].strip().split(" (", 1)[0].removeprefix("path ")
                 for i, line in enumerate(commands) if line.strip() == "cmd LC_RPATH"]
        for path in paths:
            if path not in ("@loader_path", "@executable_path"):
                subprocess.run(["install_name_tool", "-delete_rpath", path, str(binary)], check=True)
        if "@loader_path" not in paths:
            subprocess.run(["install_name_tool", "-add_rpath", "@loader_path", str(binary)], check=True)
        if binary.suffix == ".dylib":
            subprocess.run(["install_name_tool", "-id", "@rpath/" + binary.name, str(binary)], check=True)
        subprocess.run(["codesign", "--force", "--sign", "-", str(binary)], check=True)


def assemble(source, build, output, helper):
    if output.exists():
        raise ValueError("output already exists; choose a new directory")
    if run(["git", "-C", source, "rev-parse", "HEAD"]) != COMMIT:
        raise ValueError("source commit does not match the pin")
    if run(["git", "-C", source, "status", "--porcelain", "--untracked-files=no"]):
        raise ValueError("source contains tracked changes")
    output.mkdir(parents=True)
    (output / "bin").mkdir()
    (output / "licenses").mkdir()
    own = Path(__file__).resolve().parent
    for name in ("llama_decision_helper.cpp", "package_runtime.py", "LICENSE-helper.txt"):
        shutil.copy2(own / name, output / name)
    shutil.copy2(source / "LICENSE", output / "LICENSE-llama-cpp.txt")
    for relative, name in LICENSES.items():
        shutil.copy2(source / relative, output / "licenses" / name)
    shutil.copy2(own / "licenses/LICENSE-Qwen3.6-Apache-2.0.txt", output / "licenses/LICENSE-Qwen3.6-Apache-2.0.txt")
    shutil.copy2(helper, output / "bin/llama-decision-helper")
    for path in sorted((build / "bin").glob("*.dylib")):
        target = output / "bin" / path.name
        if path.is_symlink():
            target.symlink_to(os.readlink(path))
        else:
            shutil.copy2(path, target)
    relocate(output)
    run([output / "bin/llama-decision-helper", "--help"])
    write_manifest(output, provenance={
        "upstream": "https://github.com/ggml-org/llama.cpp",
        "build_script": "../build_native.sh", "helper_source": "llama_decision_helper.cpp",
        "compiler": run(["xcrun", "clang++", "--version"]).splitlines()[0],
        "cmake": run(["cmake", "--version"]).splitlines()[0],
        "sdk_version": run(["xcrun", "--show-sdk-version"]),
        "architecture": "arm64", "deployment_target": "26.4",
        "metal": True, "accelerate": True, "embedded_metal_library": True,
        "code_signature": "ad-hoc after install-name and rpath relocation",
        "verification": "package hashes, ARM64 architecture, local dependency resolution, --help; no model inference",
    })
    return verify_package(output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", type=Path)
    parser.add_argument("--source", type=Path)
    parser.add_argument("--build", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--helper", type=Path)
    args = parser.parse_args()
    try:
        if args.verify:
            result = verify_package(args.verify.resolve())
        elif all((args.source, args.build, args.output, args.helper)):
            result = assemble(args.source.resolve(), args.build.resolve(), args.output.resolve(), args.helper.resolve())
        else:
            parser.error("use --verify DIR or all of --source, --build, --output, --helper")
        print(json.dumps(result, indent=2))
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        print(f"Native packaging failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
