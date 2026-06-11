---
name: codex-rules-generated-with-undocumented-command-allowed
status: Open
severity: HIGH
reported: 2026-06-11
surface: dadaia_workspace/infrastructure/runtime_transforms/codex_assets.py / .codex/rules/dadaia-command-policy.rules
session_id: sess_efebeec4
---

**Symptom:** `dadaia public install --target codex` generates
`.codex/rules/dadaia-command-policy.rules` with a `command_allowed(cmd)` function.
The current official Codex Rules documentation describes `.rules` files as Starlark
files containing `prefix_rule(...)` declarations, loaded from `rules/` under active
config layers. It documents `pattern`, `decision`, `justification`, `match`, and
`not_match`; it does not document `command_allowed`.

**Repro:**
```
dadaia public install --target codex
sed -n '1,80p' .codex/rules/dadaia-command-policy.rules
# -> def command_allowed(cmd):
```

**Expected:** Generated Codex command policy uses documented `prefix_rule(...)`
syntax, and tests/doctor validate that the emitted file can be checked with Codex's
rules loader (for example `codex execpolicy check` when available). If
`command_allowed` is still supported by a private compatibility path, the product must
document that explicitly and pin a compatibility test; otherwise command policy may be
silently ignored or fail to load in current Codex.

**Notes:** Found while refreshing official Codex documentation for the requested
Codex entity academy/skill/audit work. Relevant official page:
https://developers.openai.com/codex/rules
