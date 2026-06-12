#!/usr/bin/env bash
# Pre-commit lease gate — dadaia-workspace v0.1.14 (FR-W1-01, T-014-14).
#
# Blocks a `git commit` into a Spec Context repo when the committing session does NOT
# hold that context's MUTATING lease. The holder's own commits flow; a commit while no
# live lease exists flows (ADDITIVE work commits freely — zero-false-block); a live
# FOREIGN holder is blocked with an actionable message. The gate consults the lease ONLY
# — never a review verdict (commits are never review-blocked; that is the push gate).
#
# This is the harness-independent chokepoint: it fires in every runtime (Claude Code,
# Codex interactive, `codex exec` headless, OpenCode, plain git) because it is a git hook,
# closing the `codex-exec-hooks-do-not-fire-headless` gap at the commit boundary.
#
# Installed to .git/hooks/pre-commit by `dadaia ci install-hook`.
# Emergency bypass (discouraged, leaves a trace): git commit --no-verify
#
# Runner resolution mirrors pre-push-ci-gate.sh (fail CLOSED — never silently skip):
#   1. $DADAIA_BIN env override        → "$DADAIA_BIN ci pre-commit-check"
#   2. walk UP from repo root to the workspace, probe "<dir>/.dadaia/.venv/bin/dadaia"
#   3. poetry on PATH                  → "poetry run dadaia ci pre-commit-check"
#   4. repo-local ".venv/bin/dadaia"
#   None found → fail CLOSED with a clear error.
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$ROOT"

RUNNER=()
RUNNER_LABEL=""

resolve_runner() {
    # 1. Explicit override.
    if [ -n "${DADAIA_BIN:-}" ]; then
        RUNNER=("$DADAIA_BIN" ci pre-commit-check)
        RUNNER_LABEL="DADAIA_BIN=$DADAIA_BIN"
        return 0
    fi

    # 2. Walk up from repo root looking for the workspace-level venv.
    local dir="$ROOT"
    while :; do
        local candidate="$dir/.dadaia/.venv/bin/dadaia"
        if [ -x "$candidate" ]; then
            RUNNER=("$candidate" ci pre-commit-check)
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
        RUNNER=(poetry run dadaia ci pre-commit-check)
        RUNNER_LABEL="poetry run dadaia"
        return 0
    fi

    # 4. Repo-local venv.
    if [ -x ".venv/bin/dadaia" ]; then
        RUNNER=(.venv/bin/dadaia ci pre-commit-check)
        RUNNER_LABEL="repo-venv .venv/bin/dadaia"
        return 0
    fi

    return 1
}

if ! resolve_runner; then
    echo "[pre-commit] ERROR: could not locate the dadaia runner to run the lease gate." >&2
    echo "[pre-commit]   tried: \$DADAIA_BIN, walk-up <ws>/.dadaia/.venv/bin/dadaia, poetry, .venv/bin/dadaia" >&2
    echo "[pre-commit]   fix: set DADAIA_BIN, install deps (poetry install), or run the check manually." >&2
    exit 1
fi

exec "${RUNNER[@]}"
