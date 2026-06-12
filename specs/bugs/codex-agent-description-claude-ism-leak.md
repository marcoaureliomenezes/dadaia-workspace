---
name: codex-agent-description-claude-ism-leak
status: Closed
severity: MEDIUM
reported: 2026-06-11
resolved_in: v0.1.13
surface: install_helpers.install_codex_agents + runtime_transforms/codex.transform_for_codex + codex_doctor D-CX-4
session_id: null
---

**Symptom:** The agent TOML `description` field is projected to `.codex/agents/*.toml`
without passing through `transform_for_codex`, so Claude-isms ship on the very field
Codex uses as the spawn-trigger surface. Live instance evidence:
`.codex/agents/project-manager.toml` description contains "dispatches sub-agents via
Agent tool" — `Agent` is a Claude Code tool name with no Codex meaning.

**Repro:** `dadaia public install --target codex` on any workspace; inspect
`.codex/agents/project-manager.toml` frontmatter `description`. Run
`dadaia public doctor` — D-CX-4 reports `[ok]` (it checks only `claude-*` model ids
and `.claude/rules/` literal paths; it is blind to tool-name Claude-isms).

**Expected:** The no-Claude-isms projection invariant covers every Codex-visible
field. `description` must run through the same replacement table as the body, and
D-CX-4 should flag Claude-only tool names (`Agent tool`, `Task tool`) in Codex
artifacts.

**Notes:** Found by the Codex runtime fidelity audit (F-4),
`specs/audits/2026-06-12T001813Z/codex-runtime-fidelity-review.md`. Body transform is
applied at `install_helpers.py` (`install_codex_agents`); description passthrough is
the gap.

**Resolution (v0.1.13, T-013-09):** `description` now runs through the same
replacement table as the body; D-CX-4 flags Claude tool names (`Agent tool`,
`Task tool`) in Codex artifacts; unit tests cover both. Evidence in
`specs/_archive/releases/v0.1.13/CLOSURE.md` (Dispositions).
