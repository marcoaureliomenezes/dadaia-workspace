# SPEC — v0.2.2 Full Codex Compatibility

**Status:** Aprovado
**Release:** v0.2.2
**Segment:** alpha-1
**Source backlog:** `specs/backlog/full-codex-compatibility.md`
**Operator approval:** 2026-06-07 — "Go ahead" and complete the canonical SDD workflow through PR, without merge.

---

## Summary

This release makes dadaia-workspace first-class compatible with Codex. The release fixes the
known Codex projection defects found in the 2026-06-07 audit:

- generated Codex agents must not corrupt semantic identifiers such as skill names;
- generated Codex rule policy must use real Codex `.rules` files for command policy;
- generated Codex agents must not point to Claude-only protocol paths;
- Codex orchestration wording must reflect current explicit subagent/custom-agent support;
- hooks and projection doctor must be validated strongly enough to prevent drift recurrence;
- memory must record the durable Codex compatibility invariant during closure.

## Evidence

- Audit report:
  `.dadaia/reports/dadaia-workspace/ai-engineer/2026-06-07T152643Z-codex-operability-audit.html`
- Audit handoff:
  `.dadaia/handoff/dadaia-workspace/2026-06-07T152643Z-ai-engineer-codex-operability-audit.handoff.json`
- Backlog:
  `specs/backlog/full-codex-compatibility.md`
- Official Codex docs checked for release definition:
  - `https://developers.openai.com/codex/subagents`
  - `https://developers.openai.com/codex/rules`
  - `https://developers.openai.com/codex/hooks`
  - `https://developers.openai.com/codex/skills`
  - `https://developers.openai.com/codex/config-advanced`

## Scope

### In scope

1. Codex projection code:
   - `dadaia_workspace/infrastructure/runtime_transforms/codex.py`
   - `dadaia_workspace/infrastructure/runtime_transforms/model_mapping.py`
   - `dadaia_workspace/infrastructure/public_assets.py`

2. Codex-facing public AI surface:
   - `dadaia_workspace/public/agents/**`
   - `dadaia_workspace/public/skills/**`
   - `dadaia_workspace/public/rules/**`
   - `dadaia_workspace/public/workflows/**`
   - `dadaia_workspace/public/runtime/codex/**`
   - `dadaia_workspace/public/scripts/**`

3. Runtime projections and instantiated workspace sync:
   - `.dadaia/agentic/**`
   - `.codex/**`
   - `.claude/**`
   - `.opencode/**`
   - `.agents/**`
   - root/scoped generated `AGENTS.md`/`CLAUDE.md`

4. Tests and doctors:
   - projection contract tests;
   - public doctor semantic checks for Codex referential integrity;
   - hook/config/rules shape tests.

5. Memory and closure:
   - update current product truth for Codex compatibility;
   - archive this release on closure.

### Out of scope

- Publishing a package.
- Merging the PR.
- OpenCode deep redesign beyond no-regression.
- Non-Codex product features.

## Acceptance Criteria

### AC-1 — Codex custom agents are valid

- `.codex/config.toml` references every generated `.codex/agents/*.toml`.
- Every agent TOML parses.
- No generated Codex agent references a non-existent skill.
- `ai-engineer.toml` references `ai-harness-claude-code`, not `ai-harness-gpt-5.3-codex`.

### AC-2 — Model mapping is precise

- Claude model identifiers in source frontmatter map to Codex model identifiers only in model fields or explicit model tables.
- The transformer does not rewrite skill names, file paths, agent names, or other semantic identifiers containing `claude-`.

### AC-3 — Codex rules are real command policy

- Generated Codex command policy is represented as official Starlark `.rules` files.
- Markdown protocols are not presented as executable Codex Rules.
- Sensitive commands have prompt/forbid decisions.

### AC-4 — Codex hooks are generated and validated

- `.codex/hooks.json` contains supported hook events.
- Hook commands point to existing workspace-local scripts after install.
- `ctx-inject.sh` can emit Codex-compatible JSON.

### AC-5 — Codex-native custom-agent config

- Generated TOML includes supported Codex role boundaries where feasible.
- Review/audit roles are least-privilege/read-only where feasible.
- Project-local config does not contain provider/auth/telemetry settings.

### AC-6 — Orchestration wording is current and honest

- Memory and personas distinguish workflow reference docs from explicit Codex subagent/custom-agent delegation.
- No stale "Codex is only reference-only" blanket claim remains.
- No fake dispatch tool is described as product truth.

### AC-7 — Harness-neutral protocol references

- Generated Codex agents do not reference `.claude/rules/...` as their governing protocol path.
- Shared protocol references are harness-neutral or Codex-native.

### AC-8 — Doctor prevents recurrence

- `dadaia public doctor` fails on Codex semantic drift:
  - non-existent skill references;
  - missing TOML files;
  - stale Claude-only protocol paths;
  - malformed rules/config/hooks;
  - unsupported or fake Codex projection claims.

### AC-9 — SDD closure

- Tests pass.
- `dadaia public stage && dadaia public install --target all && dadaia public doctor` passes.
- `dadaia specs doctor` has no new errors.
- Memory is updated during closure.
- Release is archived.
- Branch is pushed and PR opened; PR is not merged.

## Grill Confirmation

The operator explicitly authorized this release after reading the Codex operability audit and
asked to proceed through the full SDD ritual. The three decision points from the backlog are
resolved for this release:

1. `.codex/rules` is reserved for official Codex `.rules` command policy; Markdown protocols
   must not pretend to be executable rules.
2. Codex explicit subagent/custom-agent delegation becomes first-class wording; workflow files
   remain reference docs, not automatic executors.
3. Codex custom-agent TOML should encode least-privilege role boundaries where the current
   Codex config supports it, and document anything still enforced by hooks/prose.

No additional operator question is required before implementation.
