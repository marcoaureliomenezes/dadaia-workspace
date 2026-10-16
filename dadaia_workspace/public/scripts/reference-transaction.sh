#!/bin/sh
# reference-transaction shim. git fires it in every state; only an unmarked `prepared` decides
# (DADAIA_WT=1, which the worktree runner sets, passes at no cost), and the policy is
# dadaia_workspace.hooks.ref_transaction, run by the first venv interpreter found walking up from the
# repo (then the repo's own .venv); only its exit 3 refuses. None found, or a fault: warn and pass,
# since this hook fires on every ref update and failing closed would brick `git commit`; the
# pre-push gate is the fail-closed chokepoint.

[ "$1" = prepared ] || exit 0
[ "${DADAIA_WT:-}" = 1 ] && exit 0

run() {
    for PY in "$1/bin/python" "$1/Scripts/python.exe"; do
        [ -x "$PY" ] || continue
        "$PY" -B -m dadaia_workspace.hooks.ref_transaction
        rc=$?
        [ "$rc" -eq 3 ] && exit 1
        [ "$rc" -eq 0 ] || echo "reference-transaction: the ref gate failed (exit $rc); update allowed" >&2
        exit 0
    done
}

top=$(git rev-parse --show-toplevel 2>/dev/null) || top=$(pwd)
dir=$top
while :; do
    run "$dir/.dadaia/.venv"
    parent=$(dirname "$dir")
    [ "$parent" = "$dir" ] && break
    dir=$parent
done
run "$top/.venv"
echo "reference-transaction: could not locate the dadaia runner; ref gate skipped" >&2
exit 0
