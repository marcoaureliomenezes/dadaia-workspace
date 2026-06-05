#!/bin/bash
# Resolve workspace_root via the script's own absolute path — robust against
# (a) workspace dir not being a git repo, (b) $HOME not matching workspace prefix,
# (c) running from a subdir. The hook lives at <workspace_root>/.dadaia/scripts/,
# so the workspace root is two levels up from the script.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEFAULT_WORKSPACE_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
WORKSPACE_ROOT="${WORKSPACE_ROOT:-$DEFAULT_WORKSPACE_ROOT}"
PYTHON_BIN="${DADAIA_PYTHON:-$WORKSPACE_ROOT/.dadaia/.venv/bin/python}"
if [ ! -x "$PYTHON_BIN" ]; then
    PYTHON_BIN="python3"
fi

TMP_DIR="$WORKSPACE_ROOT/.dadaia/tmp"
mkdir -p "$TMP_DIR"
PAYLOAD_FILE="$(mktemp "$TMP_DIR/ctx-inject-payload.XXXXXX")"
trap 'rm -f "$PAYLOAD_FILE"' EXIT

# ---------------------------------------------------------------------------
# T-R1-01: Write runtime→session pointer file (runs before any early exit).
# When DADAIA_SESSION_ID is set (from eval $(dadaia context bind ...)), write
# a pointer file at .dadaia/sessions/runtime/<session_id>.ptr so that the SDD
# gate can resolve the session without requiring DADAIA_SESSION_ID to be
# manually exported into the agent runtime environment.
# This runs unconditionally early — before the context/specs guard — so the
# ptr file is always registered even if specs are missing.
# Cleanup: `dadaia context release` is the authoritative cleanup path; the
# EXIT trap here handles per-invocation cleanup only.
# ---------------------------------------------------------------------------
if [ -n "${DADAIA_SESSION_ID:-}" ]; then
    _RUNTIME_PTR_DIR="$WORKSPACE_ROOT/.dadaia/sessions/runtime"
    mkdir -p "$_RUNTIME_PTR_DIR" 2>/dev/null || true
    _PTR_FILE="$_RUNTIME_PTR_DIR/${DADAIA_SESSION_ID}.ptr"
    printf '%s' "$DADAIA_SESSION_ID" > "$_PTR_FILE" 2>/dev/null || true
fi

emit_payload() {
    if [ "$DADAIA_HOOK_OUTPUT" = "codex-json" ] || [ "$DADAIA_HOOK_OUTPUT" = "json" ]; then
        "$PYTHON_BIN" - "$PAYLOAD_FILE" <<'PY'
import json
import pathlib
import sys

payload = pathlib.Path(sys.argv[1]).read_text(encoding="utf-8")
print(json.dumps({
    "hookSpecificOutput": {
        "hookEventName": "UserPromptSubmit",
        "additionalContext": payload,
    }
}))
PY
    else
        cat "$PAYLOAD_FILE"
    fi
}

# ---------------------------------------------------------------------------
# Resolve context name and SPECS_DIR (preserve existing logic).
# ---------------------------------------------------------------------------
if [ -n "$DADAIA_CONTEXT" ]; then
    CONTEXT_NAME="$DADAIA_CONTEXT"
    SPECS_DIR="$WORKSPACE_ROOT/repos/$DADAIA_CONTEXT/specs"
    if [ -d "$SPECS_DIR" ]; then
        printf '[%s]\n' "$DADAIA_CONTEXT" >> "$PAYLOAD_FILE"
    else
        printf '[%s] WARNING: specs not found\n' "$DADAIA_CONTEXT" >> "$PAYLOAD_FILE"
        emit_payload
        exit 0
    fi
else
    {
        echo "[context: none] — no context bound."
        echo "  To bind a context: eval \$(.dadaia/.venv/bin/dadaia context bind <name> --mode read)"
        echo "  Then export DADAIA_CONTEXT in the shell that launches your agent runtime."
    } >> "$PAYLOAD_FILE"
    emit_payload
    exit 0
fi

# ---------------------------------------------------------------------------
# Graceful skip: if specs/memory/ does not exist, emit nothing further.
# ---------------------------------------------------------------------------
MEMORY_DIR="$SPECS_DIR/memory"
if [ ! -d "$MEMORY_DIR" ]; then
    emit_payload
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

SENTINEL="$TMP_DIR/ctx-inject-fired-${SESSION_ID}"

if [ -f "$SENTINEL" ]; then
    # Memory block already injected this session — emit only the context name (already done above).
    emit_payload
    exit 0
fi

# Create sentinel before emitting to avoid double-injection on concurrent calls.
touch "$SENTINEL"

# ---------------------------------------------------------------------------
# Emit bounded memory bootstrap block.
# tech-stack.md and product/index.md are read verbatim — no strip pass needed.
# ---------------------------------------------------------------------------

{
    echo ""
    echo "=== workspace memory (tech + catalog) ==="
} >> "$PAYLOAD_FILE"

# Tech stack — read .md verbatim (T-MMS-07: no strip pass needed for markdown)
TECH_FILE="$MEMORY_DIR/tech-stack.md"
if [ -f "$TECH_FILE" ]; then
    cat "$TECH_FILE" >> "$PAYLOAD_FILE"
fi

# Catalog: prefer catalog.json (machine-readable, generated from frontmatter);
# fall back to product/index.md verbatim when catalog.json is absent (T-MMS-07).
CATALOG_JSON="$MEMORY_DIR/product/catalog.json"
PRODUCT_INDEX_MD="$MEMORY_DIR/product/index.md"
if [ -f "$CATALOG_JSON" ]; then
    cat "$CATALOG_JSON" >> "$PAYLOAD_FILE"
elif [ -f "$PRODUCT_INDEX_MD" ]; then
    cat "$PRODUCT_INDEX_MD" >> "$PAYLOAD_FILE"
fi

echo "=== end memory bootstrap ===" >> "$PAYLOAD_FILE"
emit_payload
