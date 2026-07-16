#!/usr/bin/env sh
# Projected one-command certification entrypoint for human and agent consumers.
set -eu

workspace="${DADAIA_WORKSPACE_ROOT:-$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)}"
dadaia_bin="${DADAIA_BIN:-$workspace/.dadaia/.venv/bin/dadaia}"

test -x "$dadaia_bin" || {
    printf 'certify-dadaia-workspace: missing executable %s\n' "$dadaia_bin" >&2
    exit 2
}

exec "$dadaia_bin" certify --json "$@"
