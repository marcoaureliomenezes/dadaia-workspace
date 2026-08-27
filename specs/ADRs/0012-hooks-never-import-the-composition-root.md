# ADR 0012 — Hooks never import the composition root

Status: proposed
Status law: only the operator flips a Status to `accepted` — an agent that writes
`accepted` has violated the law.
Date: 2026-08-27
Supersedes: — · Amends: — · Amended by: —

## Context
Hooks are one-shot processes on the write hot path: every gated tool call spawns a fresh
interpreter, so module-import cost is paid per write, by the agent, on every single edit. The
container is the composition root — importing it pulls the whole application graph
(~2 s measured) to answer a question `core.specs_resolver` answers in ~10 ms. This workspace
has already shipped that regression once and had to pin the rule afterwards; the six-axis
review of 0.5.0 (F-01) restated it when hooks were sanctioned as direct importers of the
resolution authority (ADR 0009).

## Decision
We will never import the composition root from a hook: hooks reach the single resolution
authority directly, and a deferred function-local container import on a resolution path is
equally forbidden.

## Consequences
+ Gated writes stay fast enough that the gate is invisible to the operator, which is what keeps
  the gate acceptable at all.
+ The hook surface is small and directly importable, so its own tests are cheap.
− Hooks give up container-mediated substitution and must accept the narrow direct dependency
  ADR 0009 sanctions for exactly these three homes.
− Any new collaborator a hook needs has to be reachable without the graph, or not used there.

## Confirmation
Measured by: `pytest -p no:cacheprovider tests/contract/test_hook_import_surface.py` (imports
the six hook modules plus the executed gate path in a fresh interpreter and asserts
`dadaia_workspace.container` is absent from `sys.modules`).
