#!/usr/bin/env bash
# WS-CDX-VERIFY (T-013-08) — repeatable live Codex contract harness.
#
# Drives the real `codex` binary against trusted throwaway workspaces to resolve the
# Codex hook/config contract points the runtime fidelity audit left UNVERIFIED:
#   P1 PreToolUse matcher regex form           (anchored `^(apply_patch|Edit|Write)$`)
#   P2 `{"decision":"block"}` stdout envelope   (vs exit-2 / permissionDecision)
#   P3 shell-exec of env-prefixed command       (`VAR=val cmd`)
#   P4 (F-6) `approved_commands` config key      (real vs unknown)
#   P5 (F-8) `[agents."<n>"] config_file` key    (real vs unknown)
#   LIVE  do command hooks fire under `codex exec` at all?
#   LIVE  is a FROZEN `specs/_archive/` write blocked end-to-end?
#
# SAFETY: never touches ~/.codex. Builds an isolated CODEX_HOME under a throwaway dir,
# copying ONLY auth.json (chmod 600). All fixtures are git-init'd throwaway workspaces
# under the throwaway dir — NEVER inside the repo tree.
#
# Output: writes a FACTS.md and per-probe marker files into $OUT_DIR. Prints a
# machine-greppable line `PROBE <name> <PASS|FAIL|SKIP> <detail>` per probe so the
# pytest wrapper can assert on results. Exit 0 if the harness ran; non-zero only on
# harness (not contract) failure.
#
# Usage:
#   run_codex_contract_probes.sh <OUT_DIR>
# Env:
#   CODEX_BIN   override the codex binary (default: `codex` on PATH)
#   SKIP_LIVE_MODEL=1   skip probes that spend model credits (config-key probes only)
set -u

OUT_DIR="${1:-}"
if [[ -z "$OUT_DIR" ]]; then
  echo "usage: $0 <OUT_DIR>" >&2
  exit 2
fi
mkdir -p "$OUT_DIR"
CODEX_BIN="${CODEX_BIN:-codex}"

if ! command -v "$CODEX_BIN" >/dev/null 2>&1; then
  echo "PROBE harness SKIP codex-binary-absent"
  exit 0
fi
if [[ ! -f "$HOME/.codex/auth.json" ]]; then
  echo "PROBE harness SKIP codex-auth-absent"
  exit 0
fi

# --- isolated CODEX_HOME (copy auth ONLY; never modify the original) ---
export CODEX_HOME="$OUT_DIR/codex_home"
mkdir -p "$CODEX_HOME"
cp "$HOME/.codex/auth.json" "$CODEX_HOME/auth.json"
chmod 600 "$CODEX_HOME/auth.json"

emit() { echo "PROBE $1 $2 ${3:-}"; }

# ---------------------------------------------------------------------------
# P4/P5/skills — config-key recognition via --strict-config (NO model credits
# spent: config parse happens before the model turn; a 6s timeout cuts any turn).
# A config-parse error => key UNKNOWN; no error => key ACCEPTED.
# ---------------------------------------------------------------------------
FX_CFG="$OUT_DIR/fixture_config"
mkdir -p "$FX_CFG"
( cd "$FX_CFG" && git init -q 2>/dev/null && git config user.email t@t && git config user.name t )

strict_probe() {  # name, toml-body  -> echoes PROBE line
  local name="$1" body="$2"
  printf '%s\n' "$body" > "$CODEX_HOME/config.toml"
  local out
  out="$(timeout 6 "$CODEX_BIN" exec --strict-config --skip-git-repo-check \
        -C "$FX_CFG" "x" < /dev/null 2>&1)"
  if echo "$out" | grep -qiE "unknown configuration field"; then
    emit "$name" "UNKNOWN-KEY" "$(echo "$out" | grep -ioE 'unknown configuration field `[^`]+`' | head -1)"
  else
    emit "$name" "ACCEPTED-KEY"
  fi
}

strict_probe "P4-approved_commands"   'approved_commands = ["git"]'
strict_probe "P5-agents.config_file"  $'[agents."t"]\nconfig_file = "x.toml"'
strict_probe "agents.model"           $'[agents."t"]\nmodel = "gpt-5.5"'
strict_probe "skills.paths"           $'[skills]\npaths = [".agents/skills"]'
strict_probe "skills.config"          $'[[skills.config]]\nenabled = true\npath = ".agents/skills/x"'

# ---------------------------------------------------------------------------
# LIVE — do command hooks fire under `codex exec`?  (spends a few model tokens)
# ---------------------------------------------------------------------------
if [[ "${SKIP_LIVE_MODEL:-0}" != "1" ]]; then
  FX_EV="$OUT_DIR/fixture_events"
  rm -rf "$FX_EV"; mkdir -p "$FX_EV"
  ( cd "$FX_EV" && git init -q && git config user.email t@t && git config user.name t )
  MK="$OUT_DIR/markers"; rm -rf "$MK"; mkdir -p "$MK"
  cat > "$CODEX_HOME/config.toml" <<EOF
[projects."$FX_EV"]
trust_level = "trusted"

[[hooks.SessionStart]]
[[hooks.SessionStart.hooks]]
type = "command"
command = "/usr/bin/touch $MK/SessionStart"

[[hooks.PreToolUse]]
matcher = "^(apply_patch|Edit|Write)\$"
[[hooks.PreToolUse.hooks]]
type = "command"
command = "/usr/bin/touch $MK/PreToolUse"

[[hooks.PostToolUse]]
[[hooks.PostToolUse.hooks]]
type = "command"
command = "/usr/bin/touch $MK/PostToolUse"
EOF
  timeout 150 "$CODEX_BIN" exec \
    --dangerously-bypass-hook-trust --dangerously-bypass-approvals-and-sandbox \
    --skip-git-repo-check -C "$FX_EV" \
    "Create a file named hello.txt with the word HELLO via apply_patch. Nothing else." \
    < /dev/null > "$OUT_DIR/events.out" 2>&1
  if [[ -f "$FX_EV/hello.txt" ]]; then
    if [[ -f "$MK/PreToolUse" ]]; then
      emit "LIVE-hooks-fire" "PASS" "PreToolUse marker present"
    else
      emit "LIVE-hooks-fire" "FAIL" "apply_patch ran but NO hook marker fired"
    fi
  else
    emit "LIVE-hooks-fire" "INCONCLUSIVE" "model did not create the file"
  fi

  # -------------------------------------------------------------------------
  # LIVE — FROZEN specs/_archive write blocked end-to-end?
  # -------------------------------------------------------------------------
  FX_FZ="$OUT_DIR/fixture_frozen"
  rm -rf "$FX_FZ"; mkdir -p "$FX_FZ/specs/_archive" "$FX_FZ/.codex/hooks"
  ( cd "$FX_FZ" && git init -q && git config user.email t@t && git config user.name t )
  printf 'ORIGINAL FROZEN CONTENT\n' > "$FX_FZ/specs/_archive/some.md"
  ( cd "$FX_FZ" && git add -A && git commit -qm init )
  ORIG="$(sha256sum "$FX_FZ/specs/_archive/some.md" | cut -d' ' -f1)"
  cat > "$FX_FZ/.codex/hooks/frozen_gate.py" <<'PY'
import json, sys
try:
    p = json.loads(sys.stdin.read())
except Exception:
    p = {}
ti = p.get("tool_input") or {}
blob = ""
if isinstance(ti, dict):
    blob = str(ti.get("command", "")) + str(ti.get("file_path", ""))
if "specs/_archive" in blob:
    print(json.dumps({"decision": "block", "reason": "FROZEN: specs/_archive is read-only"}))
PY
  cat > "$FX_FZ/.codex/hooks.json" <<EOF
{ "hooks": { "PreToolUse": [ { "matcher": "^(apply_patch|Edit|Write)\$",
  "hooks": [ { "type": "command", "command": "/usr/bin/python3 '$FX_FZ/.codex/hooks/frozen_gate.py'" } ] } ] } }
EOF
  cat > "$CODEX_HOME/config.toml" <<EOF
[projects."$FX_FZ"]
trust_level = "trusted"
EOF
  timeout 150 "$CODEX_BIN" exec \
    --dangerously-bypass-hook-trust --dangerously-bypass-approvals-and-sandbox \
    --skip-git-repo-check -C "$FX_FZ" \
    "Use apply_patch to change specs/_archive/some.md so its only content is the word HACKED." \
    < /dev/null > "$OUT_DIR/frozen.out" 2>&1
  NEW="$(sha256sum "$FX_FZ/specs/_archive/some.md" | cut -d' ' -f1)"
  if [[ "$ORIG" == "$NEW" ]]; then
    emit "LIVE-frozen-blocked" "PASS" "file unchanged (gate blocked the write)"
  else
    emit "LIVE-frozen-blocked" "FAIL" "file overwritten (gate did NOT block on codex exec)"
  fi
else
  emit "LIVE-hooks-fire" "SKIP" "SKIP_LIVE_MODEL=1"
  emit "LIVE-frozen-blocked" "SKIP" "SKIP_LIVE_MODEL=1"
fi

echo "harness-complete"
exit 0
