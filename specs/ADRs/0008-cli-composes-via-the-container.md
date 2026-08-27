# ADR 0008 — The CLI composes via the container

Status: proposed
Status law: only the operator flips a Status to `accepted` — an agent that writes
`accepted` has violated the law.
Date: 2026-08-27
Supersedes: — · Amends: — · Amended by: —

## Context
The CLI layer had been constructing infrastructure adapters inline — 11 sites at audit time,
with 2 more added unnoticed in a single release: the edge class was growing silently because
each individual verb looked self-contained. Adjudication (ADR-4 of that release) found none
of the edges to be legitimate composition wiring: `container.py` is the sole composition
root, so a verb building its own adapter is duplicated wiring that drifts from it. Two lazy
edges remain (`ci` → process probe, `public` → codex doctor); one more was deleted outright
when `bugs` moved to container-built stores.

## Decision
We will compose the CLI through the container: a verb resolves collaborators from
`container.py` and never imports an `dadaia_workspace.infrastructure` module directly.
Transitive reach through the container is the legal direction; the direct import is the
defect.

## Consequences
+ One wiring site to change when an adapter's construction changes, so verbs cannot drift
  apart in how they build the same thing.
+ Verb tests inject through the container instead of monkeypatching an adapter import.
− Container import cost is paid by the CLI process (which is why hooks are exempted —
  ADR 0012).
− The two remaining edges hold cap budget (ADR 0010) until their DI follow-up lands.

## Confirmation
Measured by: `lint-imports --config setup.cfg --no-cache` — contract `cli-no-infrastructure`
(`allow_indirect_imports = True`; 2 declared `ignore_imports`).
