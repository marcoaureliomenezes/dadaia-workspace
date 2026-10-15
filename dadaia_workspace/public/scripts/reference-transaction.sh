#!/bin/sh
# reference-transaction hook: routes raw ref moves to the ref gate.
#
# git runs it in every state with `old new ref` lines on STDIN; only `prepared` decides.
# Refused here: creating refs/heads/wt/* without DADAIA_WT=1 (the worktree runner sets it).
# Passed here: every other creation or deletion, and an update of refs/heads/wt/* (no runner
# call). Every other update goes to `dadaia ci ref-gate-check`, which owns the policy.
# An unresolvable runner warns and passes: this hook fires on every ref update, so failing
# closed would brick `git commit`; the pre-push gate stays the fail-closed chokepoint.
# Runner resolution follows pre-push-ci-gate.sh (workspace venv walking up, repo-local venv),
# then `dadaia` on PATH.

lines=$(cat)
[ "$1" = prepared ] || exit 0

is_zero() {
    case "$1" in *[!0]*) return 1 ;; *) return 0 ;; esac
}

resolve_runner() {
    top=$(git rev-parse --show-toplevel 2>/dev/null) || top=$(pwd)
    dir=$top
    while :; do
        for c in "$dir/.dadaia/.venv/bin/dadaia" "$dir/.dadaia/.venv/Scripts/dadaia.exe"; do
            if [ -x "$c" ]; then RUNNER=$c; return 0; fi
        done
        [ "$dir" = / ] && break
        dir=$(dirname "$dir")
    done
    if [ -x "$top/.venv/bin/dadaia" ]; then RUNNER=$top/.venv/bin/dadaia; return 0; fi
    RUNNER=$(command -v dadaia) && return 0
    return 1
}

gated=""
while read -r old new ref; do
    case "$ref" in ""|HEAD) continue ;; esac
    if is_zero "$old"; then
        case "$ref" in
            refs/heads/wt/*)
                if ! is_zero "$new" && [ "${DADAIA_WT:-}" != 1 ]; then
                    name=${ref#refs/heads/wt/}
                    slug=$(basename "$(dirname "$(git rev-parse --path-format=absolute --git-common-dir)")")
                    echo "[ref-gate] BLOCKED $ref: wt/ branches are created by the worktree runner" >&2
                    echo "fix: dadaia worktree new $slug $name" >&2
                    exit 1
                fi ;;
        esac
        continue
    fi
    if is_zero "$new"; then continue; fi
    case "$ref" in refs/heads/wt/*) continue ;; esac
    gated="${gated}${old} ${new} ${ref}
"
done <<EOF
$lines
EOF

[ -n "$gated" ] || exit 0
if ! resolve_runner; then
    echo "reference-transaction: could not locate the dadaia runner; ref gate skipped" >&2
    exit 0
fi
printf '%s' "$gated" | "$RUNNER" ci ref-gate-check
