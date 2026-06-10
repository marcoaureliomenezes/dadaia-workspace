# PLAN: v0.1.9 — Skills cleanup + workflow redesign + memory tree + surface cleanup

**Status:** Em revisão
**Release ID:** v0.1.9
**Owner:** product-engineer
**Created:** 2026-06-06
**Parent program:** v0.2.0

---

## Strategy

This milestone is document-only: no Python code, no database changes, no CLI changes.
All edits are to Markdown files under `dadaia_workspace/public/` (skills, workflows,
agent personas already updated by v0.1.8) and `specs/memory/product/`. The sequencing
is dictated by one hard constraint: **D-OC-1 must pass before any workflow file is
deleted** — no deletion may create a temporary broken-ref state.

### Execution order and rationale

```
T-019-01  D-OC-1 audit: confirm zero stale workflow refs in personas/skills
             │
             ▼
T-019-02  Strip refs from project-orchestration + any persona residuals
             │
             ▼
T-019-03  Delete 7 stale workflows
             │
             ▼
T-019-04  Author release-ship + audit-fanout workflows
             │
             ▼
T-019-05  Skills text-review: 17 skills reviewed (concurrent with T-019-06 below
          only if write sets are confirmed disjoint per T-019-07 note)
             │
T-019-06  product/ tree restructure (depends on quality-assurance.md from v0.1.7)
             │
             ▼
T-019-07  Final propagation: stage + install + doctor
             │
             ▼
T-019-08  qa-engineer gate (pre-commit)
             │
             ▼
T-019-09  Operator in-workspace validation + push
```

T-019-05 (skills review) and T-019-06 (memory tree) have disjoint write sets
(`public/skills/**` vs `specs/memory/product/**`) and may proceed in parallel
once T-019-04 is DONE. T-019-07 requires both to be DONE.

---

## File map

### Deletions (public/workflows — 7 files)

| File | Action |
|---|---|
| `dadaia_workspace/public/workflows/audit-cycle.workflow.md` | DELETE |
| `dadaia_workspace/public/workflows/code-review-fan-out.workflow.md` | DELETE |
| `dadaia_workspace/public/workflows/cross-cutting-feature.workflow.md` | DELETE |
| `dadaia_workspace/public/workflows/design-first-implementation.workflow.md` | DELETE |
| `dadaia_workspace/public/workflows/hotfix-release.workflow.md` | DELETE |
| `dadaia_workspace/public/workflows/spec-refinement.workflow.md` | DELETE |
| `dadaia_workspace/public/workflows/onboarding-new-repo.workflow.md` | DELETE |

### Creations (public/workflows — 2 files)

| File | Action |
|---|---|
| `dadaia_workspace/public/workflows/release-ship.workflow.md` | NEW |
| `dadaia_workspace/public/workflows/audit-fanout.workflow.md` | NEW |

### Edits (public/skills — strip dead refs, text-review pass)

| Skill slug | Priority | Key dead-ref concentrations |
|---|---|---|
| `project-orchestration` | CRITICAL | 15-agent inventory, 7-workflow inventory, Decision Authority table, ship-gate prose referencing old fan-out model |
| `dadaia-workspace-doctor` | HIGH | `product-auditor-agent` name error; Phase 3 report path format stale |
| `dadaia-workspace-manager` | HIGH | Lock primitives pre-v0.1.6; semaphore on `context bind` references |
| `drift-detection` | HIGH | "atomic HTML files" claim must become "Markdown atoms" |
| `dadaia-release-definition` | MEDIUM | CLI commands `dadaia backlog list` / `dadaia bug list` — **CONFIRMED ABSENT** from CLI; T-019-05 item 5 must replace them with direct file reads |
| `dadaia-step0-memory-bootstrap` | MEDIUM | `memory/*.md` Markdown references verified; no stale HTML refs |
| `dadaia-workspace-spec-navigator` | LOW | Stale legacy-feature compat references |
| `dadaia-workspace-spec-reviewer` | LOW | Verify no reference to `evidence/` subtree |
| `dadaia-handoff-emitter` | LOW | Confirm schema version `handoff-v1.1` is the only cited version |
| `dadaia-grill-me` | LOW | Verify report path format is current |
| `dadaia-release-closure` | LOW | Verify no stale phase restriction language |
| `dadaia-task-manager` | LOW | Verify `SDD_LEGACY_FEATURES=1` note is still accurate |
| `harness-primitives` | LOW | Verify no platform-specific names leaked |
| `ai-harness-claude-code` | REVIEW | Restricted-scope skill; verify phase mapping stated |
| `ai-harness-codex` | REVIEW | Restricted-scope skill; verify phase mapping stated |
| `ai-context-engineering` | REVIEW | Restricted-scope skill; verify phase mapping stated |
| `dev-server-registry` | LOW | Verify no dead URLs or stale port ranges |

### Deletions (public/skills — 5 files, already stripped from personas in v0.1.8)

| File | Action |
|---|---|
| `dadaia_workspace/public/skills/frontend-design/SKILL.md` | DELETE |
| `dadaia_workspace/public/skills/frontend-implementation-quality/SKILL.md` | DELETE |
| `dadaia_workspace/public/skills/design-reference-research/SKILL.md` | DELETE |
| `dadaia_workspace/public/skills/design-report-quality-gate/SKILL.md` | DELETE |
| `dadaia_workspace/public/skills/ux-ui-review/SKILL.md` | DELETE |

### Memory tree restructure (specs/memory/product/)

| Change | Detail |
|---|---|
| Create 6 subdirectories | `agents/`, `sdd/`, `panel/`, `platform/`, `distribution/`, `philosophy/` |
| Move 24 atoms | `git mv` each atom to its thematic subdir per SPEC §4.2 (agents:8 / sdd:5 / panel:2 / platform:6 / distribution:2 / philosophy:1 = 24). `test-suite-architecture.md` is archived via `git mv` to `_archive/legacy-memory/<timestamp>/`, not placed in the catalog. |
| Update `index.md` | Rebuild catalog section with subdir-grouped relative links + Mermaid capability-map |
| Confirm `quality-assurance.md` placement | In `sdd/` — created by T-017-02; must exist before T-019-06 begins |
| `agent-sdd-alignment.md` placement | In `agents/` only (single authoritative location). Not in `philosophy/`. |
| `philosophy/` group | 1 atom (`repos-catalog.md`). project-auditor must justify single-atom group in handoff or merge it into nearest group. |
| project-auditor placement review | During T-019-06, auditor reads atoms and confirms or adjusts PE provisional placement; emits handoff with explicit placement list |

### Manifest + runtimes

| Action | Detail |
|---|---|
| `dadaia public stage` | Rebuild manifest after all skill/workflow changes |
| `dadaia public install --force --target all` | Propagate to `.claude/`, `.agents/`, `.opencode/`, `.codex/` |
| `dadaia public doctor` | Confirm exit 0; 9 agents / 17 skills / 2 workflows enumerable; no orphans |
| `dadaia specs doctor` | Confirm exit 0; memory tree valid; no broken links; all atoms have 6 sections |

---

## Fresh-init parity check

The operator runs `dadaia init` on a temporary empty directory (not the live workspace)
after T-019-07 (propagation) is confirmed green:

```bash
mkdir /tmp/dadaia-parity-test
cd /tmp/dadaia-parity-test
dadaia init
```

Expected outcome:
- `.claude/agents/` contains exactly 9 `.md` files matching the 9 core agent names.
- No `frontend-engineer.md`, `design-specialist.md`, or `devops-engineer.md` in core projection.
- `.claude/skills/` or `.agents/skills/` contains exactly 17 skill directories.
- Workflow projection (if applicable) contains exactly 2 workflows.

Any deviation is a blocking finding that must be resolved before T-019-09.

---

## Approach to the skills text-review

The review is applied by `ai-engineer` in a single pass per skill, in the priority
order shown in the file map table above (CRITICAL → HIGH → MEDIUM → LOW → REVIEW).
For each skill:

1. Read the SKILL.md in full.
2. Check each of the 6 review criteria from SPEC §2.2 (Phase mapping, Dead agent refs,
   Dead workflow refs, Evidence store, Slop prose, Stale schema refs).
3. If a criterion is not met, edit the skill text to fix it.
4. Record the changes made or "no change needed" per criterion.
5. Commit after the full 17-skill pass is complete (one commit per logical group of
   skills is acceptable; do not commit after each individual skill unless the change
   is isolable and large).

The review does not redesign skills or change their behavioral contracts. It is a
**trim and correctness pass**, not a feature edit.

---

## Approach to the new workflows

Both new workflows are authoring tasks for `ai-engineer`. The target is short,
deterministic, machine-readable sequences — not prose narratives.

**`release-ship.workflow.md`:**
- YAML or fenced-list step format showing: precondition → action → assertion for each step.
- Steps: (1) pre-push CI gate `dadaia ci preflight`; (2) merge branch → main; (3) tag;
  (4) PyPI publish; (5) smoke test.
- No judgment calls encoded. If a judgment is needed, the workflow terminates and
  delegates to PM.
- Frontmatter: `trigger: operator-elects-to-ship`, `owner: project-manager`,
  `activity_class: MUTATING`.

**`audit-fanout.workflow.md`:**
- Dispatch sequence: (1) project-auditor bootstraps memory; (2) runs doctor checks;
  (3) drift-detection per in-scope feature set (cite the `drift-detection` skill; do NOT
  restate the drift procedure inline); (4) emits findings handoff; (5) PM reads handoff
  and decides next action.
- Frontmatter: `trigger: operator-requests-audit or release-CLOSURE`,
  `owner: project-manager`, `activity_class: ADDITIVE`.

**Shared workflow authoring constraints:**
- Each new workflow file must contain an explicit honesty note: "This is a
  dispatch-reference document. Claude Code and Codex do not auto-load workflow files
  at runtime; a workflow is used only when PM explicitly loads it as context."
- `release-ship.workflow.md` must NOT encode the ship DECISION. It covers the
  deterministic sequence AFTER PM has already decided to ship. If any precondition
  fails, the workflow terminates and delegates back to PM.
- `audit-fanout.workflow.md` must CITE `drift-detection` skill rather than restating
  its procedure (anti-slop — SPEC §12 honesty).

---

## Validation plan

| Step | Validation | Evidence |
|---|---|---|
| After T-019-02 | D-OC-1 check: zero stale workflow refs | doctor output or grep evidence |
| After T-019-03 | 7 files absent from `public/workflows/` | `ls` output or `dadaia public stage` success |
| After T-019-04 | 2 new workflow files present; D-OC-1 still passes | doctor output |
| After T-019-05 | 17-skill count; no dead refs by grep | `dadaia public doctor` enumeration |
| After T-019-05 | 5 frontend/design skill files absent | `ls public/skills/` output |
| After T-019-06 | `product/` has 6 subdirs + `index.md`; no flat atoms; 24 atoms placed (agents:8 / sdd:5 / panel:2 / platform:6 / distribution:2 / philosophy:1) | `find` output |
| After T-019-06 | `dadaia specs doctor` exits 0 | doctor output |
| After T-019-07 | `dadaia public doctor` exits 0; all runtimes clean | doctor output |
| T-019-08 | qa-engineer APPROVE handoff present | handoff JSON |
| T-019-09 | Operator fresh-init parity check PASS | operator sign-off |

---

## Technical risks

| Risk | Severity | Mitigation |
|---|---|---|
| `project-orchestration` ref strip leaves residuals | HIGH | `project-orchestration` is a PM-loaded skill that stays stale through v0.1.8; T-019-01 audits its current state first, T-019-02 rebuilds it. ai-engineer reads every table row and prose block, not just keyword search. |
| Memory tree wikilinks broken after `git mv` | MEDIUM | `dadaia specs doctor` broken-link check; fix before T-019-07 |
| `dadaia specs doctor` doesn't recurse into subdirs for atom-structure checks | MEDIUM | ai-engineer verifies doctor glob depth; file a bug if insufficient before accepting T-019-06 |
| Skills review passes on "no obvious change" without deep reading | LOW | Review checklist per criterion per skill; ai-engineer attests in commit message |
| Fresh-init projects stale manifest (cached) | LOW | `dadaia public install --force` before fresh-init test |
