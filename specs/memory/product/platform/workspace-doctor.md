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

## Checks

Workspace doctor is the after-the-fact backstop for state and hygiene invariants. Because hooks
validate only at the publication boundary and never block a human ([[sdd-gate-v3]]), this verb,
`specs doctor`, `backlog doctor` and `public doctor` are where hygiene is actually observed. Each
**reports**: a non-zero exit informs an agent or the operator, never stopping work mid-flow.

| Code | Subject |
|---|---|
| `ROOT-1..4` | root whitelist, forbidden repo caches/state, required workspace directories, tool configuration placement |
| `VENV-1` | `.dadaia/.venv` Python, pip and dadaia import/entrypoint health |
| `INV-4`, `INV-5`, `CTX-URL-1` | ALIVE/DEAD repository and URL coherence |
| `INV-6` | registry-wide repo-slug ownership uniqueness |
| `PRESENCE-GC` | expired advisory presence records |
| `RETIRED-LOCK-STATE` | legacy `ctx_locks/` or `sessions/runtime/` residue |
| `EFF-1` | overdue efficiency-audit signal |

`INV-6` folds the whole registry and reports every `repos/<slug>` owned by more than one context,
naming both owners; it is deliberately report-only, since choosing which owner loses the slug is an
operator decision ([[context-management]]). `.dadaia/references/` is operator-owned and outside the
context lifecycle: ROOT-4's allowed-subdirectory set includes `references`, so a reference clone is
never flagged as slop.

`--redact` replaces each Spec Context name and repo slug other than the caller's resolved context
with a stable `[REDACTED-CONTEXT-<n>]` placeholder at the render boundary ([[quality-assurance]]).
`--fix` removes stale presence and retired lock-state trees and repairs deterministic scaffold/state
issues, leaving ambiguous or operator-authored material untouched; it creates, adopts, steals or
releases no lock, because no such runtime mechanism exists.

## Dependencies

[[context-management]], [[sdd-gate-v3]], [[workspace-init]], [[quality-assurance]].
