#!/bin/bash
# sdd-spec-gate.sh — PreToolUse hook for SDD enforcement (v2)
# Works with Claude Code (settings.json) and Codex (.codex/hooks.json)
# Blocks Write/Edit/MultiEdit on production paths when no IN PROGRESS task
# exists in TASKS.md. v2 adds primary_slug-based scope and `[-]` granularity.
# FAIL OPEN: any internal error → allow (never block legitimate edits by crashing).

LOG="/tmp/sdd-gate.log"
# Resolve workspace_root via the script's own absolute path — robust against
# the hook running from any cwd. Script lives at <workspace_root>/.dadaia/scripts/.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEFAULT_WS="$(cd "$SCRIPT_DIR/../.." && pwd)"
WS="${WORKSPACE_ROOT:-$DEFAULT_WS}"

_log() { printf '[%s] sdd-gate: %s\n' "$(date -Iseconds)" "$*" >> "$LOG" 2>/dev/null; }
_block() { _log "BLOCKED: $*"; printf '{"decision":"block","reason":"%s"}' "$1"; exit 0; }

# Read hook input from stdin
TMP=$(mktemp /tmp/sdd-gate-XXXXXX.json 2>/dev/null) || exit 0
trap 'rm -f "$TMP"' EXIT
cat > "$TMP" 2>/dev/null
[ ! -s "$TMP" ] && exit 0

# Parse tool name
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

# Meta-edits to spec/task files are always allowed — they are the very mechanism
# that creates the [-] marker the gate relies on (deadlock prevention).
case "$FPATH" in
    */TASKS.md|*/PLAN.md|*/SPEC.md|*/z_bug_specs.md)
        _log "allowed — meta-edit on spec file: $FPATH"
        exit 0
        ;;
esac

# Resolve primary slug + specs_dir from primary_context.json (best effort)
PRIMARY_SLUG=$(python3 - 2>/dev/null <<EOF
import json
try:
    print(json.load(open("$WS/.dadaia/states/primary_context.json")).get("repo_slug", ""))
except Exception:
    print("")
EOF
)
PRIMARY_SPECS=$(python3 - 2>/dev/null <<EOF
import json
try:
    print(json.load(open("$WS/.dadaia/states/primary_context.json")).get("specs_dir", ""))
except Exception:
    print("")
EOF
)

# Legacy DADAIA_CONTEXT override
if [ -n "${DADAIA_CONTEXT:-}" ]; then
    PRIMARY_SLUG="$DADAIA_CONTEXT"
    PRIMARY_SPECS="$WS/repos/$DADAIA_CONTEXT/specs"
fi

# Determine if this is a production path
IS_PROD=0
case "$FPATH" in
    "$WS/services/"*|\
    "$WS/docker/hermes/"*|\
    "$WS/docker/openclaw/"*|\
    "$WS/scripts/"*|\
    "/docker/hermes-agent-wqps/data/"*|\
    "/docker/openclaw-x44i/data/"*)
        IS_PROD=1
        ;;
esac

# v2: also gate repos/<primary_slug>/* when primary is known
if [ "$IS_PROD" = "0" ] && [ -n "$PRIMARY_SLUG" ]; then
    case "$FPATH" in
        "$WS/repos/$PRIMARY_SLUG/"*) IS_PROD=1 ;;
    esac
fi

# Not a production path → fail-open (pass silently)
[ "$IS_PROD" = "0" ] && exit 0

# Production path with no resolvable specs_dir → block with orientation
if [ -z "$PRIMARY_SPECS" ] || [ ! -d "$PRIMARY_SPECS" ]; then
    _block "[SDD GATE] Nenhum Spec Context ativo (primary). Execute: dadaia context activate <nome> antes de editar arquivos de producao em $FPATH."
fi

# v2 granularity: search for any task line marked [-] in TASKS.md(s)
ACTIVE=$(grep -rlE '^[[:space:]]*-[[:space:]]*\[-\][[:space:]]+' "$PRIMARY_SPECS" --include="TASKS.md" 2>/dev/null | head -1)

if [ -n "$ACTIVE" ]; then
    _log "allowed — active task in: $ACTIVE"
    exit 0
fi

_block "[SDD GATE] Nenhuma task IN PROGRESS (marker [-]) em $PRIMARY_SPECS/TASKS.md. Antes de editar $FPATH, marque a task alvo de '[ ]' para '[-]' e commit (skill: dadaia-task-manager)."
