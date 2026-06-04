# Closure: Release — v0.1.4.6

> **Status:** Aprovado
> **Release ID:** v0.1.4.6
> **Owner:** product-engineer
> **Closed:** 2026-06-04

## Summary

This release deepened the `ai-engineer` persona into the workspace's true harness
specialist and gave every other agent a shared literacy baseline. The inner circle
— three ai-engineer-exclusive deep skills (`ai-harness-claude-code`,
`ai-harness-codex`, `ai-context-engineering`) — compiles the academy lessons into
actionable decision protocols for each harness. The outer circle — one all-agent
literacy skill (`harness-primitives`) — gives every specialist a working mental
model of what each harness primitive is, how dadaia projects them, and when to
defer to `ai-engineer` for depth. A new restriction rule (`harness-skill-scope`)
enforces that the deep skills are `ai-engineer`-only while keeping
`harness-primitives` open.

The `ai-engineer` persona was enriched: `model: claude-opus-4-8` (operator-approved
upgrade), a new "Harness mastery" section referencing the three deep skills, and
compressed inline context-engineering prose replaced by a reference to
`ai-context-engineering`. An operator-approved scope amendment (T-FIX-01) added
the `claude-opus-4-8` entry to the `MODEL_MAP` so the model bump propagates
correctly to Codex via `dadaia public install --target all`.

All 11 tasks completed and approved by code-reviewer, security-reviewer, and
qa-engineer. `dadaia public doctor` exits 0. Pytest 975 passed.

## Tasks completed

| Task ID | Description | Final commit |
|---------|-------------|--------------|
| T-AIE-01 | Skill `ai-harness-claude-code` — Claude Code harness decision protocols | `be8f022` |
| T-AIE-02 | Skill `ai-harness-codex` — Codex harness decision protocols | `be8f022` |
| T-AIE-03 | Skill `ai-context-engineering` — harness-agnostic context engineering | `be8f022` |
| T-AIE-04 | `ai-engineer` persona enrichment (model bump + Harness mastery section) | `be8f022` |
| T-AIE-05 | Rule `harness-skill-scope` — always_on restriction rule | `be8f022` |
| T-HRN-01 | Skill `harness-primitives` — all-agent literacy | `be8f022` |
| T-HRN-02 | Propagation: `dadaia public stage && install --target all && doctor` | `be8f022` |
| T-HRN-03 | Code review — APPROVED | `be8f022` |
| T-HRN-04 | Security review — APPROVED | `be8f022` |
| T-HRN-05 | QA validation — APPROVED | `be8f022` |
| T-FIX-01 | Scope amendment: `MODEL_MAP` + pricing entry for `claude-opus-4-8` | `be8f022` |

## Validations

| Description | Command | Evidence |
|-------------|---------|----------|
| `dadaia public doctor` exits 0; all projections `[ok]` | `dadaia public doctor` | `.dadaia/handoff/dadaia-workspace/2026-06-04T233000Z-qa-engineer-t-hrn-05-validation.handoff.json` — `verdict: APPROVED`; verdict_reason cites "dadaia public doctor exits 0 with all projections [ok]" |
| 4 new skill dirs present in `.claude/skills/` | `ls .claude/skills/ai-harness-claude-code .claude/skills/ai-harness-codex .claude/skills/ai-context-engineering .claude/skills/harness-primitives` | QA handoff confirms all 4 SKILL.md files present |
| `harness-skill-scope.md` present in `.claude/rules/` with `always_on: true` and `[SCOPE ERROR]` block | `ls .claude/rules/harness-skill-scope.md` | QA handoff: "harness-skill-scope.md present in .claude/rules/ with correct always_on:true frontmatter, [SCOPE ERROR] refusal block, and harness-primitives named as open alternative" |
| `ai-engineer.md` has `model: claude-opus-4-8`; Codex TOML has `model = 'gpt-5.5'` | `grep "claude-opus-4-8" dadaia_workspace/public/agents/ai-engineer.md` | QA handoff: "ai-engineer.md has model: claude-opus-4-8; .codex/agents/ai-engineer.toml has model = 'gpt-5.5'" |
| Pytest 975 passed — no regression from public asset authoring or T-FIX-01 | `pytest -q -p no:cacheprovider` | QA handoff: `tests_passed: 975, tests_failed: 0`; `.dadaia/reports/dadaia-workspace/qa-engineer/2026-06-04T233000Z-e2e-validation.html` |
| T-FIX-01 model-map unit tests pass | `pytest -q -p no:cacheprovider tests/unit/infrastructure/runtime_transforms/test_model_mapping.py tests/unit/features/telemetry/` | software-engineer-python handoff `.dadaia/handoff/dadaia-workspace/2026-06-04T232806Z-software-engineer-python-t-fix-01-model-map-opus-4-8.handoff.json`: `"161 passed in 1.25s"` |
| Code review APPROVED — zero CRITICAL/HIGH findings | code-reviewer T-HRN-03 | `.dadaia/handoff/dadaia-workspace/2026-06-04T120000Z-code-reviewer-T-HRN-03.handoff.json` — `verdict: APPROVED`; `findings_critical: 0, findings_high: 0` |
| Security review APPROVED — 8/8 security checks pass | security-reviewer T-HRN-04 | `.dadaia/handoff/dadaia-workspace/2026-06-04T233504Z-security-reviewer-T-HRN-04.handoff.json` — `verdict: APPROVED`; `critical: 0, high: 0, medium: 0, low: 0` |

## Drifts

### scope-amendment-t-fix-01-python-model-map

**Description:** SPEC §4 declared "no Python, TypeScript, Go, or test-file changes."
After authoring `ai-engineer.md` with `model: claude-opus-4-8`, it became clear
that `dadaia public install --target all` for Codex requires a `MODEL_MAP` entry
for the new model, otherwise Codex's `config.toml` would carry an unmapped model
identifier. The SPEC principle "no Python" was written to prevent feature sprawl,
not to break the propagation chain for a one-line model alias.

**Resolution:** Operator approved T-FIX-01 as a scope amendment on 2026-06-04.
`software-engineer-python` added exactly one `MODEL_MAP` entry
(`"claude-opus-4-8": "gpt-5.5"`), one pricing row in `pricing.py` mirroring
opus-4-7, and updated the test guard from 3 to 4 entries. Code review confirmed
the change is minimal and bounded; security review confirmed no regression.

**Memory updates:** `specs/memory/product/multi-platform-parity.md` — no content
change needed; the model-map machinery is existing; only the entry list changed.
`specs/memory/tech-stack.md` — updated model assignments table to reflect
`claude-opus-4-8` for `ai-engineer`.

## Memory updates

- `specs/memory/tech-stack.md` — updated `ai-engineer` model assignment from
  `claude-sonnet-4-6` to `claude-opus-4-8` in the Model assignments table.
- `specs/memory/product/index.md` — added 4 new harness feature entries to the
  catalog: `ai-harness-claude-code`, `ai-harness-codex`, `ai-context-engineering`,
  `harness-primitives`. Also added `harness-skill-scope` as a rule (non-feature)
  referenced under agent-entity surface notes.
- `specs/memory/product/ai-harness-claude-code.md` — new feature atom (first
  production entry for this AI-entity skill).
- `specs/memory/product/ai-harness-codex.md` — new feature atom.
- `specs/memory/product/ai-context-engineering.md` — new feature atom.
- `specs/memory/product/harness-primitives.md` — new feature atom.
- `specs/memory/product/agent-orchestration.md` — updated `ai-engineer` model
  field note; updated skill inventory reference to include the 4 new skills and
  the `harness-skill-scope` rule.
- `specs/memory/architecture.md` — updated `rules folder` section to list
  `harness-skill-scope` as the 5th canonical public rule; updated agent-topology
  agent count from 15 to 15 (count unchanged; ai-engineer enrichment is not a new
  agent, but the persona description was updated to reflect `claude-opus-4-8` and
  the new skill authority).

## Backlog returns

- `backlog/candidates.md` ← `ai-harness-opencode` skill — compiled mental model
  + decision protocols for opencode runtime (deferred from v0.1.4.6 pending
  opencode runtime stability).

## Archive decision

**MOVE** — release directory will be moved to
`specs/_archive/releases/v0.1.4.6/` via `git mv`. `ACTIVE.md` will be updated
to point to the next release or `release: none`.
