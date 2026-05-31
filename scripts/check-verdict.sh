#!/usr/bin/env bash
# check-verdict.sh — Dual-approval gate for release CLOSURE.
#
# Checks that qa-engineer AND security-reviewer handoff sidecars each have
# verdict == "APPROVED".
#
# Behaviour:
#   - When no sidecars are found (normal CI run, .dadaia/reports/ is gitignored):
#     exits 0 with an INFO log — gate is a no-op.
#   - When sidecars are found and verdict == "APPROVED" for both: exits 0.
#   - When a sidecar is found but verdict != "APPROVED" or is absent: exits 1.
#
# Environment variables (optional overrides):
#   QA_SIDECAR       absolute or relative path to qa-engineer *.handoff.json
#   SECURITY_SIDECAR absolute or relative path to security-reviewer *.handoff.json
#   REPORTS_DIR      root search directory (default: .dadaia/reports)
#
# Usage:
#   ./scripts/check-verdict.sh
#   QA_SIDECAR=path/to/qa.handoff.json SECURITY_SIDECAR=path/to/sec.handoff.json \
#     ./scripts/check-verdict.sh

set -euo pipefail

REPORTS_DIR="${REPORTS_DIR:-.dadaia/reports}"

# ---------------------------------------------------------------------------
# Resolve sidecar paths
# ---------------------------------------------------------------------------
resolve_sidecar() {
  local agent="$1"
  local explicit_path="$2"

  if [ -n "$explicit_path" ]; then
    echo "$explicit_path"
    return
  fi

  # Auto-discover: find the most recent *.handoff.json for this agent.
  # The '|| true' guards against find exiting non-zero when REPORTS_DIR is absent
  # (normal in CI where .dadaia/reports/ is gitignored and not checked out).
  find "$REPORTS_DIR" -name "*.handoff.json" -path "*/${agent}/*" 2>/dev/null \
    | sort | tail -1 || true
}

qa_sidecar=$(resolve_sidecar "qa-engineer"         "${QA_SIDECAR:-}")
sec_sidecar=$(resolve_sidecar "security-reviewer"  "${SECURITY_SIDECAR:-}")

# ---------------------------------------------------------------------------
# No sidecars present → no-op pass (normal CI run)
# ---------------------------------------------------------------------------
if [ -z "$qa_sidecar" ] && [ -z "$sec_sidecar" ]; then
  echo "[verdict-gate] INFO: No qa-engineer or security-reviewer handoff sidecars found in '${REPORTS_DIR}'. Gate is a no-op — this is expected on regular CI runs."
  exit 0
fi

# ---------------------------------------------------------------------------
# Helper: check one sidecar
# ---------------------------------------------------------------------------
check_sidecar() {
  local label="$1"
  local path="$2"
  local failed=0

  if [ -z "$path" ]; then
    echo "[verdict-gate] FAIL: No ${label} handoff sidecar found. A sidecar from the other reviewer was present, so both are required."
    return 1
  fi

  if [ ! -f "$path" ]; then
    echo "[verdict-gate] FAIL: ${label} sidecar path does not exist: $path"
    return 1
  fi

  verdict=$(jq -r '.verdict // empty' "$path" 2>/dev/null || true)

  if [ -z "$verdict" ]; then
    echo "[verdict-gate] FAIL: ${label} sidecar at '$path' has no 'verdict' field."
    failed=1
  elif [ "$verdict" = "APPROVED" ]; then
    echo "[verdict-gate] PASS: ${label} verdict = APPROVED (sidecar: $path)"
  else
    reason=$(jq -r '.verdict_reason // "(no reason given)"' "$path" 2>/dev/null || echo "(no reason given)")
    echo "[verdict-gate] FAIL: ${label} verdict = ${verdict} — reason: ${reason} (sidecar: $path)"
    failed=1
  fi

  return $failed
}

# ---------------------------------------------------------------------------
# Run checks
# ---------------------------------------------------------------------------
exit_code=0

check_sidecar "qa-engineer"        "$qa_sidecar"  || exit_code=1
check_sidecar "security-reviewer"  "$sec_sidecar" || exit_code=1

if [ $exit_code -eq 0 ]; then
  echo "[verdict-gate] All required verdicts APPROVED. Release CLOSURE gate passed."
else
  echo "[verdict-gate] One or more verdicts missing or REJECTED. Release CLOSURE gate FAILED."
fi

exit $exit_code
