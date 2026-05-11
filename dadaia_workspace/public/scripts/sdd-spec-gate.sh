#!/bin/bash
# sdd-spec-gate.sh — PreToolUse hook for SDD enforcement
# Works with Claude Code (settings.json) and Codex (.codex/hooks.json)
# Blocks Write/Edit/MultiEdit on production files when no approved SPEC.md exists.
# FAIL OPEN: any internal error → allow (never block legitimate edits by crashing).

LOG="/tmp/sdd-gate.log"
WS="${WORKSPACE_ROOT:-/home/ubuntu/workspace}"

_log() { printf '[%s] sdd-gate: %s\n' "$(date -Iseconds)" "$*" >> "$LOG" 2>/dev/null; }
_block() { _log "BLOCKED: $*"; printf '{"decision":"block","reason":"%s"}' "$1"; exit 0; }

# Read hook input from stdin into a temp file (safe for special chars and concurrent runs)
TMP=$(mktemp /tmp/sdd-gate-XXXXXX.json 2>/dev/null) || exit 0
trap 'rm -f "$TMP"' EXIT
cat > "$TMP" 2>/dev/null
[ ! -s "$TMP" ] && exit 0

# Parse tool name — handle both Claude Code and Codex JSON formats
TOOL=$(python3 - "$TMP" 2>/dev/null <<'EOF'
import json, sys
try:
    d = json.load(open(sys.argv[1]))
    print(d.get("tool_name") or d.get("tool") or "")
except Exception:
    print("")
EOF
)

case "$TOOL" in
    Write|write_file|Edit|edit_file|MultiEdit|apply_patch) ;;
    *) exit 0 ;;
esac

# Parse file path from tool input
FPATH=$(python3 - "$TMP" 2>/dev/null <<'EOF'
import json, sys
try:
    d = json.load(open(sys.argv[1]))
    i = d.get("tool_input") or d
    print(i.get("file_path") or i.get("path") or "")
except Exception:
    print("")
EOF
)

[ -z "$FPATH" ] && exit 0
[[ "$FPATH" != /* ]] && FPATH="$WS/$FPATH"
_log "tool=$TOOL path=$FPATH"

# Check if this is a production file (must match sdd-enforcement.md list)
case "$FPATH" in
    "$WS/services/"*|\
    "$WS/docker/hermes/"*|\
    "$WS/docker/openclaw/"*|\
    "$WS/scripts/"*|\
    "/docker/hermes-agent-wqps/data/"*|\
    "/docker/openclaw-x44i/data/"*)
        ;;
    *)
        exit 0 ;;
esac

# Production file detected — resolve active specs_dir
if [ -n "${DADAIA_CONTEXT:-}" ]; then
    SPECS="$WS/repos/$DADAIA_CONTEXT/specs"
else
    SPECS=$(python3 - 2>/dev/null <<EOF
import json
try:
    print(json.load(open("$WS/.dadaia/states/primary_context.json")).get("specs_dir", ""))
except Exception:
    print("")
EOF
)
fi

if [ -z "$SPECS" ] || [ ! -d "$SPECS" ]; then
    _block "[SDD GATE] Nenhum Spec Context ativo. Execute: dadaia context activate <nome> antes de editar arquivos de producao."
fi

# Search for any SPEC.md with approved status
APPROVED=$(grep -rle "Status.*Aprovado" "$SPECS" --include="SPEC.md" 2>/dev/null | head -1)

if [ -n "$APPROVED" ]; then
    _log "allowed — approved spec: $APPROVED"
    exit 0
fi

_block "[SDD GATE] Nenhum SPEC.md aprovado em $SPECS. Pipeline obrigatorio: SPEC.md [Aprovado] -> PLAN.md [Aprovado] -> TASKS.md [Aprovado] -> implementacao."
