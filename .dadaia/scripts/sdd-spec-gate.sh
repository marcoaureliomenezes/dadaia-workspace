#!/bin/bash
# sdd-spec-gate.sh — PreToolUse hook for SDD enforcement (v3)
# Works with Claude Code (settings.json) and Codex (.codex/hooks.json)
# v3 adds: release-based TASKS search, ACTIVE.md phase-gated memory atomicity,
#          _archive/ read-only, release-id audit log, SDD_LEGACY_FEATURES env.
# Blocks Write/Edit/MultiEdit on production paths when no IN PROGRESS task
# exists in a TASKS.md under the active release (primary) or under legacy
# features/* if SDD_LEGACY_FEATURES=1.
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

# Resolve active release id and phase from <PRIMARY_SPECS>/releases/ACTIVE.md
ACTIVE_RELEASE=""
ACTIVE_PHASE=""
if [ -n "$PRIMARY_SPECS" ] && [ -f "$PRIMARY_SPECS/releases/ACTIVE.md" ]; then
    ACTIVE_RELEASE=$(grep -E '^release:' "$PRIMARY_SPECS/releases/ACTIVE.md" 2>/dev/null | head -1 | sed -E 's/^release:[[:space:]]*//; s/[[:space:]]*$//')
    ACTIVE_PHASE=$(grep -E '^phase:' "$PRIMARY_SPECS/releases/ACTIVE.md" 2>/dev/null | head -1 | sed -E 's/^phase:[[:space:]]*//; s/[[:space:]]*$//')
fi
[ -n "$ACTIVE_RELEASE" ] && _log "active_release=$ACTIVE_RELEASE phase=$ACTIVE_PHASE"

# v3 RULE A — Memory atomicity. Block writes to specs/memory/*.html (and *.md
# legacy), plus the product/ subfolder (catalog with index + per-feature HTMLs),
# unless ACTIVE.md phase == CLOSURE. Evaluated BEFORE the meta-edit allow-list
# so it cannot be bypassed by naming the file *.md or by nesting in product/.
case "$FPATH" in
    */specs/memory/*.html|*/specs/memory/*.md|*/specs/memory/product/*.html|*/specs/memory/product/*.md)
        if [ "$ACTIVE_PHASE" != "CLOSURE" ]; then
            _block "[SDD GATE] memory/ é atômico. Apenas product-engineer em fase CLOSURE pode editar (release ativa: ${ACTIVE_RELEASE:-none}, phase: ${ACTIVE_PHASE:-none}). Para atualizar memory: terminar implementação, marcar todas as tasks [x], setar phase=CLOSURE em releases/ACTIVE.md, e usar a skill dadaia-release-closure."
        fi
        _log "allowed — memory edit in CLOSURE phase: $FPATH"
        exit 0
        ;;
esac

# v3 RULE B — Archive is read-only. _archive/ is historical; never written
# directly. Use `git mv` from the release dir into _archive/ instead.
case "$FPATH" in
    */specs/_archive/*)
        _block "[SDD GATE] specs/_archive/ é read-only. Use git mv para mover uma release concluída para o archive — não edite arquivos arquivados diretamente."
        ;;
esac

# Meta-edits to spec/task files are always allowed — they are the very mechanism
# that creates the [-] marker the gate relies on (deadlock prevention).
case "$FPATH" in
    */TASKS.md|*/PLAN.md|*/SPEC.md|*/CLOSURE.md|*/ACTIVE.md|*/backlog/*.md)
        _log "allowed — meta-edit on spec file: $FPATH"
        exit 0
        ;;
esac

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

# v3 RULE C — Find [-] task. Priority order:
#   1. PRIMARY_SPECS/releases/<active-release>/TASKS.md
#   2. Any PRIMARY_SPECS/releases/*/TASKS.md
#   3. (legacy compat) PRIMARY_SPECS/features/*/TASKS.md or root TASKS.md
#      only when SDD_LEGACY_FEATURES=1 (default during migration window)
ACTIVE=""
GREP_PAT='^[[:space:]]*-[[:space:]]*\[-\][[:space:]]+'

if [ -n "$ACTIVE_RELEASE" ] && [ -f "$PRIMARY_SPECS/releases/$ACTIVE_RELEASE/TASKS.md" ]; then
    if grep -qE "$GREP_PAT" "$PRIMARY_SPECS/releases/$ACTIVE_RELEASE/TASKS.md" 2>/dev/null; then
        ACTIVE="$PRIMARY_SPECS/releases/$ACTIVE_RELEASE/TASKS.md"
    fi
fi

if [ -z "$ACTIVE" ] && [ -d "$PRIMARY_SPECS/releases" ]; then
    ACTIVE=$(grep -rlE "$GREP_PAT" "$PRIMARY_SPECS/releases" --include="TASKS.md" 2>/dev/null | head -1)
fi

if [ -z "$ACTIVE" ] && [ "${SDD_LEGACY_FEATURES:-1}" = "1" ]; then
    # Search outside releases/ for legacy compat: features/*/TASKS.md and root TASKS.md
    ACTIVE=$(grep -rlE "$GREP_PAT" "$PRIMARY_SPECS" --include="TASKS.md" 2>/dev/null \
        | grep -v "/_archive/" \
        | grep -v "/releases/" \
        | head -1)
fi

if [ -n "$ACTIVE" ]; then
    _log "allowed — active task in: $ACTIVE (release=${ACTIVE_RELEASE:-none})"
    exit 0
fi

_block "[SDD GATE] Nenhuma task IN PROGRESS (marker [-]) em $PRIMARY_SPECS/releases/${ACTIVE_RELEASE:-<no-active-release>}/TASKS.md. Antes de editar $FPATH, marque a task alvo de '[ ]' para '[-]' e commit (skill: dadaia-task-manager). Janela de migração: exporte SDD_LEGACY_FEATURES=1 para reaproveitar specs/features/*/TASKS.md."
