# ADR 0013 — Architecture diagrams derive from live code

Status: proposed
Status law: only the operator flips a Status to `accepted` — an agent that writes
`accepted` has violated the law.
Date: 2026-08-27
Supersedes: — · Amends: — · Amended by: —

## Context
The canonical diagrams live as mermaid blocks inside `specs/memory/ARCHITECTURE.md`. Nothing
structurally stops a rename, split or merge from stranding them, and a stale diagram is worse
than none: it is read as current truth by every agent that bootstraps from memory. The guard
therefore derives live names by importing the modules and introspecting them — a hardcoded
expectation list is forbidden, because it would stay green under exactly the sabotage the
guard exists to catch. Its scope is honest and asymmetric: classes and view modules are
checked in both directions, packages forward only, which is why the package map could carry
retired nodes until this release regenerated it.

## Decision
We will keep the architecture diagrams derived from live code: every diagrammed class and
view module is introspected from the package, every live one appears in its diagram, and the
guard fails if the atom, a subsection or a mermaid block goes missing.

## Consequences
+ A rename that skips the diagram fails in CI instead of misleading the next reader.
+ The diagrams are usable as a bootstrap surface, because a green suite means they are current
  in the checked directions.
− The reverse package check does not exist yet, so a retired package node can linger; that gap
  is routed to intake rather than patched here.
− Diagram edits become part of a refactor's diff.

## Confirmation
Measured by: `pytest -p no:cacheprovider tests/contract/test_architecture_diagrams_current.py`
(introspection-derived names; forward and reverse assertions for classes and view modules,
forward-only for packages).
