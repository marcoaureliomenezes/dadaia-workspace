#!/bin/bash
# root-whitelist-gate.sh — PreToolUse hook enforcing the workspace root whitelist law.
#
# The Law: the workspace root may contain ONLY:
#   Directories: .agents/ .claude/ .codex/ .dadaia/ .opencode/ repos/
#   File:        AGENTS.md
#   Operator exception: any human-operator-created file/dir is always allowed and
#                       MUST never be auto-deleted. Operator origin is checked via
#                       .dadaia/states/root_exceptions.txt (one glob per line).
#
# Input/output contract (same as sdd-spec-gate.sh):
#   - Reads JSON from stdin: {tool_name, tool_input{file_path|path|command}}
#   - Codex apply_patch: parses "*** Add File:" / "*** Update File:" headers.
#   - Emits {"decision":"block","reason":"..."} + exit 0 to block.
#   - Exits 0 silently to allow.
#   - Fails open on unparseable input — never hard-errors.

LOG="${ROOT_GATE_LOG:-/tmp/root-whitelist-gate.log}"
# Resolve workspace root from this script's own absolute path.
# Script lives at <workspace_root>/.dadaia/scripts/root-whitelist-gate.sh
# (projected from dadaia_workspace/public/scripts/ by dadaia public install).
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEFAULT_WS="$(cd "$SCRIPT_DIR/../.." && pwd)"
WS="${WORKSPACE_ROOT:-$DEFAULT_WS}"
PYTHON_BIN="${DADAIA_PYTHON:-$WS/.dadaia/.venv/bin/python}"
if [ ! -x "$PYTHON_BIN" ]; then
    PYTHON_BIN="${PYTHON:-python3}"
fi

_log() { printf '[%s] root-gate: %s\n' "$(date -Iseconds)" "$*" >> "$LOG" 2>/dev/null; }
_block() { _log "BLOCKED: $*"; printf '{"decision":"block","reason":"%s"}' "$1"; exit 0; }

# Read hook input from stdin
TMP=$(mktemp /tmp/root-gate-XXXXXX.json 2>/dev/null) || exit 0
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

# Only intercept write-like tools
case "$TOOL" in
    Write|write_file|Edit|edit_file|MultiEdit|apply_patch) ;;
    *) exit 0 ;;
esac

# Parse file path from tool input.
# For Codex apply_patch, extract the first touched file from patch headers.
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

# Fail open: if we cannot parse the path, let other hooks handle it
[ -z "$FPATH" ] && exit 0

# Normalise to absolute path
[[ "$FPATH" != /* ]] && FPATH="$WS/$FPATH"
_log "tool=$TOOL path=$FPATH"

# Only gate writes that target the workspace root itself.
# A write is "at root" when its immediate parent is exactly $WS.
# Writes under $WS/ sub-directories (the six whitelisted dirs, etc.) are ignored.
PARENT_DIR="$(dirname "$FPATH")"

# If the target is not directly under WS, allow immediately
if [ "$PARENT_DIR" != "$WS" ]; then
    exit 0
fi

# Extract the basename (the new root-level entry being created/modified)
BASENAME="$(basename "$FPATH")"

# Whitelisted root entries (The Law)
case "$BASENAME" in
    .agents|.claude|.codex|.dadaia|.opencode|repos|AGENTS.md)
        _log "allowed — whitelisted root entry: $BASENAME"
        exit 0
        ;;
esac

# Check operator exception list: .dadaia/states/root_exceptions.txt
# Each line is a glob pattern matched against the basename.
EXCEPTIONS_FILE="$WS/.dadaia/states/root_exceptions.txt"
if [ -f "$EXCEPTIONS_FILE" ]; then
    MATCH=$("$PYTHON_BIN" - "$BASENAME" "$EXCEPTIONS_FILE" 2>/dev/null <<'EOF'
import sys, fnmatch
basename = sys.argv[1]
efile = sys.argv[2]
try:
    with open(efile, encoding="utf-8") as f:
        for raw in f:
            pat = raw.strip()
            if pat and not pat.startswith("#"):
                if fnmatch.fnmatch(basename, pat):
                    print("yes")
                    break
except Exception:
    pass
EOF
)
    if [ "$MATCH" = "yes" ]; then
        _log "allowed — operator exception match for root entry: $BASENAME"
        exit 0
    fi
fi

# Block: this is a non-whitelisted root-level entry
_block "[ROOT WHITELIST GATE] Writing '$BASENAME' at workspace root is forbidden. The workspace root may only contain: .agents/ .claude/ .codex/ .dadaia/ .opencode/ repos/ AGENTS.md. Redirect output to .dadaia/<subdir> (temp files: .dadaia/tmp/<agent>/<date>/; tool caches: .dadaia/; MCP output: .dadaia/mcps/<server>/). If this entry is genuinely required at root, add a glob pattern to .dadaia/states/root_exceptions.txt and retry. Operator-created files are exempt — add them to root_exceptions.txt."
