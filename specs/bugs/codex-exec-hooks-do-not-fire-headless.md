---
name: codex-exec-hooks-do-not-fire-headless
status: Closed
severity: HIGH
reported: 2026-06-11
session_id: null
surface: codex projection — .codex/hooks.json / config.toml [hooks] (SDD gate enforcement on Codex)
---

**Symptom:** On `codex exec` (non-interactive) with codex-cli 0.139.0, command hooks
defined for the projected events (SessionStart, PreToolUse, PostToolUse, UserPromptSubmit)
do NOT execute. The dadaia SDD gate / root-whitelist / ctx-inject / heartbeat are wired as
Codex command hooks, so on the headless `codex exec` path **none of them run** — the
workspace's "deterministic enforcement on Codex" is silently absent. An attempted FROZEN
`specs/_archive/` write via `apply_patch` was NOT blocked (file overwritten to "HACKED").

**Repro** (isolated CODEX_HOME, copied auth, throwaway trusted fixture under `.dadaia/tmp/`):
1. Fixture workspace, git-init, mark trusted in CODEX_HOME config: `[projects."<path>"] trust_level = "trusted"`.
2. Wire a PreToolUse hook (`matcher = "^(apply_patch|Edit|Write)$"`) whose command writes a
   marker file (`/usr/bin/touch <marker>`), in ANY of the four documented locations:
   project `.codex/hooks.json`, project inline `[hooks]`, user `~/.codex/hooks.json`, user
   inline `[hooks]`.
3. Run: `codex exec --dangerously-bypass-hook-trust --dangerously-bypass-approvals-and-sandbox
   --skip-git-repo-check -C <fixture> "Create a file via apply_patch"`.
4. The apply_patch tool runs and the file is created, but NO marker file appears.
5. `RUST_LOG=codex_core=debug` shows the bypass warning and an inotify watch on `.codex/hooks`
   — but zero hook load/match/execute trace.

Confirmed across all four config forms, with the `hooks` feature flag ENABLED (visible in
`codex doctor` and the per-turn `CodexHooks` feature tag) and `--dangerously-bypass-hook-trust`
set. Tool calls fire; hooks do not.

**Expected:** The projected Codex command hooks fire on their events, so the SDD gate can
block a FROZEN/MUTATING write — or, if Codex hook execution is genuinely interactive-only
(trust persisted via the `/hooks` TUI browser), the workspace must document the Codex gate
as discipline-only / interactive-only and stop claiming deterministic enforcement on the
headless path.

**Notes:**
- Likely root cause: hook execution gates on interactive trust persistence; the documented
  automation escape hatch `--dangerously-bypass-hook-trust` did not actually fire hooks in
  this build's `codex exec` path.
- **Interactive half CONFIRMED 2026-06-11 (pty-driven TUI probe):** in the interactive
  `codex` TUI with identical wiring (project `.codex/hooks.json`, trusted project, same
  bypass flag), all four events fired (SessionStart, UserPromptSubmit, PreToolUse,
  PostToolUse) AND a gate-shaped PreToolUse hook emitting `{"decision":"block",...}`
  BLOCKED a FROZEN `specs/_archive/` apply_patch (file byte-identical; TUI rendered
  "PreToolUse hook (blocked)"). The defect is therefore scoped precisely to the
  headless `codex exec` path: the same config fires interactively and never under `exec`.
- Full evidence + the P1..P5 contract facts (matcher regex shape, block envelope, shell-exec,
  approved_commands inert, config_file real, `[skills] paths` invalid) recorded in the
  WS-CDX-VERIFY FACTS file for T-013-08.
- Environment: codex-cli 0.139.0, Linux x86_64. No secrets/operator paths in this record.

**Resolution (2026-06-12):** Closed per the bug's own option (b) in v0.1.14: the git chokepoints (pre-commit lease check + pre-push security gate) cover the headless path, and the per-harness enforcement matrix in constitution §8 honestly documents Codex headless as chokepoint-protected (hooks interactive-only) — commit `2e33b9e` on `feature/v0.1.14` + constitution §8 (T-014-17).
