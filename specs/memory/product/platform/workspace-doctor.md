---
slug: workspace-doctor
title: workspace-doctor
category: product
tldr: Diagnoses root hygiene, venv health, context coherence, slug-ownership collisions, stale presence and lock residue; repairs deterministic state only.
summary: "`dadaia doctor` is the after-the-fact backstop for workspace-state invariants — root law, caches, state layout, venv health, repo coherence, slug ownership, stale presence and retired lock residue — with `--fix` and `--redact`."
tags:
- workspace
- doctor
- health
- repair
- privacy
---

## Purpose

Workspace doctor is the after-the-fact backstop for state and hygiene invariants. Because
hooks validate only at the publication boundary and never block a human
([[sdd-gate-v3]]), this verb, `specs doctor`, `backlog doctor` and `public doctor` are
where hygiene is actually observed. Each of them **reports**: a non-zero exit informs an
agent or the operator, it never stops work mid-flow.

## Checks

| Code | Subject |
|---|---|
| `ROOT-1..4` | root whitelist, forbidden repo caches/state, required workspace directories, tool configuration placement |
| `VENV-1` | `.dadaia/.venv` Python, pip and dadaia import/entrypoint health |
| `INV-4`, `INV-5`, `CTX-URL-1` | ALIVE/DEAD repository and URL coherence |
| `INV-6` | registry-wide repo-slug ownership uniqueness |
| `PRESENCE-GC` | expired advisory presence records |
| `RETIRED-LOCK-STATE` | legacy `.dadaia/states/ctx_locks/` or `.dadaia/sessions/runtime/` residue |
| `EFF-1` | overdue efficiency-audit signal |

`INV-6` folds the whole registry and reports every `repos/<slug>` owned by more than one
context, main or associated, naming both owners. It is deliberately report-only
(`fixable=False`): choosing which owner loses the slug is an operator decision, and
`context repo remove` already exists to act on it ([[context-management]]).

`.dadaia/references/` is operator-owned and outside the context lifecycle. ROOT-4's
allowed-subdirectory set derives from the single workspace-layout authority in `core` and
includes `references`, so a reference clone is never flagged as slop, garbage-collected,
or treated as a managed context; the legacy quarantine list is computed as its own
candidates minus that set.

## Redacted output

`dadaia doctor --redact` renders every issue with each Spec Context name and repo slug
other than the caller's resolved context replaced by a stable `[REDACTED-CONTEXT-<n>]`
placeholder, ordinal by first appearance. It is opt-in and applies at the render boundary
only; the checks themselves always operate on true names ([[quality-assurance]]).

## Repair

`dadaia doctor --fix` removes stale presence and retired lock-state trees, repairs
deterministic scaffold/state issues, and leaves ambiguous or operator-authored material
untouched. It creates, adopts, steals or releases no lock, because no such runtime
mechanism exists.

## Dependencies

[[context-management]], [[sdd-gate-v3]], [[workspace-init]], [[quality-assurance]].
