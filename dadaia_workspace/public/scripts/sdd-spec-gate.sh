#!/bin/bash
# sdd-spec-gate.sh — PreToolUse hook for SDD enforcement (v3)
# Works with Claude Code (settings.json) and Codex (.codex/hooks.json)
# v3 adds: release-based TASKS search, ACTIVE.md phase-gated memory atomicity,
#          _archive/ read-only, release-id audit log, SDD_LEGACY_FEATURES env.
# v3.1 adds: path-scope gate (RULE D) — validates write against agent's
#            write_allowlist from frontmatter (AGT-r2-19).
# Blocks Write/Edit/MultiEdit on production paths when no IN PROGRESS task
# exists in a TASKS.md under the active release (primary) or under legacy
# features/* if SDD_LEGACY_FEATURES=1.
# FAIL OPEN: any internal error → allow (never block legitimate edits by crashing).

# SDD_GATE_LOG override allows tests to redirect log to a tmp file.
LOG="${SDD_GATE_LOG:-/tmp/sdd-gate.log}"
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
# v3.2: derive specs_dir from FPATH, not primary_context — fixes cross-repo
# false-positives when primary context is a different repo in a non-CLOSURE phase.
case "$FPATH" in
    */specs/memory/*.html|*/specs/memory/*.md|*/specs/memory/product/*.html|*/specs/memory/product/*.md)
        FILE_SPECS_DIR="$(echo "$FPATH" | sed -E 's|/specs/.*||')/specs"
        FILE_ACTIVE_RELEASE=$(grep -E '^release:' "$FILE_SPECS_DIR/releases/ACTIVE.md" 2>/dev/null | head -1 | sed -E 's/^release:[[:space:]]*//; s/[[:space:]]*$//')
        FILE_ACTIVE_PHASE=$(grep -E '^phase:' "$FILE_SPECS_DIR/releases/ACTIVE.md" 2>/dev/null | head -1 | sed -E 's/^phase:[[:space:]]*//; s/[[:space:]]*$//')
        if [ "$FILE_ACTIVE_PHASE" != "CLOSURE" ]; then
            _block "[SDD GATE] memory/ é atômico. Apenas product-engineer em fase CLOSURE pode editar (release ativa: ${FILE_ACTIVE_RELEASE:-none}, phase: ${FILE_ACTIVE_PHASE:-none}). Para atualizar memory: terminar implementação, marcar todas as tasks [x], setar phase=CLOSURE em releases/ACTIVE.md, e usar a skill dadaia-release-closure."
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

# v3.1 RULE D — Path-scope check (AGT-r2-19).
# Resolve agent persona via layered chain (Option D per ADR §2/§3):
#   1. DADAIA_AGENT_PERSONA  (neutral, lib-defined)
#   2. CLAUDE_AGENT_PERSONA / CODEX_AGENT_PERSONA / OPENCODE_AGENT_PERSONA
#   3. tool_input._meta.agent_persona from stdin payload
#   4. fail-open: allow + log warning
#
# When persona is resolved: read its write_allowlist from frontmatter and
# match against FPATH. Mismatch → block. Match → log + fall through to step 7.
# Missing paths block / unknown agent file → fail-open.
# If FPATH is outside WS → fail-open (edge case: symlinks, /tmp/).

_path_scope_check() {
    local persona="" env_set="unset" payload_set="unset"

    # Priority 1 — neutral env var
    if [ -n "${DADAIA_AGENT_PERSONA:-}" ]; then
        persona="$DADAIA_AGENT_PERSONA"
        env_set="set"
    fi

    # Priority 2 — harness-specific env vars (tried in fixed order)
    if [ -z "$persona" ]; then
        for _var in CLAUDE_AGENT_PERSONA CODEX_AGENT_PERSONA OPENCODE_AGENT_PERSONA; do
            _val="${!_var:-}"
            if [ -n "$_val" ]; then
                persona="$_val"
                env_set="set"
                break
            fi
        done
    fi

    # Priority 3 — JSON payload field tool_input._meta.agent_persona
    if [ -z "$persona" ]; then
        persona=$(python3 - "$TMP" 2>/dev/null <<'PYEOF'
import json, sys
try:
    d = json.load(open(sys.argv[1]))
    ti = d.get("tool_input") or {}
    meta = ti.get("_meta") or {}
    v = meta.get("agent_persona", "")
    print(v if isinstance(v, str) else "")
except Exception:
    print("")
PYEOF
)
        [ -n "$persona" ] && payload_set="set"
    fi

    # Priority 4 — fail-open: persona undetectable
    if [ -z "$persona" ]; then
        _log "FAIL-OPEN path-scope: no agent persona detected (env=${env_set} payload=${payload_set}) tool=${TOOL} path=${FPATH}"
        return  # silent fail-open: fall through to downstream gate steps
    fi

    # Locate agent frontmatter file — prefer public source, fall back to projection
    local agent_file=""
    local public_file="$WS/dadaia_workspace/public/agents/${persona}.md"
    local proj_file="$WS/.claude/agents/${persona}.md"
    if [ -f "$public_file" ]; then
        agent_file="$public_file"
    elif [ -f "$proj_file" ]; then
        agent_file="$proj_file"
    fi

    # Unknown persona (no agent file) → fail-open
    if [ -z "$agent_file" ]; then
        _log "FAIL-OPEN path-scope: agent persona ${persona} not in store (no agent file found)"
        return  # silent fail-open: fall through to downstream gate steps
    fi

    # Parse write_allowlist from frontmatter via Python (one-shot, per-invocation)
    # Returns newline-separated list of glob patterns, or empty on error/missing.
    local raw_allowlist
    raw_allowlist=$(python3 - "$agent_file" 2>/dev/null <<'PYEOF'
import sys
try:
    text = open(sys.argv[1], encoding="utf-8").read()
    # Extract YAML frontmatter between first pair of --- delimiters
    if not text.startswith("---"):
        sys.exit(0)
    end = text.find("\n---", 3)
    if end < 0:
        sys.exit(0)
    fm_text = text[3:end]
    # Minimal YAML parse: find paths.write_allowlist
    try:
        import yaml  # type: ignore[import-untyped]
        fm = yaml.safe_load(fm_text)
    except Exception:
        sys.exit(0)
    if not isinstance(fm, dict):
        sys.exit(0)
    paths = fm.get("paths")
    if not isinstance(paths, dict):
        sys.exit(0)
    wl = paths.get("write_allowlist")
    if not isinstance(wl, list):
        sys.exit(0)
    for g in wl:
        if isinstance(g, str) and g.strip():
            print(g.strip())
except Exception:
    pass
PYEOF
)

    # No paths block (or parse error) → fail-open
    if [ -z "$raw_allowlist" ]; then
        _log "FAIL-OPEN path-scope: agent persona ${persona} has no paths block (or parse error)"
        return  # silent fail-open: fall through to downstream gate steps
    fi

    # Verify FPATH is under WS (edge case: symlinks, /tmp paths)
    case "$FPATH" in
        "$WS/"*) ;;
        *)
            _log "FAIL-OPEN path-scope: target path outside workspace root, persona=${persona} path=${FPATH}"
            return  # silent fail-open: fall through to downstream gate steps
            ;;
    esac

    # Relative path from workspace root (for glob matching)
    local rel_fpath="${FPATH#$WS/}"

    # Substitute <ctx> in allowlist globs with PRIMARY_SLUG (context name).
    # If PRIMARY_SLUG is empty, leave <ctx> as literal (will not match, but
    # fail-open already covers persona-absent case; here persona is known).
    local ctx_val="${PRIMARY_SLUG:-}"

    # Match rel_fpath against each glob in write_allowlist.
    # Glob matching: ** matches any number of path segments; * matches one segment.
    local match_found=0
    local allowlist_rendered=""
    while IFS= read -r raw_glob; do
        # Substitute <ctx>
        local glob="${raw_glob//<ctx>/$ctx_val}"
        [ -n "$allowlist_rendered" ] && allowlist_rendered="${allowlist_rendered}, ${glob}"
        [ -z "$allowlist_rendered" ] && allowlist_rendered="${glob}"
        # Python fnmatch with ** expansion
        local hit
        hit=$(python3 - "$rel_fpath" "$glob" 2>/dev/null <<'PYEOF'
import sys, fnmatch, re
rel = sys.argv[1]
pat = sys.argv[2]
# Convert shell glob with ** to regex for path matching:
# ** matches zero or more path components (any character including /)
# * matches any character except /
def glob_to_regex(p):
    parts = p.split("**")
    def esc(s):
        # escape regex special chars except *
        s = re.escape(s)
        # unescape * back (single-segment wildcard)
        s = s.replace(r"\*", "[^/]*")
        return s
    joined = ".*".join(esc(part) for part in parts)
    return "^" + joined + "$"
try:
    rx = glob_to_regex(pat)
    if re.match(rx, rel):
        print("yes")
    else:
        print("no")
except Exception:
    print("no")
PYEOF
)
        if [ "$hit" = "yes" ]; then
            match_found=1
            break
        fi
    done <<< "$raw_allowlist"

    if [ "$match_found" = "1" ]; then
        _log "allowed — path-scope ok: persona=${persona} path=${FPATH}"
        return  # fall through to step 7
    fi

    # Path-scope mismatch → block
    _block "[PATH SCOPE ERROR] agent ${persona} cannot write to ${FPATH}. write_allowlist: ${allowlist_rendered}."
}

_path_scope_check

# Determine if this is a production path
# Consumer production paths (e.g. /docker/<service>/data/) should be derived from
# workspace config, not hardcoded here. Add them via workspace-local gate overrides.
IS_PROD=0
case "$FPATH" in
    "$WS/services/"*|\
    "$WS/docker/"*|\
    "$WS/scripts/"*)
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
