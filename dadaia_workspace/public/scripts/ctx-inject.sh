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
# Stable session id (rc-4 / ADR-2 — fixes repeated-visible-userpromptsubmit-memory-
# injection). Derive the once-per-session identity from the HARNESS-NATIVE id, with no
# dependency on DADAIA_SESSION_ID (no harness exports it). Resolution order:
#   1. DADAIA_SESSION_ID (explicit operator override), then harness env vars.
#   2. Codex passes session_id as a JSON field on stdin; subagents inherit the parent's.
#   3. Degenerate fallback: a single stable per-workspace key so context still injects at
#      most ONCE (never per-shell / never the volatile PID).
# This MUST be resolved before any emission so the sentinel guards the ENTIRE injection
# (context line + dispatcher preflight + memory) — already-fired prompts emit nothing.
# ---------------------------------------------------------------------------
SESSION_ID="${DADAIA_SESSION_ID:-${CLAUDE_CODE_SESSION_ID:-${CODEX_SESSION_ID:-${OPENCODE_SESSION_ID:-}}}}"
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
# Sanitize before using as a filename component — a session id containing '/' or '..'
# must never escape $TMP_DIR (CWE-22; mirrors sdd-spec-gate.sh's strip).
SESSION_ID="$(printf '%s' "$SESSION_ID" | tr -cd 'a-zA-Z0-9_-')"
SESSION_ID="${SESSION_ID:-workspace}"

# ---------------------------------------------------------------------------
# Runtime session pointer (.ptr). Written from the resolved harness-native session id so
# downstream tooling can resolve the session without DADAIA_SESSION_ID being exported.
# (The single-session lease maintains its own <ctx>.ptr on acquire; this is the
# session-keyed pointer.) Best-effort; never fail the hook.
# ---------------------------------------------------------------------------
if [ "$SESSION_ID" != "workspace" ]; then
    _RUNTIME_PTR_DIR="$WORKSPACE_ROOT/.dadaia/sessions/runtime"
    mkdir -p "$_RUNTIME_PTR_DIR" 2>/dev/null || true
    printf '%s' "$SESSION_ID" > "$_RUNTIME_PTR_DIR/${SESSION_ID}.ptr" 2>/dev/null || true
fi

# ---------------------------------------------------------------------------
# Resolve context name. Never depends on a manual `context bind`: if DADAIA_CONTEXT is
# not exported, auto-resolve the first ALIVE context from the registry. Binding is
# optional convenience; the flow must never stop or nag.
# ---------------------------------------------------------------------------
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

# No ALIVE context at all, or its specs dir is absent → inject nothing, silently.
# (No nag, no halt. The SDD gate still fail-opens on every write.)
if [ -z "$DADAIA_CONTEXT" ]; then
    emit_payload
    exit 0
fi
CONTEXT_NAME="$DADAIA_CONTEXT"
SPECS_DIR="$WORKSPACE_ROOT/repos/$DADAIA_CONTEXT/specs"
if [ ! -d "$SPECS_DIR" ]; then
    emit_payload
    exit 0
fi

# ---------------------------------------------------------------------------
# Once-per-session sentinel — guards the ENTIRE injection. If context was already
# injected this session, emit NOTHING (no context line, no preflight, no memory) so
# the bootstrap never repeats on subsequent prompts (rc-4 / ADR-2).
# ---------------------------------------------------------------------------
SENTINEL="$TMP_DIR/ctx-inject-fired-${SESSION_ID}"
if [ -f "$SENTINEL" ]; then
    exit 0
fi
# Create the sentinel before emitting to avoid double-injection on concurrent calls.
touch "$SENTINEL"

# --- First injection this session: context line + dispatcher preflight ---
printf '[%s]\n' "$DADAIA_CONTEXT" >> "$PAYLOAD_FILE"
{
    echo "=== dispatcher preflight (SDD routing) ==="
    echo "Before acting on a request in this workspace:"
    echo "1. Resolve the active context (above) and the OWNING role for the"
    echo "   artifact class you are about to touch: backlog → project-manager;"
    echo "   SPEC/PLAN/TASKS → product-engineer; hooks/agents/skills/rules/"
    echo "   workflows (the AI surface) → ai-engineer audit; production code →"
    echo "   software-engineer; reviews → code/security/qa reviewers."
    echo "2. Ownership is a COORDINATION CONVENTION, not a gate. No workflow"
    echo "   (research, backlog/release definition, implementation+review,"
    echo "   audits) is ever lock-blocked, and project-manager always spawns"
    echo "   and writes freely. Route changes through the owning role by"
    echo "   discipline. The ONLY deterministic lock is the single-session"
    echo "   lease (one bound session per Spec Context for release-definition"
    echo "   / implementation+review)."
    echo "3. If the operator asks for multi-agent / deep / AI-surface work and a"
    echo "   subagent or dispatch tool is not in your active tool set, DISCOVER it"
    echo "   first (e.g. tool_search for the agent/dispatch tool) BEFORE starting"
    echo "   the main task — do not silently proceed as a generic single agent."
    echo "4. Limitation (truthful): this harness does NOT auto-spawn subagents"
    echo "   from static .codex/.claude workflow files. Workflow files are"
    echo "   reference docs; explicit dispatcher/operator fan-out is required."
    echo "=== end dispatcher preflight ==="
} >> "$PAYLOAD_FILE"

# --- Memory bootstrap (once per session, only when memory/ exists) ---
# tech-stack.md and product/index.md are read verbatim — no strip pass needed.
MEMORY_DIR="$SPECS_DIR/memory"
if [ -d "$MEMORY_DIR" ]; then
    {
        echo ""
        echo "=== workspace memory (tech + catalog) ==="
    } >> "$PAYLOAD_FILE"

    TECH_FILE="$MEMORY_DIR/tech-stack.md"
    if [ -f "$TECH_FILE" ]; then
        cat "$TECH_FILE" >> "$PAYLOAD_FILE"
    fi

    # Catalog: prefer catalog.json (machine-readable, generated from frontmatter);
    # fall back to product/index.md verbatim when catalog.json is absent.
    CATALOG_JSON="$MEMORY_DIR/product/catalog.json"
    PRODUCT_INDEX_MD="$MEMORY_DIR/product/index.md"
    if [ -f "$CATALOG_JSON" ]; then
        cat "$CATALOG_JSON" >> "$PAYLOAD_FILE"
    elif [ -f "$PRODUCT_INDEX_MD" ]; then
        cat "$PRODUCT_INDEX_MD" >> "$PAYLOAD_FILE"
    fi

    echo "=== end memory bootstrap ===" >> "$PAYLOAD_FILE"
fi

emit_payload
exit 0
