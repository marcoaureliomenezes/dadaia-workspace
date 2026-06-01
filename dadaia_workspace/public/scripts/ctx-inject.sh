#!/bin/bash
# Resolve workspace_root via the script's own absolute path — robust against
# (a) workspace dir not being a git repo, (b) $HOME not matching workspace prefix,
# (c) running from a subdir. The hook lives at <workspace_root>/.dadaia/scripts/,
# so the workspace root is two levels up from the script.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEFAULT_WORKSPACE_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
WORKSPACE_ROOT="${WORKSPACE_ROOT:-$DEFAULT_WORKSPACE_ROOT}"
STATE_FILE="$WORKSPACE_ROOT/.dadaia/states/primary_context.json"

# ---------------------------------------------------------------------------
# Resolve context name and SPECS_DIR (preserve existing logic).
# ---------------------------------------------------------------------------
if [ -n "$DADAIA_CONTEXT" ]; then
    CONTEXT_NAME="$DADAIA_CONTEXT"
    SPECS_DIR="$WORKSPACE_ROOT/repos/$DADAIA_CONTEXT/specs"
    if [ -d "$SPECS_DIR" ]; then
        echo "[$DADAIA_CONTEXT]"
    else
        echo "[$DADAIA_CONTEXT] WARNING: specs not found"
        exit 0
    fi
elif [ -f "$STATE_FILE" ]; then
    CONTEXT_NAME=$(python3 -c "import json; d=json.load(open('$STATE_FILE')); print(d.get('name',''))" 2>/dev/null)
    if [ -z "$CONTEXT_NAME" ]; then
        echo "[context: none] — run: eval \$(dadaia context use <name>)"
        exit 0
    fi
    SPECS_DIR="$WORKSPACE_ROOT/repos/$CONTEXT_NAME/specs"
    echo "[$CONTEXT_NAME]"
else
    echo "[context: none] — run: eval \$(dadaia context use <name>)"
    exit 0
fi

# ---------------------------------------------------------------------------
# Graceful skip: if specs/memory/ does not exist, emit nothing further.
# ---------------------------------------------------------------------------
MEMORY_DIR="$SPECS_DIR/memory"
if [ ! -d "$MEMORY_DIR" ]; then
    exit 0
fi

# ---------------------------------------------------------------------------
# First-message sentinel guard (OQ-1/OQ-2 working assumption).
# Probe session env vars in preference order; fall back to shell PID.
# NOTE for devops-engineer (T-MCE-09 / OQ-1 / OQ-2): confirm the real session
# env var available in Claude Code and OpenCode and replace the probe below with
# the confirmed var. If CLAUDE_CODE_SESSION_ID is reliable for Claude Code, it
# is the preferred source. The PID fallback is safe but causes re-injection on
# every new shell invocation of the script in the same logical session.
# ---------------------------------------------------------------------------
if [ -n "$CLAUDE_CODE_SESSION_ID" ]; then
    SESSION_ID="$CLAUDE_CODE_SESSION_ID"
elif [ -n "$OPENCODE_SESSION_ID" ]; then
    SESSION_ID="$OPENCODE_SESSION_ID"
else
    SESSION_ID="$$"
fi

mkdir -p "$WORKSPACE_ROOT/.dadaia/tmp"
SENTINEL="$WORKSPACE_ROOT/.dadaia/tmp/ctx-inject-fired-${SESSION_ID}"

if [ -f "$SENTINEL" ]; then
    # Memory block already injected this session — emit only the context name (already done above).
    exit 0
fi

# Create sentinel before emitting to avoid double-injection on concurrent calls.
touch "$SENTINEL"

# ---------------------------------------------------------------------------
# Emit bounded memory bootstrap block.
# tech-stack.md and product/index.md are read verbatim — no strip pass needed.
# ---------------------------------------------------------------------------

echo ""
echo "=== workspace memory (tech + catalog) ==="

# Tech stack — read .md verbatim (T-MMS-07: no strip pass needed for markdown)
TECH_FILE="$MEMORY_DIR/tech-stack.md"
if [ -f "$TECH_FILE" ]; then
    cat "$TECH_FILE"
fi

# Catalog: prefer catalog.json (machine-readable, generated from frontmatter);
# fall back to product/index.md verbatim when catalog.json is absent (T-MMS-07).
CATALOG_JSON="$MEMORY_DIR/product/catalog.json"
PRODUCT_INDEX_MD="$MEMORY_DIR/product/index.md"
if [ -f "$CATALOG_JSON" ]; then
    cat "$CATALOG_JSON"
elif [ -f "$PRODUCT_INDEX_MD" ]; then
    cat "$PRODUCT_INDEX_MD"
fi

echo "=== end memory bootstrap ==="
