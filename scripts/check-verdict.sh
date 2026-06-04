#!/usr/bin/env bash
# check-verdict.sh — Dual-approval gate for release CLOSURE.
#
# Checks that qa-engineer AND security-reviewer handoff JSON files each have
# verdict == "APPROVED".
#
# Behaviour:
#   - When no handoffs are found (normal CI run, .dadaia/handoff/ is gitignored):
#     exits 0 with an INFO log — gate is a no-op.
#   - When handoffs are found and verdict == "APPROVED" for both: exits 0.
#   - When a handoff is found but verdict != "APPROVED" or is absent: exits 1.
#
# Environment variables (optional overrides):
#   QA_HANDOFF       absolute or relative path to qa-engineer *.handoff.json
#   SECURITY_HANDOFF absolute or relative path to security-reviewer *.handoff.json
#   HANDOFF_DIR      root search directory (default: .dadaia/handoff)
#   RELEASE_ID       release id that both reviewer handoffs must match
#   CONTEXT          optional context that both reviewer handoffs must match
#
# Usage:
#   ./scripts/check-verdict.sh
#   QA_HANDOFF=path/to/qa.handoff.json SECURITY_HANDOFF=path/to/sec.handoff.json \
#     ./scripts/check-verdict.sh

set -euo pipefail

HANDOFF_DIR="${HANDOFF_DIR:-${REPORTS_DIR:-.dadaia/handoff}}"
RELEASE_ID="${RELEASE_ID:-}"
CONTEXT="${CONTEXT:-${DADAIA_CONTEXT:-}}"

# ---------------------------------------------------------------------------
# Resolve handoff paths
# ---------------------------------------------------------------------------
resolve_handoff() {
  local agent="$1"
  local explicit_path="$2"

  if [ -n "$explicit_path" ]; then
    echo "$explicit_path"
    return
  fi

  # Auto-discover: find the most recent *.handoff.json for this agent.
  # The '|| true' guards against find exiting non-zero when HANDOFF_DIR is absent
  # (normal in CI where .dadaia/handoff/ is gitignored and not checked out).
  find "$HANDOFF_DIR" -name "*${agent}*.handoff.json" 2>/dev/null \
    | sort | tail -1 || true
}

qa_handoff=$(resolve_handoff "qa-engineer"         "${QA_HANDOFF:-${QA_SIDECAR:-}}")
sec_handoff=$(resolve_handoff "security-reviewer"  "${SECURITY_HANDOFF:-${SECURITY_SIDECAR:-}}")

# ---------------------------------------------------------------------------
# No handoffs present → no-op pass (normal CI run)
# ---------------------------------------------------------------------------
if [ -z "$qa_handoff" ] && [ -z "$sec_handoff" ]; then
  echo "[verdict-gate] INFO: No qa-engineer or security-reviewer handoffs found in '${HANDOFF_DIR}'. Gate is a no-op — this is expected on regular CI runs."
  exit 0
fi

if [ -z "$RELEASE_ID" ]; then
  echo "[verdict-gate] FAIL: RELEASE_ID is required when reviewer handoffs are present."
  exit 1
fi

if [ "$(realpath -m "$qa_handoff")" = "$(realpath -m "$sec_handoff")" ]; then
  echo "[verdict-gate] FAIL: qa-engineer and security-reviewer handoffs must be distinct files."
  exit 1
fi

# ---------------------------------------------------------------------------
# Helper: check one handoff
# ---------------------------------------------------------------------------
check_handoff() {
  local label="$1"
  local path="$2"
  local failed=0

  if [ -z "$path" ]; then
    echo "[verdict-gate] FAIL: No ${label} handoff found. A handoff from the other reviewer was present, so both are required."
    return 1
  fi

  if [ ! -f "$path" ]; then
    echo "[verdict-gate] FAIL: ${label} handoff path does not exist: $path"
    return 1
  fi

  verdict=$(jq -r '.verdict // empty' "$path" 2>/dev/null || true)
  agent=$(jq -r '.agent // empty' "$path" 2>/dev/null || true)
  release_id=$(jq -r '.release_id // empty' "$path" 2>/dev/null || true)
  context=$(jq -r '.context // empty' "$path" 2>/dev/null || true)

  if [ "$agent" != "$label" ]; then
    echo "[verdict-gate] FAIL: ${label} handoff agent '${agent}' does not match required '${label}'."
    failed=1
  fi

  if [ "$release_id" != "$RELEASE_ID" ]; then
    echo "[verdict-gate] FAIL: ${label} handoff release_id '${release_id}' does not match required '${RELEASE_ID}'."
    failed=1
  fi

  if [ -n "$CONTEXT" ] && [ "$context" != "$CONTEXT" ]; then
    echo "[verdict-gate] FAIL: ${label} handoff context '${context}' does not match required '${CONTEXT}'."
    failed=1
  fi

  if [ -z "$verdict" ]; then
    echo "[verdict-gate] FAIL: ${label} handoff at '$path' has no 'verdict' field."
    failed=1
  elif [ "$verdict" = "APPROVED" ]; then
    echo "[verdict-gate] PASS: ${label} verdict = APPROVED (handoff: $path)"
  else
    reason=$(jq -r '.verdict_reason // "(no reason given)"' "$path" 2>/dev/null || echo "(no reason given)")
    echo "[verdict-gate] FAIL: ${label} verdict = ${verdict} — reason: ${reason} (handoff: $path)"
    failed=1
  fi

  return $failed
}

# ---------------------------------------------------------------------------
# Run checks
# ---------------------------------------------------------------------------
exit_code=0

check_handoff "qa-engineer"        "$qa_handoff"  || exit_code=1
check_handoff "security-reviewer"  "$sec_handoff" || exit_code=1

if [ $exit_code -eq 0 ]; then
  echo "[verdict-gate] All required verdicts APPROVED. Release CLOSURE gate passed."
else
  echo "[verdict-gate] One or more verdicts missing or REJECTED. Release CLOSURE gate FAILED."
fi

exit $exit_code
