#!/usr/bin/env bash
# Pre-commit presence WARN — dadaia-workspace (FR-W1-01; v0.1.25 R1; presence rewrite:
# NO-LOCKS DOCTRINE, v0.1.76 FR3; de-slopped to advisory-only: v0.5.0 FR9/D9).
#
# ADVISORY-ONLY, ALWAYS EXIT 0 (v0.5.0 FR9/D9): this hook never blocks a `git commit`,
# for ANY reason. It still WARNS when another live session holds presence on the
# context (NO-LOCKS DOCTRINE, v0.1.76) and it still WARNS (never blocks) when the
# dadaia runner cannot be located.
#
# The `backlog doctor` BLOCK and the fail-closed runner resolution that used to live
# here are DELETED, in this script only (`pre-push-ci-gate.sh` keeps its fail-closed
# runner — it is the publication boundary, not this one). CI's `backlog-doctor` job
# already runs the unscoped sweep over the whole tree, so blocking commits here only
# ever punished humans and agents on a shared tree and pushed them toward
# `--no-verify` and worse workarounds — a gate that caused the behaviour it existed to
# prevent (bug `precommit-backlog-doctor-blocks-unrelated-commits`).
#
# This is the harness-independent chokepoint: it fires in every runtime (Claude Code,
# Codex interactive, `codex exec` headless, PI, plain git) because it is a git hook,
# closing the `codex-exec-hooks-do-not-fire-headless` gap at the commit boundary.
#
# Installed to .git/hooks/pre-commit by `dadaia ci install-hook`.
#
# Runner resolution mirrors pre-push-ci-gate.sh's search order, but FAILS OPEN here
# (never blocks the commit on a missing runner — pre-push is the fail-closed
# publication boundary, this is not):
#   1. $DADAIA_BIN env override        → "$DADAIA_BIN ci pre-commit-check"
#   2. walk UP from repo root to the workspace, probe "<dir>/.dadaia/.venv/bin/dadaia"
#   3. poetry on PATH                  → "poetry run dadaia ci pre-commit-check"
#   4. repo-local ".venv/bin/dadaia"
#   None found → WARN and exit 0 (never block the commit).
set -uo pipefail

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$ROOT" 2>/dev/null || exit 0

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

if resolve_runner; then
    # Advisory only: whatever this prints/returns, the commit still proceeds.
    "${RUNNER[@]}" || true
else
    echo "[pre-commit] advisory: could not locate the dadaia runner (tried \$DADAIA_BIN, workspace-venv walk-up, poetry, repo-venv) — skipping the presence check; commit proceeds." >&2
fi

exit 0
