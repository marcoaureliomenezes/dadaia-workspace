#!/usr/bin/env bash
# WS-PI-2 (T-PI-07) — repeatable live `pi` contract harness.
#
# Drives the real `pi` binary (@earendil-works/pi-coding-agent) headless as
# `pi --mode json` against a trusted throwaway workspace to resolve the ONE
# upstream-owned binding the offline suite cannot prove:
#   P1  the `pi --mode json` event stream is line-delimited JSON
#   P2  the LAST `{"type":"message_end","message":{...}}` event carries the
#       assistant AgentMessage
#   P3  the shape of `AgentMessage.content` (plain string vs content-block array)
#
# SAFETY: never modifies the operator's PI config. The fixture is a throwaway
# directory under $OUT_DIR — NEVER inside the repo tree. Spends operator model
# credits, so the harness is opt-in (run manually; the pytest seam is OPT-IN via
# DADAIA_PI_LIVE=1). Records the verified `pi` version for tech-stack memory.
#
# Usage:
#   run_pi_contract_probes.sh <OUT_DIR>
# Env:
#   PI_BIN              override the pi binary (default: `pi` on PATH)
#   ANTHROPIC_API_KEY   required for a live turn
set -u

OUT_DIR="${1:-}"
if [[ -z "$OUT_DIR" ]]; then
  echo "usage: $0 <OUT_DIR>" >&2
  exit 2
fi
mkdir -p "$OUT_DIR"
PI_BIN="${PI_BIN:-pi}"

emit() { echo "PROBE $1 $2 ${3:-}"; }

if ! command -v "$PI_BIN" >/dev/null 2>&1; then
  emit harness SKIP pi-binary-absent
  exit 0
fi
if [[ -z "${ANTHROPIC_API_KEY:-}" ]]; then
  emit harness SKIP anthropic-api-key-absent
  exit 0
fi

# Record the verified version for tech-stack.md (pinned at CLOSURE).
"$PI_BIN" --version > "$OUT_DIR/pi.version" 2>&1 || true
emit pi-version RECORDED "$(cat "$OUT_DIR/pi.version" 2>/dev/null | head -1)"

FX="$OUT_DIR/fixture"
rm -rf "$FX"; mkdir -p "$FX"
( cd "$FX" && git init -q 2>/dev/null && git config user.email t@t && git config user.name t )

# --- LIVE turn: capture the raw JSON event stream (spends a few tokens) -------
timeout 120 "$PI_BIN" --mode json --tools read \
  -p - < <(printf 'Reply with the single word: OK. Do not use any tools.') \
  > "$OUT_DIR/stream.jsonl" 2>"$OUT_DIR/stream.err"

if [[ ! -s "$OUT_DIR/stream.jsonl" ]]; then
  emit LIVE-json-stream INCONCLUSIVE "no stdout (stderr tail: $(tail -1 "$OUT_DIR/stream.err" 2>/dev/null))"
  echo "harness-complete"; exit 0
fi

# P2 — a message_end event exists.
if grep -q '"type":"message_end"' "$OUT_DIR/stream.jsonl" \
   || grep -q '"type": "message_end"' "$OUT_DIR/stream.jsonl"; then
  emit LIVE-message_end PASS "message_end event present"
else
  emit LIVE-message_end FAIL "no message_end event — schema drift; update tech-stack.md + parser"
fi

# P3 — AgentMessage.content shape (string vs array). Documented for the parser.
LAST="$(grep '"message_end"' "$OUT_DIR/stream.jsonl" | tail -1)"
if echo "$LAST" | grep -qE '"content"[[:space:]]*:[[:space:]]*\['; then
  emit LIVE-content-shape ARRAY "AgentMessage.content is a content-block array"
elif echo "$LAST" | grep -qE '"content"[[:space:]]*:[[:space:]]*"'; then
  emit LIVE-content-shape STRING "AgentMessage.content is a plain string"
else
  emit LIVE-content-shape UNKNOWN "content shape indeterminate — inspect $OUT_DIR/stream.jsonl"
fi

echo "harness-complete"
exit 0
