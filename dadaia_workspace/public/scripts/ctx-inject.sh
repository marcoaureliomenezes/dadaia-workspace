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
    # Sanitize before using as a filename component — never let a session id with
    # path separators escape the runtime dir (CWE-22; mirrors sdd-spec-gate.sh).
    _SAFE_PTR_ID="$(printf '%s' "$DADAIA_SESSION_ID" | tr -cd 'a-zA-Z0-9_-')"
    if [ -n "$_SAFE_PTR_ID" ]; then
        _PTR_FILE="$_RUNTIME_PTR_DIR/${_SAFE_PTR_ID}.ptr"
        printf '%s' "$DADAIA_SESSION_ID" > "$_PTR_FILE" 2>/dev/null || true
    fi
fi

# Hook event name carried in the JSON envelope. SessionStart (Codex/Claude once-per-
# session) and UserPromptSubmit both inject via additionalContext; default keeps the
# historical UserPromptSubmit value for callers that do not set it.
DADAIA_HOOK_EVENT="${DADAIA_HOOK_EVENT:-UserPromptSubmit}"

emit_payload() {
    if [ "$DADAIA_HOOK_OUTPUT" = "codex-json" ] || [ "$DADAIA_HOOK_OUTPUT" = "json" ]; then
        "$PYTHON_BIN" - "$PAYLOAD_FILE" "$DADAIA_HOOK_EVENT" <<'PY'
import json
import pathlib
import sys

payload = pathlib.Path(sys.argv[1]).read_text(encoding="utf-8")
event = sys.argv[2]
print(json.dumps({
    "hookSpecificOutput": {
        "hookEventName": event,
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
# Context resolution never depends on a manual `context bind`. If DADAIA_CONTEXT
# is not exported, auto-resolve the first ALIVE context from the registry —
# exactly as the SDD gate does. Binding is optional convenience; the flow must
# never stop or nag the operator to rebind.
if [ -z "$DADAIA_CONTEXT" ]; then
    DADAIA_CONTEXT="$("$PYTHON_BIN" - "$WORKSPACE_ROOT" 2>/dev/null <<'PY'
import json
import os
import sys

ws = sys.argv[1]
try:
    data = json.load(open(os.path.join(ws, ".dadaia/states/spec_contexts.json")))
    for c in data.get("contexts", []):
        if str(c.get("state", "")).lower() == "alive":
            print(c.get("repo_slug") or c.get("name") or "")
            break
except Exception:
    pass
PY
)"
fi

if [ -n "$DADAIA_CONTEXT" ]; then
    CONTEXT_NAME="$DADAIA_CONTEXT"
    SPECS_DIR="$WORKSPACE_ROOT/repos/$DADAIA_CONTEXT/specs"
    if [ -d "$SPECS_DIR" ]; then
        printf '[%s]\n' "$DADAIA_CONTEXT" >> "$PAYLOAD_FILE"
    else
        # Context known but specs dir absent — inject nothing further, silently.
        emit_payload
        exit 0
    fi
else
    # No ALIVE context in the workspace at all — nothing to inject. Stay silent:
    # no nag, no halt. (The SDD gate still fail-opens on every write.)
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
# First-message sentinel guard — idempotence keyed on a STABLE session id.
# Resolution order (no PID fallback — $$ changes per shell and breaks idempotence):
#   1. Harness session env vars (Claude Code / Codex / OpenCode).
#   2. Codex passes session_id as a JSON field on stdin at SessionStart; subagents
#      inherit the parent session_id. Parse it when present.
#   3. Degenerate fallback: a single stable per-workspace key so context still
#      injects at most ONCE (never per-shell), never the volatile PID.
# ---------------------------------------------------------------------------
SESSION_ID="${CLAUDE_CODE_SESSION_ID:-${CODEX_SESSION_ID:-${OPENCODE_SESSION_ID:-}}}"
if [ -z "$SESSION_ID" ] && [ ! -t 0 ]; then
    # stdin is not a tty — it may carry the harness hook JSON with a session_id field.
    # Bounded read so a hook invoked without stdin never blocks.
    _STDIN_JSON="$(timeout 0.2 cat 2>/dev/null || true)"
    if [ -n "$_STDIN_JSON" ]; then
        SESSION_ID="$(printf '%s' "$_STDIN_JSON" | "$PYTHON_BIN" -c 'import json,sys
try:
    print(json.load(sys.stdin).get("session_id", "") or "")
except Exception:
    pass' 2>/dev/null)"
    fi
fi
SESSION_ID="${SESSION_ID:-workspace}"
# Sanitize before using as a filename component — a session id containing '/' or
# '..' must never escape $TMP_DIR (CWE-22; mirrors sdd-spec-gate.sh's strip).
SESSION_ID="$(printf '%s' "$SESSION_ID" | tr -cd 'a-zA-Z0-9_-')"
SESSION_ID="${SESSION_ID:-workspace}"

SENTINEL="$TMP_DIR/ctx-inject-fired-${SESSION_ID}"

if [ -f "$SENTINEL" ]; then
    # Context already injected this session. Per-prompt path is SILENT — no memory,
    # no breadcrumb (SessionStart carries context once). Emit nothing, exit 0.
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
