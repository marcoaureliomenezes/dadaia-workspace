# Closure: Release — v0.1.12 (SUPERSEDED / ABANDONED)

> **Status:** Aprovado
> **Release ID:** v0.1.12
> **Owner:** product-engineer
> **Closed:** 2026-06-25 (hygiene archival — v0.1.22)

## Summary

v0.1.12 ("Panel Auth Coherence + Memory Truth + Header") was opened 2026-06-11 and left
**`Em revisão`, never completed** — 4 of 21 tasks `[x]`, 15 `[ ]`, 2 `[-]`. Its central
pillar (auth model v2, "cookie session done right") was **superseded** by the operator's
subsequent decision to **remove ALL panel authentication** (loopback bind = the security
boundary, Host-guard only). The secondary goals (browser-viewable memory across all five
surfaces; the header/logo/layout/deep-linking/honest-error UX) were absorbed by later panel
work (the panel memory atom documents in-browser memory rendering + the Kanban/agents/academy
tabs that shipped in subsequent releases).

This file is a **hygiene archival** (v0.1.22): the abandoned, superseded release is moved
out of the live `specs/releases/` tree into `_archive/` so it no longer reads as in-flight.
It is **not** a normal completion — the undelivered tasks are recorded honestly below and
were **not** flipped to `[x]`.

## Tasks completed

Only the 4 tasks already marked `[x]` in TASKS.md were delivered as part of this release's
short life; the remaining 15 `[ ]` + 2 `[-]` were **not delivered under v0.1.12** — the
auth-v2 work was rendered moot by the panel-no-auth decision, and the memory/UX items were
re-scoped into later panel releases. See TASKS.md for the per-task state (left as-is, not
back-filled).

## Validations

| Description | Command | Evidence |
|-------------|---------|----------|
| Archival hygiene — release moved out of the live tree | `git mv specs/releases/v0.1.12 specs/_archive/releases/v0.1.12` | dir now under `_archive/releases/`; `releases/` no longer lists it |
| Spec-tree health after archival | `dadaia specs doctor --specs-dir specs` | exit 0 (no errors) |
| Release completion | n/a — abandoned | **N/A — superseded**; never reached an approved, fully-`[x]` state (4/21 tasks) |
| Auth-v2 pillar disposition | n/a — superseded | **Superseded** by the panel-no-auth rework (all panel auth removed; loopback = boundary) |

## Drifts

None introduced. This archival removes a stale live-release dir (slow drift the operator
asked to clear in the v0.1.22 hygiene sweep). No code, no memory, no dependency change. The
release's original two bug files and any shipped panel behavior live in their own records;
this disposition does not alter them.

## Memory updates

None. No memory atom is written by this archival. The supersession context already lives in
the `panel` memory atom (panel no-auth model) and the auto-memory panel-rework note.

## Disposition

**SUPERSEDED.** Recorded, not deleted (per `release-governance`: never delete a release).
If any sub-goal is still wanted, it should be re-picked into a fresh release via the backlog,
not resurrected here.
