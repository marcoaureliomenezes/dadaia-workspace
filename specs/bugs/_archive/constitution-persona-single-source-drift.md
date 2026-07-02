---
title: constitution-persona-single-source-drift
severity: High
opened: 2026-06-06
session_id: null
status: Closed
adopted: 0.1.6
source: ".dadaia/reports/dadaia-workspace/2026-06-06T193749Z/audit.md (§2, §6); handoff .dadaia/handoff/dadaia-workspace/2026-06-06T193749Z-project-auditor-lifecycle-audit.handoff.json"
resolved_in: 0.1.7 (rc-4, T-017-31)
---

**Resolution (0.1.7 rc-4, T-017-31):** memory-write phase aligned to DEFINITION+CLOSURE across all surfaces — fixed the CLOSURE-only claim in `dadaia-step0-memory-bootstrap/SKILL.md` and two in `dadaia-release-closure/SKILL.md` (AGENTS.md + constitution §13 were already correct; the `quality-assurance.md` path ref was a false finding — the file exists). Added an enforcement lint `check_memory_phase_single_source` (SINGLE-SRC-1) wired into `dadaia public doctor` so the drift cannot recur, with test `test_check_memory_phase_single_source`.


# Bug: constitution-persona-single-source-drift

## Description

The project-auditor lifecycle audit (2026-06-06T193749Z) found **four
single-source-of-truth contradictions** where one governance fact is duplicated
and diverged across the constitution and persona files, violating constitution
§12.3 (a fact must live in exactly one place). These are defects, not design
decisions — each has a determinable canonical answer. They are grouped here as
one bug because v0.2.0's milestones v0.1.7 (constitution v2 freeze) and v0.1.8
(persona roster rewrite) re-author exactly this text; the fix is to make the
re-authored single source correct, not to patch the old duplicated copies.

### P1a — memory-write-phase contradiction (HIGH)

`@product-engineer.md:86-89` and `@specs/constitution.md:210-213` permit memory
writes in **DEFINITION + CLOSURE**. `@product-engineer.md:208-209` and
`@workspace-protocol.md §5` say **CLOSURE-only** ("the gate enforces this"). Same
fact, two sources, diverged. Risk: a persona claims a DEFINITION-phase memory
write the gate denies → soft-deadlock (the exact failure class of prior lock
incidents).

**Canonical answer (already chosen by the v0.2.0 SPEC §5):** product-engineer may
write memory during **DEFINITION and CLOSURE**. The v0.1.6 gate path classifier
must permit this for product-engineer and deny it for all other agents. The
CLOSURE-only statements in product-engineer.md and workspace-protocol §5 are the
losing copies and must be deleted/aligned. **NOTE:** this is provisional pending
the mandatory grill (the SPEC pre-dates the audit confirmation); see the grill
agenda in the dispatch report.

### P1b — quality-assurance.md path drift (HIGH)

`@specs/constitution.md:201` names `specs/memory/product/quality-assurance.md`;
the file actually lives at `specs/memory/product/sdd/quality-assurance.md`. The
documented path is absent on disk.

**Canonical answer:** v0.2.0 §5 OD-5 + the v0.1.9 memory-tree restructure
(`product/{agents,sdd,panel,...}/`) determine the final path. Constitution §13/§201
must match whatever the v0.1.9 tree lands on. Constitution must match disk — no
dangling path.

### P1c — project-auditor dispatch wording self-contradiction (HIGH)

`@project-auditor.md:63-65` says "NOT dispatched by PM, both Tier-1, do not nest";
`@project-auditor.md:277` says "Dispatched by project-manager via the audit-fanout
workflow." Likely intent: `audit-fanout` is operator/top-level orchestration, not
PM nesting the auditor as a leaf sub-agent.

**Canonical answer:** reword one section so they agree (audit-fanout = top-level,
not PM→auditor nesting). Resolved in the v0.1.8 persona rewrite.

### P1d — dual grill-me ownership (HIGH)

`@project-manager.md:86-91` (PM intake grill, mandatory before dispatch) vs
`@product-engineer.md:284-286` (PE release-definition grill on the picked set
before SPEC). Both claim mandatory ownership; the handoff boundary is undefined.

**Canonical answer:** state once that PM owns the **intake** grill and
product-engineer owns the **release-definition** grill on the picked set; the
other persona cites it (no duplication). Resolved in the v0.1.8 persona rewrite.

## P2 items (low priority, fold in opportunistically)

These three MEDIUM findings are not blocking but should be fixed in the same
v0.1.8 persona pass to avoid a second drift round:

- **P2b — worker→worker wording in qa-engineer** (`@qa-engineer.md:258-261,
  391-392`): "escalate to security-reviewer" / "when invoked by
  software-architect or product-engineer" — those workers hold no `Agent` tool.
  Route through project-manager.
- **P2c — gate-trio sequence invisible in reviewer personas**: add a one-line cite
  of §11's ordered trio (qa→commit / security→push / code-review→PR) to each of
  `@qa-engineer.md`, `@security-reviewer.md`, `@code-reviewer.md` (cite §11, do
  not duplicate).
- **P2a — plugin stubs vs §14 persona-existence rule** (`@specs/constitution.md:236-238`):
  the rule requires every persona to own a §7 phase; the 3 plugin stubs
  (frontend/design/devops) own none. Add an explicit plugin-stub exemption in the
  v0.1.7 constitution freeze. NOTE: v0.2.0 OD-4 removes devops-engineer from
  `public/agents/` entirely; the exemption then covers only frontend/design.

## Environment

- dadaia version: working tree on `feature/0.2.0` base; v0.2.0 DEFINITION phase
- OS: Linux / Python 3.12

## Root cause hypothesis

The constitution and personas grew incrementally without a §12.3 single-source
audit. v0.2.0 re-authors both surfaces; the fix is to apply the canonical answers
above when authoring the v0.1.7 constitution and v0.1.8 personas, then verify
`dadaia specs doctor` / a single-source lint catches any residual duplication.

## Resolution

**Bug-always-solved (release-governance):** adopted into **v0.2.0** — P1a/P1b/P2a
land in milestone **v0.1.7** (constitution v2 freeze + memory canon); P1c/P1d/P2b/P2c
land in milestone **v0.1.8** (persona roster rewrite). product-engineer sets the
final `adopted:`/`superseded_by:` annotation and TASKS coverage at SPEC time. This
bug is **not** silently dropped — every sub-finding maps to a v0.2.0 milestone
acceptance criterion. The P1a canonical choice is **provisional** until confirmed
by the mandatory grill (see dispatch report).
