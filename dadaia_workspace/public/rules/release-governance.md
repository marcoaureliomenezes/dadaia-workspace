---
name: release-governance
description: How bugs and backlog become releases, and how releases mature and are reviewed (alpha/rc cadence). Always active.
always_on: true
---

# release-governance

This rule is always active. It governs how reported bugs and backlog items become
releases, and how releases mature and are reviewed. Full detail: the
`dadaia-release-definition` skill and ADR-1..4 of release v0.1.5.

## Bug & backlog → release

- **`product-engineer` picks** the bug + backlog set, **dispatched by
  `project-manager`** — never self-initiated, never another agent.
- **Bugs are always solved.** Every picked bug is fixed in the release, **unless**
  a picked backlog item supersedes it with a more complete solution — then record
  `superseded_by: <backlog-slug>` in the bug's frontmatter + a SPEC note, and the
  backlog item's TASKS must cover the bug's acceptance. A bug is **never silently
  dropped**.
- **Sanitize continuously.** Stale or invalid bugs/backlog are marked `deferred`
  or `rejected` with a reason. **Never delete** a bug or backlog file.
- **Grill is mandatory.** A `dadaia-grill-me` session on the picked set is required
  **before** the SPEC is written. `project-manager` will not let a
  release-from-backlog reach SPEC without it.

## Release maturity & review cadence

- A release is `major.minor.patch` and matures through `alpha-N → rc-N` segments
  (ADR-1). It is implemented on a single **`feature/{version}`** branch.
- **End of each `alpha-N`**: `qa-engineer` only reviews → a commit on the feature
  branch. No push, no PR, no other reviewers.
- **End of each `rc-N`**: the operator chooses to **ship** (spawn `qa-engineer` +
  `code-reviewer` + `security-reviewer`; all must `APPROVE` → push + PR → merge →
  CLOSURE → next release) or **iterate** (open `rc-(N+1)`).
- This replaces per-task reviewer fan-out; per-task implementer discipline
  (markers, tests, the pre-push CI gate) is unchanged.

## Never push red

A push must never carry code that fails locally-runnable CI checks. The pre-push
CI gate (`dadaia ci preflight`) runs `ruff format --check`, `ruff check`,
`mypy --strict`, and `pytest` and blocks the push on any failure.
