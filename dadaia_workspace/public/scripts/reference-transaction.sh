#!/bin/sh
# reference-transaction shim. git fires it in every state; only `prepared` decides, and the policy is
# dadaia_workspace.hooks.ref_transaction, run by the first venv interpreter found walking up from the
# repo (then the repo's own .venv). None found: warn and pass, since this hook fires on every ref
# update and failing closed would brick `git commit`; the pre-push gate is the fail-closed chokepoint.

[ "$1" = prepared ] || exit 0

run() {
    for PY in "$1/bin/python" "$1/Scripts/python.exe"; do
        [ -x "$PY" ] && exec "$PY" -B -m dadaia_workspace.hooks.ref_transaction
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
