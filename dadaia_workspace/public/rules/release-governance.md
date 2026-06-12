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
- **Push gate = security APPROVE per push-cycle (mechanical).** Every `git push` is
  deterministically gated by the pre-push security-verdict chokepoint: an APPROVED
  `security-reviewer` handoff whose `metrics.commit_sha` equals each pushed ref sha
  must exist on disk. Stale approvals (older sha) do not pass; branch deletions and
  tag-only pushes pass with no verdict. Commits are never review-blocked — only
  pushes.
- **End of each `rc-N`**: the operator chooses to **ship** (push + PR → merge →
  CLOSURE → next release) or **iterate** (open `rc-(N+1)`). Reviews mature the
  release; the push boundary itself is gated by the per-push-cycle security verdict
  above.
- The full review gate ladder (which reviews mechanically gate which lifecycle
  transitions) is codified in v0.1.15.
- This replaces per-task reviewer fan-out; per-task implementer discipline
  (markers, tests, the pre-push CI gate) is unchanged.

## Never push red

A push must never carry code that fails locally-runnable CI checks. The pre-push
CI gate (`dadaia ci preflight`, installed as a git pre-push hook —
`public/scripts/pre-push-ci-gate.sh`) runs `ruff format --check`, `ruff check`,
`mypy --strict`, and `pytest` and blocks the push on any failure. The hook resolves its
runner in order: `$DADAIA_BIN` override → walk up from the repo root to the workspace
venv (`<ws>/.dadaia/.venv/bin/dadaia`) → PATH → repo-local `.venv`; it fails closed
when none is found (`--probe-only` prints the resolved runner). The same pre-push hook
forwards its stdin ref lines to `dadaia ci push-gate-check` — the security-verdict
chokepoint — in addition to (not replacing) the CI preflight.
