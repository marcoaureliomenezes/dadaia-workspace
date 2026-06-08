#!/bin/bash
# sdd-spec-gate.sh — PreToolUse hook for SDD enforcement (v0.1.6 + D1/D2/D6 soul-fold).
# Classifier (first match wins): ADDITIVE(backlog/bugs/audits/.dadaia/reports,handoff,tmp)->ALLOW;
# MEMORY(specs/memory)->phase gate; FROZEN(specs/_archive)->block; MUTATING(specs/releases,
# repos/<ctx>)->TTL-lease acquire; UNGATED->ALLOW. Gate is the SINGLE lease acquisition
# point (O_EXCL CAS in lease.py). Fail-safe: inconclusive ALLOWs+logs; only a live-foreign
# lease conflict blocks (yield-iff-live-foreign, FR-P1-15).
# Cross-harness enforcement honesty:
#   Claude Code: real PreToolUse block (decision: block)
#   Codex:       real block in trusted workspace; hooks parallel — must be idempotent
#   opencode:    advisory only — JSON PreToolUse unsupported; lease record + doctor enforce.
# Audit dirs (FR-P1-16/D6): specs/audits/<YYYYMMDDTHHMMSSZ>-<session_id_8chars>/
LOG="${SDD_GATE_LOG:-/tmp/sdd-gate.log}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WS="${WORKSPACE_ROOT:-$(cd "$SCRIPT_DIR/../.." && pwd)}"
PYTHON_BIN="${DADAIA_PYTHON:-$WS/.dadaia/.venv/bin/python}"
[ -x "$PYTHON_BIN" ] || PYTHON_BIN="${PYTHON:-python3}"
_log() { printf '[%s] sdd-gate: %s\n' "$(date -Iseconds)" "$*" >>"$LOG" 2>/dev/null; }
_block() {
    _log "BLOCKED: $1"
    "$PYTHON_BIN" - "$1" 2>/dev/null <<'PYEOF'
import json, sys
print(json.dumps({"decision": "block", "reason": sys.argv[1]}))
PYEOF
    exit 0
}
TMP=$(mktemp /tmp/sdd-gate-XXXXXX.json 2>/dev/null) || exit 0
trap 'rm -f "$TMP"' EXIT
cat >"$TMP" 2>/dev/null
[ ! -s "$TMP" ] && exit 0
TOOL=$("$PYTHON_BIN" - "$TMP" 2>/dev/null <<'PYEOF'
import json, sys
try:
    d = json.load(open(sys.argv[1]))
    print(d.get("tool_name") or d.get("tool") or "")
except Exception:
    print("")
PYEOF
)
case "$TOOL" in
    Write | write_file | Edit | edit_file | MultiEdit | NotebookEdit | apply_patch) ;;
    *) exit 0 ;;
esac
FPATH=$("$PYTHON_BIN" - "$TMP" 2>/dev/null <<'PYEOF'
import json, sys
try:
    d = json.load(open(sys.argv[1]))
    i = d.get("tool_input") or d
    direct = i.get("file_path") or i.get("path") or i.get("notebook_path") or ""
    if direct:
        print(direct); sys.exit(0)
    command = i.get("command") or ""
    if isinstance(command, str):
        for line in command.splitlines():
            for p in ("*** Update File: ", "*** Add File: ", "*** Delete File: "):
                if line.startswith(p):
                    print(line[len(p):].strip()); sys.exit(0)
    print("")
except Exception:
    print("")
PYEOF
)
# Fail-safe: unparseable target → ALLOW + log (never deadlock on a parse miss).
if [ -z "$FPATH" ]; then _log "ALLOW: unparseable target for tool=$TOOL"; exit 0; fi
[[ "$FPATH" != /* ]] && FPATH="$WS/$FPATH"
_log "tool=$TOOL path=$FPATH"
# Resolve bound context slug: DADAIA_CONTEXT -> first ALIVE in spec_contexts.json.
# Sanitized to [A-Za-z0-9_-] (CWE-22).
CONTEXT_SLUG=$("$PYTHON_BIN" - "$WS" "${DADAIA_CONTEXT:-}" "${DADAIA_SESSION_ID:-}" 2>/dev/null <<'PYEOF'
import json, os, re, sys
ws, env_ctx, sess = sys.argv[1], sys.argv[2], sys.argv[3]
slug = env_ctx
if not slug:
    try:
        d = json.load(open(os.path.join(ws, ".dadaia/states/spec_contexts.json")))
        for c in d.get("contexts", []):
            if c.get("state", "").lower() == "alive":
                slug = c.get("repo_slug", "") or ""
                break
    except Exception:
        pass
if not slug and sess:
    try:
        p = os.path.join(ws, ".dadaia/sessions", sess + ".json")
        slug = json.load(open(p)).get("context", "") or ""
    except Exception:
        pass
print(re.sub(r"[^A-Za-z0-9_-]", "", slug or ""))
PYEOF
)
# Stable session id (so consecutive edits RENEW, never self-block). Falls back to
# the harness session id; anon only when nothing identifies the session (fail-open).
SESSION_ID="${DADAIA_SESSION_ID:-${CLAUDE_CODE_SESSION_ID:-${CODEX_SESSION_ID:-${OPENCODE_SESSION_ID:-anon-session}}}}"
SESSION_ID=$(printf '%s' "$SESSION_ID" | tr -cd 'a-zA-Z0-9_-')
export DADAIA_RUNTIME="${DADAIA_RUNTIME:-unknown}"
_phase_of() { # $1 = a specs dir; echoes phase from releases/ACTIVE.md
    grep -E '^phase:' "$1/releases/ACTIVE.md" 2>/dev/null | head -1 |
        sed -E 's/^phase:[[:space:]]*//; s/[[:space:]]*$//'
}
# specs/audits/ is ADDITIVE (FR-P1-14/D2): no lease check, no phase check.
case "$FPATH" in
    */specs/backlog/* | */specs/bugs/* | */specs/audits/* | \
    */.dadaia/reports/* | */.dadaia/handoff/* | */.dadaia/tmp/*)
        CLASS=ADDITIVE ;;
    */specs/memory/*) CLASS=MEMORY ;;
    */specs/_archive/*) CLASS=FROZEN ;;
    */specs/releases/*) CLASS=MUTATING ;;
    # T-017-15 / SEC-01 (CWE-284): .dadaia/sessions/ holds CLI-owned runtime
    # session state, incl. the persona pointers the backlog-ownership fallback
    # trusts. Agents must NOT be able to write these via Write/Edit, else a
    # confused-deputy agent could forge a project-manager persona pointer and
    # bypass the owner-only backlog gate. The dadaia CLI/bootstrap writes these
    # via Python (outside the tool gate), so it is unaffected by this block.
    */.dadaia/sessions/*) CLASS=PROTECTED ;;
    *) CLASS=UNGATED ;;
esac
if [ "$CLASS" = "UNGATED" ] && [ -n "$CONTEXT_SLUG" ]; then
    case "$FPATH" in "$WS/repos/$CONTEXT_SLUG/"*) CLASS=MUTATING ;; esac
fi
_log "class=$CLASS ctx=${CONTEXT_SLUG:-<none>} session=$SESSION_ID"
if [ "$CLASS" = "PROTECTED" ]; then
    _block "[GATE] .dadaia/sessions/ is CLI-owned runtime state (incl. persona pointers the backlog-ownership gate trusts). Agents must not write here via Write/Edit — only the dadaia CLI/bootstrap may. Blocked to prevent persona-pointer forgery (SEC-01 / CWE-284, rule: backlog-ownership)."
fi
[ "$CLASS" = "UNGATED" ] && exit 0
if [ "$CLASS" = "ADDITIVE" ]; then
    case "$FPATH" in
        */specs/backlog/*)
            # T-016-C03 (FORK-4): backlog is owner-only — fail-safe-BLOCK, never
            # silently allow. An unresolved/empty persona is blocked too (the prior
            # fail-open was reclassified a bug in the 0.1.6 grill). This is the narrow
            # owner-only exception to the gate's fail-open default; it does not touch
            # the lease/production path, so it cannot reintroduce the lease deadlock.
            PERSONA="${DADAIA_AGENT_PERSONA:-${CLAUDE_AGENT_PERSONA:-${CODEX_AGENT_PERSONA:-${OPENCODE_AGENT_PERSONA:-}}}}"
            # T-017-15: persona session-pointer fallback. When no persona env var is
            # exported (e.g. a runtime that dispatches agents without setting it), resolve
            # the owning role the SAME way context already falls back to a session pointer
            # (.dadaia/sessions/runtime/<ctx>.ptr). This is fail-CLOSED: it only ADDS a
            # resolution source; if it yields nothing or a non-owner the blocks below still
            # fire. It never silently allows. Sources, in order: a one-line .persona pointer,
            # then the `persona` field of the session JSON the gate already reads for context.
            if [ -z "$PERSONA" ] && [ -n "$SESSION_ID" ]; then
                _PFILE="$WS/.dadaia/sessions/runtime/$SESSION_ID.persona"
                [ -f "$_PFILE" ] && PERSONA=$(tr -cd 'a-zA-Z0-9_-' <"$_PFILE" 2>/dev/null)
                if [ -z "$PERSONA" ]; then
                    PERSONA=$("$PYTHON_BIN" - "$WS/.dadaia/sessions/$SESSION_ID.json" 2>/dev/null <<'PYEOF'
import json, re, sys
try:
    p = json.load(open(sys.argv[1])).get("persona", "") or ""
except Exception:
    p = ""
print(re.sub(r"[^A-Za-z0-9_-]", "", p))
PYEOF
)
                fi
            fi
            if [ -z "$PERSONA" ]; then
                _block "[BACKLOG OWNERSHIP ERROR] writer persona unresolved — only project-manager may write specs/backlog/. Set DADAIA_AGENT_PERSONA=project-manager (the owning role), or record it in the session pointer .dadaia/sessions/runtime/<session>.persona, and retry (rule: backlog-ownership)."
            elif [ "$PERSONA" != "project-manager" ]; then
                _block "[BACKLOG OWNERSHIP ERROR] agent ${PERSONA} cannot write to specs/backlog/ — only project-manager creates or edits backlog entries (rule: backlog-ownership)."
            fi ;;
    esac
    exit 0
fi
if [ "$CLASS" = "MEMORY" ]; then
    case "$FPATH" in *.md) ;; *) _block "[SDD GATE] memory/ uses Markdown as the sole source; .html/.yaml/.yml atoms are read-only legacy." ;; esac
    PHASE="$(_phase_of "$(echo "$FPATH" | sed -E 's|/specs/.*|/specs|')")"
    case "$PHASE" in
        CLOSURE | DEFINITION) _log "ALLOW: memory edit in phase=$PHASE"; exit 0 ;;
        *) _block "[SDD GATE] memory/ is atomic — only product-engineer in DEFINITION or CLOSURE phase may edit (current phase: ${PHASE:-none})." ;;
    esac
fi
[ "$CLASS" = "FROZEN" ] && _block "[SDD GATE] specs/_archive/ is read-only. Use 'git mv' to archive a finished release; never edit archived files."
# RULE D — write-allowlist via pre-compiled agents.index.json. Fail-open when no
# persona / no index entry (the gate never hard-blocks on an unknown writer).
PERSONA="${DADAIA_AGENT_PERSONA:-${CLAUDE_AGENT_PERSONA:-${CODEX_AGENT_PERSONA:-${OPENCODE_AGENT_PERSONA:-}}}}"
if [ -n "$PERSONA" ]; then
    RD=$("$PYTHON_BIN" - "$WS/.dadaia/agentic/agents.index.json" "$PERSONA" "${FPATH#"$WS"/}" "$CONTEXT_SLUG" 2>/dev/null <<'PYEOF'
import fnmatch, json, sys
idx_path, persona, rel, ctx = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
try:
    idx = json.load(open(idx_path))
except Exception:
    print("skip"); sys.exit(0)
if persona not in idx:
    print("skip"); sys.exit(0)
globs = [g.replace("<ctx>", ctx) for g in idx[persona]]
print("ok" if any(fnmatch.fnmatch(rel, g) for g in globs) else "deny")
PYEOF
)
    [ "$RD" = "deny" ] && _block "[SDD GATE] agent ${PERSONA} write_allowlist does not permit '${FPATH#"$WS"/}' (rule: agent path-scope)."
fi
if [ -z "$CONTEXT_SLUG" ]; then _log "ALLOW: MUTATING path but no context resolved (fail-open)"; exit 0; fi
REL="$(grep -E '^release:' "$WS/repos/$CONTEXT_SLUG/specs/releases/ACTIVE.md" 2>/dev/null | head -1 | sed -E 's/^release:[[:space:]]*//; s/[[:space:]]*$//')"
MODE="${DADAIA_MODE:-IMPLEMENTATION}"
LEASE_OUT=$(WORKSPACE_ROOT="$WS" "$PYTHON_BIN" -m dadaia_workspace.features.spec_context.lease acquire \
    "$CONTEXT_SLUG" "$SESSION_ID" "${REL:-none}" "$MODE" 2>>"$LOG")
LEASE_EXIT=$?
# exit 0 (ACQUIRED/RENEWED) → ALLOW. exit 1 (live-foreign LockHeldError,
# FR-P1-15 yield) → BLOCK with informative message (never "bind --mode write"/
# "relaunch"; steal only as conditional emergency escape). Other exit → ALLOW (fail-open).
if [ "$LEASE_EXIT" -eq 0 ]; then
    _log "ALLOW: lease $LEASE_OUT ctx=$CONTEXT_SLUG session=$SESSION_ID"; exit 0
elif [ "$LEASE_EXIT" -eq 1 ]; then
    _log "BLOCKED: live-foreign lease ctx=$CONTEXT_SLUG session=$SESSION_ID"; _block "$LEASE_OUT"
else
    _log "ALLOW: lease subsystem error (exit=$LEASE_EXIT) — fail-open"; exit 0
fi
