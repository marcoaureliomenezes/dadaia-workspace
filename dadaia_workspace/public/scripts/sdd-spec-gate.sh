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
# Resolve context slug from the WRITE-TARGET PATH first (rc-4 / ADR-1 — fixes
# gate-cross-context-lock-contamination): a write under $WS/repos/<slug>/... belongs to
# context <slug>, regardless of which context is first-ALIVE in spec_contexts.json. The old
# first-ALIVE fallback conflated contexts — a session editing repo B acquired repo A's lease.
# Only an explicit DADAIA_CONTEXT overrides when the path is under no repo; otherwise the slug
# is empty -> the MUTATING branch fails open (UNGATED, no lease). Sanitized [A-Za-z0-9_-] (CWE-22).
CONTEXT_SLUG=$("$PYTHON_BIN" - "$WS" "$FPATH" "${DADAIA_CONTEXT:-}" 2>/dev/null <<'PYEOF'
import os, re, sys
ws, fpath, env_ctx = sys.argv[1], sys.argv[2], sys.argv[3]
slug = ""
prefix = os.path.join(ws, "repos") + os.sep
cand = fpath if fpath.startswith(prefix) else os.path.realpath(fpath)
rp = os.path.realpath(os.path.join(ws, "repos")) + os.sep
if cand.startswith(prefix):
    slug = cand[len(prefix):].split(os.sep, 1)[0]
elif cand.startswith(rp):
    slug = cand[len(rp):].split(os.sep, 1)[0]
if not slug:
    slug = env_ctx  # explicit operator override only; else empty -> UNGATED (no lease)
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
    # SEC-01 (CWE-284): .dadaia/sessions/ holds CLI-owned runtime session state,
    # incl. the single-session lease identity pointer (.dadaia/sessions/runtime/
    # <ctx>.ptr). Agents must NOT write these via Write/Edit, else a confused-deputy
    # agent could forge the lease .ptr and steal a Spec Context binding from the
    # holding session — defeating the one deterministic lock the product keeps. The
    # dadaia CLI/bootstrap writes these via Python (outside the tool gate), unaffected.
    */.dadaia/sessions/*) CLASS=PROTECTED ;;
    *) CLASS=UNGATED ;;
esac
if [ "$CLASS" = "UNGATED" ] && [ -n "$CONTEXT_SLUG" ]; then
    case "$FPATH" in "$WS/repos/$CONTEXT_SLUG/"*) CLASS=MUTATING ;; esac
fi
_log "class=$CLASS ctx=${CONTEXT_SLUG:-<none>} session=$SESSION_ID"
if [ "$CLASS" = "PROTECTED" ]; then
    _block "[GATE] .dadaia/sessions/ is CLI-owned runtime state, incl. the single-session lease identity pointer .dadaia/sessions/runtime/<ctx>.ptr. Agents must not write here via Write/Edit — only the dadaia CLI/bootstrap may. Blocked to protect lease-identity integrity (the sole deterministic lock); forging the .ptr would let a second session steal a Spec Context binding (SEC-01 / CWE-284)."
fi
[ "$CLASS" = "UNGATED" ] && exit 0
if [ "$CLASS" = "ADDITIVE" ]; then
    # ADDITIVE = backlog / bugs / audits / .dadaia reports,handoff,tmp. All ALLOW.
    # rc-3 (0.1.7): the backlog-ownership persona block was REMOVED. It was a lock
    # with no key — no harness sets *_AGENT_PERSONA in the hook process environment,
    # and no `dadaia` CLI verb writes the .persona pointer, so the legitimate owner
    # (project-manager) was blocked in EVERY harness (Codex + Claude, both reproduced).
    # Backlog ownership is a coordination convention (rule: backlog-ownership), not a
    # gate. The only deterministic lock the product keeps is the single-session
    # MUTATING lease below. ADDITIVE writes never block a workflow.
    _log "ALLOW: ADDITIVE $FPATH"
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
# rc-3 (0.1.7): RULE D (per-persona write-allowlist deny via agents.index.json) was
# REMOVED. It was fail-open and never fired for an agent — persona is never set in the
# hook process environment — so it was a dormant latent lock. Path-scope is now an
# agent-instruction convention, not a gate. Only the single-session lease below can
# block a MUTATING write.
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
