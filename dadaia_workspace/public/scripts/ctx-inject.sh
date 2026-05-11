#!/bin/bash
WORKSPACE_ROOT="${WORKSPACE_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || echo "$HOME/workspace")}"
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
