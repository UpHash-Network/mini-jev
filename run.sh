#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "$0")"
if [[ -n "${MINI_JEV_PYTHON:-}" ]]; then
  runtime_python="$MINI_JEV_PYTHON"
elif [[ -x .venv/bin/python ]]; then
  runtime_python=.venv/bin/python
else
  runtime_python="$(command -v python3 || true)"
fi
if [[ ! -x "$runtime_python" ]]; then
  echo "Python runtime not found. Follow README.md, or set MINI_JEV_PYTHON to its executable path." >&2
  exit 1
fi
export PYTHONDONTWRITEBYTECODE=1
if ! "$runtime_python" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)'; then
  echo "Python 3.10 or newer is required." >&2
  exit 1
fi
exec "$runtime_python" run_native_service.py "$@"
