# TASKS: v0.2.0 — milestone index (READ-ONLY)

**Status:** Em revisão
**Release ID:** v0.2.0

> **This file is a read-only INDEX, not a task list.** (architect F-01: the umbrella must not duplicate
> per-milestone tasks — duplicate `[-]` markers across two files = dual gate-authority.) The SDD gate and
> all implementers use the **per-milestone `TASKS.md`** as the single authoritative source. Do not flip
> markers here.

This release is delivered as four non-deployed internal milestones + one deploy milestone, each with its
own SPEC/PLAN/TASKS, implemented + tested + gate-reviewed + operator-validated **in this workspace** before
the next opens. **Only v0.2.0 deploys.**

| # | Milestone | Authoritative tasks | Scope |
|---|-----------|---------------------|-------|
| 1 | **v0.1.6** | `v0.1.6/TASKS.md` (T-016-00..10) | State model: one cross-platform TTL-lease, O_EXCL CAS, fail-safe gate (single acquisition point), GC, cut Lock-3/session-writer/semaphore.py, agents.index.json |
| 2 | **v0.1.7** | `v0.1.7/TASKS.md` (T-017-PRE, 01..03) | Constitution v2 + lifecycle law (normative §7 matrix) + memory canon + quality-assurance.md (THE FREEZE) |
| 3 | **v0.1.8** | `v0.1.8/TASKS.md` (T-018-01..09) | Coordinator + sub-agent architecture, roster 15->9, persona tailoring (PM <=120 lines), A-2 lease model |
| 4 | **v0.1.9** | `v0.1.9/TASKS.md` (T-019-01..09) | Skills 22->17 + text review, workflow redesign (delete 7, author release-ship + audit-fanout), product/ tree (24 atoms) |
| 5 | **v0.2.0** | `integration/TASKS.md` (T-020-01..05) | Integration, full lifecycle dogfood, drift-elimination to instance, ship-trio, single deploy, CLOSURE |

**Dependency order (acyclic):** v0.1.6 -> v0.1.7 -> v0.1.8 -> v0.1.9 -> v0.2.0. Each milestone's gate sequence
(qa->commit, security->push, code-review->PR) runs locally on `feature/0.2.0`; evidence in `.dadaia/handoff/`
+ `.dadaia/reports/` (no `evidence/` subtree — architect A-1). Operator gives in-workspace sign-off per
milestone before the next opens.

**Review status:** all five milestones specialist-reviewed (software-architect: v0.1.6 + integration;
ai-engineer: v0.1.7/v0.1.8/v0.1.9) and findings incorporated. v0.1.6 NO-GO -> resolved. Remaining verdicts
were GO-WITH-CHANGES, all changes applied. Awaiting operator review -> Aprovado.
