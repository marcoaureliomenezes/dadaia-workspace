---
title: "Dangling panel-runtime-reliability deferral pointer in the bug ledger"
status: candidate
opened: 2026-08-14
description: >-
  v0.8.0 CLOSURE backlog return, materialized 2026-08-14. The bug ledger's deferred
  event for panel-telemetry-sqlite-corrupts-under-concurrent-access (bugs.jsonl line
  202, ts 2026-07-01T23:14:54Z) reads "deferred to backlog panel-runtime-reliability",
  but that backlog slug is terminal: it was consumed by release v0.1.52 and lives only
  at specs/_archive/v0.1.52/consumed-backlog/panel-runtime-reliability.md. No live
  backlog entry carries the slug, so the deferral points at a target that can never
  absorb the bug. The ledger is append-only — the correction is a new clarifying
  event, never a rewrite of the existing line.
intents:
  - subject:
      kind: doc
      ref: memory/product/sdd/sdd-bug-backlog-governance.md#Bugs
    change: >-
      Per the append-only ledger governance this section states, append a clarifying
      event (via dadaia bugs append) to bug
      panel-telemetry-sqlite-corrupts-under-concurrent-access recording that the
      2026-07-01 deferral target (backlog panel-runtime-reliability) was already
      consumed by v0.1.52 at deferral time, and naming the corrected disposition:
      either a live successor backlog entry or the operator's ruling that deferred is
      terminal for this bug. No existing ledger line is modified; the mutation target
      is specs/bugs/bugs.jsonl data, not code.
---

# Dangling `panel-runtime-reliability` deferral pointer in the bug ledger

## Description

See frontmatter. Provenance: `specs/_archive/releases/v0.8.0/CLOSURE.md` §"Backlog
returns", second item (destination `backlog/candidates.md`; SPEC §4 non-goal 4 —
noted by the v0.8.0 deep triage and explicitly not repaired there).

Investigation evidence (2026-08-14, HEAD `c71b21c4`):

- `grep -n "panel-runtime-reliability" specs/bugs/bugs.jsonl` → exactly one hit,
  line 202: the `deferred` event of
  `panel-telemetry-sqlite-corrupts-under-concurrent-access`, reason "deferred to
  backlog panel-runtime-reliability: pragma'd factory unification + DAO lifecycle +
  WAL-aware quarantine".
- The referenced slug exists nowhere in the live backlog. Its only occurrence in the
  tree is `specs/_archive/v0.1.52/consumed-backlog/panel-runtime-reliability.md`
  (plus `specs/_archive/v0.1.52/consumed_backlog.json`) — consumed by v0.1.52.
- The pointer is therefore not a nonexistent *bug-id* but a **terminal backlog
  target**: the deferral parks the bug on an entry that can never be picked again.

## Motivation

Every release pick re-reads open/deferred bugs (DADAIA.md §5 pick precedence). A
deferral whose target is terminal silently exempts the bug from ever resurfacing
through its declared route, while the bug's own undecided state keeps surfacing at
every pick. The ledger should say truthfully where the bug's future work lives.

## Acceptance criteria

- A new ledger event on `panel-telemetry-sqlite-corrupts-under-concurrent-access`
  documents the dangling target and names the corrected disposition route (live
  successor entry, or terminal-deferred per operator decision).
- No pre-existing line of `specs/bugs/bugs.jsonl` is modified (append-only law).
- `dadaia bugs status` and `dadaia specs doctor` remain clean.

## Dependency

The corrected route needs the operator's pending decision on whether `deferred` is
terminal for this bug — routed separately by the same v0.8.0 CLOSURE (third
"Backlog returns" item). This entry materializes the pointer repair regardless of
which way that decision goes.
