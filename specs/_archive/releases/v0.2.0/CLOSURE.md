# Closure: Release — v0.2.0

> **Status:** Aprovado
> **Release ID:** v0.2.0
> **Owner:** product-engineer
> **Closed:** 2026-06-07

## Summary

v0.2.0 delivered the canonical agentic development lifecycle for dadaia-workspace. The release
addressed the root dysfunction that had soft-deadlocked legitimate work: the lock/session
machinery was unsound (semaphore.py with no liveness reclaim, 188-record graveyard), the agent
surface had grown to 15 agents with overlapping roles, and the lifecycle phases and the agents
that own them had never been formally defined together.

The program was executed as four sequenced internal milestones (v0.1.6 → v0.1.9) plus a deploy
milestone, all on a single `feature/0.2.0` branch. Each milestone was implemented, tested, and
gate-reviewed (qa→commit, security→push, code-review→PR) before the next opened. The v0.2.0
integration milestone then bumped `pyproject.toml` to `0.2.0`, ran a full lifecycle dogfood,
eliminated drift across all runtimes, and passed the ship-trio gate, culminating in PR #39
squash-merged to `main` at commit `44757d8` with tag `v0.2.0`. PyPI publication was deferred by
operator decision (see Drifts section).

The soul-and-correctness fold (audit findings D1–D13) was folded before deploy, adding the
stable-session-identity mechanism, the 3-channel report model, dispatcher-purity law, the §0
Identity & Core Concepts section, and a full rewrite of `architecture.md`. The operator
personally confirmed the 5-point /goal identity checklist (AC-17 Gate 1) and approved the §0
prose (AC-17 Gate 2) before CLOSURE proceeded.

## Tasks completed

| Task ID | Description | Final commit |
|---------|-------------|--------------|
| T-016-00 | agents.index.json pre-compilation for RULE D | `feature/0.2.0` |
| T-016-01 | is_stale predicate + lease.py single-record module | `feature/0.2.0` |
| T-016-02 | Unit test suite: is_stale branch table + fail-safe property + exemption matrix | `feature/0.2.0` |
| T-016-03 | Delete Lock-3 + session-writer + semaphore.py enforcement | `feature/0.2.0` |
| T-016-04 | Atomic gate migration: sdd-spec-gate.sh → fail-safe ≤175 lines | `feature/0.2.0` |
| T-016-05 | context.py CLI: remove semaphore acquire + dadaia lock steal | `feature/0.2.0` |
| T-016-06 | service.py + doctor.py: GC integration + single-record invariant | `feature/0.2.0` |
| T-016-07 | TOCTOU interleave test + e2e two-process denial | `feature/0.2.0` |
| T-016-08 | qa-engineer gate (pre-commit) | `feature/0.2.0` |
| T-016-09 | security-reviewer gate (pre-push) | `feature/0.2.0` |
| T-016-10 | code-reviewer gate (pre-PR) + operator in-workspace validation | `feature/0.2.0` |
| T-016-11 | Stable session identity: .ptr file mechanism + short-heartbeat liveness (D1 + OQ-1) | `feature/0.2.0` |
| T-016-12 | E2E yield-iff-live-foreign denial test + short-heartbeat triad (D1 + OQ-1) | `feature/0.2.0` |
| T-016-13 | Gate extension: specs/audits/** ADDITIVE + D6 naming comment (D2/D6) | `feature/0.2.0` |
| T-016-14 | Soul-fold unit tests: exemption matrix extension + stable-identity rows (D1/D2) | `feature/0.2.0` |
| T-016-15 | qa-engineer gate: soul-fold (D1/D2/D6 + OQ-1) | `feature/0.2.0` |
| T-016-16 | security-reviewer gate: soul-fold (D1 + OQ-1) | `feature/0.2.0` |
| T-016-17 | code-reviewer gate: soul-fold (D1/D2/D6) + operator in-workspace validation | `feature/0.2.0` |
| T-017-PRE | Diagnose existing LINT-1 doctor errors (read-only prerequisite) | (no commit) |
| T-017-01 | specs/constitution.md v2 | `feature/0.2.0` |
| T-017-02 | Memory atom authoring + LINT-1 fixes | `feature/0.2.0` |
| T-017-03 | qa-engineer gate (pre-commit) + operator in-workspace validation | `feature/0.2.0` |
| T-017-04 | Constitution §0 + D2/D3/D4/D5/D6-law/D10/D13 soul-fold additions | `feature/0.2.0` |
| T-017-05 | Delete CLOSURE-only duplicates in product-engineer + workspace-protocol (P1a deduplication) | `feature/0.2.0` |
| T-017-06 | qa-engineer gate: soul-fold (D2/D3/D4/D5/D6-law/D10/D13) + extended operator sign-off | `feature/0.2.0` |
| T-018-01 | Author software-engineer.md generic implementer | `feature/0.2.0` |
| T-018-02 | Delete 4 persona files (python/node/backend/researcher) | `feature/0.2.0` |
| T-018-03 | Plugin stubs + skill removals + plugin-scope rule update | `feature/0.2.0` |
| T-018-04 | Deepen 4 coordinator personas | `feature/0.2.0` |
| T-018-05 | Sharpen 3 gate personas + software-architect §1 | `feature/0.2.0` |
| T-018-06 | Bug file annotations | `feature/0.2.0` |
| T-018-07 | Propagation: stage → install --force --target all → doctor exit 0 | `feature/0.2.0` |
| T-018-08 | qa-engineer gate (pre-commit) | `feature/0.2.0` |
| T-018-09 | Operator in-workspace validation + push | `feature/0.2.0` |
| T-019-01 | D-OC-1 audit: confirm zero stale workflow refs | `feature/0.2.0` |
| T-019-02 | Strip stale workflow refs from project-orchestration and any residual personas | `feature/0.2.0` |
| T-019-03 | Delete 7 stale workflow files | `feature/0.2.0` |
| T-019-04 | Author release-ship.workflow.md + audit-fanout.workflow.md | `feature/0.2.0` |
| T-019-05 | Skills text-review: 17 skills — strip dead refs, verify phase mapping, trim slop | `feature/0.2.0` |
| T-019-06 | product/ memory tree restructure + index.md rebuild | `feature/0.2.0` |
| T-019-07 | Final propagation: dadaia public stage && install --force --target all + doctor exit 0 | `feature/0.2.0` |
| T-019-08 | qa-engineer gate (pre-commit) | `feature/0.2.0` |
| T-019-09 | Operator in-workspace validation + push to feature/0.2.0 | `feature/0.2.0` |
| T-020-01 | pyproject bump + full suite + drift-elimination | `feature/0.2.0` |
| T-020-02 | Full lifecycle dogfood on live instance | `feature/0.2.0` |
| T-020-03 | Ship-trio gate: qa + security + code-review APPROVE | `feature/0.2.0` |
| T-020-04 | Single deploy: CI preflight + merge + tag (PyPI DEFERRED) | `44757d8` (merge commit on main) |
| T-020-05 | CLOSURE: memory atoms + CLOSURE.md + archive (D7/D11/D12 soul-fold) | this commit |

## Validations

| Description | Command | Evidence |
|-------------|---------|----------|
| qa-engineer ship-trio APPROVE (T-020-03) | (handoff review) | `.dadaia/handoff/dadaia-workspace/2026-06-06T120000Z-qa-engineer-T-020-03-qa.handoff.json` |
| security-reviewer ship-trio APPROVE (T-020-03) | (handoff review) | `.dadaia/handoff/dadaia-workspace/2026-06-06T120000Z-security-reviewer-T-020-03-security.handoff.json` |
| code-reviewer ship-trio APPROVE (T-020-03) | (handoff review) | `.dadaia/handoff/dadaia-workspace/2026-06-06T180000Z-code-reviewer-T-020-03-codereview.handoff.json` |
| qa-engineer soul-fold review APPROVE (AC-17 Gate 1) | (handoff review) | `.dadaia/handoff/dadaia-workspace/2026-06-07T014922Z-qa-engineer-soul-fold-review.handoff.json` |
| security-reviewer soul-fold push gate APPROVE | (handoff review) | `.dadaia/handoff/dadaia-workspace/2026-06-07T030338Z-security-reviewer-soulfold-pushgate2.handoff.json` |
| Closure audit PASS (D1–D13 verified) | (committed audit) | `specs/audits/20260607T023738Z-782f775d/closure-audit.md` |
| PR #39 squash-merged to main | `git log --oneline main` | `44757d8` |
| Tag v0.2.0 created | `git tag -l v0.2.0` | tag `v0.2.0` @ `44757d8` |

## Drifts

### pypi-publish-deferred

**Description:** The SPEC and integration TASKS.md declared PyPI publication as part of T-020-04's
done criteria. The operator decided to defer the publish after the branch was merged to `main` and
tagged `v0.2.0`. The deploy is therefore local-only: `feature/0.2.0` merged to `main` at `44757d8`,
tag `v0.2.0` created. PyPI was not published; `dadaia==0.2.0` does not appear on pypi.org.

**Resolution:** Operator decision (2026-06-07). T-020-04 is marked `[x]` with a note recording the
deferred scope. A future release (v0.2.1 or v0.3.0) will include the PyPI publish when the operator
elects to proceed. No hotfix is required; the local workspace is fully functional at v0.2.0.

**Memory updates:** No memory file change needed. The deferred PyPI step is a deploy-lifecycle
decision, not a feature-state change. `tech-stack.md` describes the publish mechanism as available
but not required for workspace operation, which remains accurate.

### spec-context-project-atom-added

**Description:** T-020-05 write-set did not originally list `specs/memory/product/philosophy/spec-context-project.md`
as a new atom. The prior product-engineer session (commit `b83e7bf`) added this atom as the keystone
D12 elevation artifact, placing it in `philosophy/` alongside `repos-catalog.md`. This was an
appropriate scope extension — the task spec required D12 elevation and the dedicated atom was the
natural vehicle.

**Resolution:** The atom was committed in the prior session. It is present in memory and reflected
in `index.md`. No corrective action needed.

**Memory updates:** `specs/memory/product/philosophy/spec-context-project.md` (new atom),
`specs/memory/product/index.md` (catalog updated).

## Memory updates

All memory atom updates were committed in commit `b83e7bf` (prior product-engineer session).

- `specs/memory/architecture.md` — full rewrite: 9-agent topology, single JSON TTL-lease model,
  3-channel report model, Spec Context Project as headline concept, no legacy semaphore/Lock-3
  references (D11)
- `specs/memory/product/index.md` — catalog updated: 6 thematic subdirs, spec-context-project
  entry added, test-suite-architecture removed (archived), capability-map Mermaid reflects 9-agent
  topology (D12)
- `specs/memory/product/philosophy/spec-context-project.md` — NEW atom for keystone D12 concept:
  bind→inject→enforce→parallel-multi-project value chain
- `specs/memory/product/sdd/sdd-gate-v3.md` — D7 purge: path-classifier updated, semaphore refs
  removed, audits ADDITIVE noted
- `specs/memory/product/platform/context-management.md` — D7 purge: semaphore/SEM-1/Lock-3
  references removed, TTL-lease + stable-session-identity described
- `specs/memory/product/platform/workspace-doctor.md` — D7 purge: stale semaphore/Lock-3/SEM-1
  references removed, single-record GC behavior described
- `specs/memory/product/agents/agent-sdd-alignment.md` — 9-agent roster with §1 positions,
  sub-agent model described
- `specs/memory/product/agents/agent-orchestration.md` — coordinator + sub-agent architecture,
  ADDITIVE/MUTATING activity classes, dispatcher-purity clause (D3)
- `specs/memory/product/platform/multi-platform-parity.md` — 9-agent / 17-skill / 2-workflow
  surface, plugin stubs noted
- `specs/memory/tech-stack.md` — no change: release did not modify approved technology list
- `specs/_archive/legacy-memory/20260606/test-suite-architecture.md` — legacy atom archived
  (superseded by quality-assurance.md in v0.1.7)

## Backlog returns

No items were pushed to backlog during this release. The PyPI deferred decision is not a backlog
item — it is an operator deployment decision to be revisited at the next release. If the operator
wishes to track the publish explicitly, a bullet should be filed in `specs/backlog/candidates.md
§Hotfixes pendentes` or `ideas.md`.

## Archive decision

**MOVE** — release directory will be moved to `specs/_archive/releases/v0.2.0/` via `git mv`.
`ACTIVE.md` will be updated to `release: none` (no active release after archive).

```
git mv specs/releases/v0.2.0 specs/_archive/releases/v0.2.0
```
