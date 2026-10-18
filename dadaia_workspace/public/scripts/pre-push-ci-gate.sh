#!/bin/sh
# Mandatory pre-push gate shim: git's pre-push ref lines (STDIN) go to `dadaia ci push-gate-check`,
# whose decision is the one list of refusals (the branch model is the `gitflow:` block of
# specs/constitution.md); this file only refuses an unresolvable runner, closed, never a silent skip.
# The runner is the first venv `dadaia` found walking up from the repo root.
# Installed to .git/hooks/pre-push by `dadaia ci install-hook`. --probe-only prints the resolved
# runner and exits 0.

ROOT=$(git rev-parse --show-toplevel 2>/dev/null) || ROOT=$(pwd)

probe() {
    for RUNNER in "$1/bin/dadaia" "$1/Scripts/dadaia.exe"; do
        [ -x "$RUNNER" ] && return 0
    done
    return 1
}

resolve() {
    dir=$ROOT
    while :; do
        probe "$dir/.dadaia/.venv" && LABEL=workspace-venv && return 0
        parent=$(dirname "$dir")
        [ "$parent" = "$dir" ] && return 1
        dir=$parent
    done
}

if ! resolve; then
    echo "[pre-push] ERROR: could not locate the dadaia runner to run the push gate." >&2
    echo "[pre-push]   tried: the workspace venv walking up from $ROOT" >&2
    echo "[pre-push]   fix: Agent action: install the workspace venv (re-run \`uvx dadaia-workspace init\` at the workspace root)." >&2
    exit 1
fi
if [ "${1:-}" = "--probe-only" ]; then
    echo "[pre-push] runner resolved: $LABEL $RUNNER"
    exit 0
fi
echo "[pre-push] push gate (gitflow: specs/constitution.md)…"
exec "$RUNNER" ci push-gate-check
