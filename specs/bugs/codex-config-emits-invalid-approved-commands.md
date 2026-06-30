---
name: codex-config-emits-invalid-approved-commands
status: Closed
severity: LOW
reported: 2026-06-24
surface: dadaia public install (codex target) — runtime_config.codex_config()
session_id: null
---

**Symptom:** The generated Codex `config.toml` still emits an `approved_commands = [...]` array
(`dadaia_workspace/runtime_config.py:165–174`). The `ai-harness-codex` skill (§6) live-verified
against codex-cli 0.139.0 that `approved_commands` is **not a valid config key** — Codex silently
ignores it. Command policy on Codex is owned by the generated Starlark `dadaia-command-policy.rules`,
not this flat list, so the emitted array is dead configuration that misleads readers into thinking
command approval is driven by the TOML list.

**Repro:**
1. `.dadaia/.venv/bin/dadaia public install --target codex` (or inspect `runtime_config.codex_config()`).
2. Observe `approved_commands = [...]` in the produced `.codex/config.toml`.
3. Cross-check against codex-cli 0.139.0 config schema — the key is unrecognized / ignored.

**Expected:** The projected `config.toml` contains only keys valid for the targeted codex-cli
version; command approval is expressed solely through the Starlark `.rules` policy. No dead/ignored
keys that imply a non-existent enforcement path.

**Notes:** Discovered during the 2026-06-24 design-only multi-harness lifecycle-engine investigation
(report:
`.dadaia/reports/dadaia-workspace/software-architect/2026-06-24T004654Z-multiharness-workflow-engine-shift.html`).
Independently flagged by both the ai-engineer (AI-surface pass) and software-architect (engine pass).
Low severity — cosmetic/misleading, not a security or correctness failure; the real policy enforcement
(`.rules`) is unaffected. Out of scope for the engine design itself; filed for separate cleanup. No
operator-local paths/secrets in this record.
