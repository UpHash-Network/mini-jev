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
exec "$runtime_python" run_service.py "$@"
