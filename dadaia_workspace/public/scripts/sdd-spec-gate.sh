#!/bin/bash
# sdd-spec-gate.sh — PreToolUse hook for SDD enforcement (v3)
# Works with Claude Code (settings.json) and Codex (.codex/hooks.json)
# v3 adds: release-based TASKS search, ACTIVE.md phase-gated memory atomicity,
#          _archive/ read-only, release-id audit log, SDD_LEGACY_FEATURES env.
# v3.1 adds: path-scope gate (RULE D) — validates write against agent's
#            write_allowlist from frontmatter (AGT-r2-19).
# Blocks Write/Edit/MultiEdit/apply_patch on production paths unless a bound
# implementation session owns the active release lock and a TASKS.md marker is
# IN PROGRESS. Write-like tool calls with unparseable target paths fail closed.

# SDD_GATE_LOG override allows tests to redirect log to a tmp file.
LOG="${SDD_GATE_LOG:-/tmp/sdd-gate.log}"
# Resolve workspace_root via the script's own absolute path — robust against
# the hook running from any cwd. Script lives at <workspace_root>/.dadaia/scripts/.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEFAULT_WS="$(cd "$SCRIPT_DIR/../.." && pwd)"
WS="${WORKSPACE_ROOT:-$DEFAULT_WS}"
PYTHON_BIN="${DADAIA_PYTHON:-$WS/.dadaia/.venv/bin/python}"
if [ ! -x "$PYTHON_BIN" ]; then
    PYTHON_BIN="${PYTHON:-python3}"
fi

_log() { printf '[%s] sdd-gate: %s\n' "$(date -Iseconds)" "$*" >> "$LOG" 2>/dev/null; }
_block() { _log "BLOCKED: $*"; printf '{"decision":"block","reason":"%s"}' "$1"; exit 0; }

# Read hook input from stdin
TMP=$(mktemp /tmp/sdd-gate-XXXXXX.json 2>/dev/null) || exit 0
trap 'rm -f "$TMP"' EXIT
cat > "$TMP" 2>/dev/null
[ ! -s "$TMP" ] && exit 0

# Parse tool name
TOOL=$("$PYTHON_BIN" - "$TMP" 2>/dev/null <<'EOF'
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

# Parse file path from tool input. Codex apply_patch sends the patch as
# tool_input.command, so extract touched files from patch headers too.
FPATH=$("$PYTHON_BIN" - "$TMP" 2>/dev/null <<'EOF'
import json, sys
try:
    d = json.load(open(sys.argv[1]))
    i = d.get("tool_input") or d
    direct = i.get("file_path") or i.get("path") or ""
    if direct:
        print(direct)
        sys.exit(0)
    command = i.get("command") or ""
    if not isinstance(command, str):
        print("")
        sys.exit(0)
    for line in command.splitlines():
        for prefix in ("*** Update File: ", "*** Add File: ", "*** Delete File: "):
            if line.startswith(prefix):
                print(line[len(prefix):].strip())
                sys.exit(0)
    print("")
except Exception:
    print("")
EOF
)

if [ -z "$FPATH" ]; then
    _block "[SDD GATE] Write-like tool '${TOOL}' did not provide a parseable target path. Blocking to avoid bypassing SDD enforcement."
fi
[[ "$FPATH" != /* ]] && FPATH="$WS/$FPATH"
_log "tool=$TOOL path=$FPATH"

# Resolve context slug + specs_dir via 4-step chain (T-HARD-01):
#   Step 1 — DADAIA_CONTEXT env var (highest priority)
#   Step 2 — spec_contexts.json: first ALIVE entry (v2 schema; no global context flag)
#   Step 3 — session file: DADAIA_SESSION_ID.json → context field
#   Step 4 — fail-open (last resort; logs a meaningful warning)
CONTEXT_SLUG=""
CONTEXT_SPECS=""

# Step 1 — DADAIA_CONTEXT env var
if [ -n "${DADAIA_CONTEXT:-}" ]; then
    CONTEXT_SLUG="$DADAIA_CONTEXT"
    CONTEXT_SPECS="$WS/repos/$DADAIA_CONTEXT/specs"
    _log "context-resolution step1 (DADAIA_CONTEXT): slug=$CONTEXT_SLUG specs=$CONTEXT_SPECS"
fi

# Step 2 — spec_contexts.json: first ALIVE entry
if [ -z "$CONTEXT_SLUG" ]; then
    _CTX_RESULT=$("$PYTHON_BIN" - "$WS/.dadaia/states/spec_contexts.json" 2>/dev/null <<'PYEOF'
import json, sys
try:
    data = json.load(open(sys.argv[1]))
    for ctx in data.get("contexts", []):
        if ctx.get("state", "").lower() == "alive":
            print(ctx.get("repo_slug", "") + "|" + ctx.get("name", ""))
            break
except Exception:
    pass
PYEOF
)
    if [ -n "$_CTX_RESULT" ]; then
        CONTEXT_SLUG="${_CTX_RESULT%%|*}"
        _CTX_NAME="${_CTX_RESULT##*|}"
        CONTEXT_SPECS="$WS/repos/$CONTEXT_SLUG/specs"
        _log "context-resolution step2 (spec_contexts.json ALIVE): name=$_CTX_NAME slug=$CONTEXT_SLUG specs=$CONTEXT_SPECS"
    fi
fi

# Step 3 — session file: DADAIA_SESSION_ID -> context field
if [ -z "$CONTEXT_SLUG" ] && [ -n "${DADAIA_SESSION_ID:-}" ]; then
    _SESS_CTX=$("$PYTHON_BIN" - "$WS/.dadaia/sessions/${DADAIA_SESSION_ID}.json" 2>/dev/null <<'PYEOF'
import json, sys
try:
    print(json.load(open(sys.argv[1])).get("context", ""))
except Exception:
    pass
PYEOF
)
    if [ -n "$_SESS_CTX" ]; then
        CONTEXT_SLUG="$_SESS_CTX"
        CONTEXT_SPECS="$WS/repos/$_SESS_CTX/specs"
        _log "context-resolution step3 (session file $DADAIA_SESSION_ID): slug=$CONTEXT_SLUG specs=$CONTEXT_SPECS"
    fi
fi

# Step 4 — fail-open: log a meaningful warning but do not block
if [ -z "$CONTEXT_SLUG" ]; then
    _log "WARN context-resolution: could not resolve bound context (DADAIA_CONTEXT unset, spec_contexts.json absent/empty, no session); gate will fail-open on IS_PROD check"
fi

# T-R1-04: Sanitize CONTEXT_SLUG before any path construction (CWE-22).
# Strip all characters except alphanumerics, hyphens, and underscores.
# This prevents path traversal (e.g. "../../etc") injected via DADAIA_CONTEXT env var.
if [ -n "$CONTEXT_SLUG" ]; then
    CONTEXT_SLUG=$(printf '%s' "$CONTEXT_SLUG" | tr -cd 'a-zA-Z0-9_-')
fi

# Resolve active release id, segment, and phase from <CONTEXT_SPECS>/releases/ACTIVE.md
# Schema v2 (ADR-1/ADR-5): an optional `segment:` line (alpha-N/rc-N) selects the
# active segment's TASKS.md. Absent/`none` segment → flat release (back-compat).
ACTIVE_RELEASE=""
ACTIVE_SEGMENT=""
ACTIVE_PHASE=""
if [ -n "$CONTEXT_SPECS" ] && [ -f "$CONTEXT_SPECS/releases/ACTIVE.md" ]; then
    ACTIVE_RELEASE=$(grep -E '^release:' "$CONTEXT_SPECS/releases/ACTIVE.md" 2>/dev/null | head -1 | sed -E 's/^release:[[:space:]]*//; s/[[:space:]]*$//')
    ACTIVE_SEGMENT=$(grep -E '^segment:' "$CONTEXT_SPECS/releases/ACTIVE.md" 2>/dev/null | head -1 | sed -E 's/^segment:[[:space:]]*//; s/[[:space:]]*$//')
    ACTIVE_PHASE=$(grep -E '^phase:' "$CONTEXT_SPECS/releases/ACTIVE.md" 2>/dev/null | head -1 | sed -E 's/^phase:[[:space:]]*//; s/[[:space:]]*$//')
fi
[ "$ACTIVE_SEGMENT" = "none" ] && ACTIVE_SEGMENT=""
# Relative release path: <release>/<segment> when a segment is active, else <release>.
ACTIVE_REL_PATH="$ACTIVE_RELEASE"
[ -n "$ACTIVE_SEGMENT" ] && ACTIVE_REL_PATH="$ACTIVE_RELEASE/$ACTIVE_SEGMENT"
[ -n "$ACTIVE_RELEASE" ] && _log "active_release=$ACTIVE_RELEASE segment=${ACTIVE_SEGMENT:-<none>} phase=$ACTIVE_PHASE rel_path=$ACTIVE_REL_PATH"

# v3 RULE A — Memory atomicity. Markdown is the sole editable memory source.
# Legacy specs/memory/*.html and YAML atoms are always read-only. Markdown atoms
# are write-locked unless ACTIVE.md phase == CLOSURE. Evaluated BEFORE the
# meta-edit allow-list so it cannot be bypassed by nesting in product/.
# v3.2: derive specs_dir from FPATH to avoid cross-repo false positives when
# the bound context is a different repo in a non-CLOSURE phase.
case "$FPATH" in
    */specs/memory/*.html|*/specs/memory/*.yaml|*/specs/memory/*.yml|\
    */specs/memory/product/*.html|*/specs/memory/product/*.yaml|*/specs/memory/product/*.yml)
        _block "[SDD GATE] memory/ usa Markdown como fonte única. Arquivos .html/.yaml/.yml em specs/memory/ são legado read-only; escreva apenas atoms .md durante CLOSURE."
        ;;
    */specs/memory/*.md|*/specs/memory/product/*.md)
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
#
# R-9 EXCEPTION (T-13): when DADAIA_SESSION_ID is SET, the release-tree spec files
# SPEC.md, PLAN.md, and TASKS.md must NOT short-circuit here. RULE E (below) applies
# the path-policy matrix: SPEC/READ/BOUND_REVIEW → BLOCK; IMPLEMENTATION owns lock →
# TASKS.md allowed (flips [-] markers), SPEC.md/PLAN.md still BLOCK (read-only once
# impl starts). CLOSURE.md, ACTIVE.md, and backlog/*.md are NOT R-9 targets — they
# keep the always-allow short-circuit regardless of session state.
# When DADAIA_SESSION_ID is UNSET (no session / legacy / fail-open) → keep the
# existing always-allow for ALL paths to preserve RULE A-D tests + product-engineer
# authoring behavior.
case "$FPATH" in
    */TASKS.md|*/PLAN.md|*/SPEC.md|*/CLOSURE.md|*/ACTIVE.md|*/backlog/*.md)
        if [ -n "${DADAIA_SESSION_ID:-}" ]; then
            case "$FPATH" in
                */SPEC.md|*/PLAN.md|*/TASKS.md)
                    # Session bound: defer to RULE E for R-9 enforcement.
                    _log "meta-edit deferred to RULE E (session bound, R-9): $FPATH"
                    ;; # fall through — do NOT exit 0 here
                *)
                    # CLOSURE.md / ACTIVE.md / backlog/*.md — not R-9 targets; always allow.
                    _log "allowed — meta-edit on spec file (session-safe): $FPATH"
                    exit 0
                    ;;
            esac
        else
            # No session (legacy / fail-open): always allow meta-edits (deadlock prevention).
            _log "allowed — meta-edit on spec file (no session / legacy): $FPATH"
            exit 0
        fi
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

    # R-9 guard: when a session is bound AND the target is a release-tree spec file
    # (SPEC.md / PLAN.md / TASKS.md inside specs/releases/<id>/), RULE E is the
    # authoritative gate. Skip RULE D so it cannot block paths that RULE E must govern.
    if [ -n "${DADAIA_SESSION_ID:-}" ]; then
        case "$FPATH" in
            */specs/releases/*/SPEC.md|*/specs/releases/*/PLAN.md|*/specs/releases/*/TASKS.md)
                _log "RULE-D SKIP: release-tree spec file deferred to RULE E (session bound): $FPATH"
                return  # fall through to IS_PROD + RULE E
                ;;
        esac
    fi

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
        persona=$("$PYTHON_BIN" - "$TMP" 2>/dev/null <<'PYEOF'
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
    raw_allowlist=$("$PYTHON_BIN" - "$agent_file" 2>/dev/null <<'PYEOF'
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

    # Substitute <ctx> in allowlist globs with CONTEXT_SLUG (context name).
    # If CONTEXT_SLUG is empty, leave <ctx> as literal (will not match, but
    # fail-open already covers persona-absent case; here persona is known).
    local ctx_val="${CONTEXT_SLUG:-}"

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
        hit=$("$PYTHON_BIN" - "$rel_fpath" "$glob" 2>/dev/null <<'PYEOF'
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

# RULE F — tmp path fast-allow (T-HARD-05)
# Writes whose target is under .dadaia/tmp/ are always allowed without further
# gate checks. This makes the tmp-file-guardrail rule deterministic in addition
# to its prose form. Placed before IS_PROD so tmp writes are never gated.
case "$FPATH" in
    "$WS/.dadaia/tmp/"*)
        _log "allowed — tmp path fast-allow (RULE F): $FPATH"
        exit 0
        ;;
esac

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
if [ "$IS_PROD" = "0" ] && [ -n "$CONTEXT_SLUG" ]; then
    case "$FPATH" in
        "$WS/repos/$CONTEXT_SLUG/"*) IS_PROD=1 ;;
    esac
fi

# Not a production path → fail-open (pass silently)
[ "$IS_PROD" = "0" ] && exit 0

# ---------------------------------------------------------------------------
# RULE E — Session and lock enforcement (T-13)
#
# Session identity resolution order (SPEC §6):
#   1. DADAIA_SESSION_ID env var — set by eval $(dadaia context bind ...).
#      This is the primary stable key, portable across Claude Code / Codex /
#      OpenCode. The hook reads this first.
#   2. Fail-closed for production paths — if DADAIA_SESSION_ID is absent,
#      production writes are blocked. Temporary paths are allowed by RULE F.
#
# The native runtime session_id (e.g. from Claude Code's hook stdin payload)
# is runtime-specific and NOT portable; it is used for correlation logging
# only, not as the primary key.
# ---------------------------------------------------------------------------
_rule_e() {
    # Step 1 — Resolve DADAIA_SESSION_ID
    local sess_id="${DADAIA_SESSION_ID:-}"

    # Step 1b (T-R1-01) — Runtime→session pointer file resolution.
    # ctx-inject.sh writes .dadaia/sessions/runtime/<session_id>.ptr at session
    # start (when DADAIA_SESSION_ID is set in the bind shell). The agent runtime
    # process inherits DADAIA_SESSION_ID from the bind shell through the ptr file
    # rather than requiring the env var to be re-exported into every spawned
    # subprocess. Resolution: scan .dadaia/sessions/runtime/*.ptr; if exactly one
    # fresh ptr file exists, adopt its session_id. Multiple ptr files (concurrent
    # sessions) are not adopted — require env var or lock fallback.
    # When the env var IS set, it always wins (Step 1 above).
    if [ -z "$sess_id" ]; then
        local _runtime_dir="$WS/.dadaia/sessions/runtime"
        if [ -d "$_runtime_dir" ]; then
            local _ptr_count=0
            local _ptr_sess=""
            local _pf
            for _pf in "$_runtime_dir"/*.ptr; do
                [ -f "$_pf" ] || continue
                local _candidate
                _candidate=$(cat "$_pf" 2>/dev/null)
                [ -n "$_candidate" ] || continue
                # Verify the session file exists and is non-stale
                local _sf="$WS/.dadaia/sessions/${_candidate}.json"
                if [ -f "$_sf" ]; then
                    local _stale
                    _stale=$("$PYTHON_BIN" - "$_sf" 2>/dev/null <<'PYEOF'
import json, sys
from datetime import datetime, timezone
try:
    d = json.load(open(sys.argv[1]))
    ttl = int(d.get("ttl_seconds", 300))
    ls = d.get("last_seen_at", "")
    if not ls:
        print("ok"); sys.exit(0)
    elapsed = (datetime.now(tz=timezone.utc) - datetime.fromisoformat(ls.replace("Z", "+00:00"))).total_seconds()
    print("stale" if elapsed > ttl else "ok")
except Exception:
    print("ok")
PYEOF
)
                    if [ "$_stale" = "ok" ]; then
                        _ptr_count=$(( _ptr_count + 1 ))
                        _ptr_sess="$_candidate"
                    fi
                fi
            done
            if [ "$_ptr_count" -eq 1 ] && [ -n "$_ptr_sess" ]; then
                sess_id="$_ptr_sess"
                export DADAIA_SESSION_ID="$sess_id"
                _log "RULE-E ptr-file: adopted session '$sess_id' from runtime ptr file (DADAIA_SESSION_ID was unset)"
            elif [ "$_ptr_count" -gt 1 ]; then
                _log "RULE-E ptr-file: multiple ($_ptr_count) active ptr files; cannot auto-adopt — require DADAIA_SESSION_ID env var"
            fi
        fi
    fi

    # Step 1c (T-SEMA-01 / FEAT-SESSION-SEMAPHORE-01 root cause #1) —
    # Lock-file env-free session resolution (fallback when ptr file not available).
    # A running agent runtime cannot inject DADAIA_SESSION_ID into its own (parent)
    # environment, so requiring it from env alone fails closed whenever the runtime
    # was not launched with the export — a stop-the-flow defect with no in-session
    # recovery. Fallback: when the env var is absent and no ptr file resolved,
    # adopt the session that already owns a NON-STALE implementation lock for the
    # resolved context. The lock file records session_id, so `dadaia context bind`
    # from ANY shell (including an in-session `! dadaia context bind ...`) unblocks
    # writes — no relaunch. A stale lock is never adopted.
    if [ -z "$sess_id" ] && [ -n "$CONTEXT_SLUG" ] && [ -n "$ACTIVE_RELEASE" ]; then
        local _semaf_lockdir="$WS/.dadaia/locks/implementation"
        if [ -d "$_semaf_lockdir" ]; then
            local _semaf_lf
            # T-R1-04: narrow the lock lookup to the ACTIVE release only. The old
            # glob ${CONTEXT_SLUG}__*.json adopted ANY release's lock for this
            # context — non-deterministic when two releases held locks at once.
            # Match the active release exactly so env-free adoption is stable and
            # a lock for a different (e.g. older) release is never adopted.
            for _semaf_lf in "$_semaf_lockdir/${CONTEXT_SLUG}__${ACTIVE_RELEASE}.json"; do
                [ -f "$_semaf_lf" ] || continue
                local _semaf_state
                _semaf_state=$("$PYTHON_BIN" - "$_semaf_lf" 2>/dev/null <<'PYEOF'
import json, sys
from datetime import datetime, timezone
try:
    d = json.load(open(sys.argv[1]))
    ttl = int(d.get("ttl_seconds", 300))
    ls = d.get("last_seen_at", "")
    if not ls:
        print("held"); sys.exit(0)
    elapsed = (datetime.now(tz=timezone.utc) - datetime.fromisoformat(ls.replace("Z", "+00:00"))).total_seconds()
    print("stale" if elapsed > ttl else "held")
except Exception:
    print("held")
PYEOF
)
                if [ "$_semaf_state" = "held" ]; then
                    sess_id=$("$PYTHON_BIN" - "$_semaf_lf" 2>/dev/null <<'PYEOF'
import json, sys
try:
    print(json.load(open(sys.argv[1])).get("session_id", ""))
except Exception:
    print("")
PYEOF
)
                    if [ -n "$sess_id" ]; then
                        export DADAIA_SESSION_ID="$sess_id"
                        _log "RULE-E env-free: adopted session '$sess_id' from non-stale lock $_semaf_lf (DADAIA_SESSION_ID was unset)"
                        break
                    fi
                fi
            done
        fi
    fi

    if [ -z "$sess_id" ]; then
        _block "[RULE E] No active implementation session for context '${CONTEXT_SLUG:-<ctx>}'. Bind it from ANY shell — no relaunch needed: eval \$(dadaia context bind ${CONTEXT_SLUG:-<ctx>} --mode implementation --release ${ACTIVE_RELEASE:-<release-id>}). (DADAIA_SESSION_ID was unset and no non-stale implementation lock was found.)"
        return
    fi

    # Step 2 — Load session file
    local sess_file="$WS/.dadaia/sessions/${sess_id}.json"
    if [ ! -f "$sess_file" ]; then
        _block "[RULE E] Session file missing for session '${sess_id}'. Run: eval \$(dadaia context bind ...) to create a new session."
        return  # unreachable; _block calls exit
    fi

    # Step 3 — Staleness check: last_seen_at + ttl_seconds < now → BLOCK
    local is_stale
    is_stale=$("$PYTHON_BIN" - "$sess_file" 2>/dev/null <<'PYEOF'
import json, sys
from datetime import datetime, timezone
try:
    data = json.load(open(sys.argv[1]))
    last_seen_raw = data.get("last_seen_at", "")
    ttl = int(data.get("ttl_seconds", 300))
    if not last_seen_raw:
        print("ok")
        sys.exit(0)
    last_seen = datetime.fromisoformat(last_seen_raw.replace("Z", "+00:00"))
    now = datetime.now(tz=timezone.utc)
    elapsed = (now - last_seen).total_seconds()
    print("stale" if elapsed > ttl else "ok")
except Exception:
    print("ok")  # fail-open on parse error
PYEOF
)
    if [ "$is_stale" = "stale" ]; then
        _block "[RULE E] Session '${sess_id}' is STALE (TTL exceeded). Re-bind: eval \$(dadaia context bind ...) to start a new session."
        return
    fi

    # Read session mode, context, release from session file
    local sess_mode sess_context sess_release
    sess_mode=$("$PYTHON_BIN" - "$sess_file" 2>/dev/null <<'PYEOF'
import json, sys
try:
    print(json.load(open(sys.argv[1])).get("mode", ""))
except Exception:
    print("")
PYEOF
)
    sess_context=$("$PYTHON_BIN" - "$sess_file" 2>/dev/null <<'PYEOF'
import json, sys
try:
    print(json.load(open(sys.argv[1])).get("context", ""))
except Exception:
    print("")
PYEOF
)
    sess_release=$("$PYTHON_BIN" - "$sess_file" 2>/dev/null <<'PYEOF'
import json, sys
try:
    print(json.load(open(sys.argv[1])).get("release", "") or "")
except Exception:
    print("")
PYEOF
)
    _log "RULE-E: sess_id=$sess_id mode=$sess_mode context=$sess_context release=$sess_release path=$FPATH"

    # Relative path from workspace root for pattern matching
    local rel_fpath="${FPATH#$WS/}"

    # Step 4a — .dadaia/reports/** or .dadaia/tmp/** → ALWAYS ALLOW
    case "$rel_fpath" in
        .dadaia/reports/*|.dadaia/tmp/*)
            _log "RULE-E ALLOW: reports/tmp path always allowed for sess=$sess_id"
            exit 0
            ;;
    esac

    # Step 4b — specs/memory/** → REQUIRE mode ≥ SPEC
    # READ mode → BLOCK; BOUND_REVIEW mode → BLOCK; SPEC/IMPLEMENTATION → allowed
    case "$rel_fpath" in
        */specs/memory/*)
            if [ "$sess_mode" = "READ" ] || [ "$sess_mode" = "BOUND_REVIEW" ]; then
                _block "[RULE E] Session '${sess_id}' (mode=${sess_mode}) cannot write to specs/memory/. Requires SPEC or IMPLEMENTATION mode."
            fi
            _log "RULE-E ALLOW: specs/memory write allowed for mode=$sess_mode"
            exit 0
            ;;
    esac

    # Step 4d — R-9: releases/<id>/SPEC.md, PLAN.md, or TASKS.md when impl lock HELD for <id>.
    # Path-policy matrix (SPEC §3 T-13, lines 579-588):
    #   SPEC mode:              SPEC.md/PLAN.md/TASKS.md → BLOCK
    #   BOUND_IMPLEMENTATION (owns lock): SPEC.md/PLAN.md → BLOCK; TASKS.md → ALLOW
    #   READ / BOUND_REVIEW:    all → BLOCK
    #   No lock held:           fall through to step 4c / RULE C
    local rel_id_from_path="" rel_file_type=""
    local _match_result
    _match_result=$("$PYTHON_BIN" - "$rel_fpath" 2>/dev/null <<'PYEOF'
import sys, re
m = re.match(r'.*specs/releases/([^/]+)/(SPEC|PLAN|TASKS)\.md$', sys.argv[1])
if m:
    print(m.group(1) + " " + m.group(2))
else:
    print("")
PYEOF
)
    if [ -n "$_match_result" ]; then
        rel_id_from_path="${_match_result%% *}"
        rel_file_type="${_match_result##* }"
    fi
    if [ -n "$rel_id_from_path" ]; then
        # Check if an impl lock is HELD for this release
        local lock_for_rel
        lock_for_rel="$WS/.dadaia/locks/implementation"
        local lock_held="no"
        local lock_owner_sess=""
        if [ -d "$lock_for_rel" ]; then
            for lf in "$lock_for_rel"/*__"${rel_id_from_path}".json; do
                [ -f "$lf" ] || continue
                local lstate
                lstate=$("$PYTHON_BIN" - "$lf" 2>/dev/null <<'PYEOF'
import json, sys
from datetime import datetime, timezone
try:
    data = json.load(open(sys.argv[1]))
    ttl = int(data.get("ttl_seconds", 300))
    last_seen_raw = data.get("last_seen_at", "")
    if not last_seen_raw:
        print("held")
        sys.exit(0)
    last_seen = datetime.fromisoformat(last_seen_raw.replace("Z", "+00:00"))
    elapsed = (datetime.now(tz=timezone.utc) - last_seen).total_seconds()
    print("stale" if elapsed > ttl else "held")
except Exception:
    print("held")  # conservative: treat unreadable as held
PYEOF
)
                if [ "$lstate" = "held" ]; then
                    lock_held="yes"
                    lock_owner_sess=$("$PYTHON_BIN" - "$lf" 2>/dev/null <<'PYEOF'
import json, sys
try:
    print(json.load(open(sys.argv[1])).get("session_id", ""))
except Exception:
    print("")
PYEOF
)
                    break
                fi
            done
        fi
        if [ "$lock_held" = "yes" ]; then
            # TASKS.md in BOUND_IMPLEMENTATION mode by the lock owner → ALLOW (flips [-] markers)
            if [ "$rel_file_type" = "TASKS" ] && [ "$sess_mode" = "BOUND_IMPLEMENTATION" ] && [ "$lock_owner_sess" = "$sess_id" ]; then
                _log "RULE-E ALLOW: TASKS.md write allowed for BOUND_IMPLEMENTATION lock owner=$sess_id release=$rel_id_from_path"
                return 0  # fall through to RULE C task check
            fi
            # All other cases: block (R-9 closure)
            _block "[RULE E] Session '${sess_id}' (mode=${sess_mode}) cannot write to releases/${rel_id_from_path}/$(basename "$FPATH"). This release has an active implementation lock — SPEC.md and PLAN.md are read-only once implementation starts, and TASKS.md requires BOUND_IMPLEMENTATION with lock ownership (R-9 closure)."
        fi
        # No impl lock held → fall through
        _log "RULE-E: no impl lock held for release=$rel_id_from_path; fall through"
        # For SPEC.md/PLAN.md/TASKS.md with no impl lock, allow the write (authoring phase).
        # Exit here to bypass the IS_PROD / step 4c block that would otherwise fire for
        # paths under repos/<slug>/ (which includes the specs/ tree).
        exit 0
    fi

    # Step 4c — Production code: repos/<slug>/ outside specs/ → REQUIRE IMPLEMENTATION + lock ownership
    # If FPATH is not a production path (IS_PROD=1 due to repos/<slug>/) this block fires.
    # Note: IS_PROD is already 1 here (we only reach RULE E for production paths).
    if [ "$IS_PROD" = "1" ]; then
        case "$sess_mode" in
            BOUND_IMPLEMENTATION)
                # Verify the session owns the impl lock for CONTEXT_SLUG
                local lock_file="$WS/.dadaia/locks/implementation"
                local found_owner=""
                if [ -d "$lock_file" ] && [ -n "$CONTEXT_SLUG" ]; then
                    for lf in "$lock_file/${CONTEXT_SLUG}__"*.json; do
                        [ -f "$lf" ] || continue
                        local owner_sess
                        owner_sess=$("$PYTHON_BIN" - "$lf" 2>/dev/null <<'PYEOF'
import json, sys
try:
    print(json.load(open(sys.argv[1])).get("session_id", ""))
except Exception:
    print("")
PYEOF
)
                        local lstate2
                        lstate2=$("$PYTHON_BIN" - "$lf" 2>/dev/null <<'PYEOF'
import json, sys
from datetime import datetime, timezone
try:
    data = json.load(open(sys.argv[1]))
    ttl = int(data.get("ttl_seconds", 300))
    last_seen_raw = data.get("last_seen_at", "")
    if not last_seen_raw:
        print("held")
        sys.exit(0)
    last_seen = datetime.fromisoformat(last_seen_raw.replace("Z", "+00:00"))
    elapsed = (datetime.now(tz=timezone.utc) - last_seen).total_seconds()
    print("stale" if elapsed > ttl else "held")
except Exception:
    print("held")
PYEOF
)
                        # T-R1-04: only adopt the held lock OWNED BY the resolved
                        # session. The previous logic took the first held lock for
                        # the context and compared afterwards, so an unrelated
                        # release's lock (alphabetically earlier) shadowed the real
                        # owner and produced a spurious "does not own the lock" block.
                        if [ "$lstate2" = "held" ] && [ "$owner_sess" = "$sess_id" ]; then
                            found_owner="$owner_sess"
                            break
                        fi
                    done
                fi
                if [ -z "$found_owner" ]; then
                    _block "[RULE E] Session '${sess_id}' (mode=BOUND_IMPLEMENTATION) has no HELD implementation lock for context '${CONTEXT_SLUG:-<unknown>}'. Acquire lock via: eval \$(dadaia context bind ${CONTEXT_SLUG:-<ctx>} --mode implementation --release <release-id>)"
                fi
                if [ "$found_owner" != "$sess_id" ]; then
                    _block "[RULE E] Session '${sess_id}' does not own the implementation lock for '${CONTEXT_SLUG:-<unknown>}'. Lock is owned by session '${found_owner}'. Cannot write to production paths."
                fi
                # Owns the lock — resolve active release from lock file (T-8 completion / ADR D-9)
                # For IMPLEMENTATION mode, ACTIVE.md is NOT consulted; release comes from the lock.
                local lock_release
                lock_release=$("$PYTHON_BIN" - "$lock_file" "$CONTEXT_SLUG" "$sess_id" 2>/dev/null <<'PYEOF'
import json, sys
from pathlib import Path
lock_dir = Path(sys.argv[1])
ctx = sys.argv[2]
sess_id = sys.argv[3]
prefix = f"{ctx}__"
for lf in lock_dir.glob("*.json"):
    if not lf.name.startswith(prefix):
        continue
    try:
        data = json.loads(lf.read_text())
        if data.get("session_id") == sess_id:
            print(data.get("release", ""))
            break
    except Exception:
        pass
PYEOF
)
                # Override ACTIVE_RELEASE with lock-derived release for RULE C task lookup
                if [ -n "$lock_release" ]; then
                    ACTIVE_RELEASE="$lock_release"
                    _log "RULE-E IMPL: resolved release from lock file: $ACTIVE_RELEASE (overrides ACTIVE.md)"
                fi
                # Fall through to RULE C with updated ACTIVE_RELEASE
                return 0
                ;;
            READ|SPEC|BOUND_REVIEW)
                _block "[RULE E] Session '${sess_id}' (mode=${sess_mode}) cannot write to production path '${FPATH}'. Production writes require BOUND_IMPLEMENTATION mode with an owned implementation lock."
                ;;
            *)
                _log "RULE-E FAIL-OPEN: unknown mode '${sess_mode}' for sess=$sess_id; fall through"
                return 0
                ;;
        esac
    fi

    return 0
}

_rule_e

# Production path with no resolvable specs_dir → block with orientation
if [ -z "$CONTEXT_SPECS" ] || [ ! -d "$CONTEXT_SPECS" ]; then
    _block "[SDD GATE] No active Spec Context resolved. To bind a context run: eval \$(dadaia context bind <name> --mode read). Then retry the edit on $FPATH."
fi

# v3 RULE C — Find [-] task. Priority order:
#   1. CONTEXT_SPECS/releases/<active-release>/TASKS.md
#   2. Any CONTEXT_SPECS/releases/*/TASKS.md
#   3. (legacy compat) CONTEXT_SPECS/features/*/TASKS.md only
#      only when SDD_LEGACY_FEATURES=1 (default during migration window)
#      Note: root-level CONTEXT_SPECS/TASKS.md is no longer searched (removed T-8a)
ACTIVE=""
# T-SEMA-01 (Bug B): match BOTH canonical TASKS.md marker line forms:
#   "- [-] T-001 ..."            (gate test / inline list style)
#   "- **Status:** [-]"          (release TASKS.md style used by every release)
# The release style places the marker after a "**Status:**" label, and the
# marker may sit at end-of-line, so no trailing-space is required. Without this,
# RULE C never matches a real release marker and every production write blocks.
GREP_PAT='^[[:space:]]*-[[:space:]]*(\*\*Status:\*\*[[:space:]]*)?\[-\]'

# Priority 1: the active release's TASKS.md — the active segment's
# (releases/<release>/<segment>/TASKS.md) when ACTIVE.md carries a segment:,
# else the flat release's (releases/<release>/TASKS.md). ADR-1/ADR-5.
if [ -n "$ACTIVE_RELEASE" ] && [ -f "$CONTEXT_SPECS/releases/$ACTIVE_REL_PATH/TASKS.md" ]; then
    if grep -qE "$GREP_PAT" "$CONTEXT_SPECS/releases/$ACTIVE_REL_PATH/TASKS.md" 2>/dev/null; then
        ACTIVE="$CONTEXT_SPECS/releases/$ACTIVE_REL_PATH/TASKS.md"
    fi
fi

if [ -z "$ACTIVE" ] && [ -d "$CONTEXT_SPECS/releases" ]; then
    ACTIVE=$(grep -rlE "$GREP_PAT" "$CONTEXT_SPECS/releases" --include="TASKS.md" 2>/dev/null | head -1)
fi

if [ -z "$ACTIVE" ] && [ "${SDD_LEGACY_FEATURES:-1}" = "1" ]; then
    # Search outside releases/ for legacy compat: features/*/TASKS.md only.
    # Root-level $CONTEXT_SPECS/TASKS.md is no longer supported (removed per T-8a).
    ACTIVE=$(grep -rlE "$GREP_PAT" "$CONTEXT_SPECS" --include="TASKS.md" 2>/dev/null \
        | grep -v "/_archive/" \
        | grep -v "/releases/" \
        | grep -v "^$CONTEXT_SPECS/TASKS\.md$" \
        | head -1)
fi

# One-[-]-per-owner warn (T-HARD-05).
# Workspace-protocol says "at most one [-] at a time unless disjoint write sets
# are declared." When the resolved TASKS.md has 2+ [-] markers without a
# parallel_tasks: header, emit a WARN to the gate log. Do NOT hard-block — warn
# only, to avoid breaking declared-disjoint parallel work.
if [ -n "$ACTIVE" ]; then
    _COUNT=$(grep -cE "$GREP_PAT" "$ACTIVE" 2>/dev/null || echo 0)
    if [ "$_COUNT" -gt 1 ]; then
        # grep -c exits 0 when lines match, 1 when zero lines match; avoid the
        # `|| echo 0` pattern here — it double-appends when grep itself outputs "0".
        # Use arithmetic test instead: if grep finds no parallel_tasks: line, count is 0.
        _HAS_PARALLEL=0
        grep -qF 'parallel_tasks:' "$ACTIVE" 2>/dev/null && _HAS_PARALLEL=1
        if [ "$_HAS_PARALLEL" = "0" ]; then
            _log "WARN one-active-task: $_COUNT simultaneous [-] markers in $ACTIVE without parallel_tasks declaration"
        fi
    fi
fi

if [ -n "$ACTIVE" ]; then
    _log "allowed — active task in: $ACTIVE (release=${ACTIVE_RELEASE:-none})"
    # OpenCode post-hook fallback (OQ-3): inline heartbeat — OpenCode hooks are
    # plugin-based, JSON post-hook unsupported. Claude Code and Codex also run
    # this path; the double-renew (pre + post hook) is idempotent and harmless.
    # Guard: only when DADAIA_SESSION_ID is set + session file exists; never on
    # fail-open. Best-effort: failures are silently ignored, gate never blocks.
    if [ -n "${DADAIA_SESSION_ID:-}" ]; then
        _INLINE_SESS_FILE="$WS/.dadaia/sessions/${DADAIA_SESSION_ID}.json"
        if [ -f "$_INLINE_SESS_FILE" ]; then
            "$PYTHON_BIN" - "$_INLINE_SESS_FILE" "$WS" "$DADAIA_SESSION_ID" 2>/dev/null <<'PYEOF' || true
import json, os, sys
from datetime import UTC, datetime
from pathlib import Path
sess_file = Path(sys.argv[1])
ws = Path(sys.argv[2])
sess_id = sys.argv[3]
try:
    data = json.loads(sess_file.read_text())
except (json.JSONDecodeError, OSError):
    sys.exit(0)
now = datetime.now(tz=UTC).isoformat()
data["last_seen_at"] = now
tmp = sess_file.with_suffix(".tmp")
tmp.write_text(json.dumps(data, indent=2))
os.replace(tmp, sess_file)
context = data.get("context", "")
release = data.get("release", "") or ""
# T-SEMA-01 (SCOPE-02): also renew the implementation lock owned by this
# session so env-free resolution (which only adopts NON-STALE locks) keeps
# working across a long agent session. Best-effort; never blocks the gate.
if context and release:
    lock_path = ws / ".dadaia" / "locks" / "implementation" / f"{context}__{release}.json"
    try:
        ldata = json.loads(lock_path.read_text())
        if ldata.get("session_id") == sess_id:
            ldata["last_seen_at"] = now
            ltmp = lock_path.with_suffix(".tmp")
            ltmp.write_text(json.dumps(ldata, indent=2))
            os.replace(ltmp, lock_path)
    except (json.JSONDecodeError, OSError):
        pass
runtime = data.get("runtime", "unknown")
pid = data.get("pid", 0)
record = {"ts": now, "event": "HEARTBEAT", "context": context, "release": release,
          "session_id": sess_id, "runtime": runtime, "pid": pid}
line = (json.dumps(record) + "\n").encode("utf-8")
audit_path = ws / ".dadaia" / "logs" / "lock-events.jsonl"
audit_path.parent.mkdir(parents=True, exist_ok=True)
fd = os.open(str(audit_path), os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
try:
    os.write(fd, line)
finally:
    os.close(fd)
PYEOF
        fi
    fi
    exit 0
fi

_block "[SDD GATE] Nenhuma task IN PROGRESS (marker [-]) em $CONTEXT_SPECS/releases/${ACTIVE_RELEASE:-<no-active-release>}/TASKS.md. Antes de editar $FPATH, marque a task alvo de '[ ]' para '[-]' e commit (skill: dadaia-task-manager). Janela de migração: exporte SDD_LEGACY_FEATURES=1 para reaproveitar specs/features/*/TASKS.md."
