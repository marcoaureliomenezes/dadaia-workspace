# ADR 0004 — `core` is the bottom ring

Status: proposed
Status law: only the operator flips a Status to `accepted` — an agent that writes
`accepted` has violated the law.
Date: 2026-08-27
Supersedes: — · Amends: — · Amended by: —

## Context
The downward-only layering graph was verified clean at the time of the reverse-direction
architecture finding (A3) and was, until then, held by discipline alone — the same posture
that let the lock family rot. An upward import from `core` (to a feature, an adapter, the CLI
or a hook) creates a cycle that no single reviewer sees, because it looks locally reasonable:
a helper needed "just this once". `core` has zero upward edges today, so the rule can be
pinned at zero cost.

## Decision
We will keep `core` the bottom ring: it imports no `dadaia_workspace.features`,
`dadaia_workspace.infrastructure`, `dadaia_workspace.cli` or `dadaia_workspace.hooks`. A
capability `core` appears to need from an upper ring is expressed as a port that the upper
ring implements.

## Consequences
+ The dependency graph stays acyclic in the direction that matters, so `core` is importable
  in isolation — hooks depend on that (ADR 0012).
+ A "shared helper" that would couple two rings is caught at lint time as the design error it
  is, instead of after it has three callers.
− Some duplication or a port definition is the price of a helper that two rings want.

## Confirmation
Measured by: `lint-imports --config setup.cfg --no-cache` — contract `core-no-upper-layers`
(zero `ignore_imports`; the edge class has never been accepted as debt).
