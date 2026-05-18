# Plan: Release — agents-r1-v1

> **Status:** Aprovado
> **Approved:** 2026-05-18
> **Approved-by:** operator
> **Release ID:** agents-r1-v1
> **Owner:** product-engineer
> **Created:** 2026-05-18
> **Companion:** SPEC.md (acceptance criteria + frontmatter sketches)
> **Length budget:** ≤ 300 lines (gate-enforced for releases created 2026-05-17+)

---

## 1. Strategy in one paragraph

Land **foundations first** (rules + skill stubs) so agent frontmatter references resolve
at install time, then ship the **agent files** (new + slim) in one phase with disjoint
write sets, then fill the **skill bodies**, then **refactor workflows** (PE→PM swap),
then **add new workflows**, then **touch the reader + tests**. P0 (close panel-r3-v1) is
already done at `427ab86`. The release closes the moment all tasks are `[x]` DONE,
memory is updated atomically, and the directory is archived.

---

## 2. Phase order and dependency graph

```
P0 (DONE)           P1 (PE)              P2 (PE)               P3 (PE/architect)
[panel-r3-v1   ──►  [rules + grill-me  ──►  [6 new agents +  ──►  [5 new skill
  archived]          preamble +            slim PE/FE +          bodies]
                     skill stubs]          strip Agent ×8]
                                                                      │
                                                                      ▼
                          P6 (SE)           P5 (PE)            P4 (PE)
                          [reader paths  ◄──  [3 new          ◄──  [6 existing
                           + 10 panel        workflows]            workflows
                           test updates]                            PE→PM swap]
                              │
                              ▼
                          P7 (PE+devops)        P8 (PE)
                          [consumer-repo    ──►  [CLOSURE + memory
                           doctor audit]         + archive]
```

Stage+install+doctor sequence runs after **every** phase that touches
`dadaia_workspace/public/`. The doctor is the heartbeat of this release.

---

## 3. Phase-by-phase deliverables

### P0 — Close `panel-r3-v1`

Already done. Branch `release/agents-r1-v1` cut from `427ab86`. `ACTIVE.md` set to
`release: agents-r1-v1 / phase: SPEC`. Nothing further.

### P1 — Foundations

- Author 3 new rules:
  - `dadaia_workspace/public/rules/project-manager-scope.md`
  - `dadaia_workspace/public/rules/project-auditor-scope.md`
  - `dadaia_workspace/public/rules/design-specialist-scope.md`
- Update 3 existing rules:
  - `dadaia_workspace/public/rules/dadaia-workspace-dev-guardrail.md` (append PM/auditor `--force` ban)
  - `dadaia_workspace/public/rules/game-agents-coordination.md` (Decision Authority Matrix row update)
  - `dadaia_workspace/public/rules/game-developer-scope.md` (extend forbidden list)
- Update `dadaia_workspace/public/skills/dadaia-grill-me/SKILL.md` preamble (primary caller → PM).
- Author skill **stubs** (frontmatter only, body = TODO marker resolved in P3) for the
  5 new skills so P2 agent frontmatter references resolve at install time.
- Run `dadaia public stage && dadaia public install --target all && dadaia public doctor`.
- Run `dadaia specs doctor`.

### P2 — Agents

Six new agent files (parallel-safe, disjoint write sets):
- `dadaia_workspace/public/agents/project-manager.md`
- `dadaia_workspace/public/agents/project-auditor.md`
- `dadaia_workspace/public/agents/code-reviewer.md`
- `dadaia_workspace/public/agents/researcher.md`
- `dadaia_workspace/public/agents/security-reviewer.md`
- `dadaia_workspace/public/agents/design-specialist.md`

Slim two agents (parallel-safe with new files; disjoint with each other):
- `dadaia_workspace/public/agents/product-engineer.md`
- `dadaia_workspace/public/agents/frontend-engineer.md`

Strip `Agent` from 8 leaf implementers (parallel-safe, disjoint):
- `software-engineer.md`, `backend-engineer.md`, `qa-engineer.md`,
  `software-architect.md`, `devops-engineer.md`, `game-developer.md`,
  `game-designer.md`, `game-tester.md`.

After: stage+install+doctor; manually verify `Agent` tool only on PM + auditor via
`grep -E '^tools:' dadaia_workspace/public/agents/*.md`.

### P3 — Skill bodies

Fill the 5 skills authored as stubs in P1 (parallel-safe across files):
- `project-orchestration/SKILL.md`
- `architecture-code-review/SKILL.md`
- `security-audit-protocol/SKILL.md`
- `drift-detection/SKILL.md`
- `ux-ui-review/SKILL.md`

After: stage+install+doctor.

### P4 — Refactor 6 existing workflows

PE → PM stage swap (parallel-safe per workflow; each file is independent):
- `spec-refinement.workflow.md`
- `game-spec-definition.workflow.md`
- `cross-cutting-feature.workflow.md`
- `onboarding-new-repo.workflow.md`
- `architecture-review.workflow.md`
- `hotfix-release.workflow.md`

After: stage+install+doctor; `dadaia panel` LIST shows refreshed orchestrator names.

### P5 — 3 new workflows

Parallel-safe across files:
- `audit-cycle.workflow.md`
- `code-review-fan-out.workflow.md`
- `design-validation.workflow.md`

After: stage+install+doctor; `dadaia panel` LIST shows 15 cards total.

### P6 — Reader `paths` field + tests

Sequential within the reader file; then test edits parallel-safe across files:
- `dadaia_workspace/features/agents/reader.py` — extend `_ALLOWED_FIELDS` with `paths`;
  map to optional `paths: dict[str, list[str]] | None` on `AgentDTO`.
- 10 test files per SPEC §9.

Validation: `pytest -q tests/unit/features/agents tests/unit/features/panel tests/unit/features/workflows tests/unit/test_workflow_schema.py` green; then full `pytest -q tests/`.

### P7 — Consumer-repo audit

For every consumer repo enumerated in the workspace catalog:

```bash
cd <consumer-repo> && dadaia public doctor
```

Record results as CLOSURE evidence triples. Any `drift` or `missing` → fix via
`dadaia public install --target all` and retry. Any `unsupported` is acceptable when
the runtime declares the asset type unsupported (e.g. Codex workflows = `[not-applicable]`).

### P8 — CLOSURE

1. Set `ACTIVE.md` phase to `CLOSURE` (allows memory writes).
2. Render memory updates per SPEC §11 from canonical templates in
   `dadaia_workspace/public/templates/memory-*.html.j2`.
3. Write `CLOSURE.md` using `dadaia-release-closure` skill template.
4. Run `dadaia specs doctor` → green.
5. `git mv specs/releases/agents-r1-v1 specs/_archive/releases/agents-r1-v1`.
6. Set `ACTIVE.md` to `release: none / phase: none`.

---

## 4. Parallelism notes

Within a phase, tasks are parallel-safe when their write sets are disjoint. The
following groups are explicitly safe to run as parallel `[-]` tasks:

- **P1 rules group:** 3 new + 3 updates × 1 file each — fully parallel.
- **P2 new agents:** 6 new files — fully parallel.
- **P2 strip-Agent:** 8 edits, 1 file each — fully parallel with each other and with the
  new agents.
- **P2 slim:** PE.md and FE.md are independent — parallel with each other and with
  the strip-Agent and new-agents groups.
- **P3 skills:** 5 files — fully parallel.
- **P4 workflows:** 6 files — fully parallel.
- **P5 new workflows:** 3 files — fully parallel.
- **P6 tests:** 10 files — fully parallel after the reader edit lands.
- **P7 consumer audits:** N consumers — fully parallel.

Sequential gates (cannot be parallelized):
- P1 → P2 (skill stubs must exist before agents reference them).
- P2 → P3 (agents declared first; skill bodies filled second).
- P5 → P6 (workflow files must be present before panel snapshot tests assert them).
- P6 → P7 (tests must pass green locally before sweeping consumer audits).
- P7 → P8 (audit evidence required for CLOSURE).

---

## 5. Risks and mitigations (operational)

| Risk | Where it shows up | Mitigation |
|---|---|---|
| Skill stubs trigger `dadaia public doctor` `[drift]` | end of P1 | Stubs include the canonical frontmatter + minimal `## TODO` body — doctor checks SHA, not "is this a stub"; if doctor flags, switch to placeholder body and re-stage. |
| `Agent` tool accidentally re-added during merge | end of P2 | `grep -E "^\s*-\s*Agent\b" dadaia_workspace/public/agents/*.md` should return only project-manager.md and project-auditor.md. |
| Workflow YAML schema rejects refactored PE→PM stages | end of P4 | Each workflow change is a value-level edit (`agent: project-manager` instead of `agent: product-engineer`); schema does not check agent identity, only structure. |
| 10 panel/test files assume hardcoded counts | end of P6 | Run `pytest -q -k "test_api_agents or test_api_workflows or test_views"` first, then full suite; fix breakage incrementally. |
| Consumer-repo projections fail | end of P7 | Run `dadaia public install --target all --force` per consumer if `drift` persists; record force-install as drift in CLOSURE. |
| Memory atom validation fails at CLOSURE | P8 | `dadaia specs doctor` runs after every memory write; any forbidden `<h2>Changelog</h2>` or broken `<img>` is caught immediately. |

---

## 6. Validation plan

| Check | Command | When |
|---|---|---|
| Specs doctor | `dadaia specs doctor` | after each phase that touches `specs/` |
| Public doctor | `dadaia public stage && dadaia public install --target all && dadaia public doctor` | after each phase that touches `dadaia_workspace/public/` |
| Pytest fast | `pytest -q tests/unit/features/agents tests/unit/features/panel tests/unit/features/workflows tests/unit/test_workflow_schema.py` | end of P6 |
| Pytest full | `pytest -q tests/` | end of P6 and again before CLOSURE |
| Frontmatter grep | `grep -nE '^\s*-?\s*Agent\b' dadaia_workspace/public/agents/*.md` | end of P2 |
| Agent count | `ls dadaia_workspace/public/agents/*.md \| wc -l` → 16 | end of P2 |
| Workflow count | `ls dadaia_workspace/public/workflows/*.workflow.md \| wc -l` → 15 | end of P5 |
| Panel smoke | `dadaia panel` → manual check 16 + 15 cards | end of P6 |

---

## 7. Out of scope (PLAN echo of SPEC §15)

- Sub-agent promotion of `dadaia-grill-me`.
- Enforcement of agent `paths` field.
- Workflow schema `when:` clause.
- Production source outside `features/agents/reader.py` + test files.
- `specs/backlog/ideas.md` edits.

---

## 8. Exit criteria

PLAN exits when:
- TASKS.md is `Aprovado` (next document down the ladder).
- `ACTIVE.md` phase advances to `TASKS` then `IMPLEMENTATION`.
- Implementer agents (PE, SE, FE, devops, etc.) pick up `[-]` tasks per
  `dadaia-task-manager` protocol.
