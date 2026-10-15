#!/bin/sh
# reference-transaction hook: routes raw ref moves to the ref gate.
#
# git runs it in every state with `old new ref` lines on STDIN; only `prepared` decides.
# DADAIA_WT=1 (the worktree runner sets it) passes every line. Unmarked, creating
# refs/heads/wt/* is refused here; an update of refs/heads/wt/* passes; an update of any
# other refs/heads/* ref whose new sha is not origin's goes to `dadaia ci ref-gate-check`,
# which owns the policy. Only that command's refusal (its `[ref-gate] BLOCKED` line) blocks:
# an unresolvable or faulting runner warns and passes, since this hook fires on every ref
# update and failing closed would brick `git commit`; the pre-push gate stays the
# fail-closed chokepoint. Runner resolution follows pre-push-ci-gate.sh.

lines=$(cat)
[ "$1" = prepared ] || exit 0
[ "${DADAIA_WT:-}" = 1 ] && exit 0

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
        parent=$(dirname "$dir")
        [ "$parent" = "$dir" ] && break
        dir=$parent
    done
    if [ -x "$top/.venv/bin/dadaia" ]; then RUNNER=$top/.venv/bin/dadaia; return 0; fi
    return 1
}

quote() {
    printf "'%s'" "$(printf '%s' "$1" | sed "s/'/'\\\\''/g")"
}

gated=""
while read -r old new ref; do
    case "$ref" in
        refs/heads/wt/*)
            if is_zero "$old" && ! is_zero "$new"; then
                name=${ref#refs/heads/wt/}
                slug=$(basename "$(dirname "$(cd "$(git rev-parse --git-common-dir)" && pwd -P)")")
                echo "[ref-gate] BLOCKED $ref: wt/ branches are created by the worktree runner" >&2
                if resolve_runner; then
                    echo "fix: $(quote "$RUNNER") worktree new $(quote "$slug") $(quote "$name")" >&2
                else
                    echo "fix: Agent action: install the workspace venv (re-run \`uvx dadaia-workspace init\` at the workspace root)" >&2
                fi
                exit 1
            fi ;;
        refs/heads/*)
            origin=$(git rev-parse -q --verify "refs/remotes/origin/${ref#refs/heads/}" 2>/dev/null)
            [ "$new" = "$origin" ] && continue
            gated="${gated}${old} ${new} ${ref}
" ;;
    esac
done <<EOF
$lines
EOF

[ -n "$gated" ] || exit 0
if ! resolve_runner; then
    echo "reference-transaction: could not locate the dadaia runner; ref gate skipped" >&2
    exit 0
fi
out=$(printf '%s' "$gated" | "$RUNNER" ci ref-gate-check 2>&1)
rc=$?
[ -n "$out" ] && printf '%s\n' "$out" >&2
[ "$rc" -eq 0 ] && exit 0
case "$out" in *"[ref-gate] BLOCKED"*) exit 1 ;; esac
echo "reference-transaction: the ref gate failed (exit $rc); update allowed" >&2
exit 0
