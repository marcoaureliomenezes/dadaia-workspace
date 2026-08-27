# ADR 0019 — Complexity ceilings ratchet down

Status: proposed
Status law: only the operator flips a Status to `accepted` — an agent that writes
`accepted` has violated the law.
Date: 2026-08-27
Supersedes: — · Amends: — · Amended by: —

## Context
The standing order this workspace operates under names the mechanism of its bug loop: a fix
that adds a branch, a flag or a special case to an existing feature breeds the next bug. Line
counts (ADR 0018) do not see that; cyclomatic complexity and nesting depth do — each added
branch is one more path nobody tested. The ceilings are the maxima measured on the tree at
pin time, not aspirations, so they can be enforced honestly today and lowered as decomposition
lands.

## Decision
We will pin cyclomatic complexity and nesting depth at the measured maxima and move them only
downward, recording the justification for a reduction in the reducing release's CLOSURE.

## Consequences
+ A puxadinho fix that adds branches to an already-complex function fails the lint that runs
  in `dadaia ci preflight` before it can be pushed.
+ The ceilings become a visible, monotonically improving score of decomposition progress.
− A pinned maximum measured on a bad function legitimises that function until someone lowers
  the pin; the ratchet direction, not the current value, is the law.
− A genuinely complex algorithm needs a decomposition rather than an exemption.

## Confirmation
Measured by: `ruff check --no-cache dadaia_workspace/` (`C901`, `PLR1702`; ceilings declared in
`pyproject.toml`) — run by `dadaia ci preflight` and the CI lint job.
