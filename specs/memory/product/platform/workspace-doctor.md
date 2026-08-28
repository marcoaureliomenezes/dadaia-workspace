---
slug: workspace-doctor
title: workspace-doctor
category: product
tldr: Diagnoses root hygiene, venv health, context coherence, slug-ownership collisions, stale presence and lock residue; repairs deterministic state only.
summary: dadaia doctor is the after-the-fact backstop for workspace-state invariants — root law, caches, state layout, venv health, repo coherence, slug ownership and stale presence.
tags: [workspace, doctor, health, repair, privacy]
---

## Checks

- Workspace doctor is the after-the-fact backstop for state and hygiene invariants, alongside `specs doctor`, `backlog doctor` and `public doctor`.
- Each reports: a non-zero exit informs an agent or the operator and never stops work mid-flow.

| Code | Subject |
|---|---|
| `ROOT-1..4` | root whitelist, forbidden repo caches/state, required directories, tool-config placement |
| `VENV-1` | `.dadaia/.venv` Python, pip and dadaia import/entrypoint health |
| `INV-4`, `INV-5`, `CTX-URL-1` | ALIVE/DEAD repository and URL coherence |
| `INV-6` | registry-wide repo-slug ownership uniqueness |
| `PRESENCE-GC` | expired advisory presence records |
| `RETIRED-LOCK-STATE` | legacy `ctx_locks/` or `sessions/runtime/` residue |
| `EFF-1` | overdue efficiency-audit signal |

- `INV-6` folds the registry and reports every `repos/<slug>` owned by more than one context, naming both owners, report-only because choosing the loser is an operator decision ([[context-management]]).
- ROOT-4's allowed-subdirectory set includes the operator-owned `references`, so a reference clone is never flagged.
- `--redact` replaces each foreign Spec Context name and repo slug with a stable `[REDACTED-CONTEXT-<n>]` placeholder at the render boundary.
- `--fix` removes stale presence and retired lock-state trees and repairs deterministic scaffold/state issues, leaving ambiguous or operator-authored material untouched.

## Dependencies

[[context-management]], [[sdd-gate-v3]], [[workspace-init]], [[quality-assurance]].
