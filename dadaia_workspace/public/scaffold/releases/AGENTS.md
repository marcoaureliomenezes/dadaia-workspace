# specs/releases/ — Release Rules

Scope: this file governs only `specs/releases/`. It replaces the retired
`releases/README.md` (v6 canon, FR1) — its content lives here now.

This directory contains all release directories for this Spec Context Project.

## Structure

```
releases/
  ACTIVE.md                  — points to the currently active release
  AGENTS.md                  — this file
  <release-id>/               — bare SemVer (e.g. `0.6.0`), the current axis
    SPEC.md                  — release specification (Status: Draft → Aprovado)
    PLAN.md                  — implementation plan (added after SPEC is approved)
    TASKS.md                 — task checklist with [ ]/[-]/[x] markers
    reviews/                 — pre-PR review artifacts
    verdicts/                — required-check evidence handoffs
    CLOSURE.md               — closure report (added after all tasks are done)
  _ideas/<release-id>/        — pre-approval drafts; MUTATING, never a trust root
  _archive/<release-id>/      — archived releases (`v`-prefixed ids resolve here too)
```

## Authoring Rules

- Each live release directory is named with a **bare** SemVer id (`^\d+\.\d+\.\d+$`, e.g.
  `0.6.0`) — the canonical current-axis pattern; a `v`-prefixed id is minted nowhere and
  resolves only archived directories (read-only lookup).
- Release directories are created with `dadaia release new <id>` — do NOT create them
  manually to ensure canonical SPEC.md frontmatter.
- SDD lifecycle order: `SPEC.md` (Status: Draft) → operator approval → `PLAN.md` →
  `TASKS.md` → implementation → `CLOSURE.md`.
- Only one release may be in IMPLEMENTATION phase at a time. The active release is
  declared in `ACTIVE.md`.
- The `ACTIVE.md` format (schema v2):
  ```
  release: <release-id>
  segment: <alpha-N|rc-N>   # optional — present for segmented releases
  phase: <DISCOVERY|DEFINITION|SPEC|PLAN|TASKS|IMPLEMENTATION|CLOSURE|ARCHIVED>
  ```
  The branch, commit and push contract for each SDD stage is the `dd-gitflow-default`
  skill — this file states only the specs-directory layout.

## ACTIVE.md Management

`ACTIVE.md` is managed by `product-engineer`. Agents must read it at the start of every
session to resolve the active release before touching any implementation file. When no
release is active, `ACTIVE.md` must contain `release: none`.

## `_ideas/` and `_archive/`

`_ideas/<release-id>/` holds a pre-approval Draft (SPEC, and sometimes PLAN/TASKS) before
its release opens for real — it stays MUTATING and is never treated as an evidence root
by any required check. `_archive/<release-id>/` is the landing zone for a closed
release, moved there by `git mv` at closure; both bare and legacy `v`-prefixed ids
resolve for read-only archive lookups.
