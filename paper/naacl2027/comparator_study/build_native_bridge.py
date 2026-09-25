#!/usr/bin/env python3
"""Build the isolated research helper against an existing verified native runtime."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys

PIN = "f072b103714dfa1eee531f80b24512faf38e3dd2"
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--llama-source", required=True)
    parser.add_argument("--runtime", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--cxx", default=os.environ.get("CXX", "c++"))
    parser.add_argument("--cc", default=os.environ.get("CC", "cc"))
    args = parser.parse_args()
    source, runtime, output = [Path(p).resolve() for p in (args.llama_source, args.runtime, args.output)]
    if output.is_relative_to(ROOT):
        raise ValueError("compiled research output must be outside the Git repository")
    if output.exists():
        raise ValueError("output already exists; choose a new directory")
    revision = subprocess.check_output(["git", "-C", str(source), "rev-parse", "HEAD"], text=True).strip()
    dirty = subprocess.check_output(["git", "-C", str(source), "status", "--porcelain", "--untracked-files=no"], text=True).strip()
    if revision != PIN or dirty:
        raise ValueError("llama.cpp source must be clean and at pinned commit")
    manifest = json.loads((runtime / "BUILD.json").read_text())
    if manifest.get("schema_version") != 1 or manifest.get("llama_cpp_commit") != PIN:
        raise ValueError("wrong native runtime revision/schema")
    for name, expected in manifest["files_sha256"].items():
        path = runtime / name
        if not path.resolve().is_relative_to(runtime) or sha(path) != expected:
            raise ValueError("native runtime hash mismatch")
    for name, target in manifest["symlinks"].items():
        path = runtime / name
        if not path.is_symlink() or os.readlink(path) != target or not path.resolve().is_relative_to(runtime):
            raise ValueError("native runtime alias mismatch")
    (output / "bin").mkdir(parents=True)
    for path in (runtime / "bin").iterdir():
        if not path.name.startswith("lib"):
            continue
        destination = output / "bin" / path.name
        if path.is_symlink():
            destination.symlink_to(os.readlink(path))
        else:
            shutil.copy2(path, destination)
    for path in runtime.iterdir():
        if path.is_file() and path.name.startswith("LICENSE"):
            shutil.copy2(path, output / path.name)
    if (runtime / "licenses").is_dir():
        shutil.copytree(runtime / "licenses", output / "licenses")
    shutil.copy2(HERE / "llama_lmql_helper.cpp", output / "llama_lmql_helper.cpp")
    shutil.copy2(HERE / "NOTICE.md", output / "NOTICE.md")
    obj = output / "sha256.o"
    platform_flags = ["-mmacosx-version-min=" + platform.mac_ver()[0]] if sys.platform == "darwin" else []
    subprocess.run([args.cc, "-O2", *platform_flags, "-I", str(source / "vendor/hash"), "-c", str(source / "vendor/hash/sha256/sha256.c"), "-o", str(obj)], check=True)
    rpath = "@loader_path" if sys.platform == "darwin" else "$ORIGIN"
    includes = [source / name for name in ("include", "common", "ggml/include", "vendor/nlohmann", "vendor/hash/sha256")]
    command = [args.cxx, "-std=c++17", "-O2", *platform_flags]
    for folder in includes:
        command += ["-I", str(folder)]
    command += [str(HERE / "llama_lmql_helper.cpp"), str(obj), "-L", str(output / "bin"),
                "-Wl,-rpath," + rpath, "-lllama-common", "-lllama", "-lggml", "-lggml-base",
                "-o", str(output / "bin/llama-lmql-helper")]
    subprocess.run(command, check=True)
    obj.unlink()
    if sys.platform == "darwin":
        subprocess.run(["codesign", "--force", "--sign", "-", str(output / "bin/llama-lmql-helper")], check=True)
    files = {str(p.relative_to(output)): sha(p) for p in sorted(output.rglob("*")) if p.is_file() and not p.is_symlink()}
    aliases = {str(p.relative_to(output)): os.readlink(p) for p in sorted(output.rglob("*")) if p.is_symlink()}
    build = {"schema_version": 1, "purpose": "lmql_diagnostic_native_bridge", "llama_cpp_commit": PIN,
             "runtime_build_sha256": sha(runtime / "BUILD.json"), "source_sha256": sha(HERE / "llama_lmql_helper.cpp"),
             "build_script_sha256": sha(Path(__file__)), "sha256_c_source_sha256": sha(source / "vendor/hash/sha256/sha256.c"),
             "compiler": subprocess.check_output([args.cxx, "--version"], text=True).splitlines()[0],
             "platform": platform.system(), "machine": platform.machine(),
             "files_sha256": files, "symlinks": aliases}
    (output / "BUILD.json").write_text(json.dumps(build, indent=2) + "\n")
    print(json.dumps({"built": True, "source_sha256": build["source_sha256"], "files": len(files)}))


if __name__ == "__main__":
    main()
