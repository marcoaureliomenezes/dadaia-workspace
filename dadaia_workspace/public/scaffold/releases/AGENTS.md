# specs/releases/ — Release Rules

Scope: this file governs only `specs/releases/`. It replaces the retired
`releases/README.md` (v6 canon, FR1) — its content lives here now.

This directory contains all release directories for this Spec Context Project.

## Structure

```
releases/
  AGENTS.md                  — this file
  <release-id>/               — bare SemVer (e.g. `0.6.0`), the current axis
    SPEC.md                  — release specification (Status: Draft → Aprovado)
    PLAN.md                  — implementation plan (added after SPEC is approved)
    TASKS.md                 — task checklist with [ ]/[-]/[x] markers
    RELEASE.json              — ONE mutable state document: phase/rc/defined/
                                implemented/shipped/audited + an append-only `log`
                                array (v0.5.x FR — the canonical release+phase record
                                and the closure narrative's home)
    verdicts/                — required-check evidence handoffs, deleted once consumed
  _ideas/<release-id>/        — pre-approval drafts; MUTATING, never a trust root
  _archive/releases_histo.jsonl — one summary record per archived release (no
                                per-release directory survives archiving)
```

## Authoring Rules

- Each live release directory is named with a **bare** SemVer id (`^\d+\.\d+\.\d+$`, e.g.
  `0.6.0`) — the canonical current-axis pattern; a `v`-prefixed id is minted nowhere.
  A legacy `v`-prefixed id resolves only in `_archive/releases_histo.jsonl` (read-only
  lookup) — no archived directory exists to resolve to.
- Release directories are created with `dadaia release new <id>` — do NOT create them
  manually to ensure canonical SPEC.md frontmatter.
- SDD lifecycle order: `SPEC.md` (Status: Draft) → operator approval → `PLAN.md` →
  `TASKS.md` → implementation → closure (memory update, closure narrative in
  `RELEASE.json`'s `log`, disposition sweep, artifact GC, archive — no separate
  `CLOSURE.md`; full arc: `dd-release-implement`'s `RC-FLOW.md`).
- Only one release may be in IMPLEMENTATION phase at a time.

## The active release and its phase (RELEASE.json, D3/D7/D11)

**Canonical record: `RELEASE.json`.** The active release's phase is its `phase` field —
read directly, no fold (retires the `RELEASE.jsonl` event stream, SPEC FR4-successor).
Who sets which milestone, and the exact shape per field: `dd-release-implement`'s
`RELEASE-EVENTS.md` — referenced, not restated.

**No dual-write, no mirror file (v0.5.0 FR4/T-050-21A, A4.1).** The SDD gate resolves
the active release and its phase directly from `RELEASE.json`'s `phase` field: the ONE
non-archived, non-`_ideas` directory under `releases/` that carries a `RELEASE.json`
is the live release. When no such directory exists, there is no active release — the
honest absence, with no placeholder file to say so.

## `_ideas/` and `_archive/`

`_ideas/<release-id>/` holds a pre-approval Draft (SPEC, and sometimes PLAN/TASKS) before
its release opens for real — it stays MUTATING and is never treated as an evidence root
by any required check; it carries no `RELEASE.json` (a Draft mints no milestone). Its own
scoped rule: `releases/_ideas/AGENTS.md`. `_archive/releases_histo.jsonl` is the ADDITIVE,
append-only landing zone for a closed release — one summary record per release, appended
at archive time; the release directory itself is deleted, never `git mv`'d — history
survives in git and this record, never a second on-disk copy.
