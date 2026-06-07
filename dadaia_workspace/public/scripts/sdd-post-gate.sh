#!/bin/bash
# sdd-post-gate.sh — PostToolUse hook for SDD session heartbeat (T-13)
#
# Runs after every tool call across all three runtimes (Claude Code, Codex,
# OpenCode). Its sole purpose: keep the active session alive by renewing
# last_seen_at and appending a HEARTBEAT event to lock-events.jsonl.
#
# Session identity resolution order (SPEC §6):
#   1. DADAIA_SESSION_ID env var — primary stable key, set by
#      eval $(dadaia context bind ...). Portable across all runtimes.
#   2. Fail-open — if absent, exit 0 (no-op). Heartbeat only works when
#      session identity is established.
#
# The native runtime session_id (e.g. from Claude Code's stdin payload) is
# runtime-specific and NOT portable; it is NOT used as the primary key here.
#
# This script does NOT block any tool call. It always exits 0.

# Resolve workspace root via the script's own absolute path.
# Script lives at <workspace_root>/.dadaia/scripts/ when installed.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEFAULT_WS="$(cd "$SCRIPT_DIR/../.." && pwd)"
WS="${WORKSPACE_ROOT:-$DEFAULT_WS}"
PYTHON_BIN="${DADAIA_PYTHON:-$WS/.dadaia/.venv/bin/python}"
if [ ! -x "$PYTHON_BIN" ]; then
    PYTHON_BIN="${PYTHON:-python3}"
fi

LOG="${SDD_GATE_LOG:-/tmp/sdd-gate.log}"
_log() { printf '[%s] sdd-post-gate: %s\n' "$(date -Iseconds)" "$*" >> "$LOG" 2>/dev/null; }

# Step 1 — Read DADAIA_SESSION_ID; if absent, exit 0 (no-op)
SESS_ID="${DADAIA_SESSION_ID:-}"
if [ -z "$SESS_ID" ]; then
    exit 0
fi

# Step 2 — Load session file; if absent, exit 0 (no-op)
SESS_FILE="$WS/.dadaia/sessions/${SESS_ID}.json"
if [ ! -f "$SESS_FILE" ]; then
    _log "session file absent for $SESS_ID; no-op"
    exit 0
fi

# Step 3 — Renew session last_seen_at atomically (tmp → os.replace())
# Step 4 — Append HEARTBEAT event to .dadaia/logs/lock-events.jsonl
# (The per-context semaphore was retired in v0.1.6; there is no semaphore to
#  renew here — the single TTL lease is renewed by the PreToolUse gate.)
"$PYTHON_BIN" - "$SESS_FILE" "$WS" "$SESS_ID" 2>/dev/null <<'PYEOF'
import json
import os
import sys
import uuid
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

# Step 3: Renew session file last_seen_at atomically
data["last_seen_at"] = now
tmp_suffix = uuid.uuid4().hex
tmp = sess_file.with_suffix(f".{tmp_suffix}.tmp")
tmp.write_text(json.dumps(data, indent=2))
os.replace(tmp, sess_file)

# v0.1.6: the per-context semaphore is retired. The single TTL-lease
# (.dadaia/states/ctx_locks/<ctx>.lock.json) is renewed by the PreToolUse gate's
# acquire (RENEWED branch) — no PostToolUse semaphore renewal remains.
context = data.get("context", "")

# Step 4: Append HEARTBEAT event to lock-events.jsonl
release = data.get("release", "") or ""
runtime = data.get("runtime", "unknown")
pid = data.get("pid", 0)

record = {
    "ts": now,
    "event": "HEARTBEAT",
    "context": context,
    "release": release,
    "session_id": sess_id,
    "runtime": runtime,
    "pid": pid,
}
line = json.dumps(record) + "\n"
encoded = line.encode("utf-8")

audit_path = ws / ".dadaia" / "logs" / "lock-events.jsonl"
audit_path.parent.mkdir(parents=True, exist_ok=True)
fd = os.open(str(audit_path), os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
try:
    os.write(fd, encoded)
finally:
    os.close(fd)
PYEOF

exit 0
