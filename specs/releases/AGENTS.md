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
    RELEASE.jsonl            — append-only event stream: phase/defined/implemented/
                                shipped/audited/rc/note (v0.5.0 FR4) — the canonical
                                release+phase record and the closure narrative's home
    reviews/                 — pre-PR review artifacts
    verdicts/                — required-check evidence handoffs
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
  `TASKS.md` → implementation → closure (memory update, closure narrative in
  `RELEASE.jsonl`, disposition sweep, artifact GC, archive — no separate `CLOSURE.md`;
  full arc: `dd-release-implement`'s `RC-FLOW.md`).
- Only one release may be in IMPLEMENTATION phase at a time.

## The active release and its phase (RELEASE.jsonl fold, D3/D7/D11)

**Canonical record: `RELEASE.jsonl`.** The active release's phase is the fold of the
newest `phase` record in the live release's own `specs/releases/<release-id>/RELEASE.jsonl`
(last `phase` record wins) — one file, event-sourced (SPEC FR4). The seven event kinds,
who appends which milestone, and the exact `data` shape per kind: `dd-release-implement`'s
`RELEASE-EVENTS.md` — referenced, not restated.

**No dual-write, no mirror file (v0.5.0 FR4/T-050-21A, A4.1).** The SDD gate resolves
the active release and its phase directly from folding `RELEASE.jsonl`: the ONE
non-archived, non-`_ideas` directory under `releases/` that carries a `RELEASE.jsonl`
is the live release. When no such directory exists, there is no active release — the
honest absence, with no placeholder file to say so.

## `_ideas/` and `_archive/`

`_ideas/<release-id>/` holds a pre-approval Draft (SPEC, and sometimes PLAN/TASKS) before
its release opens for real — it stays MUTATING and is never treated as an evidence root
by any required check; it carries no `RELEASE.jsonl` (a Draft mints no milestone).
`_archive/<release-id>/` is the landing zone for a closed release, moved there by
`git mv` at closure; both bare and legacy `v`-prefixed ids resolve for read-only archive
lookups.
