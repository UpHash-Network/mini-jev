#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: ./build_native.sh --work-dir DIR --output DIR [--jobs N]

Build the pinned native runtime for macOS ARM64 in a separate work directory.
The output directory must not exist. No model is downloaded or loaded.
Requires Xcode command-line tools, CMake, Git, and Python 3.10 or newer.
EOF
}

task_base="$(cd "$(dirname "$0")" && pwd)"
task_work=""
task_output=""
task_jobs=2
while [[ $# -gt 0 ]]; do
  case "$1" in
    --work-dir) task_work="${2:?missing --work-dir value}"; shift 2 ;;
    --output) task_output="${2:?missing --output value}"; shift 2 ;;
    --jobs) task_jobs="${2:?missing --jobs value}"; shift 2 ;;
    --help|-h) usage; exit 0 ;;
    *) usage >&2; exit 2 ;;
  esac
done
[[ -n "$task_work" && -n "$task_output" ]] || { usage >&2; exit 2; }
[[ "$task_jobs" =~ ^[1-9][0-9]*$ ]] || { echo "--jobs must be a positive integer" >&2; exit 2; }
[[ "$(uname -s)" == Darwin && "$(uname -m)" == arm64 ]] || { echo "Run on native macOS ARM64, outside Rosetta." >&2; exit 2; }
[[ ! -e "$task_output" ]] || { echo "Output already exists; choose a new directory." >&2; exit 2; }
for task_tool in git cmake python3 xcrun install_name_tool codesign lipo otool; do
  command -v "$task_tool" >/dev/null || { echo "Missing tool: $task_tool" >&2; exit 2; }
done
python3 -c 'import sys; assert sys.version_info >= (3, 10), "Python 3.10 or newer is required"'
mkdir -p "$task_work"
task_work="$(cd "$task_work" && pwd)"
task_source="$task_work/llama.cpp"
task_build="$task_work/build-arm64"
task_commit=f072b103714dfa1eee531f80b24512faf38e3dd2
[[ ! -e "$task_build/CMakeCache.txt" ]] || { echo "Existing CMake cache found; choose a new work directory for a reproducible build." >&2; exit 2; }

if [[ ! -e "$task_source" ]]; then
  git init "$task_source"
  git -C "$task_source" remote add origin https://github.com/ggml-org/llama.cpp.git
  git -C "$task_source" fetch --depth 1 origin "$task_commit"
  git -C "$task_source" checkout --detach "$task_commit"
fi
[[ "$(git -C "$task_source" rev-parse HEAD)" == "$task_commit" ]] || { echo "Source revision differs from fixed commit." >&2; exit 2; }
[[ -z "$(git -C "$task_source" status --porcelain --untracked-files=no)" ]] || { echo "Source has tracked changes." >&2; exit 2; }

cmake -S "$task_source" -B "$task_build" \
  -DCMAKE_BUILD_TYPE=Release -DCMAKE_OSX_ARCHITECTURES=arm64 \
  -DCMAKE_OSX_DEPLOYMENT_TARGET=26.4 -DBUILD_SHARED_LIBS=ON \
  -DGGML_METAL=ON -DGGML_METAL_EMBED_LIBRARY=ON -DGGML_BLAS=ON -DGGML_BLAS_VENDOR=Apple \
  -DLLAMA_OPENSSL=OFF -DLLAMA_BUILD_COMMON=ON -DLLAMA_BUILD_TESTS=OFF \
  -DLLAMA_BUILD_TOOLS=OFF -DLLAMA_BUILD_EXAMPLES=OFF -DLLAMA_BUILD_SERVER=OFF \
  -DLLAMA_BUILD_APP=OFF -DLLAMA_BUILD_MTMD=OFF
cmake --build "$task_build" --parallel "$task_jobs" --target llama-common
xcrun clang++ -arch arm64 -mmacosx-version-min=26.4 -std=c++17 -O2 \
  -I "$task_source/include" -I "$task_source/common" -I "$task_source/ggml/include" \
  -I "$task_source/vendor/nlohmann" "$task_base/native/llama_decision_helper.cpp" \
  -L "$task_build/bin" -Wl,-rpath,@loader_path \
  -lllama-common -lllama -lggml -lggml-base -o "$task_work/llama-decision-helper"
python3 "$task_base/native/package_runtime.py" --source "$task_source" --build "$task_build" \
  --helper "$task_work/llama-decision-helper" --output "$task_output"
