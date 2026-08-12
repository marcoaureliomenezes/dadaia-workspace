#!/usr/bin/env bash
# Mandatory pre-push gate — dadaia-workspace v0.1.5 (CI) + v0.1.14 (security verdict)
# + v0.6.0 (gitflow branch policy).
#
# Two gates run in sequence and BOTH must pass before a push proceeds:
#   1. CI-equivalent preflight (ruff format --check, ruff check, mypy --strict, pytest).
#      Locally-solvable failures must never reach a push (post-mortem: the v0.1.4 family
#      was pushed + closed while CI was red).
#   2. Branch policy + security-verdict gate (FR-W1-02 / v0.6.0 FR4): only
#      refs/heads/develop is pushable (main advances via PR from develop only;
#      feature/hotfix branches are local-only; names outside the four permitted
#      patterns are refused; tag pushes carve out), and the pushed develop tip must be
#      covered by a security-reviewer APPROVE handoff whose `metrics.commit_sha`
#      equals it — a DIFF review of origin/develop..develop. The pre-push ref lines
#      git feeds on STDIN are forwarded to `ci push-gate-check`.
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

# git feeds the pre-push ref lines on STDIN exactly once. Capture them now so the
# security-verdict gate can be fed the same lines after the CI preflight has run.
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

echo "[pre-push] CI-equivalent preflight via $RUNNER_LABEL (ruff · mypy --strict · pytest, --quick: no e2e)…"
"${RUNNER_BIN[@]}" ci preflight --quick

echo "[pre-push] branch-policy + security-verdict gate (develop-only push; diff-covering security-reviewer APPROVE)…"
printf '%s' "$PUSH_REFS" | "${RUNNER_BIN[@]}" ci push-gate-check
