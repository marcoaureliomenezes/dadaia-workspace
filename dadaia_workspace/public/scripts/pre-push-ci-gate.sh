#!/usr/bin/env bash
# Mandatory pre-push gate — dadaia-workspace (de-slopped to the publication boundary:
# v0.5.0 FR9/D9).
#
# Branch model: this file states it nowhere — see `DADAIA.md` §4 (Gitflow) +
# `dd-gitflow-default`.
#
# What THIS script does — the publication boundary, and NOTHING else: branch-name
# validation + the range-scoped denylist scan on the feature push (`ci
# push-gate-check`) — `develop`/`main` refuse a direct push and name the PR path
# instead. The pre-push ref lines git feeds on STDIN are forwarded there. This hook
# refuses exactly three things: an invalid branch name, a denylist hit, and an
# unresolvable runner (below) — never a fourth reason (v0.5.0 A9.2).
#
# The CI-equivalent preflight (ruff format --check, ruff check, mypy --strict,
# lint-imports, pytest) NO LONGER runs from this hook (v0.5.0 FR9/D9 — it moved OFF
# the hook and became the always-on rule "run `dadaia ci preflight` before you push",
# `DADAIA.md` §7 + `dd-gitflow-default` + `dd-release-implement`). A failing local
# preflight therefore no longer blocks a push through THIS hook — run `dadaia ci
# preflight` yourself before pushing; CI still gates on the same checks independently,
# on every push.
#
# Installed to .git/hooks/pre-push by `dadaia ci install-hook`.
# Emergency bypass (discouraged, leaves a trace in reflog): git push --no-verify
#
# Runner resolution (v0.1.10, T-010-26, bug pre-push-gate-cannot-locate-workspace-venv):
#   1. $DADAIA_BIN env override        → "$DADAIA_BIN ci <verb>"
#   2. walk UP from repo root to the workspace root, probe
#      "<dir>/.dadaia/.venv/bin/dadaia"  (canonical self-hosting layout: the repo
#      lives at <ws>/repos/<slug> and the venv at <ws>/.dadaia/.venv)
#   3. poetry on PATH                  → "poetry run dadaia ci <verb>"
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

# git feeds the pre-push ref lines on STDIN exactly once. Capture them now so
# `ci push-gate-check` can be fed the same lines.
PUSH_REFS=""
if [ "$PROBE_ONLY" -eq 0 ] && [ ! -t 0 ]; then
    PUSH_REFS="$(cat)"
fi

# Resolve the dadaia runner. Echoes a human-readable label to stderr and sets
# RUNNER_BIN to a parallel array that, when expanded with a verb, runs `<...> ci <verb>`.
RUNNER_BIN=()
RUNNER_LABEL=""

resolve_runner() {
    # 1. Explicit override.
    if [ -n "${DADAIA_BIN:-}" ]; then
        RUNNER_BIN=("$DADAIA_BIN")
        RUNNER_LABEL="DADAIA_BIN=$DADAIA_BIN"
        return 0
    fi

    # 2. Walk up from repo root looking for the workspace-level venv.
    local dir="$ROOT"
    while :; do
        local candidate="$dir/.dadaia/.venv/bin/dadaia"
        if [ -x "$candidate" ]; then
            RUNNER_BIN=("$candidate")
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
        RUNNER_BIN=(poetry run dadaia)
        RUNNER_LABEL="poetry run dadaia"
        return 0
    fi

    # 4. Repo-local venv.
    if [ -x ".venv/bin/dadaia" ]; then
        RUNNER_BIN=(.venv/bin/dadaia)
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

echo "[pre-push] branch-name + denylist gate (feature/{M.m.p} push; develop/main refused — PR path)…"
printf '%s' "$PUSH_REFS" | "${RUNNER_BIN[@]}" ci push-gate-check
