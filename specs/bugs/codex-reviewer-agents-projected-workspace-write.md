---
name: codex-reviewer-agents-projected-workspace-write
status: Closed
severity: HIGH
reported: 2026-06-11
resolved_in: v0.1.13
surface: dadaia_workspace/infrastructure/runtime_transforms/codex_assets.py / .codex/agents/*.toml
session_id: sess_efebeec4
---

**Symptom:** Codex reviewer agents that declare "NEVER edits code" / "never write
fixes" are projected with `sandbox_mode = "workspace-write"`. In the current runtime
projection, `code-reviewer.toml` and `security-reviewer.toml` both have workspace
write access even though their personas are ADDITIVE evidence-only roles. The
read-only allowlist in `codex_assets.py` contains `security-engineer`, but the actual
agent is named `security-reviewer`, so that boundary is missed. `code-reviewer` is
also not included.

**Repro:**
```
sed -n '1,12p' .codex/agents/security-reviewer.toml
sed -n '1,12p' .codex/agents/code-reviewer.toml
# -> sandbox_mode = "workspace-write"
```

**Expected:** Evidence-only reviewer agents project as `sandbox_mode = "read-only"`
unless a specific task explicitly requires an additive report write path through a
controlled mechanism. At minimum, `security-reviewer` must replace the stale
`security-engineer` name in the Codex read-only projection set, and `code-reviewer`
should be classified consistently with its persona.

**Notes:** Current official Codex subagent docs say custom agents may set sandbox
configuration individually and inherit the parent runtime overrides. Dadaia should use
that field to make role boundaries mechanically visible in Codex, especially where the
persona says "never edit".

**Resolution (v0.1.13, T-013-04):** evidence-only reviewers (`code-reviewer`,
`security-reviewer`) project as `sandbox_mode = "read-only"`; the stale
`security-engineer` allowlist entry was corrected; codex_doctor verifies role
boundaries. Evidence in `specs/_archive/releases/v0.1.13/CLOSURE.md` (Dispositions).
