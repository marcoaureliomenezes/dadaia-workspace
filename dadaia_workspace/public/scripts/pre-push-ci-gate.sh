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
#
# Runner resolution (v0.1.10, T-010-26, bug pre-push-gate-cannot-locate-workspace-venv):
#   1. $DADAIA_BIN env override        → "$DADAIA_BIN ci preflight"
#   2. walk UP from repo root to the workspace root, probe
#      "<dir>/.dadaia/.venv/bin/dadaia"  (canonical self-hosting layout: the repo
#      lives at <ws>/repos/<slug> and the venv at <ws>/.dadaia/.venv)
#   3. poetry on PATH                  → "poetry run dadaia ci preflight"
#   4. repo-local ".venv/bin/dadaia"
#   None found → fail CLOSED with a clear error (never silently skip the gate).
#
# --probe-only: print the resolved runner and exit 0 without running the suite
#               (cheap smoke for CLOSURE evidence).
set -euo pipefail

PROBE_ONLY=0
if [ "${1:-}" = "--probe-only" ]; then
    PROBE_ONLY=1
fi

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$ROOT"

# Resolve the dadaia runner. Echoes a human-readable label to stderr and sets
# RUNNER to an array that, when expanded, runs `<...> ci preflight`.
RUNNER=()
RUNNER_LABEL=""

resolve_runner() {
    # 1. Explicit override.
    if [ -n "${DADAIA_BIN:-}" ]; then
        RUNNER=("$DADAIA_BIN" ci preflight)
        RUNNER_LABEL="DADAIA_BIN=$DADAIA_BIN"
        return 0
    fi

    # 2. Walk up from repo root looking for the workspace-level venv.
    local dir="$ROOT"
    while :; do
        local candidate="$dir/.dadaia/.venv/bin/dadaia"
        if [ -x "$candidate" ]; then
            RUNNER=("$candidate" ci preflight)
            RUNNER_LABEL="workspace-venv $candidate"
            return 0
        fi
        local parent
        parent="$(dirname "$dir")"
        if [ "$parent" = "$dir" ]; then
            break
        fi
        dir="$parent"
    done

    # 3. poetry on PATH.
    if command -v poetry >/dev/null 2>&1; then
        RUNNER=(poetry run dadaia ci preflight)
        RUNNER_LABEL="poetry run dadaia"
        return 0
    fi

    # 4. Repo-local venv.
    if [ -x ".venv/bin/dadaia" ]; then
        RUNNER=(.venv/bin/dadaia ci preflight)
        RUNNER_LABEL="repo-venv .venv/bin/dadaia"
        return 0
    fi

    return 1
}

if ! resolve_runner; then
    echo "[pre-push] ERROR: could not locate the dadaia runner to run the CI gate." >&2
    echo "[pre-push]   tried: \$DADAIA_BIN, walk-up <ws>/.dadaia/.venv/bin/dadaia, poetry, .venv/bin/dadaia" >&2
    echo "[pre-push]   fix: set DADAIA_BIN, install deps (poetry install), or run the checks manually." >&2
    exit 1
fi

if [ "$PROBE_ONLY" -eq 1 ]; then
    echo "[pre-push] runner resolved: $RUNNER_LABEL"
    exit 0
fi

echo "[pre-push] CI-equivalent preflight via $RUNNER_LABEL (ruff · mypy --strict · pytest)…"
exec "${RUNNER[@]}"
