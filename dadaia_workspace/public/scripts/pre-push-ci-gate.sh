#!/usr/bin/env bash
# Mandatory pre-push CI gate — dadaia-workspace v0.1.5 (T-GATE-01).
#
# Runs the CI-equivalent suite locally (ruff format --check, ruff check,
# mypy --strict, pytest) and BLOCKS the push (exit non-zero) if any check fails.
# Locally-solvable failures must never reach a push (post-mortem: the v0.1.4
# family was pushed + closed while CI was red).
#
# Installed to .git/hooks/pre-push by `dadaia ci install-hook`.
# Emergency bypass (discouraged, leaves a trace in reflog): git push --no-verify
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$ROOT"

echo "[pre-push] CI-equivalent preflight (ruff · mypy --strict · pytest)…"

if command -v poetry >/dev/null 2>&1; then
    exec poetry run dadaia ci preflight
elif [ -x ".venv/bin/dadaia" ]; then
    exec .venv/bin/dadaia ci preflight
else
    echo "[pre-push] ERROR: neither 'poetry' nor '.venv/bin/dadaia' found to run the gate." >&2
    echo "[pre-push] Install deps (poetry install) or run the checks manually before pushing." >&2
    exit 1
fi
