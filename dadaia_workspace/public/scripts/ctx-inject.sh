#!/bin/bash
# Resolve workspace_root via the script's own absolute path — robust against
# (a) workspace dir not being a git repo, (b) $HOME not matching workspace prefix,
# (c) running from a subdir. The hook lives at <workspace_root>/.dadaia/scripts/,
# so the workspace root is two levels up from the script.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEFAULT_WORKSPACE_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
WORKSPACE_ROOT="${WORKSPACE_ROOT:-$DEFAULT_WORKSPACE_ROOT}"
STATE_FILE="$WORKSPACE_ROOT/.dadaia/states/primary_context.json"

if [ -n "$DADAIA_CONTEXT" ]; then
    SPECS_DIR="$WORKSPACE_ROOT/repos/$DADAIA_CONTEXT/specs"
    if [ -d "$SPECS_DIR" ]; then
        echo "[$DADAIA_CONTEXT]"
    else
        echo "[$DADAIA_CONTEXT] WARNING: specs not found"
    fi
    exit 0
fi

if [ ! -f "$STATE_FILE" ]; then
    echo "[context: none] — run: eval \$(dadaia context use <name>)"
    exit 0
fi

NAME=$(python3 -c "import json; d=json.load(open('$STATE_FILE')); print(d.get('name',''))" 2>/dev/null)

if [ -z "$NAME" ]; then
    echo "[context: none] — run: eval \$(dadaia context use <name>)"
else
    echo "[$NAME]"
fi
