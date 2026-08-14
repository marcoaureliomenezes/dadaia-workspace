---
title: "bug `picked` ledger event — a reservation marker for Arm B under NO-LOCKS"
status: candidate
opened: 2026-08-14
description: >-
  Created by grill ADR #10/E-4 (2026-08-14 refinement report). TASKS.md has an
  observable reservation marker ([ ] → [-] plus the chore(tasks) commit); the bug
  ledger has no analogue: BugEventKind (core/models/bugs.py:30-40) is a closed 6-kind
  enum (reported, resolved, superseded, deferred, rejected, archived) with no
  reservation event. Under the NO-LOCKS doctrine two agents can pick the same open bug
  with nothing but an advisory presence warning between them — the race is accepted,
  but today it is not even observable in the ledger. The fix is a schema + coherence +
  CLI surface (software-architect + software-engineer), deliberately kept OUT of the
  dd-skills AI-surface release: dd-bug-fix documents today's advisory-presence signal
  only, and this entry owns the primitive.
intents:
  - subject:
      kind: code
      ref: dadaia_workspace/core/models/bugs.py#BugEventKind
    change: >-
      Add a `picked` (reservation) event kind — a NON-terminal annotation, like
      `archived` — so an agent taking an open bug appends an observable event naming
      itself, mirroring the TASKS [-] marker.
  - subject:
      kind: code
      ref: dadaia_workspace/core/models/bugs.py#advance_coherence
    change: >-
      Coherence rules for `picked`: valid only on an open (reported, non-terminated)
      stream; must not count as terminal; define behavior for repeated picks (the
      NO-LOCKS answer: allowed, surfaced — the second pick is visible in the stream,
      never blocked) and for pick-after-terminal (incoherent).
  - subject:
      kind: cli
      ref: bugs append
    change: >-
      `dadaia bugs append --event picked` accepts the reservation fields (who picked,
      optional release/branch note); `dadaia bugs status` surfaces picked-by on open
      bugs; schema bug-event-v1 evolves in lockstep (schema + fold + CLI in one
      change, per the v0.1.72 single-authority law).
---

# bug `picked` ledger event

## Description

See frontmatter. Gap evidence at HEAD:

- `BugEventKind` is a closed `StrEnum` of six kinds (`core/models/bugs.py:30-40`);
  `TERMINAL_EVENTS` covers four; `archived` is the only non-terminal annotation and is
  defined-but-unemitted.
- `advance_coherence` (`core/models/bugs.py:57+`) is the single authority for stream
  coherence (doctor DIAGNOSEs and `BugService.append_event` REFUSEs through the same
  fold) — any new kind must be added there, not beside it.
- The TASKS analogue this mirrors is the `[-]` reservation marker + observable
  `chore(tasks): start <task-id>` commit (dadaia-task-manager protocol).

## Acceptance criteria

`picked` exists in schema, model, fold, and CLI with the coherence semantics above; a
second `picked` on the same open stream is accepted and visible (NO-LOCKS: surfaced,
never blocked); doctor and append can never diverge (one fold); tests pin
open/terminal/reopen interactions; suite green.
