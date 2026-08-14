---
slug: workspace-doctor
title: workspace-doctor
category: product
tldr: Diagnoses root hygiene, venv health, context coherence, stale presence, and retired lock-state residue; repairs only deterministic state.
summary: >-
  `dadaia doctor` checks workspace-root law, forbidden caches, required state layout,
  workspace venv health, context repository coherence, repo URLs, stale presence, and
  legacy lock/pointer residue. `--fix` performs bounded deterministic cleanup and
  `--redact` masks foreign Spec Context names in the reported issues.
tags:
- workspace
- doctor
- health
- repair
- privacy
token_estimate: 260
last_updated: '2026-08-14'
release_origin: v0.2.3
---

## Purpose

Workspace doctor is the after-the-fact backstop for state and hygiene invariants that
cannot all be enforced by write hooks.

## Checks

- `ROOT-1..4`: root whitelist, forbidden repo caches/state, required workspace
  directories, and tool configuration placement.
- `VENV-1`: `.dadaia/.venv` Python, pip, and dadaia import/entrypoint health.
- `INV-4`, `INV-5`, `CTX-URL-1`: ALIVE/DEAD repository and URL coherence.
- `PRESENCE-GC`: expired advisory presence records.
- `RETIRED-LOCK-STATE`: any legacy `.dadaia/states/ctx_locks/` or
  `.dadaia/sessions/runtime/` residue.
- `EFF-1`: overdue efficiency-audit signal.

## Redacted Output

`dadaia doctor --redact` renders every issue with each Spec Context name and repo slug
other than the caller's resolved context replaced by a stable `[REDACTED-CONTEXT-<n>]`
placeholder, ordinal by first appearance within the invocation. It exists because
doctor's own diagnostics — stale-presence lines and the ALIVE/DEAD repository coherence
checks — name foreign contexts, and that output gets transcribed into authored documents
([[quality-assurance]]). The flag is opt-in and applies at the render boundary only:
without it the output is unchanged, and the checks themselves always operate on true
names.

## Repair

`dadaia doctor --fix` removes stale presence and retired lock-state trees, repairs
deterministic scaffold/state issues, and leaves ambiguous or operator-authored material
untouched. It never creates, adopts, steals, or releases a concurrency lock because no
such runtime mechanism exists.

## Runtime State

Reads workspace state under `.dadaia/states/` and registered repositories. Repairs are
confined to deterministic workspace-owned state.

## Dependencies

[[context-management]], [[sdd-gate-v3]], [[workspace-init]], [[quality-assurance]].
